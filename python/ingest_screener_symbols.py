#!/usr/bin/env python3
"""
Ingest TradingView screener results into stockmarket core tables.

Reads latest tradingview_screener_results, upserts symbols into
symbol_master, and triggers price/indicator updates for changed symbols.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

import pymysql
import sys
from pathlib import Path

# Ensure python/src/ is importable so we can reuse the shared symbol normalizer
_src_dir = Path(__file__).resolve().parent / 'src'
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

# Ensure the repo root is importable so `import python.db_connector` works
# regardless of how this script is invoked (e.g. `python3
# python/ingest_screener_symbols.py` would otherwise only put `python/` on
# sys.path, not the repo root). tv_screener.py works because it lives at the
# repo root; this script lives inside python/.
_repo_root = Path(__file__).resolve().parents[1]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
from symbol_resolver import normalize_symbol

TRADING_VIEW_TABLE = "tradingview_screener_results"
SYMBOL_MASTER_TABLE = "symbol_master"
STOCK_PRICES_TABLE = "stockprices"
# Use actual MySQL table from compute_all_talib_indicators.py
TECH_TABLE = "ta_indicators"

# Credentials are resolved at connect time from config.yaml (vault) / environment
# via python.db_connector — no hardcoded secrets in source.
BASE_CONFIG = None  # deprecated; _connect() uses db_connector

REPO_ROOT = Path(__file__).resolve().parents[1]
FETCH_PRICES_SCRIPT = REPO_ROOT / "python" / "fetch_prices.py"


def _connect():
    # Resolve credentials the same way the screener does (config.yaml vault /
    # environment) so we never fall back to a stale hardcoded password.
    import python.db_connector as _dc
    if not _dc.DB_CONFIG:
        _dc._init_config()
    cfg = _dc.DB_CONFIG
    return pymysql.connect(
        host=cfg.get("host"),
        port=cfg.get("port"),
        user=cfg.get("user"),
        password=cfg.get("password"),
        database=cfg.get("database"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def _latest_run(conn) -> Dict:
    """
    Find the latest logical screener run and return the full time window
    containing every row written during that run.

    The screener inserts each preset's rows with NOW(), so a single logical
    run spans a few seconds across multiple presets. We take the newest run_at
    and expand a short trailing window (2 minutes) to capture the entire run
    without bleeding into the previous scheduled run (which is >= 15 minutes
    earlier). The previous implementation used `run_at = MAX(run_at)`, so it
    ingested only the single newest second (typically a handful of rows)
    instead of the whole run.
    """
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT MAX(run_at) AS max_run FROM {TRADING_VIEW_TABLE}"
        )
        row = cur.fetchone()
        max_run = row.get("max_run") if isinstance(row, dict) else (row[0] if row else None)
        if not max_run:
            return {}
        cur.execute(
            f"""
            SELECT MIN(run_at) AS window_start, MAX(run_at) AS window_end,
                   COUNT(*) AS row_count
            FROM {TRADING_VIEW_TABLE}
            WHERE run_at >= %s - INTERVAL 2 MINUTE AND run_at <= %s
            """,
            (max_run, max_run),
        )
        window = cur.fetchone()
        if not window:
            return {}
        start = (window.get("window_start") if isinstance(window, dict) else window[0]) or max_run
        end = (window.get("window_end") if isinstance(window, dict) else window[1]) or max_run
        return {"window_start": start, "window_end": end, "row_count": window.get("row_count") if isinstance(window, dict) else window[2]}


def _results_for_run(conn, window_start, window_end) -> List[Dict]:
    """Return all rows whose run_at falls within the latest batch window."""
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT preset_name, market, symbol, data FROM {TRADING_VIEW_TABLE} "
            "WHERE run_at >= %s AND run_at <= %s",
            (window_start, window_end),
        )
        rows = cur.fetchall()
        results = []
        for row in rows:
            payload = row.get("data")
            if isinstance(payload, str):
                payload = json.loads(payload)
            results.append({
                "preset_name": row.get("preset_name"),
                "market": row.get("market"),
                "symbol": row.get("symbol"),
                "payload": payload or {},
            })
        return results


def _existing_symbols(conn) -> Set[str]:
    with conn.cursor() as cur:
        cur.execute(f"SELECT symbol FROM {SYMBOL_MASTER_TABLE}")
        return {row["symbol"] for row in cur.fetchall()}


def _upsert_symbol_master(conn, items: Iterable[Tuple[str, Dict]]) -> int:
    now = datetime.now().isoformat()
    updated = 0
    with conn.cursor() as cur:
        for symbol, payload in items:
            cur.execute(
                f"""
                INSERT INTO {SYMBOL_MASTER_TABLE} (symbol, name, exchange, sector, industry, last_updated)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  name = VALUES(name),
                  sector = VALUES(sector),
                  industry = VALUES(industry),
                  last_updated = VALUES(last_updated)
                """,
                (
                    symbol,
                    payload.get("name"),
                    payload.get("exchange"),
                    payload.get("sector"),
                    payload.get("industry"),
                    now,
                ),
            )
            updated += cur.rowcount
    conn.commit()
    return updated


def _pending_price_symbols(
    conn, candidates: Iterable[str]
) -> Tuple[List[str], Dict[str, str]]:
    """Return symbols needing price sync and their sources.

    A symbol is pending when:
      * stockprices is missing the latest expected date, or
      * technical_indicators is older than the latest price date, or
      * the symbol is new to stockprices.
    """
    today = datetime.now().date().isoformat()
    need_price: List[str] = []
    source_map: Dict[str, str] = {}
    with conn.cursor() as cur:
        for sym in candidates:
            cur.execute(
                f"SELECT MAX(price_date) AS price_date FROM {STOCK_PRICES_TABLE} WHERE symbol = %s",
                (sym,),
            )
            price_row = cur.fetchone()
            latest_price = price_row.get("price_date") if price_row else None

            if latest_price is not None and str(latest_price) == today:
                continue

            cur.execute(
                f"SELECT MAX(price_date) AS indicator_date FROM ta_indicators WHERE symbol = %s",
                (sym,),
            )
            indicator_row = cur.fetchone()
            latest_indicator = indicator_row.get("indicator_date") if indicator_row else None

            if latest_price != latest_indicator:
                need_price.append(sym)
                source_map[sym] = "screener" if latest_price is None else "stale-price"
    return need_price, source_map


def _trigger_price_sync(symbols: List[str]) -> bool:
    if not symbols:
        return True
    if not FETCH_PRICES_SCRIPT.exists():
        return False

    # Fetch exactly the screened symbols that need prices. Batch into chunks of
    # 50 so a large pending set (the full screener run can surface hundreds of
    # symbols) is fully synced instead of being silently truncated at 50.
    ok = True
    for i in range(0, len(symbols), 50):
        chunk = symbols[i:i + 50]
        cmd = [
            sys.executable,
            str(FETCH_PRICES_SCRIPT),
            "--symbols",
            ",".join(chunk),
        ]
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(REPO_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=1800,
            )
            if proc.returncode != 0:
                ok = False
                print(f"Price sync chunk failed (rc={proc.returncode}): {proc.stderr[:500]}")
        except Exception as exc:
            print(f"Price sync failed: {exc}")
            ok = False
    return ok


def main() -> int:
    print(f"[{datetime.now().isoformat()}] Screener ingestion start")

    conn = _connect()
    try:
        latest = _latest_run(conn)
        if not latest:
            print("No screener results found")
            return 0

        print(f"Latest run window: {latest.get('window_start')} → {latest.get('window_end')} ({latest.get('row_count')} rows)")
        rows = _results_for_run(conn, latest.get("window_start"), latest.get("window_end"))
        print(f"Loaded {len(rows)} screener rows")

        # Normalize symbols (strip AMEX:/OTC: prefixes, '/'-preferred, class '.')
        # so symbol_master, the screener view, and stockprices all share the
        # yfinance-resolvable ticker and joins line up.
        candidates = {}
        for r in rows:
            raw = r.get("symbol")
            if not raw:
                continue
            norm = normalize_symbol(raw)
            candidates[norm] = r.get("payload") or {}
            if norm != raw:
                with conn.cursor() as cur:
                    # A canonical (preset_name, market, norm) row may already
                    # exist: TradingView often emits the same security under two
                    # spellings across runs (e.g. 'SF/PB' and 'SF-PB'). Folding
                    # the fresh raw payload into the canonical row and dropping
                    # the redundant variant keeps the unique key intact without
                    # losing screening data.
                    cur.execute(
                        f"SELECT id FROM {TRADING_VIEW_TABLE} "
                        "WHERE preset_name=%s AND market=%s AND symbol=%s",
                        (r.get("preset_name"), r.get("market"), norm),
                    )
                    canon = cur.fetchone()
                    if canon:
                        cur.execute(
                            f"UPDATE {TRADING_VIEW_TABLE} SET data=%s, run_at=NOW() "
                            "WHERE id=%s",
                            (json.dumps(r.get("payload") or {}), canon["id"]),
                        )
                        cur.execute(
                            f"DELETE FROM {TRADING_VIEW_TABLE} "
                            "WHERE preset_name=%s AND market=%s AND symbol=%s",
                            (r.get("preset_name"), r.get("market"), raw),
                        )
                    else:
                        cur.execute(
                            f"UPDATE {TRADING_VIEW_TABLE} SET symbol=%s "
                            "WHERE preset_name=%s AND market=%s AND symbol=%s",
                            (norm, r.get("preset_name"), r.get("market"), raw),
                        )
        conn.commit()
        if not candidates:
            print("No valid candidate symbols")
            return 0

        existing = _existing_symbols(conn)
        new_symbols = {sym for sym in candidates if sym not in existing}
        updated_symbols = _upsert_symbol_master(conn, list(candidates.items()))
        print(f"Symbol master: {len(new_symbols)} new, {updated_symbols - len(new_symbols)} updated (total rows affected: {updated_symbols})")

        pending, source_map = _pending_price_symbols(conn, candidates.keys())
        if not pending:
            print("Price/indicators already up to date")
            return 0

        print(f"Triggering price sync for {len(pending)} symbols")
        ok = _trigger_price_sync(pending)
        if ok:
            print("Price sync completed")
        else:
            print("Price sync completed with warnings")
    except Exception as exc:
        print(f"Ingestion error: {exc}")
        return 1
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
