#!/usr/bin/env python3
"""
fetch_prices.py — Download OHLCV price data from yfinance for symbols.

Respects 500MB disk budget by fetching incrementally and inserting into
partitioned MySQL stockprices table via the central StockPricesDAO.
Skips symbols already in DB unless explicitly requested with --symbols or
--full-history.

Writes go through CentralStockPricesDAO (python/src/db/stockprice_dao.py),
which handles:
  - INSERT ... ON DUPLICATE KEY UPDATE against ksfraser_stock_market.stockprices
  - Optional dual-write to per-exchange DB (ksfraser_sm_<exchange>.stockprices)
  - The nightly migrate_stockprices stored proc catches any missed rows.

Usage:
    python3 fetch_prices.py [--max 100] [--start-from SYMBOL] [--days N]
                            [--full-history] [--symbols A,B]
"""

import pymysql, yfinance as yf, pandas as pd, re, csv
import sys, os, time, argparse
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from config_loader import Config

# Ensure python/, python/src/ and repo root are importable from any cwd
_script_dir = Path(__file__).resolve().parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))
_src_dir = _script_dir / 'src'
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))
_repo_root = _script_dir.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from src.events.publisher import EventPublisher
from db.stockprice_dao import PriceRow, create_central_stockprice_dao

# ALL yfinance calls MUST resolve through symbol_resolver first.
from symbol_resolver import resolve_for_yfinance, normalize_symbol

# Credentials loaded from Ansible Vault via config_loader, fallback to .env
_cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml')
_cfg = None
try:
    _cfg = Config(_cfg_path) if os.path.exists(_cfg_path) else Config()
except FileNotFoundError:
    _cfg = None


def _load_env_db():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
    if not os.path.exists(env_path):
        return None
    vals = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                vals[k.strip()] = v.strip().strip('"').strip("'")
    return vals


def _load_manifest(path: str) -> dict:
    manifest = {}
    if not os.path.exists(path):
        return manifest
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sym = row.get('symbol')
            if not sym:
                continue
            manifest[sym] = {
                'status': row.get('status', ''),
                'rows': int(row.get('rows', 0) or 0),
                'start_date': row.get('start_date', ''),
                'end_date': row.get('end_date', ''),
                'error': row.get('error', ''),
            }
    return manifest


def _save_manifest(path: str, manifest: dict) -> None:
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['symbol', 'status', 'rows', 'start_date', 'end_date', 'error'])
        for sym in sorted(manifest):
            row = manifest[sym]
            writer.writerow([
                sym,
                row.get('status', ''),
                row.get('rows', 0),
                row.get('start_date', ''),
                row.get('end_date', ''),
                row.get('error', ''),
            ])


def _update_manifest(manifest: dict, sym: str, status: str, rows: int = 0,
                     start_date: str = '', end_date: str = '', error: str = '') -> None:
    manifest[sym] = {
        'status': status,
        'rows': rows,
        'start_date': start_date,
        'end_date': end_date,
        'error': error,
    }


def _build_mysql_config():
    """Build MYSQL config dict from config_loader + .env (mirrors original MYSQL dict)."""
    env = _load_env_db() or {}
    if _cfg is not None:
        password = getattr(_cfg, 'db_password', None) or os.environ.get('DB_PASSWORD') or env.get('DB_PASS') or ''
        return dict(
            host=getattr(_cfg.data, 'db_host', None) or env.get('DB_HOST', 'localhost'),
            user=getattr(_cfg.data, 'db_user', None) or env.get('DB_USER', ''),
            password=password,
            database=getattr(_cfg.data, 'db_name', None) or env.get('DB_NAME', ''),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=20,
            read_timeout=120,
            write_timeout=120,
        )
    # Fallback: pure env
    return dict(
        host=env.get('DB_HOST', 'localhost'),
        user=env.get('DB_USER', ''),
        password=env.get('DB_PASS', ''),
        database=env.get('DB_NAME', ''),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=20,
        read_timeout=120,
        write_timeout=120,
    )


def get_existing_symbols(cur):
    """Return set of symbols that already have price data in the central DB."""
    cur.execute("SELECT DISTINCT symbol FROM stockprices")
    return set(r['symbol'] for r in cur.fetchall())


def get_pending_symbols(cur, existing):
    """Return symbols needing price sync (active in symbol_master, not in stockprices)."""
    cur.execute("SELECT symbol FROM symbol_master WHERE is_active = 1 ORDER BY symbol")
    all_syms = set(r['symbol'] for r in cur.fetchall())
    # Skip synthetic / manually-maintained symbols
    skip = {"BOND_AVG.TO"}
    all_syms -= skip
    return sorted(all_syms - existing)


def is_yfinance_resolvable(sym: str) -> bool:
    """Return False for tickers yfinance consistently cannot resolve."""
    norm = normalize_symbol(sym)
    # Common ETF series suffix patterns on TSX that trip up yfinance
    if re.search(r'\.[A-Z]\.TO$', norm):
        return False
    return True


def _normalize_price_cols(df):
    """Coerce OHLCV column names to the yfinance shape insert_prices expects."""
    if df is None or df.empty:
        return df
    ren = {}
    for c in df.columns:
        cl = str(c).strip().lower()
        if cl in ('open', 'o'):
            ren[c] = 'Open'
        elif cl in ('high', 'h'):
            ren[c] = 'High'
        elif cl in ('low', 'l'):
            ren[c] = 'Low'
        elif cl in ('close', 'c'):
            ren[c] = 'Close'
        elif cl in ('adj close', 'adjclose', 'adjusted close'):
            ren[c] = 'Adj Close'
        elif cl in ('volume', 'v'):
            ren[c] = 'Volume'
    if ren:
        df = df.rename(columns=ren)
    if 'Adj Close' not in df.columns and 'Close' in df.columns:
        df['Adj Close'] = df['Close']
    return df


def _fetch_stooq(norm, start, end):
    """Fallback: fetch daily OHLCV from Stooq via public CSV endpoint (no key)."""
    import io
    import urllib.request
    import urllib.parse
    s = urllib.parse.quote(norm.lower())
    url = f"https://stooq.com/q/d/l/?s={s}.us&i=d"
    try:
        with urllib.request.urlopen(url, timeout=25) as resp:
            raw = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"  stooq: download failed for {norm}: {e}")
        return None
    if not raw or 'Date,Open' not in raw:
        return None
    try:
        df = pd.read_csv(io.StringIO(raw))
    except Exception:
        return None
    if df.empty or 'Date' not in df.columns:
        return None
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    df = df[(df['Date'] >= pd.Timestamp(start)) & (df['Date'] <= pd.Timestamp(end))]
    if df.empty:
        return None
    df = df.set_index('Date').sort_index()
    return _normalize_price_cols(df)


def _fetch_xfinance(norm, start, end):
    """Fallback: fetch via the xfinance drop-in yfinance replacement."""
    try:
        import xfinance as xf
    except Exception:
        return None
    try:
        df = xf.download(norm, start=start, end=end, auto_adjust=False)
    except Exception as e:
        print(f"  xfinance: download failed for {norm}: {e}")
        return None
    if df is None or df.empty:
        return None
    return _normalize_price_cols(df)


def fetch_symbol(sym, start='2014-01-01', end=None):
    """Fetch daily OHLCV with a yfinance -> Stooq -> xfinance fallback chain.

    Returns (DataFrame | None, normalized_symbol). The normalized symbol is the
    ticker actually stored in stockprices so screener/symbol_master joins line up.
    """
    if end is None:
        end = (date.today() + timedelta(days=1)).isoformat()
    norm = normalize_symbol(sym)
    # 1. yfinance (primary)
    try:
        resolved = resolve_for_yfinance(norm)
        hist = yf.Ticker(resolved).history(start=start, end=end, auto_adjust=False)
        if hist is not None and not hist.empty:
            return hist, norm
    except Exception as e:
        print(f"  yfinance: failed for {norm}: {e}")
    # 2. Stooq (free, no key)
    hist = _fetch_stooq(norm, start, end)
    if hist is not None and not hist.empty:
        return hist, norm
    # 3. xfinance (multi-source failover)
    hist = _fetch_xfinance(norm, start, end)
    if hist is not None and not hist.empty:
        return hist, norm
    return None, norm


def insert_prices(dao, sym, hist):
    """Insert OHLCV rows into stockprices via the DAO. Skip existing.

    Builds PriceRow objects from the DataFrame and writes them through the
    central stockprice DAO (which handles INSERT ... ON DUPLICATE KEY UPDATE
    against ksfraser_stock_market.stockprices, with optional dual-write to
    the exchange DB).
    """
    rows = []
    for idx in hist.index:
        row = hist.loc[idx]
        d = idx.strftime('%Y-%m-%d')
        close = row['Close']
        adj = row.get('Adj Close', close)
        if pd.isna(close):
            continue
        rows.append(PriceRow(
            symbol=sym,
            price_date=date.fromisoformat(d),
            open=(Decimal(str(row['Open'])) if pd.notna(row['Open']) else None),
            high=(Decimal(str(row['High'])) if pd.notna(row['High']) else None),
            low=(Decimal(str(row['Low'])) if pd.notna(row['Low']) else None),
            close=Decimal(str(close)),
            volume=(int(row['Volume']) if pd.notna(row['Volume']) else None),
            adj_close=(Decimal(str(adj)) if pd.notna(adj) else Decimal(str(close))),
            currency=None,
            dividend=(Decimal(str(row.get('Dividends', 0))) if pd.notna(row.get('Dividends', 0)) else None),
            split_ratio=(Decimal(str(row.get('Stock Splits', 1))) if pd.notna(row.get('Stock Splits', 1)) else None),
        ))
    if not rows:
        return 0
    return dao.write_prices(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max', type=int, default=None, help='Max symbols to fetch')
    parser.add_argument('--start-from', default=None, help='Start from this symbol')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--full-history', help='Fetch full history from 2014-01-01')
    parser.add_argument('--days', type=int, default=None, help='Fetch only last N days')
    parser.add_argument('--symbols', default=None, help='Comma-separated symbols to force fetch')
    parser.add_argument('--manifest', default=None, help='Path to CSV manifest for resumable fetches')
    args = parser.parse_args()

    # Get the DAO's central connection (a pymysql connection to ksfraser_stock_market).
    dao = create_central_stockprice_dao()
    conn = dao._central_db
    cur = conn.cursor()

    custom_symbols = None
    if args.symbols:
        custom_symbols = [s.strip() for s in args.symbols.split(',') if s.strip()]
        if not custom_symbols:
            custom_symbols = None

    # Determine pending symbol list
    if custom_symbols:
        pending = custom_symbols
        print(f"Force-fetching specified symbols: {len(pending)}")
    else:
        existing = get_existing_symbols(cur)
        print(f"Already have price data for: {len(existing)} symbols")

        if args.full_history or (args.days and args.days > 0):
            cur.execute("SELECT symbol FROM symbol_master WHERE is_active = 1 ORDER BY symbol")
            pending = [r['symbol'] for r in cur.fetchall()]
        else:
            pending = get_pending_symbols(cur, existing)
        if args.start_from:
            pending = [s for s in pending if s >= args.start_from]

    skipped = [s for s in pending if not is_yfinance_resolvable(s)]
    if skipped:
        print(f"Skipping {len(skipped)} known-bad patterns (AMEX:/OTC:/slash/series)")
    pending = [s for s in pending if is_yfinance_resolvable(s)]

    if args.max:
        pending = pending[:args.max]

    # Manifest resumability: skip symbols already marked success
    manifest_path = args.manifest
    manifest = {}
    if manifest_path:
        manifest = _load_manifest(manifest_path)
        already_done = [s for s in pending if manifest.get(s, {}).get('status') == 'success']
        if already_done:
            print(f"Resuming from manifest: skipping {len(already_done)} already-success symbols")
        pending = [s for s in pending if manifest.get(s, {}).get('status') != 'success']

    print(f"Fetching: {len(pending)} symbols")

    # Determine date range
    if args.full_history:
        default_start = '2014-01-01'
        print("Mode: FULL HISTORY (2014-01-01 -> today)")
    elif args.days and args.days > 0:
        default_start = (date.today() - timedelta(days=args.days)).isoformat()
        print(f"Mode: LAST {args.days} DAYS ({default_start} -> today)")
    else:
        default_start = '2014-01-01'
        print("Mode: FULL HISTORY (default)")

    ok, fail, total_rows = 0, 0, 0
    for i, sym in enumerate(pending):
        hist, norm = fetch_symbol(sym, start=default_start)
        if hist is None:
            fail += 1
            if manifest_path:
                _update_manifest(manifest, sym, status='failed', error='no_data')
            if args.verbose:
                print(f"  [{i+1}/{len(pending)}] {sym}: NO DATA")
            time.sleep(1)
            continue

        # Insert via DAO (handles central + optional exchange dual-write).
        n = insert_prices(dao, norm, hist)
        conn.commit()
        ok += 1
        total_rows += n
        start_d = str(hist.index[0])[:10]
        end_d = str(hist.index[-1])[:10]
        print(f"  [{i+1}/{len(pending)}] {norm}: {n} rows ({start_d} -> {end_d})")

        if manifest_path:
            _update_manifest(manifest, sym, status='success', rows=n,
                             start_date=start_d, end_date=end_d)

        # Rate limit: max ~100/hour
        time.sleep(1.5)

        # Publish event (uses the same central connection).
        publisher = EventPublisher(conn)
        try:
            publisher.publish('prices_loaded', {'symbol': norm})
        except Exception:
            pass

        # Update symbol_master data_start / last_updated.
        cur.execute(
            "UPDATE symbol_master SET data_start=%s, last_updated=CURRENT_TIMESTAMP WHERE symbol=%s",
            (hist.index[0].date().isoformat(), norm)
        )
        conn.commit()

    if manifest_path:
        _save_manifest(manifest_path, manifest)
        print(f"Manifest saved to {manifest_path}")

    print(f"\nDone: Fetched {ok} symbols, {fail} failed, {total_rows:,} total rows")

    # Final summary with retry/health-check
    try:
        conn.ping(reconnect=True)
    except Exception:
        try:
            cur.close()
            conn.close()
            new_conn = pymysql.connect(**_build_mysql_config())
            dao._central_db = new_conn
            conn = new_conn
            cur = conn.cursor()
        except Exception as e:
            print(f"WARN: could not reconnect for summary query: {e}")
            return

    try:
        cur.execute("SELECT COUNT(DISTINCT symbol) as cnt FROM stockprices")
        print(f"  Total symbols with prices: {cur.fetchone()['cnt']}")
    except Exception as e:
        print(f"WARN: summary count failed after reconnect: {e}")
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    main()
