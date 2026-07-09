#!/usr/bin/env python3
"""
fetch_prices.py — Download OHLCV price data from yfinance for symbols.

Respects 500MB disk budget by fetching incrementally and inserting into
partitioned MySQL stockprices table. Skips symbols already in DB unless
explicitly requested with --symbols or --full-history.

Usage:
    python3 fetch_prices.py [--max 100] [--start-from SYMBOL] [--days N] [--full-history] [--symbols A,B]
"""
import pymysql, yfinance as yf, pandas as pd, re, csv
import sys, os, time, argparse
from datetime import date, timedelta
from pathlib import Path
from config_loader import Config

# Ensure python/ and repo root are importable from any cwd
_script_dir = Path(__file__).resolve().parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))
_repo_root = _script_dir.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# Try relative first (CWD = python/), fallback to package-style import
from src.events.publisher import EventPublisher

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

if _cfg is not None:
    MYSQL = dict(
        host=_cfg.data.db_host,
        user=_cfg.data.db_user,
        password=_cfg.db_password,
        database=_cfg.data.db_name,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=20,
        read_timeout=120,
        write_timeout=120,
    )
else:
    _env = _load_env_db() or {}
    MYSQL = dict(
        host=_env.get('DB_HOST', 'localhost'),
        user=_env.get('DB_USER', ''),
        password=_env.get('DB_PASS', ''),
        database=_env.get('DB_NAME', ''),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=20,
        read_timeout=120,
        write_timeout=120,
    )


def _retry(fn, label="operation", attempts=4):
    """Reconnect on transient MySQL connection errors, then retry."""
    delay = 1
    last = RuntimeError(f"_retry() failed after {attempts} attempts for {label}")
    for i in range(1, attempts + 1):
        try:
            return fn()
        except Exception as e:
            last = e
            name = type(e).__name__
            if name in ("OperationalError", "InterfaceError"):
                print(f"  WARN {label} attempt {i}/{attempts} failed ({name}), reconnecting in {delay}s...")
                try:
                    conn.ping(reconnect=True)
                except Exception:
                    pass
                time.sleep(delay)
                delay = min(delay * 2, 30)
            else:
                raise
    raise last


def get_existing_symbols(c):
    c.execute("SELECT DISTINCT symbol FROM stockprices")
    return set(r['symbol'] for r in c.fetchall())


def get_pending_symbols(c, existing):
    c.execute("SELECT symbol FROM symbol_master WHERE is_active = 1 ORDER BY symbol")
    all_syms = set(r['symbol'] for r in c.fetchall())
    # Skip synthetic / manually-maintained symbols
    skip = {"BOND_AVG.TO"}
    all_syms -= skip
    return sorted(all_syms - existing)


def is_yfinance_resolvable(sym: str) -> bool:
    """Return False for tickers yfinance consistently cannot resolve."""
    if sym.startswith('AMEX:') or sym.startswith('OTC:') or sym.startswith('NYSE:') or sym.startswith('NASDAQ:'):
        return False
    if '/' in sym:
        return False
    # Common ETF series suffix patterns on TSX that trip up yfinance
    if re.search(r'\.[A-Z]\.TO$', sym):
        return False
    if re.search(r'/PD\.TO$|/PB\.TO$|/PE\.TO$|/PF\.TO$|/PG\.TO$|/PH\.TO$|/PI\.TO$|/PJ\.TO$|/PK\.TO$|/PL\.TO$|/PM\.TO$|/PN\.TO$|/PO\.TO$|/PQ\.TO$|/PS\.TO$|/PT\.TO$', sym):
        return False
    return True


def fetch_symbol(sym, start='2014-01-01', end=None):
    """Fetch daily OHLCV from yfinance. Returns DataFrame or None."""
    if end is None:
        end = (date.today() + timedelta(days=1)).isoformat()
    try:
        hist = yf.Ticker(sym).history(start=start, end=end, auto_adjust=False)
        if hist is None or hist.empty:
            return None
        return hist
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def insert_prices(c, sym, hist):
    """Insert OHLCV rows into stockprices. Skip existing."""
    if not hasattr(insert_prices, '_conn'):
        raise RuntimeError('insert_prices requires conn attribute set by caller')
    rows = []
    for idx, row in hist.iterrows():
        d = idx.strftime('%Y-%m-%d')
        close = row['Close']
        adj = row.get('Adj Close', close)
        if pd.isna(close):
            continue
        rows.append((
            sym,
            d,
            float(row['Open']) if pd.notna(row['Open']) else None,
            float(row['High']) if pd.notna(row['High']) else None,
            float(row['Low']) if pd.notna(row['Low']) else None,
            float(close),
            int(row['Volume']) if pd.notna(row['Volume']) else None,
            float(adj) if pd.notna(adj) else float(close),
            float(row.get('Dividends', 0)) if pd.notna(row.get('Dividends', 0)) else 0,
            float(row.get('Stock Splits', 1)) if pd.notna(row.get('Stock Splits', 1)) else 1,
        ))
    if not rows:
        return 0
    try:
        c.executemany(
            'INSERT IGNORE INTO stockprices (symbol,price_date,open,high,low,close,volume,adj_close,dividend,split_ratio) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
            rows,
        )
    except pymysql.err.InterfaceError:
        insert_prices._conn.ping(reconnect=True)
        c = insert_prices._conn.cursor()
        c.executemany(
            'INSERT IGNORE INTO stockprices (symbol,price_date,open,high,low,close,volume,adj_close,dividend,split_ratio) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
            rows,
        )
    return len(rows)


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

    conn = pymysql.connect(**MYSQL)
    c = conn.cursor()
    insert_prices._conn = conn

    custom_symbols = None
    if args.symbols:
        custom_symbols = [s.strip() for s in args.symbols.split(',') if s.strip()]
        if not custom_symbols:
            custom_symbols = None

    if custom_symbols:
        pending = custom_symbols
        print(f"Force-fetching specified symbols: {len(pending)}")
    else:
        existing = _retry(lambda: get_existing_symbols(c), label="existing symbols")
        print(f"Already have price data for: {len(existing)} symbols")

        if args.full_history or (args.days and args.days > 0):
            c.execute("SELECT symbol FROM symbol_master WHERE is_active = 1 ORDER BY symbol")
            pending = [r['symbol'] for r in c.fetchall()]
        else:
            pending = get_pending_symbols(c, existing)
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
        hist = fetch_symbol(sym, start=default_start)
        if hist is None:
            fail += 1
            if manifest_path:
                _update_manifest(manifest, sym, status='failed', error='no_data')
            if args.verbose:
                print(f"  [{i+1}/{len(pending)}] {sym}: NO DATA")
            time.sleep(1)
            continue

        n = _retry(lambda: insert_prices(c, sym, hist), label=f"insert {sym}")
        conn.commit()
        ok += 1
        total_rows += n
        start_d = str(hist.index[0])[:10]
        end_d = str(hist.index[-1])[:10]
        print(f"  [{i+1}/{len(pending)}] {sym}: {n} rows ({start_d} -> {end_d})")

        if manifest_path:
            _update_manifest(manifest, sym, status='success', rows=n,
                             start_date=start_d, end_date=end_d)

        # Rate limit: max ~100/hour
        time.sleep(1.5)

        publisher = EventPublisher(conn)
        try:
            publisher.publish(
                'prices_loaded',
                {'symbol': sym},
            )
        except Exception:
            pass
        _retry(lambda: c.execute("UPDATE symbol_master SET data_start=%s, last_updated=CURRENT_TIMESTAMP WHERE symbol=%s",
                  (hist.index[0].date().isoformat(), sym)), label=f"update symbol_master {sym}")
        conn.commit()

    if manifest_path:
        _save_manifest(manifest_path, manifest)
        print(f"Manifest saved to {manifest_path}")

    print(f"\n✓ Fetched {ok} symbols, {fail} failed, {total_rows:,} total rows")

    # Final summary with retry/health-check
    try:
        conn.ping(reconnect=True)
    except Exception:
        try:
            conn = pymysql.connect(**MYSQL)
            c = conn.cursor()
        except Exception as e:
            print(f"WARN: could not reconnect for summary query: {e}")
            return

    try:
        c.execute("SELECT COUNT(DISTINCT symbol) as cnt FROM stockprices")
        print(f"  Total symbols with prices: {c.fetchone()['cnt']}")
    except Exception as e:
        print(f"WARN: summary count failed after reconnect: {e}")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
