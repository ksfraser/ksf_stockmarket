#!/usr/bin/env python3
"""
correlation_analysis.py — Signal Correlation & Lead/Lag Analysis
=================================================================
Analyzes correlations between TA signals and future price returns.
Updates the signal_weights table with correlation metrics, lead/lag data,
and boosted weights.

Pipeline:
  1. get_signal_fire_dates()  — Find dates when a signal fired
  2. compute_lead_lag()       — Lead/lag between two signals + conditional win rates
  3. compute_correlation_matrix() — Per-signal correlation with future 5-day return
  4. update_signal_weights()  — Write results to signal_weights table
  5. run_correlation_analysis() — Main loop over all symbols

Usage:
  python3 correlation_analysis.py                    # All active symbols
  python3 correlation_analysis.py --symbols AAPL,MSFT,RY.TO
  python3 correlation_analysis.py --lookback 500
"""

import argparse
import json
import logging
import sys
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import mysql.connector
from mysql.connector import Error as MySQLError
import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# Configuration — mirrors ta_calculator.py / scoring_engine.py DB_CONFIG
# --------------------------------------------------------------------------
DB_CONFIG = {
    'host': 'localhost',
    'user': 'ksf_stockmarket',
    'password': 'change_me',
    'database': 'ksf_stockmarket',
    'charset': 'utf8mb4',
    'use_unicode': True,
    'autocommit': False,
}

LOOKBACK_DAYS = 250          # Default lookback for signal fire date queries
FUTURE_RETURN_DAYS = 5       # Forward window for return correlation
MIN_OVERLAP_DATES = 10       # Minimum shared fire dates for lead/lag computation
MIN_SIGNAL_OCCURRENCES = 5   # Minimum times a signal must fire to be scored

# Boost formula: effective_weight = base_weight * (1 + correlation * 0.5) * recency_factor
BOOST_CORR_MULTIPLIER = 0.5
PRE_INDICATOR_MIN_LEAD = 2   # avg_lead_days > 2
PRE_INDICATOR_MIN_CORR = 0.3  # correlation > 0.3

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


# ==========================================================================
# DATABASE HELPERS
# ==========================================================================

def get_connection():
    """Get a MariaDB connection."""
    return mysql.connector.connect(**DB_CONFIG)


def get_active_symbols(conn, symbols: Optional[List[str]] = None) -> List[str]:
    """Get list of active symbols from stockinfo."""
    cursor = conn.cursor()
    if symbols:
        format_strings = ','.join(['%s'] * len(symbols))
        cursor.execute(f"""
            SELECT stocksymbol FROM stockinfo
            WHERE stocksymbol IN ({format_strings})
            ORDER BY stocksymbol
        """, tuple(symbols))
    else:
        cursor.execute("""
            SELECT stocksymbol FROM stockinfo s
            WHERE EXISTS (
                SELECT 1 FROM stockprices p
                WHERE p.symbol = s.stocksymbol
                AND p.price_date >= DATE_SUB(CURDATE(), INTERVAL 5 DAY)
            )
            ORDER BY s.stocksymbol
        """)
    result = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return result


def fetch_price_data(conn, symbol: str, lookback: int = LOOKBACK_DAYS) -> pd.DataFrame:
    """Fetch OHLCV data for a symbol as a DataFrame indexed by price_date."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT price_date, day_open, day_high, day_low, day_close, volume
        FROM stockprices
        WHERE symbol = %s
          AND price_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        ORDER BY price_date ASC
    """, (symbol, lookback + FUTURE_RETURN_DAYS))
    rows = cursor.fetchall()
    cursor.close()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df['price_date'] = pd.to_datetime(df['price_date'])
    df.set_index('price_date', inplace=True)
    for col in ('day_open', 'day_high', 'day_low', 'day_close', 'volume'):
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


# ==========================================================================
# 1. SIGNAL FIRE DATE EXTRACTION
# ==========================================================================

def get_signal_fire_dates(
    conn,
    symbol: str,
    signal_type: str,
    lookback_days: int = LOOKBACK_DAYS
) -> List[date]:
    """
    Find all dates when a specific signal fired for a given signal_type.

    Queries two sources:
      A) ta_values — individual indicator signals where signal IN ('BUY','SELL')
         and the indicator name matches signal_type.
      B) daily_tier2 — summary signals where signal_reasons contains the
         signal_type code (comma-separated).

    Returns a sorted list of datetime.date objects.
    """
    fire_dates: set = set()

    # --- Source A: ta_values ---
    cursor = conn.cursor()
    cursor.execute("""
        SELECT price_date
        FROM ta_values
        WHERE symbol = %s
          AND indicator = %s
          AND signal IN ('BUY', 'SELL')
          AND price_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        ORDER BY price_date ASC
    """, (symbol, signal_type, lookback_days))
    for row in cursor.fetchall():
        fire_dates.add(row[0])

    # --- Source B: daily_tier2 (signal_reasons is comma-separated) ---
    cursor.execute("""
        SELECT price_date
        FROM daily_tier2
        WHERE symbol = %s
          AND signal_reasons IS NOT NULL
          AND (
              signal_reasons = %s
              OR signal_reasons LIKE CONCAT(%s, ',%%')
              OR signal_reasons LIKE CONCAT('%%,', %s, ',%%')
              OR signal_reasons LIKE CONCAT('%%,', %s)
          )
          AND price_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        ORDER BY price_date ASC
    """, (symbol, signal_type, signal_type, signal_type, signal_type, lookback_days))
    for row in cursor.fetchall():
        fire_dates.add(row[0])

    cursor.close()

    sorted_dates = sorted(fire_dates)
    logger.debug(
        f"  [{symbol}] Signal '{signal_type}' fired {len(sorted_dates)} times "
        f"in last {lookback_days}d"
    )
    return sorted_dates


# ==========================================================================
# 2. LEAD / LAG COMPUTATION
# ==========================================================================

def compute_lead_lag(
    conn,
    symbol: str,
    signal_a: str,
    signal_b: str
) -> Dict:
    """
    Compute the average lead/lag in days between two signal types.

    For each occurrence of signal A, find the nearest signal B within a
    forward window of FUTURE_RETURN_DAYS * 2. The lead is positive when B
    fires after A (A leads B).

    Also computes conditional win rates:
      - P(profit | A→B sequence)
      - P(profit | A alone)
      - P(profit | B alone)

    Returns dict:
      {
        avg_lead_days: float,
        seq_win_rate: float,
        a_win_rate: float,
        b_win_rate: float,
        correlation: float
      }
    """
    result = {
        'avg_lead_days': 0.0,
        'seq_win_rate': 0.0,
        'a_win_rate': 0.0,
        'b_win_rate': 0.0,
        'correlation': 0.0,
    }

    # Get fire dates
    dates_a = get_signal_fire_dates(conn, symbol, signal_a)
    dates_b = get_signal_fire_dates(conn, symbol, signal_b)

    if len(dates_a) < MIN_SIGNAL_OCCURRENCES or len(dates_b) < MIN_SIGNAL_OCCURRENCES:
        logger.debug(
            f"  [{symbol}] Insufficient data for {signal_a} ({len(dates_a)}) "
            f"or {signal_b} ({len(dates_b)}), skipping lead/lag"
        )
        return result

    # Fetch price data for win-rate computation
    df = fetch_price_data(conn, symbol)
    if df.empty or len(df) < FUTURE_RETURN_DAYS + 10:
        return result

    set_b = set(dates_b)

    # --- Lead/lag computation ---
    lead_days_list = []
    seq_profits = []
    a_profits = []
    b_profits = []

    search_window = FUTURE_RETURN_DAYS * 2  # Look up to 10 days ahead

    for d_a in dates_a:
        # Find nearest B after A
        best_lead = None
        for offset in range(0, search_window + 1):
            candidate = d_a + timedelta(days=offset)
            # Skip weekends — find next trading day
            if candidate in set_b:
                best_lead = offset
                break

        if best_lead is not None:
            lead_days_list.append(best_lead)

            # Compute profit for A→B sequence: return from A fire to A+5d
            try:
                idx_a = df.index.get_loc(d_a)
                if isinstance(idx_a, slice):
                    idx_a = idx_a.start
                if idx_a + FUTURE_RETURN_DAYS < len(df):
                    ret = (
                        df.iloc[idx_a + FUTURE_RETURN_DAYS]['day_close']
                        - df.iloc[idx_a]['day_close']
                    ) / df.iloc[idx_a]['day_close']
                    seq_profits.append(1 if ret > 0 else 0)
            except (KeyError, IndexError):
                pass

        # Compute profit for A alone
        try:
            idx_a = df.index.get_loc(d_a)
            if isinstance(idx_a, slice):
                idx_a = idx_a.start
            if idx_a + FUTURE_RETURN_DAYS < len(df):
                ret = (
                    df.iloc[idx_a + FUTURE_RETURN_DAYS]['day_close']
                    - df.iloc[idx_a]['day_close']
                ) / df.iloc[idx_a]['day_close']
                a_profits.append(1 if ret > 0 else 0)
        except (KeyError, IndexError):
            pass

    # Compute profit for B alone
    for d_b in dates_b:
        try:
            idx_b = df.index.get_loc(d_b)
            if isinstance(idx_b, slice):
                idx_b = idx_b.start
            if idx_b + FUTURE_RETURN_DAYS < len(df):
                ret = (
                    df.iloc[idx_b + FUTURE_RETURN_DAYS]['day_close']
                    - df.iloc[idx_b]['day_close']
                ) / df.iloc[idx_b]['day_close']
                b_profits.append(1 if ret > 0 else 0)
        except (KeyError, IndexError):
            pass

    # --- Aggregate ---
    if lead_days_list:
        result['avg_lead_days'] = round(float(np.mean(lead_days_list)), 1)

    if seq_profits:
        result['seq_win_rate'] = round(float(np.mean(seq_profits)), 4)
    if a_profits:
        result['a_win_rate'] = round(float(np.mean(a_profits)), 4)
    if b_profits:
        result['b_win_rate'] = round(float(np.mean(b_profits)), 4)

    # Correlation: binary fire/no-fire vectors over the lookback window
    result['correlation'] = _binary_signal_correlation(dates_a, dates_b)

    logger.debug(
        f"  [{symbol}] {signal_a}→{signal_b}: "
        f"lead={result['avg_lead_days']}d, "
        f"seq_wr={result['seq_win_rate']}, "
        f"corr={result['correlation']}"
    )
    return result


def _binary_signal_correlation(dates_a: List[date], dates_b: List[date]) -> float:
    """
    Compute Pearson correlation between two binary signal vectors.
    Build aligned date ranges and correlate fire (1) / no-fire (0) vectors.
    """
    if not dates_a or not dates_b:
        return 0.0

    all_dates = sorted(set(dates_a) | set(dates_b))
    if len(all_dates) < MIN_OVERLAP_DATES:
        return 0.0

    set_a = set(dates_a)
    set_b = set(dates_b)

    vec_a = np.array([1.0 if d in set_a else 0.0 for d in all_dates])
    vec_b = np.array([1.0 if d in set_b else 0.0 for d in all_dates])

    std_a = vec_a.std()
    std_b = vec_b.std()
    if std_a == 0 or std_b == 0:
        return 0.0

    corr = float(np.corrcoef(vec_a, vec_b)[0, 1])
    if np.isnan(corr):
        return 0.0
    return round(corr, 4)


# ==========================================================================
# 3. CORRELATION MATRIX
# ==========================================================================

def compute_correlation_matrix(
    conn,
    symbol: str
) -> Dict[str, float]:
    """
    Compute per-signal correlation with the future 5-day return.

    For each signal type that fired in the lookback window, build a binary
    vector (1 = fired, 0 = didn't fire) aligned with the price DataFrame.
    Correlate this with the forward 5-day return at each date.

    Returns dict: {signal_type: correlation_with_future_return}
    """
    correlations: Dict[str, float] = {}

    # Fetch price data
    df = fetch_price_data(conn, symbol)
    if df.empty or len(df) < MIN_SIGNAL_OCCURRENCES + FUTURE_RETURN_DAYS:
        logger.debug(f"  [{symbol}] Insufficient price data ({len(df)} rows)")
        return correlations

    # Compute future 5-day return for each date
    df['future_5d_ret'] = df['day_close'].pct_change(periods=FUTURE_RETURN_DAYS).shift(-FUTURE_RETURN_DAYS)

    # Get all distinct signal types that fired for this symbol
    cursor = conn.cursor()

    # From ta_values
    cursor.execute("""
        SELECT DISTINCT indicator
        FROM ta_values
        WHERE symbol = %s
          AND signal IN ('BUY', 'SELL')
          AND price_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
    """, (symbol, LOOKBACK_DAYS))
    signal_types = set(row[0] for row in cursor.fetchall())

    # From daily_tier2 signal_reasons
    cursor.execute("""
        SELECT DISTINCT signal_reasons
        FROM daily_tier2
        WHERE symbol = %s
          AND signal_reasons IS NOT NULL
          AND signal_reasons != ''
          AND price_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
    """, (symbol, LOOKBACK_DAYS))
    for row in cursor.fetchall():
        if row[0]:
            for code in row[0].split(','):
                code = code.strip()
                if code:
                    signal_types.add(code)

    cursor.close()

    if not signal_types:
        logger.debug(f"  [{symbol}] No signal types found")
        return correlations

    # For each signal type, compute correlation with future return
    valid_mask = df['future_5d_ret'].notna()
    future_returns = df.loc[valid_mask, 'future_5d_ret'].values.astype(float)
    valid_dates = df.index[valid_mask].date  # numpy array of date objects

    for sig_type in sorted(signal_types):
        fire_dates = get_signal_fire_dates(conn, symbol, sig_type)
        if len(fire_dates) < MIN_SIGNAL_OCCURRENCES:
            continue

        fire_set = set(fire_dates)

        # Build binary vector aligned with valid dates
        binary_vec = np.array([
            1.0 if d in fire_set else 0.0
            for d in valid_dates
        ])

        std_sig = binary_vec.std()
        std_ret = future_returns.std()
        if std_sig == 0 or std_ret == 0:
            correlations[sig_type] = 0.0
            continue

        corr_val = float(np.corrcoef(binary_vec, future_returns)[0, 1])
        if np.isnan(corr_val):
            corr_val = 0.0

        correlations[sig_type] = round(corr_val, 4)

    logger.info(
        f"  [{symbol}] Computed correlations for {len(correlations)} signal types"
    )
    return correlations


# ==========================================================================
# 4. UPDATE SIGNAL WEIGHTS
# ==========================================================================

def update_signal_weights(
    conn,
    symbol: str
) -> None:
    """
    Main per-symbol update function.

    1. Compute per-signal correlations with future 5-day return.
    2. For each signal, compute lead/lag against all other signals.
    3. Determine if signal is a pre-indicator (avg_lead_days > 2 AND corr > 0.3).
    4. Compute boosted weight: base_weight * (1 + correlation * 0.5) * recency_factor.
    5. Upsert into signal_weights table.
    """
    logger.info(f"[{symbol}] Starting correlation analysis...")

    # Step 1: Correlation matrix
    correlations = compute_correlation_matrix(conn, symbol)
    if not correlations:
        logger.info(f"[{symbol}] No correlations computed, skipping.")
        return

    # Get existing signal_weights rows for this symbol
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, signal_type, weight, default_weight, win_rate, n_trades,
               avg_return, avg_lead_days, is_pre_indicator, correlation,
               correlates_with, weight_boosted, boost_condition
        FROM signal_weights
        WHERE symbol = %s
    """, (symbol,))
    existing = {row['signal_type']: row for row in cursor.fetchall()}
    cursor.close()

    # Get all signal types (from correlations + existing rows)
    all_signal_types = sorted(set(correlations.keys()) | set(existing.keys()))

    for sig_type in all_signal_types:
        corr_val = correlations.get(sig_type, 0.0)
        existing_row = existing.get(sig_type, {})

        # Step 2: Compute lead/lag against other signals
        avg_lead = 0.0
        lead_count = 0
        correlates_with_list = []

        for other_sig in all_signal_types:
            if other_sig == sig_type:
                continue
            ll = compute_lead_lag(conn, symbol, sig_type, other_sig)
            if ll['avg_lead_days'] != 0.0:
                avg_lead += ll['avg_lead_days']
                lead_count += 1
            if abs(ll['correlation']) > 0.1:
                correlates_with_list.append({
                    'signal': other_sig,
                    'corr': ll['correlation'],
                    'lag_days': ll['avg_lead_days'],
                    'seq_win_rate': ll['seq_win_rate'],
                })

        if lead_count > 0:
            avg_lead = round(avg_lead / lead_count, 1)

        # Step 3: Pre-indicator check
        is_pre = 1 if (avg_lead > PRE_INDICATOR_MIN_LEAD and corr_val > PRE_INDICATOR_MIN_CORR) else 0

        # Step 4: Boosted weight
        base_weight = float(existing_row.get('default_weight', 1.0) or 1.0)
        recency_factor = 1.0  # Could be tuned based on how recently signal fired
        boosted = round(
            base_weight * (1 + corr_val * BOOST_CORR_MULTIPLIER) * recency_factor,
            4
        )

        # Determine boost condition description
        boost_condition = None
        if is_pre and correlates_with_list:
            top_corr = sorted(correlates_with_list, key=lambda x: abs(x['corr']), reverse=True)[:3]
            parts = [f"{s['signal']}(r={s['corr']:.2f})" for s in top_corr]
            boost_condition = f"Pre-indicator confirmed by: {', '.join(parts)}"

        # Sort correlates_with by absolute correlation descending
        correlates_with_list.sort(key=lambda x: abs(x.get('corr', 0)), reverse=True)
        correlates_with_json = json.dumps(correlates_with_list[:10]) if correlates_with_list else None

        # Step 5: Upsert
        cursor = conn.cursor()
        if sig_type in existing:
            cursor.execute("""
                UPDATE signal_weights SET
                    correlation = %s,
                    avg_lead_days = %s,
                    is_pre_indicator = %s,
                    correlates_with = %s,
                    weight_boosted = %s,
                    boost_condition = %s,
                    updated_by = 'correlation_analysis'
                WHERE symbol = %s AND signal_type = %s
            """, (
                corr_val, avg_lead, is_pre, correlates_with_json,
                boosted, boost_condition, symbol, sig_type
            ))
        else:
            cursor.execute("""
                INSERT INTO signal_weights
                    (symbol, signal_type, weight, default_weight,
                     avg_lead_days, is_pre_indicator, correlation,
                     correlates_with, weight_boosted, boost_condition,
                     updated_by)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'correlation_analysis')
            """, (
                symbol, sig_type, base_weight, base_weight,
                avg_lead, is_pre, corr_val,
                correlates_with_json, boosted, boost_condition
            ))
        cursor.close()

        logger.info(
            f"  [{symbol}] {sig_type}: corr={corr_val}, lead={avg_lead}d, "
            f"pre={is_pre}, boosted={boosted}"
        )

    conn.commit()
    logger.info(f"[{symbol}] signal_weights updated ({len(all_signal_types)} signals).")


# ==========================================================================
# 5. MAIN LOOP
# ==========================================================================

def run_correlation_analysis(symbols: Optional[List[str]] = None) -> None:
    """
    Main entry point. Loop over all (or specified) symbols, compute
    correlations, and update signal_weights.

    Designed to run after ta_calculator.py completes its daily batch.
    """
    conn = get_connection()
    try:
        active_symbols = get_active_symbols(conn, symbols)
        total = len(active_symbols)
        logger.info(f"Starting correlation analysis for {total} symbols...")

        for idx, symbol in enumerate(active_symbols, 1):
            logger.info(f"[{idx}/{total}] Processing {symbol}...")
            try:
                update_signal_weights(conn, symbol)
            except Exception as e:
                logger.error(f"  [{symbol}] Error during analysis: {e}", exc_info=True)
                conn.rollback()
                continue

        logger.info(f"Correlation analysis complete. {total} symbols processed.")
    finally:
        conn.close()


# ==========================================================================
# CLI
# ==========================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Signal Correlation & Lead/Lag Analysis'
    )
    parser.add_argument(
        '--symbols', type=str, default=None,
        help='Comma-separated list of symbols (default: all active)'
    )
    parser.add_argument(
        '--lookback', type=int, default=LOOKBACK_DAYS,
        help=f'Lookback window in trading days (default: {LOOKBACK_DAYS})'
    )
    parser.add_argument(
        '--verbose', action='store_true',
        help='Enable DEBUG logging'
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    global LOOKBACK_DAYS
    LOOKBACK_DAYS = args.lookback

    symbol_list = None
    if args.symbols:
        symbol_list = [s.strip().upper() for s in args.symbols.split(',')]

    run_correlation_analysis(symbols=symbol_list)


if __name__ == '__main__':
    main()
