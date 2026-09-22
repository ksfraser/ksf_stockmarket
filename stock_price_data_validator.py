#!/usr/bin/env python3
"""
stock_price_data_validator.py
================================

Validates stock price data integrity in the central MariaDB stockprices table.
Checks for structural problems, missing recent data, and per-symbol anomalies.
Outputs a report to stdout + optionally to a file.

Usage:
    python3 stock_price_data_validator.py [--output /tmp/price_validation_report.txt]
"""

import os
import sys
import logging
from datetime import date, timedelta
from pathlib import Path

# ── Load DB credentials from .env ────────────────────────────────────────────
ENV_PATH = Path('/home/ksf_stockmarket/ksf_stockmarket/.env')
if not ENV_PATH.exists():
    # Fall back to env vars
    env = os.environ
else:
    env = {}
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip()

DB_HOST = env.get('DB_HOST', 'ksfraser.ca')
DB_PORT = int(env.get('DB_PORT', 3306))
DB_USER = env.get('DB_USER', 'ksfraser_stockmarket')
DB_PASS = env.get('DB_PASS', '')
DB_NAME = env.get('DB_NAME', 'ksfraser_stock_market')
DB_CHARSET = env.get('DB_CHARSET', 'utf8mb4')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('price_validator')


# ── DB connection ────────────────────────────────────────────────────────────
def get_connection():
    import mysql.connector
    return mysql.connector.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASS,
        database=DB_NAME, charset=DB_CHARSET
    )


# ── Structural checks ────────────────────────────────────────────────────────
def check_structural_integrity(cur):
    """Check the table-wide structure for obvious problems."""
    issues = []

    # Total row count
    cur.execute("SELECT COUNT(*) as cnt FROM stockprices WHERE close IS NOT NULL")
    total = cur.fetchone()['cnt']
    logger.info(f"Total price rows (non-null close): {total:,}")

    # Symbols count
    cur.execute("SELECT COUNT(DISTINCT symbol) as cnt FROM stockprices WHERE close IS NOT NULL")
    n_syms = cur.fetchone()['cnt']
    logger.info(f"Distinct symbols: {n_syms}")

    # Negative closes
    cur.execute("SELECT COUNT(*) as cnt FROM stockprices WHERE close < 0")
    neg = cur.fetchone()['cnt']
    if neg > 0:
        issues.append(f"CRITICAL: {neg} rows with negative close prices")
        # Sample them
        cur.execute("SELECT symbol, price_date, close FROM stockprices WHERE close < 0 LIMIT 10")
        samples = cur.fetchall()
        for s in samples:
            issues.append(f"  sample: {s['symbol']} {s['price_date']} close={s['close']}")

    # Zero closes
    cur.execute("SELECT COUNT(*) as cnt FROM stockprices WHERE close = 0")
    zero = cur.fetchone()['cnt']
    if zero > 0:
        issues.append(f"WARNING: {zero} rows with zero close prices")
        cur.execute("SELECT symbol, price_date, close, volume FROM stockprices WHERE close = 0 LIMIT 10")
        samples = cur.fetchall()
        for s in samples:
            issues.append(f"  sample: {s['symbol']} {s['price_date']} close={s['close']} vol={s['volume']}")

    # Zero or negative volume
    cur.execute("SELECT COUNT(*) as cnt FROM stockprices WHERE volume IS NOT NULL AND volume <= 0")
    badvol = cur.fetchone()['cnt']
    if badvol > 0:
        issues.append(f"WARNING: {badvol} rows with zero or negative volume")
        cur.execute("SELECT symbol, price_date, volume FROM stockprices WHERE volume IS NOT NULL AND volume <= 0 LIMIT 10")
        samples = cur.fetchall()
        for s in samples:
            issues.append(f"  sample: {s['symbol']} {s['price_date']} vol={s['volume']}")

    # OHLC violations: open > high, close > high, low > open, low > close
    cur.execute("""
        SELECT COUNT(*) as cnt FROM stockprices
        WHERE open IS NOT NULL AND high IS NOT NULL AND low IS NOT NULL AND close IS NOT NULL
        AND (open > high OR close > high OR low > open OR low > close
             OR high < open OR high < close OR high < low)
    """)
    viol = cur.fetchone()['cnt']
    if viol > 0:
        issues.append(f"CRITICAL: {viol} rows with OHLC constraint violations (open/close > high or low > open/close)")
        cur.execute("""
            SELECT symbol, price_date, open, high, low, close
            FROM stockprices
            WHERE open IS NOT NULL AND high IS NOT NULL AND low IS NOT NULL AND close IS NOT NULL
            AND (open > high OR close > high OR low > open OR low > close
                 OR high < open OR high < close OR high < low)
            LIMIT 10
        """)
        samples = cur.fetchall()
        for s in samples:
            issues.append(f"  sample: {s['symbol']} {s['price_date']} O={s['open']} H={s['high']} L={s['low']} C={s['close']}")

    # Null close on rows that have volume (missing price data)
    cur.execute("SELECT COUNT(*) as cnt FROM stockprices WHERE close IS NULL AND volume IS NOT NULL")
    null_on_vol = cur.fetchone()['cnt']
    if null_on_vol > 0:
        issues.append(f"WARNING: {null_on_vol} rows with volume but null close (missing price data)")
        cur.execute("SELECT symbol, price_date, volume FROM stockprices WHERE close IS NULL AND volume IS NOT NULL LIMIT 10")
        samples = cur.fetchall()
        for s in samples:
            issues.append(f"  sample: {s['symbol']} {s['price_date']} vol={s['volume']}")

    # Suspiciously low volume (> 0 but < 1 — likely decimal error or bad data)
    cur.execute("SELECT COUNT(*) as cnt FROM stockprices WHERE volume IS NOT NULL AND volume > 0 AND volume < 1")
    lowvol = cur.fetchone()['cnt']
    if lowvol > 0:
        issues.append(f"WARNING: {lowvol} rows with positive but sub-1 volume (possible decimal error)")
        cur.execute("SELECT symbol, price_date, volume FROM stockprices WHERE volume IS NOT NULL AND volume > 0 AND volume < 1 LIMIT 10")
        samples = cur.fetchall()
        for s in samples:
            issues.append(f"  sample: {s['symbol']} {s['price_date']} vol={s['volume']}")

    return issues


# ── Per-symbol anomaly checks ────────────────────────────────────────────────
def check_per_symbol_anomalies(conn):
    """Check each symbol for price-range anomalies, missing recent data, etc."""
    issues = []
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT symbol,
               MIN(price_date) as first_date, MAX(price_date) as last_date,
               COUNT(*) as total_rows,
               MIN(close) as min_close, MAX(close) as max_close,
               AVG(close) as avg_close
        FROM stockprices
        WHERE close IS NOT NULL
        GROUP BY symbol
        HAVING total_rows >= 10
        ORDER BY symbol
    """)
    symbols = cur.fetchall()
    logger.info(f"Checking {len(symbols)} symbols with >=10 rows for anomalies...")

    for s in symbols:
        sym = s['symbol']
        total_rows = s['total_rows']
        min_close = s['min_close']
        max_close = s['max_close']
        avg_close = s['avg_close']
        first_date = s['first_date']
        last_date = s['last_date']

        sym_flags = []

        # A) Negative or zero min close
        if min_close < 0:
            sym_flags.append(f"NEGATIVE min close: {min_close:.4f}")
        if min_close == 0:
            sym_flags.append(f"ZERO min close (possible bad data)")

        # B) Extreme price range (>100x) — could be split OR bad data
        if max_close > 0 and min_close > 0 and max_close / min_close > 100:
            sym_flags.append(f"EXTREME range: max/min = {max_close/min_close:.1f}x (min={min_close:.4f}, max={max_close:.2f}) — check for splits or bad data")

        # C) Tiny min close with large range — could be pre-split bad data OR legitimate split
        if 0 < min_close < 0.50 and max_close / min_close > 10:
            sym_flags.append(f"Tiny min close={min_close:.4f} with range {max_close/min_close:.1f}x — possible split artifact or bad decimal data")

        # D) Missing recent data
        cur2 = conn.cursor(dictionary=True)
        cur2.execute("SELECT MAX(price_date) as last FROM stockprices WHERE symbol=%s AND close IS NOT NULL", (sym,))
        last = cur2.fetchone()['last']
        cur2.close()
        if last:
            cutoff = date.today() - timedelta(days=45)  # allow some gap for non-trading
            last_dt = date.fromisoformat(str(last)[:10]) if hasattr(last, 'strftime') else date.today()
            try:
                last_dt = date.fromisoformat(str(last)[:10])
            except:
                last_dt = date.today()
            days_since = (date.today() - last_dt).days
            if days_since > 45:
                sym_flags.append(f"NO DATA in {days_since} days (last: {last}) — possible delisted or data feed broken")

        # E) OHLC violations per symbol
        cur2 = conn.cursor(dictionary=True)
        cur2.execute("""
            SELECT COUNT(*) as cnt FROM stockprices
            WHERE symbol=%s AND open IS NOT NULL AND high IS NOT NULL AND low IS NOT NULL AND close IS NOT NULL
            AND (open > high OR close > high OR low > open OR low > close
                 OR high < open OR high < close OR high < low)
        """, (sym,))
        viol = cur2.fetchone()['cnt']
        cur2.close()
        if viol > 0:
            sym_flags.append(f"{viol} OHLC constraint violations")

        # F) Zero/negative volume
        cur2 = conn.cursor(dictionary=True)
        cur2.execute("""
            SELECT COUNT(*) as cnt FROM stockprices
            WHERE symbol=%s AND volume IS NOT NULL AND volume <= 0
        """, (sym,))
        badvol = cur2.fetchone()['cnt']
        cur2.close()
        if badvol > 0:
            sym_flags.append(f"{badvol} rows with zero/negative volume")

        if sym_flags:
            issues.append(f"{sym} ({total_rows} rows, date range {first_date} to {last_date}, close range {min_close:.4f}–{max_close:.2f}, avg {avg_close:.2f}):")
            for f in sym_flags:
                issues.append(f"  ⚠ {f}")

    return issues


# ── Random sampling check ────────────────────────────────────────────────────
def random_sample_check(cur, n_samples=50):
    """Randomly sample n rows and print them for visual inspection."""
    import random
    logger.info(f"Random sampling {n_samples} rows for visual inspection...")

    cur.execute("""
        SELECT symbol, price_date, open, high, low, close, volume, adj_close, dividend, split_ratio
        FROM stockprices
        WHERE close IS NOT NULL
        ORDER BY RAND() LIMIT %s
    """, (n_samples,))
    rows = cur.fetchall()

    print("\n=== RANDOM SAMPLE ({} rows) ===\n".format(n_samples))
    print(f"{'SYMBOL':<12} {'DATE':<12} {'OPEN':>10} {'HIGH':>10} {'LOW':>10} {'CLOSE':>10} {'VOLUME':>14} {'DIV':>8} {'SPLIT':>8}")
    print("-" * 110)
    for r in rows:
        o = f"{r['open']:.4f}" if r['open'] is not None else "NULL"
        h = f"{r['high']:.4f}" if r['high'] is not None else "NULL"
        l = f"{r['low']:.4f}" if r['low'] is not None else "NULL"
        c = f"{r['close']:.4f}" if r['close'] is not None else "NULL"
        v = f"{r['volume']:,.0f}" if r['volume'] is not None else "NULL"
        d = f"{r['dividend']:.4f}" if r['dividend'] is not None else "NULL"
        sp = f"{r['split_ratio']:.4f}" if r['split_ratio'] is not None else "NULL"
        print(f"{r['symbol']:<12} {str(r['price_date'])[:10]:<12} {o:>10} {h:>10} {l:>10} {c:>10} {v:>14} {d:>8} {sp:>8}")

    return rows


# ── Recent price sanity check (spot-check holdings) ─────────────────────────
def recent_price_sanity(cur):
    """Print latest close for every symbol for a quick sanity look."""
    cur.execute("""
        SELECT symbol, price_date, close, volume, open, high, low
        FROM stockprices
        WHERE (symbol, price_date) IN (
            SELECT symbol, MAX(price_date) FROM stockprices WHERE close IS NOT NULL GROUP BY symbol
        )
        ORDER BY symbol
    """)
    rows = cur.fetchall()

    print(f"\n=== LATEST PRICE PER SYMBOL ({len(rows)} symbols) ===")
    print(f"{'SYMBOL':<12} {'DATE':<12} {'CLOSE':>10} {'VOLUME':>14} {'OPEN':>10} {'HIGH':>10} {'LOW':>10}")
    print("-" * 90)
    for r in rows:
        v = f"{r['volume']:,.0f}" if r['volume'] is not None else "NULL"
        print(f"{r['symbol']:<12} {str(r['price_date'])[:10]:<12} {r['close']:>10.4f} {v:>14} {r['open']:>10.4f} {r['high']:>10.4f} {r['low']:>10.4f}")

    return rows


# ── Main ─────────────────────────────────────────────────────────────────────
def main(output_path=None):
    logger.info("Starting stock price data validation")
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    all_issues = []

    # 1) Structural integrity
    print("\n" + "="*70)
    print("SECTION 1: STRUCTURAL INTEGRITY")
    print("="*70)
    struct_issues = check_structural_integrity(cur)
    if struct_issues:
        print("\nISSUES FOUND:")
        for i in struct_issues:
            print(f"  {i}")
        all_issues.extend(struct_issues)
    else:
        print("\n✓ No structural integrity issues found.")

    # 2) Per-symbol anomalies
    print("\n" + "="*70)
    print("SECTION 2: PER-SYMBOL ANOMALIES")
    print("="*70)
    sym_issues = check_per_symbol_anomalies(conn)
    if sym_issues:
        print("\nISSUES FOUND:")
        for i in sym_issues:
            print(f"  {i}")
        all_issues.extend(sym_issues)
    else:
        print("\n✓ No per-symbol anomalies found.")

    # 3) Random sample
    n = 50
    print("\n" + "="*70)
    print(f"SECTION 3: RANDOM SAMPLE ({n} rows)")
    print("="*70)
    random_sample_check(cur, n)

    # 4) Latest prices
    print("\n" + "="*70)
    print("SECTION 4: LATEST PRICE PER SYMBOL")
    print("="*70)
    recent_price_sanity(cur)

    cur.close()
    conn.close()

    # Summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)
    if all_issues:
        print(f"\n⚠ {len(all_issues)} issue(s) found:")
        for i in all_issues:
            print(f"  - {i}")
    else:
        print("\n✓ No issues found. Data appears clean.")

    # Write to file if requested
    if output_path:
        path = Path(output_path)
        path.write_text("\n".join(all_issues) if all_issues else "No issues found.\n")
        logger.info(f"Report written to {path}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Validate stock price data integrity')
    parser.add_argument('--output', '-o', help='Write report to file')
    args = parser.parse_args()
    main(output_path=args.output)
