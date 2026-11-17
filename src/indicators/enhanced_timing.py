#!/usr/bin/env python3
"""
Enhanced Timing Analysis with:
1. Timing-aware confidence discounts (EARNINGS_1D = -20%, FOMC = -10%, etc.)
2. Query interface for comparing runs over time
3. FOMC days and options expiry timing buckets
"""

import sys
import os
import json
import sqlite3
import pandas as pd
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))
from analysis_db import get_db, compute_timing_analysis, compute_ticker_calibration, generate_timing_report


# ============================================================================
# TIMING CALENDAR DATA
# ============================================================================

FOMC_DATES = {
    '2024': ['2024-01-30', '2024-01-31', '2024-03-19', '2024-03-20', '2024-04-30', '2024-05-01',
             '2024-06-11', '2024-06-12', '2024-07-30', '2024-07-31', '2024-09-17', '2024-09-18',
             '2024-11-06', '2024-11-07', '2024-12-17', '2024-12-18'],
    '2025': ['2025-01-28', '2025-01-29', '2025-03-18', '2025-03-19', '2025-05-06', '2025-05-07',
             '2025-06-17', '2025-06-18', '2025-07-29', '2025-07-30', '2025-09-16', '2025-09-17',
             '2025-10-28', '2025-10-29', '2025-12-09', '2025-12-10'],
    '2026': ['2026-01-27', '2026-01-28', '2026-03-17', '2026-03-18', '2026-04-28', '2026-04-29',
             '2026-06-16', '2026-06-17', '2026-07-28', '2026-07-29', '2026-09-15', '2026-09-16',
             '2026-10-27', '2026-10-28', '2026-12-08', '2026-12-09'],
}

OPTIONS_EXPIRY = {
    '2024': ['2024-01-19', '2024-02-16', '2024-03-15', '2024-04-19', '2024-05-17', '2024-06-21',
             '2024-07-19', '2024-08-16', '2024-09-20', '2024-10-18', '2024-11-15', '2024-12-20'],
    '2025': ['2025-01-17', '2025-02-21', '2025-03-21', '2025-04-18', '2025-05-16', '2025-06-20',
             '2025-07-18', '2025-08-15', '2025-09-19', '2025-10-17', '2025-11-21', '2025-12-19'],
    '2026': ['2026-01-16', '2026-02-20', '2026-03-20', '2026-04-17', '2026-05-15', '2026-06-19',
             '2026-07-17', '2026-08-21', '2026-09-18', '2026-10-16', '2026-11-20', '2026-12-18'],
}


def days_to_nearest(date_str: str, event_dates: List[str]) -> Optional[int]:
    """Find minimum days to any event date."""
    dt = pd.Timestamp(date_str)
    min_days = None
    for e_str in event_dates:
        try:
            e_dt = pd.Timestamp(e_str)
            days = (e_dt - dt).days
            if min_days is None or abs(days) < abs(min_days):
                min_days = days
        except:
            continue
    return min_days


def classify_timing_enhanced(signal_date: str, earnings_dates: List[str] = None) -> Dict:
    """
    Enhanced timing classification with FOMC, options expiry, and confidence discounts.
    
    Returns timing info including a confidence discount multiplier.
    """
    dt = pd.Timestamp(signal_date)
    year_str = str(dt.month)
    year = str(dt.year)
    
    # Gather all event dates
    all_fomc = []
    all_options = []
    for y in [str(dt.year - 1), str(dt.year), str(dt.year + 1)]:
        all_fomc.extend(FOMC_DATES.get(y, []))
        all_options.extend(OPTIONS_EXPIRY.get(y, []))
    
    # Calculate proximity
    days_to_fomc = days_to_nearest(signal_date, all_fomc)
    days_to_options = days_to_nearest(signal_date, all_options)
    days_to_earnings = days_to_nearest(signal_date, earnings_dates) if earnings_dates else None
    
    # Days to month end
    if dt.month == 12:
        month_end = pd.Timestamp(dt.year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = pd.Timestamp(dt.year, dt.month + 1, 1) - timedelta(days=1)
    days_to_month_end = (month_end - dt).days
    
    # Month start
    month_start = pd.Timestamp(dt.year, dt.month, 1)
    days_from_month_start = (dt - month_start).days
    
    # Classify bucket
    bucket = 'REGULAR'
    confidence_discount = 1.0
    discount_reasons = []
    
    # Earnings proximity (highest priority)
    if days_to_earnings is not None:
        if abs(days_to_earnings) <= 1:
            bucket = 'EARNINGS_1D'
            confidence_discount = 0.80  # -20% — earnings day is noisy
            discount_reasons.append(f"Earnings {'day-of' if days_to_earnings == 0 else '±1d'} → -20% confidence")
        elif abs(days_to_earnings) <= 3:
            bucket = 'EARNINGS_3D'
            confidence_discount = 0.85
            discount_reasons.append(f"Earnings ±3d → -15% confidence")
        elif 0 < days_to_earnings <= 7:
            bucket = 'EARNINGS_NEXT_7D'
            confidence_discount = 0.90
            discount_reasons.append(f"Earnings next 7d → -10% confidence")
        elif days_to_earnings < 0 and abs(days_to_earnings) <= 7:
            bucket = 'EARNINGS_PAST_7D'
            confidence_discount = 0.95
    
    # FOMC proximity
    if days_to_fomc is not None and abs(days_to_fomc) <= 3:
        if bucket == 'REGULAR':
            bucket = 'FOMC_3D'
        confidence_discount *= 0.90  # Stack: -10% for FOMC
        discount_reasons.append(f"FOMC ±3d → -10% confidence")
    elif days_to_fomc is not None and abs(days_to_fomc) <= 7:
        if bucket == 'REGULAR':
            bucket = 'FOMC_7D'
        confidence_discount *= 0.95
        discount_reasons.append(f"FOMC ±7d → -5% confidence")
    
    # Options expiry proximity
    if days_to_options is not None and abs(days_to_options) <= 2:
        if bucket == 'REGULAR':
            bucket = 'OPTIONS_2D'
        confidence_discount *= 0.92
        discount_reasons.append(f"Options expiry ±2d → -8% confidence")
    elif days_to_options is not None and abs(days_to_options) <= 5:
        if bucket == 'REGULAR':
            bucket = 'OPTIONS_5D'
        confidence_discount *= 0.95
        discount_reasons.append(f"Options expiry ±5d → -5% confidence")
    
    # Month/quarter boundaries
    if days_from_month_start <= 4:
        bucket = 'MONTH_START'
    if days_to_month_end <= 4:
        bucket = 'MONTH_END'
    if dt.month in (3, 6, 9, 12) and days_to_month_end <= 5:
        bucket = 'QUARTER_END'
    
    # Tax season
    if dt.month in (10, 11, 12):
        bucket = 'TAX_SELL'
        confidence_discount *= 1.05  # Slight boost — tax loss harvesting is predictable
        discount_reasons.append("Tax season → +5% confidence (predictable)")
    elif dt.month == 1:
        bucket = 'TAX_BUY'
        confidence_discount *= 1.03
        discount_reasons.append("January bounce → +3% confidence")
    
    return {
        'timing_bucket': bucket,
        'confidence_discount': min(confidence_discount, 1.10),  # Cap at +10%
        'discount_reasons': discount_reasons,
        'days_to_earnings': days_to_earnings,
        'days_to_fomc': days_to_fomc,
        'days_to_options': days_to_options,
        'days_to_month_end': days_to_month_end,
    }


# ============================================================================
# QUERY INTERFACE
# ============================================================================

class AnalysisQuery:
    """Query interface for comparing analysis runs over time."""
    
    def __init__(self, db_path: str = None):
        self.db = get_db()
    
    def list_runs(self) -> pd.DataFrame:
        """List all analysis runs."""
        return pd.read_sql_query("""
            SELECT run_id, timestamp, model_version, total_positions, macro_regime, vix_value, notes
            FROM analysis_runs
            ORDER BY run_id DESC
        """, self.db)
    
    def compare_runs(self, run_ids: List[int]) -> pd.DataFrame:
        """Compare calibration across multiple runs."""
        placeholders = ','.join(['?' for _ in run_ids])
        query = f"""
            SELECT 
                ts.run_id,
                ts.ticker,
                ts.backtest_win_rate,
                ts.win_loss_spread,
                ts.calibration,
                ts.current_signal,
                ts.current_confidence,
                ts.timing_best_bucket,
                ts.timing_worst_bucket
            FROM ticker_summaries ts
            WHERE ts.run_id IN ({placeholders})
            ORDER BY ts.run_id DESC, ts.backtest_win_rate DESC
        """
        return pd.read_sql_query(query, self.db, params=run_ids)
    
    def timing_comparison(self, run_ids: List[int]) -> pd.DataFrame:
        """Compare timing bucket performance across runs."""
        placeholders = ','.join(['?' for _ in run_ids])
        query = f"""
            SELECT 
                tb.run_id,
                tb.timing_bucket,
                tb.total_periods,
                tb.win_rate,
                tb.spread,
                tb.avg_return,
                tb.avg_confidence
            FROM timing_buckets tb
            WHERE tb.run_id IN ({placeholders})
            ORDER BY tb.run_id DESC, tb.win_rate DESC
        """
        return pd.read_sql_query(query, self.db, params=run_ids)
    
    def best_worst_tickers(self, run_id: int, n: int = 5) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Get best and worst calibrated tickers for a run."""
        query = """
            SELECT ticker, backtest_win_rate, win_loss_spread, calibration, 
                   current_signal, current_confidence, timing_best_bucket, timing_worst_bucket
            FROM ticker_summaries
            WHERE run_id = ?
            ORDER BY win_loss_spread DESC
        """
        df = pd.read_sql_query(query, self.db, params=(run_id,))
        best = df.head(n)
        worst = df.tail(n).iloc[::-1]
        return best, worst
    
    def signal_accuracy_trend(self, ticker: str) -> pd.DataFrame:
        """Track how a ticker's backtest accuracy has changed over runs."""
        query = """
            SELECT 
                ts.run_id,
                ar.timestamp,
                ts.backtest_win_rate,
                ts.win_loss_spread,
                ts.calibration,
                ts.current_signal,
                ts.current_confidence,
                ts.timing_best_bucket,
                ts.worst_bucket
            FROM ticker_summaries ts
            JOIN analysis_runs ar ON ts.run_id = ar.run_id
            WHERE ts.ticker = ?
            ORDER BY ts.run_id
        """
        return pd.read_sql_query(query, self.db, params=(ticker,))
    
    def generate_comparison_report(self, run_ids: List[int] = None) -> str:
        """Generate a comparison report across runs."""
        L = []
        L.append("=" * 80)
        L.append("ANALYSIS RUN COMPARISON REPORT")
        L.append("=" * 80)
        L.append("")
        
        # Run summaries
        runs = self.list_runs()
        if run_ids:
            runs = runs[runs['run_id'].isin(run_ids)]
        
        L.append("RUN SUMMARIES:")
        L.append(f"{'Run':>4} {'Date':<20} {'Model':<6} {'Positions':>9} {'Regime':<10} {'VIX':>6} {'Notes'}")
        L.append("─" * 80)
        for _, r in runs.iterrows():
            notes = (r['notes'] or '')[:40]
            L.append(f"{r['run_id']:>4} {str(r['timestamp'])[:19]:<20} {r['model_version'] or 'N/A':<6} {r['total_positions']:>9} {r['macro_regime'] or 'N/A':<10} {r['vix_value'] or 0:>6.2f} {notes}")
        
        L.append("")
        
        # Best/worst for latest run
        if runs.empty:
            return "\n".join(L)
        
        latest_run = runs.iloc[0]['run_id']
        best, worst = self.best_worst_tickers(latest_run)
        
        L.append(f"BEST CALIBRATED (Run {latest_run}):")
        L.append(f"{'Ticker':<10} {'Win%':>6} {'Spread':>8} {'Calibr.':<18} {'Signal':<6} {'Conf':>6} {'Best Bucket':<15}")
        L.append("─" * 80)
        for _, r in best.iterrows():
            L.append(f"{r['ticker']:<10} {r['backtest_win_rate']:>5.0f}% {r['win_loss_spread']:>+7.1%} {r['calibration'] or 'N/A':<18} {r['current_signal'] or 'N/A':<6} {r['current_confidence'] or 0:>5.0%} {r['timing_best_bucket'] or 'N/A':<15}")
        
        L.append("")
        L.append(f"WORST CALIBRATED (Run {latest_run}):")
        L.append(f"{'Ticker':<10} {'Win%':>6} {'Spread':>8} {'Calibr.':<18} {'Signal':<6} {'Conf':>6} {'Worst Bucket':<15}")
        L.append("─" * 80)
        for _, r in worst.iterrows():
            L.append(f"{r['ticker']:<10} {r['backtest_win_rate']:>5.0f}% {r['win_loss_spread']:>+7.1%} {r['calibration'] or 'N/A':<18} {r['current_signal'] or 'N/A':<6} {r['current_confidence'] or 0:>5.0%} {r['timing_worst_bucket'] or 'N/A':<15}")
        
        L.append("")
        
        # Timing comparison
        timing = self.timing_comparison(run_ids if run_ids else [latest_run])
        if not timing.empty:
            L.append("TIMING BUCKET COMPARISON:")
            L.append(f"{'Run':>4} {'Bucket':<18} {'N':>4} {'Win%':>6} {'Spread':>8} {'AvgRet':>8} {'AvgConf':>8}")
            L.append("─" * 80)
            for _, r in timing.iterrows():
                L.append(f"{r['run_id']:>4} {r['timing_bucket']:<18} {r['total_periods']:>4} {r['win_rate']:>5.0f}% {r['spread']:>+7.1%} {r['avg_return']:>+7.2f}% {r['avg_confidence']:>7.1%}")
        
        L.append("")
        L.append("=" * 80)
        
        return "\n".join(L)


# ============================================================================
# ENHANCED TIMING ANALYSIS RUNNER
# ============================================================================

def run_enhanced_timing_analysis():
    """Run the full timing analysis with all enhancements."""
    import yfinance as yf
    from investment_monitor import InvestmentMonitor, SymbolResolver
    
    # Load portfolio
    with open('/tmp/portfolio_from_email.json', 'r') as f:
        portfolio_shares = json.load(f)
    
    portfolio = {sym: {'shares': s, 'cost_basis': 0} for sym, s in portfolio_shares.items()}
    
    monitor = InvestmentMonitor()
    monitor.portfolio = portfolio
    tickers = list(portfolio.keys())
    
    print(f"Analyzing {len(tickers)} positions with enhanced timing...")
    monitor.fetch_all_data(tickers)
    monitor.run_backtests(tickers)
    
    # Get earnings dates
    resolver = SymbolResolver()
    earnings_map = {}
    for sym in tickers:
        resolved = resolver.resolve(sym)
        try:
            stock = yf.Ticker(resolved)
            ed = stock.earnings_dates
            if ed is not None and len(ed) > 0:
                dates = []
                for idx, row in ed.iterrows():
                    try:
                        if hasattr(idx, 'tz_localize'):
                            e_dt = idx.tz_localize(None) if idx.tzinfo else idx
                        else:
                            e_dt = idx
                        dates.append(str(e_dt)[:10])
                    except:
                        continue
                earnings_map[sym] = dates
        except:
            pass
    
    # Store in DB with enhanced timing
    conn = get_db()
    
    vix_value = None
    try:
        vix_hist = yf.Ticker('^VIX').history(period='5d')
        if not vix_hist.empty:
            vix_value = float(vix_hist['Close'].iloc[-1])
    except:
        pass
    
    macro_regime = 'UNKNOWN'
    if tickers and tickers[0] in monitor.macro_regime:
        macro_regime = monitor.macro_regime[tickers[0]].get('regime', 'UNKNOWN')
    
    cursor = conn.execute("""
        INSERT INTO analysis_runs (timestamp, model_version, portfolio_hash, parameters, total_positions, macro_regime, vix_value, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        'v5',
        hash(frozenset(portfolio.keys())) % 100000,
        json.dumps({
            'lookback_months': [12, 9, 6, 3, 2, 1],
            'timing_aware': True,
            'fomc_dates': True,
            'options_expiry': True,
            'confidence_discounts': {
                'EARNINGS_1D': 0.80,
                'EARNINGS_3D': 0.85,
                'FOMC_3D': 0.90,
                'OPTIONS_2D': 0.92,
                'TAX_SELL': 1.05,
            }
        }),
        len(tickers),
        macro_regime,
        vix_value,
        'Enhanced timing: FOMC, options expiry, confidence discounts, tax season boost'
    ))
    run_id = cursor.lastrowid
    print(f"Analysis run ID: {run_id}")
    
    # Store backtest periods with enhanced timing + confidence discounts
    for ticker in tickers:
        bt = monitor.backtest_data.get(ticker, {})
        if not bt or 'error' in bt or not bt.get('periods'):
            continue
        
        earnings_dates = earnings_map.get(ticker, [])
        
        for p in bt['periods']:
            timing = classify_timing_enhanced(p['date'], earnings_dates)
            
            raw_conf = p['confidence']
            discounted_conf = min(raw_conf * timing['confidence_discount'], 0.95)
            
            conn.execute("""
                INSERT OR REPLACE INTO backtest_periods 
                (run_id, ticker, resolved_ticker, signal_date, signal, raw_confidence, calibrated_confidence,
                 confidence_multiplier, macro_regime, strength, buy_score, sell_score, actual_1m_return,
                 outcome, timing_bucket, days_to_earnings, days_to_month_end, is_tax_season)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                ticker,
                monitor.symbol_map.get(ticker, ticker),
                p['date'],
                p['signal'],
                raw_conf,
                discounted_conf,
                timing['confidence_discount'],
                macro_regime,
                'UNKNOWN',
                p.get('buy_score', 0),
                p.get('sell_score', 0),
                p['actual_1m_return'],
                p['outcome'],
                timing['timing_bucket'],
                timing['days_to_earnings'],
                timing['days_to_month_end'],
                1 if 'TAX' in timing['timing_bucket'] else 0,
            ))
    
    # Store ticker summaries
    ticker_df = compute_ticker_calibration(conn, run_id)
    report = monitor.generate_report()
    
    for _, row in ticker_df.iterrows():
        ticker_timing = pd.read_sql_query("""
            SELECT timing_bucket, 
                   SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN outcome='LOSS' THEN 1 ELSE 0 END) as losses,
                   COUNT(*) as total
            FROM backtest_periods
            WHERE run_id = ? AND ticker = ? AND outcome != 'HOLD'
            GROUP BY timing_bucket
            HAVING total >= 2
            ORDER BY CAST(wins AS FLOAT)/total DESC
        """, conn, params=(run_id, row['ticker']))
        
        best_bucket = ticker_timing.iloc[0]['timing_bucket'] if not ticker_timing.empty else 'N/A'
        worst_bucket = ticker_timing.iloc[-1]['timing_bucket'] if not ticker_timing.empty else 'N/A'
        
        conn.execute("""
            INSERT OR REPLACE INTO ticker_summaries
            (run_id, ticker, current_signal, current_confidence, current_strength,
             backtest_win_rate, backtest_total, backtest_wins, backtest_losses,
             avg_signal_confidence, win_loss_spread, calibration,
             timing_best_bucket, timing_worst_bucket)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            row['ticker'],
            report.get('holdings', {}).get(row['ticker'], {}).get('signal', {}).get('signal', 'UNKNOWN'),
            report.get('holdings', {}).get(row['ticker'], {}).get('signal', {}).get('confidence', 0),
            report.get('holdings', {}).get(row['ticker'], {}).get('signal', {}).get('strength', 'UNKNOWN'),
            row.get('win_rate', 0),
            int(row['wins'] + row['losses'] + row['holds']),
            int(row['wins']),
            int(row['losses']),
            row.get('avg_conf', 0),
            row.get('spread', 0),
            row.get('calibration', 'UNKNOWN'),
            best_bucket,
            worst_bucket
        ))
    
    # Store timing bucket summaries
    timing_df = compute_timing_analysis(conn, run_id)
    for _, row in timing_df.iterrows():
        conn.execute("""
            INSERT OR REPLACE INTO timing_buckets
            (run_id, timing_bucket, total_periods, wins, losses, holds, win_rate,
             avg_confidence, avg_win_confidence, avg_loss_confidence, spread, avg_return)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            row['timing_bucket'] or 'UNKNOWN',
            int(row['total']),
            int(row['wins']),
            int(row['losses']),
            int(row['holds']),
            row.get('win_rate', 0),
            row.get('avg_conf', 0),
            row.get('avg_win_conf', 0),
            row.get('avg_loss_conf', 0),
            row.get('spread', 0),
            row.get('avg_return', 0)
        ))
    
    conn.commit()
    
    # Generate reports
    print("\n" + "=" * 80)
    print("GENERATING REPORTS")
    print("=" * 80)
    
    # Timing report
    timing_report = generate_timing_report(conn, run_id)
    print(timing_report)
    
    with open('/tmp/timing_analysis_v5.txt', 'w') as f:
        f.write(timing_report)
    
    # Comparison report
    query = AnalysisQuery()
    comparison = query.generate_comparison_report()
    print("\n" + comparison)
    
    with open('/tmp/comparison_report.txt', 'w') as f:
        f.write(comparison)
    
    print(f"\nReports saved:")
    print(f"  /tmp/timing_analysis_v5.txt")
    print(f"  /tmp/comparison_report.txt")
    print(f"  DB: ~/.hermes/cache/analysis_results.db (run_id={run_id})")
    
    conn.close()


if __name__ == '__main__':
    run_enhanced_timing_analysis()
