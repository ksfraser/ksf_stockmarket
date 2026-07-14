"""
Batch cleanup for dead-name symbol_master rows.

Scans symbol_master WHERE name LIKE '%(no data)%', attempts yfinance
enrichment, and updates rows where a real name/exchange/sector can be found.

Writes:
  results/batch_cleanup.log
  results/batch_cleanup_manifest.csv
  results/batch_cleanup_result.json
"""
import sys
import os
import time
import csv
import json
import argparse
import pymysql.cursors
import yfinance as yf
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python', 'src'))
from symbol_resolver import resolve_for_yfinance, _safe_info

DB_CFG = {
    'host': 'ksfraser.ca',
    'port': 3306,
    'user': 'ksfraser_stockmarket',
    'password': 'Zaqwsx9sm1@',
    'database': 'ksfraser_stock_market',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}

RESULTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'results')
PID_FILE = os.path.join(RESULTS_DIR, 'batch_cleanup.pid')
DEFAULT_BATCH = 20
DEFAULT_SLEEP = 5


def set_pid():
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))


def clear_pid():
    try:
        os.remove(PID_FILE)
    except OSError:
        pass


def is_running():
    if not os.path.exists(PID_FILE):
        return False
    try:
        pid = int(open(PID_FILE).read().strip())
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        clear_pid()
        return False


def get_dead_symbols(limit=None):
    conn = pymysql.connect(**DB_CFG)
    try:
        sql = """
            SELECT symbol, exchange, sector, industry
              FROM symbol_master
             WHERE name LIKE '%%(no data)%%'
             ORDER BY symbol
        """
        if limit:
            sql += f" LIMIT {int(limit)}"
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()
    finally:
        conn.close()


def enrich_symbol(symbol, exchange):
    resolved = resolve_for_yfinance(symbol)
    if not resolved or resolved == symbol:
        return None, None, None, None, "skip_resolve"

    try:
        info = _safe_info(resolved)
        if not info:
            return None, None, None, None, "empty_info"
    except Exception as e:
        return None, None, None, None, f"error:{e}"

    name = info.get("shortName") or info.get("longName") or info.get("name")
    if not name or not isinstance(name, str) or not name.strip():
        return None, None, None, None, "no_name"

    name = name.strip()
    sector = info.get("sector")
    industry = info.get("industry")
    ex = info.get("exchange") or info.get("fullExchangeName", "")
    if ex:
        ex = ex.split()[0].upper()
        if ex in ("NYSEMKT", "AMEX"):
            ex = "AMEX"
        elif ex in ("NASDAQ", "NASDAQGM", "NASDAQGS"):
            ex = "NASDAQ"
        elif ex in ("NYSEARCA", "NYSE", "NYSEMKT"):
            ex = "NYSE"
        elif ex in ("TSX", "TSXV", "CVE", "CNQ"):
            ex = "TSX" if ex in ("TSX", "CNQ") else ex
        elif "TO" in ex:
            ex = "TSX"
        elif "HK" in ex:
            ex = "HKEX"
        elif "LON" in ex or "LSE" in ex:
            ex = "LSE"
        elif "ASX" in ex:
            ex = "ASX"
        elif not exchange:
            ex = ex
    return name, ex, sector, industry, "enriched"


def update_symbol_master(symbol, name, exchange, sector, industry):
    conn = pymysql.connect(**DB_CFG)
    try:
        sql = """
            UPDATE symbol_master
               SET name = %s,
                   exchange = COALESCE(%s, exchange),
                   sector = COALESCE(%s, sector),
                   industry = COALESCE(%s, industry),
                   last_updated = NOW()
             WHERE symbol = %s
        """
        with conn.cursor() as cur:
            cur.execute(sql, (name, exchange, sector, industry, symbol))
        conn.commit()
    finally:
        conn.close()


def run(batch_size=DEFAULT_BATCH, sleep_sec=DEFAULT_SLEEP, limit=0):
    if is_running():
        print(json.dumps({"status": "already_running"}))
        sys.exit(0)

    set_pid()
    os.makedirs(RESULTS_DIR, exist_ok=True)

    log_path = os.path.join(RESULTS_DIR, 'batch_cleanup.log')
    manifest_path = os.path.join(RESULTS_DIR, 'batch_cleanup_manifest.csv')
    result_path = os.path.join(RESULTS_DIR, 'batch_cleanup_result.json')

    symbols = get_dead_symbols()
    total = len(symbols)
    updated = 0
    skipped = 0
    errors = []
    start = datetime.utcnow()

    def log(msg):
        line = f"[{datetime.utcnow().isoformat()}] {msg}"
        print(line, flush=True)
        with open(log_path, 'a') as f:
            f.write(line + "\n")

    log(f"Started batch cleanup. pid={os.getpid()} total={total} batch={batch_size} sleep={sleep_sec}s")
    with open(manifest_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["symbol", "resolved", "status", "name", "exchange", "sector", "industry"])

        for idx, row in enumerate(symbols, 1):
            symbol = row['symbol']
            exchange = row.get('exchange')
            log(f"[{idx}/{total}] {symbol}")
            try:
                name, ex, sector, industry, status = enrich_symbol(symbol, exchange)
            except Exception as e:
                status = f"exception:{e}"
                log(f"  exception: {e}")
                with open(manifest_path, 'a', newline='') as mf:
                    csv.writer(mf).writerow([symbol, "", status, "", "", "", ""])
                errors.append(f"{symbol}: {e}")
                skipped += 1
                continue

            if status == "enriched":
                update_symbol_master(symbol, name, ex, sector, industry)
                updated += 1
                log(f"  updated -> {name} | {ex} | {sector} | {industry}")
            else:
                skipped += 1
                log(f"  skip status={status}")

            with open(manifest_path, 'a', newline='') as mf:
                csv.writer(mf).writerow([symbol, "", status, name or "", ex or "", sector or "", industry or ""])

            if idx % batch_size == 0 and idx < total:
                log(f"  sleeping {sleep_sec}s to avoid rate-limit ...")
                time.sleep(sleep_sec)

    summary = {
        "status": "complete",
        "started_at": start.isoformat(),
        "finished_at": datetime.utcnow().isoformat(),
        "total": total,
        "updated": updated,
        "skipped": skipped,
        "errors": errors[:20],
    }
    with open(result_path, 'w') as f:
        json.dump(summary, f, indent=2)

    log(f"Complete. total={total} updated={updated} skipped={skipped}")
    clear_pid()
    print(json.dumps(summary))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Batch cleanup dead-name symbol_master rows")
    parser.add_argument("--batch", type=int, default=DEFAULT_BATCH, help="Batch size between sleeps")
    parser.add_argument("--sleep", type=int, default=DEFAULT_SLEEP, help="Seconds to sleep between batches")
    parser.add_argument("--status", action="store_true", help="Check if already running")
    parser.add_argument("--limit", type=int, default=0, help="Max rows to process (0 = all)")
    args = parser.parse_args()

    if args.status:
        sys.exit(0 if is_running() else 1)
    else:
        run(args.batch, args.sleep, args.limit)
