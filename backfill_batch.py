#!/usr/bin/env python3
"""Batch backfill script for historical price data with retries, rate limiting, and indicator recalculation."""
import subprocess
import sys
import time
import datetime
import os

LOG_FILE = "/home/ksf_stockmarket/ksf_stockmarket/data_fetch_progress.log"
BATCH_SIZE = 10
INDICATOR_INTERVAL = 50
SLEEP_BETWEEN_BATCHES = 30
MAX_RETRIES = 3
END_DATE = "2026-05-31"
START_DATE = "2000-01-01"

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def run_backfill(symbol):
    """Run backfill for a single symbol with retries. Returns (success, error_msg)."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = subprocess.run(
                ["/usr/bin/python3", "python/daily_pipeline.py", "--mode", "backfill",
                 "--symbol", symbol, "--start", START_DATE, "--end", END_DATE],
                capture_output=True, text=True, timeout=300,
                cwd="/home/ksf_stockmarket/ksf_stockmarket"
            )
            if result.returncode == 0:
                return True, ""
            else:
                err = (result.stderr + result.stdout)[:500]
                log(f"  Attempt {attempt}/{MAX_RETRIES} failed for {symbol}: {err}")
        except subprocess.TimeoutExpired:
            log(f"  Attempt {attempt}/{MAX_RETRIES} timed out for {symbol}")
        except Exception as e:
            log(f"  Attempt {attempt}/{MAX_RETRIES} exception for {symbol}: {e}")
        
        if attempt < MAX_RETRIES:
            time.sleep(5 * attempt)
    
    return False, f"Failed after {MAX_RETRIES} retries"

def run_indicators():
    """Recalculate indicators."""
    log("Running indicator recalculation...")
    try:
        result = subprocess.run(
            ["/usr/bin/python3", "python/daily_pipeline.py", "--mode", "indicators"],
            capture_output=True, text=True, timeout=600,
            cwd="/home/ksf_stockmarket/ksf_stockmarket"
        )
        if result.returncode == 0:
            log("Indicators recalculated successfully.")
        else:
            log(f"Indicator recalculation error: {(result.stderr + result.stdout)[:300]}")
    except Exception as e:
        log(f"Indicator recalculation exception: {e}")

def get_remaining_symbols():
    """Get symbols still without data."""
    import pymysql
    conn = pymysql.connect(
        host='ksfraser.ca', user='ksfraser_stockmarket',
        password='Zaqwsx9sm1@', database='ksfraser_stock_market'
    )
    cur = conn.cursor()
    cur.execute("""SELECT symbol FROM symbol_master 
                   WHERE symbol NOT IN (SELECT DISTINCT symbol FROM stockprices) 
                   ORDER BY symbol""")
    symbols = [row[0] for row in cur.fetchall()]
    conn.close()
    return symbols

def main():
    log("=" * 60)
    log("BATCH BACKFILL STARTED")
    log("=" * 60)
    
    symbols = get_remaining_symbols()
    total = len(symbols)
    log(f"Symbols to backfill: {total}")
    
    if not total:
        log("No symbols to backfill. Exiting.")
        return
    
    success_count = 0
    fail_count = 0
    processed_count = 0
    failed_symbols = []
    
    start_time = time.time()
    
    for i, symbol in enumerate(symbols):
        log(f"[{i+1}/{total}] Backfilling {symbol}...")
        ok, err = run_backfill(symbol)
        processed_count += 1
        
        if ok:
            success_count += 1
            log(f"  OK {symbol} done")
        else:
            fail_count += 1
            failed_symbols.append(symbol)
            log(f"  FAIL {symbol} - skipping")
        
        # Every 50 symbols, recalculate indicators
        if processed_count % INDICATOR_INTERVAL == 0:
            elapsed = (time.time() - start_time) / 60
            log(f"--- Progress: {success_count} OK, {fail_count} FAIL, {elapsed:.1f} min elapsed ---")
            run_indicators()
            # After indicators, refresh the list
            symbols = get_remaining_symbols()
            total = len(symbols)
            log(f"Remaining symbols after refresh: {total}")
            if not total:
                break
        
        # Sleep every BATCH_SIZE symbols
        if processed_count % BATCH_SIZE == 0 and processed_count < total:
            log(f"Rate limit: sleeping {SLEEP_BETWEEN_BATCHES}s...")
            time.sleep(SLEEP_BETWEEN_BATCHES)
    
    # Final indicator recalc
    if success_count > 0:
        run_indicators()
    
    elapsed = (time.time() - start_time) / 60
    log("=" * 60)
    log(f"BACKFILL COMPLETE")
    log(f"  Processed: {processed_count}")
    log(f"   Success:   {success_count}")
    log(f"   Failed:    {fail_count}")
    log(f"   Time:      {elapsed:.1f} minutes")
    if failed_symbols:
        log(f"   Failed symbols: {', '.join(failed_symbols)}")
    log("=" * 60)
    
    # Write final state for next agent
    with open("/home/ksf_stockmarket/ksf_stockmarket/last_progress.txt", "w") as f:
        f.write(f"Processed: {processed_count}\n")
        f.write(f"Success: {success_count}\n")
        f.write(f"Failed: {fail_count}\n")
        f.write(f"Failed symbols: {', '.join(failed_symbols)}\n")

if __name__ == "__main__":
    main()
