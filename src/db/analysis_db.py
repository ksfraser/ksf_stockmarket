#!/usr/bin/env python3
"""
Analysis Database & Timing-Aware Backtest Engine

DB Schema:
- analysis_runs: Each time we run analysis, record parameters
- backtest_periods: Individual period results with timing context
- timing_buckets: Aggregated stats by timing category
- signals: All signal outputs for correlation analysis

Timing buckets:
- MONTH_START: First 3 trading days of month
- MONTH_END: Last 3 trading days of month
- QUARTER_END: Last 5 trading days of quarter
- EARNINGS_3D: Within 3 days of earnings
- EARNINGS_1D: Day before/day of/day after earnings
- EARNINGS_NEXT_3D: 3 days after earnings
- TAX_SELL: Oct-Dec (tax loss harvesting)
- TAX_BUY: Jan (tax-loss bounce)
- REGULAR: Everything else
"""

import sqlite3
import json
import os
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

try:
    from .connection import DataSource  # package-style (e.g. `from db.analysis_db import get_db`)
except ImportError:
    from connection import DataSource  # flat-style (`src/db` on sys.path)

DB_PATH = os.path.expanduser('~/.hermes/cache/analysis_results.db')


def get_db():
    """Get database connection, creating tables if needed."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = DataSource.sqlite_connection(DB_PATH)
    
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS analysis_runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            model_version TEXT DEFAULT 'v4',
            portfolio_hash TEXT,
            parameters TEXT,
            total_positions INTEGER,
            macro_regime TEXT,
            vix_value REAL,
            notes TEXT
        );
        
        CREATE TABLE IF NOT EXISTS backtest_periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER REFERENCES analysis_runs(run_id),
            ticker TEXT NOT NULL,
            resolved_ticker TEXT,
            signal_date TEXT NOT NULL,
            signal TEXT NOT NULL,
            raw_confidence REAL,
            calibrated_confidence REAL,
            confidence_multiplier REAL,
            macro_regime TEXT,
            strength TEXT,
            buy_score REAL,
            sell_score REAL,
            actual_1m_return REAL,
            outcome TEXT,
            timing_bucket TEXT,
            days_to_earnings INTEGER,
            days_to_month_end INTEGER,
            is_tax_season INTEGER,
            score INTEGER DEFAULT 0,
            UNIQUE(run_id, ticker, signal_date)
        );
        
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER REFERENCES analysis_runs(run_id),
            ticker TEXT NOT NULL,
            signal_date TEXT NOT NULL,
            signal TEXT NOT NULL,
            confidence REAL,
            strength TEXT,
            buy_score REAL,
            sell_score REAL,
            macro_regime TEXT,
            confidence_multiplier REAL,
            relative_strength TEXT,
            market_correlation REAL,
            volume_poc REAL,
            volume_vwap REAL,
            price_vs_vwap REAL,
            trend_duration INTEGER,
            has_divergence_conflict INTEGER,
            min_alignment_met INTEGER,
            reasons_json TEXT,
            details_json TEXT,
            UNIQUE(run_id, ticker, signal_date)
        );
        
        CREATE TABLE IF NOT EXISTS timing_buckets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER REFERENCES analysis_runs(run_id),
            timing_bucket TEXT NOT NULL,
            total_periods INTEGER,
            wins INTEGER,
            losses INTEGER,
            holds INTEGER,
            win_rate REAL,
            avg_confidence REAL,
            avg_win_confidence REAL,
            avg_loss_confidence REAL,
            spread REAL,
            avg_return REAL,
            UNIQUE(run_id, timing_bucket)
        );
        
        CREATE TABLE IF NOT EXISTS ticker_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER REFERENCES analysis_runs(run_id),
            ticker TEXT NOT NULL,
            current_signal TEXT,
            current_confidence REAL,
            current_strength TEXT,
            backtest_win_rate REAL,
            backtest_total INTEGER,
            backtest_wins INTEGER,
            backtest_losses INTEGER,
            avg_signal_confidence REAL,
            win_loss_spread REAL,
            calibration TEXT,
            timing_best_bucket TEXT,
            timing_worst_bucket TEXT,
            UNIQUE(run_id, ticker)
        );
        
        CREATE INDEX IF NOT EXISTS idx_periods_run ON backtest_periods(run_id);
        CREATE INDEX IF NOT EXISTS idx_periods_ticker ON backtest_periods(ticker);
        CREATE INDEX IF NOT EXISTS idx_periods_timing ON backtest_periods(timing_bucket);
        CREATE INDEX IF NOT EXISTS idx_periods_outcome ON backtest_periods(outcome);
        CREATE INDEX IF NOT EXISTS idx_signals_run ON signals(run_id);
        CREATE INDEX IF NOT EXISTS idx_timing_run ON timing_buckets(run_id);
    """)
    
    return conn


def classify_timing_bucket(signal_date: str, earnings_dates: List[str] = None) -> Dict:
    """
    Classify a signal date into timing buckets.
    
    Returns:
        bucket: Primary timing category
        days_to_earnings: Days to nearest earnings (negative = past)
        days_to_month_end: Days to month end
        is_tax_season: 1 if Oct-Dec (tax loss harvesting season)
    """
    dt = pd.Timestamp(signal_date)
    result = {
        'timing_bucket': 'REGULAR',
        'days_to_earnings': None,
        'days_to_month_end': None,
        'is_tax_season': 1 if dt.month in (10, 11, 12) else 0,
    }
    
    # Days to month end
    if dt.month == 12:
        month_end = pd.Timestamp(dt.year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = pd.Timestamp(dt.year, dt.month + 1, 1) - timedelta(days=1)
    result['days_to_month_end'] = (month_end - dt).days
    
    # Month start: first 3 trading days
    month_start = pd.Timestamp(dt.year, dt.month, 1)
    days_from_start = (dt - month_start).days
    if days_from_start <= 4:  # Allow for weekends/holidays
        result['timing_bucket'] = 'MONTH_START'
    
    # Month end: last 3 trading days
    if result['days_to_month_end'] <= 4:
        result['timing_bucket'] = 'MONTH_END'
    
    # Quarter end: last 5 days of quarter
    if dt.month in (3, 6, 9, 12) and result['days_to_month_end'] <= 5:
        result['timing_bucket'] = 'QUARTER_END'
    
    # Tax season
    if dt.month in (10, 11, 12):
        result['timing_bucket'] = 'TAX_SELL'
    elif dt.month == 1:
        result['timing_bucket'] = 'TAX_BUY'
    
    # Earnings proximity
    if earnings_dates:
        min_days = None
        for e_str in earnings_dates:
            try:
                e_dt = pd.Timestamp(e_str)
                days = (e_dt - dt).days
                if min_days is None or abs(days) < abs(min_days):
                    min_days = days
            except:
                continue
        
        if min_days is not None:
            result['days_to_earnings'] = min_days
            if abs(min_days) <= 1:
                result['timing_bucket'] = 'EARNINGS_1D'
            elif abs(min_days) <= 3:
                result['timing_bucket'] = 'EARNINGS_3D'
            elif 0 < min_days <= 7:
                result['timing_bucket'] = 'EARNINGS_NEXT_7D'
    
    return result


def compute_timing_analysis(conn: sqlite3.Connection, run_id: int) -> pd.DataFrame:
    """Aggregate backtest results by timing bucket."""
    query = """
        SELECT 
            timing_bucket,
            COUNT(*) as total,
            SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
            SUM(CASE WHEN outcome = 'HOLD' THEN 1 ELSE 0 END) as holds,
            AVG(calibrated_confidence) as avg_conf,
            AVG(CASE WHEN outcome = 'WIN' THEN calibrated_confidence END) as avg_win_conf,
            AVG(CASE WHEN outcome = 'LOSS' THEN calibrated_confidence END) as avg_loss_conf,
            AVG(actual_1m_return) as avg_return
        FROM backtest_periods
        WHERE run_id = ?
        GROUP BY timing_bucket
        ORDER BY total DESC
    """
    df = pd.read_sql_query(query, conn, params=(run_id,))
    
    if not df.empty:
        df['win_rate'] = df['wins'] / (df['wins'] + df['losses']) * 100
        df['spread'] = df['avg_win_conf'] - df['avg_loss_conf']
        df['directional_total'] = df['wins'] + df['losses']
    
    return df


def compute_ticker_calibration(conn: sqlite3.Connection, run_id: int) -> pd.DataFrame:
    """Per-ticker calibration summary."""
    query = """
        SELECT 
            ticker,
            COUNT(*) as total,
            SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
            SUM(CASE WHEN outcome = 'HOLD' THEN 1 ELSE 0 END) as holds,
            AVG(calibrated_confidence) as avg_conf,
            AVG(CASE WHEN outcome = 'WIN' THEN calibrated_confidence END) as avg_win_conf,
            AVG(CASE WHEN outcome = 'LOSS' THEN calibrated_confidence END) as avg_loss_conf,
            AVG(actual_1m_return) as avg_return
        FROM backtest_periods
        WHERE run_id = ?
        GROUP BY ticker
    """
    df = pd.read_sql_query(query, conn, params=(run_id,))
    
    if not df.empty:
        df['win_rate'] = df['wins'] / (df['wins'] + df['losses']) * 100
        df['spread'] = df['avg_win_conf'] - df['avg_loss_conf']
        
        # Calibration rating
        def rate_calibration(row):
            if row['win_rate'] >= 70 and row['spread'] > 5:
                return 'WELL_CALIBRATED'
            elif row['win_rate'] >= 50 and row['spread'] > 0:
                return 'ACCEPTABLE'
            elif row['win_rate'] < 50 and row['spread'] < 0:
                return 'POOR_CALIBRATION'
            else:
                return 'MIXED'
        
        df['calibration'] = df.apply(rate_calibration, axis=1)
    
    return df


def generate_timing_report(conn: sqlite3.Connection, run_id: int) -> str:
    """Generate a comprehensive timing analysis report."""
    L = []
    L.append("=" * 80)
    L.append("TIMING-AWARE BACKTEST ANALYSIS")
    L.append("=" * 80)
    L.append("")
    
    # Overall summary
    overall = pd.read_sql_query("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN outcome='LOSS' THEN 1 ELSE 0 END) as losses,
            AVG(calibrated_confidence) as avg_conf,
            AVG(actual_1m_return) as avg_return
        FROM backtest_periods WHERE run_id = ?
    """, conn, params=(run_id,))
    
    if not overall.empty:
        r = overall.iloc[0]
        directional = r['wins'] + r['losses']
        wr = r['wins'] / directional * 100 if directional > 0 else 0
        L.append(f"Overall: {r['total']} periods | Win Rate: {wr:.0f}% | Avg Conf: {r['avg_conf']:.1%} | Avg Return: {r['avg_return']:+.2f}%")
        L.append("")
    
    # Timing bucket analysis
    L.append("─" * 80)
    L.append("RESULTS BY TIMING BUCKET")
    L.append("─" * 80)
    L.append(f"{'Bucket':<18} {'N':>4} {'Win%':>6} {'AvgConf':>8} {'WinConf':>8} {'LosConf':>8} {'Spread':>8} {'AvgRet':>8}")
    L.append("─" * 80)
    
    timing_df = compute_timing_analysis(conn, run_id)
    for _, row in timing_df.iterrows():
        bucket = row['timing_bucket'] or 'UNKNOWN'
        n = int(row['total'])
        wr = row.get('win_rate', 0) or 0
        avg_c = row.get('avg_conf', 0) or 0
        wc = row.get('avg_win_conf', 0) or 0
        lc = row.get('avg_loss_conf', 0) or 0
        spread = row.get('spread', 0) or 0
        avg_ret = row.get('avg_return', 0) or 0
        
        L.append(f"{bucket:<18} {n:>4} {wr:>5.0f}% {avg_c:>7.1%} {wc:>7.1%} {lc:>7.1%} {spread:>+7.1%} {avg_ret:>+7.2f}%")
    
    L.append("")
    
    # Best/worst timing buckets
    if not timing_df.empty:
        directional = timing_df[timing_df['directional_total'] >= 3]  # Min 3 directional signals
        if not directional.empty:
            best = directional.loc[directional['win_rate'].idxmax()]
            worst = directional.loc[directional['win_rate'].idxmin()]
            L.append(f"Best timing:  {best['timing_bucket']} ({best['win_rate']:.0f}% win rate, {int(best['total'])} periods)")
            L.append(f"Worst timing: {worst['timing_bucket']} ({worst['win_rate']:.0f}% win rate, {int(worst['total'])} periods)")
            L.append("")
    
    # Ticker calibration
    L.append("─" * 80)
    L.append("PER-TICKER CALIBRATION")
    L.append("─" * 80)
    L.append(f"{'Ticker':<10} {'Win%':>6} {'AvgConf':>8} {'WConf':>8} {'LConf':>8} {'Spread':>8} {'Calibr.':<18}")
    L.append("─" * 80)
    
    ticker_df = compute_ticker_calibration(conn, run_id)
    for _, row in ticker_df.iterrows():
        wr = row.get('win_rate', 0) or 0
        avg_c = row.get('avg_conf', 0) or 0
        wc = row.get('avg_win_conf', 0) or 0
        lc = row.get('avg_loss_conf', 0) or 0
        spread = row.get('spread', 0) or 0
        cal = row.get('calibration', 'UNKNOWN')
        L.append(f"{row['ticker']:<10} {wr:>5.0f}% {avg_c:>7.1%} {wc:>7.1%} {lc:>7.1%} {spread:>+7.1%} {cal:<18}")
    
    L.append("")
    
    # Earnings proximity analysis
    L.append("─" * 80)
    L.append("EARNINGS PROXIMITY ANALYSIS")
    L.append("─" * 80)
    
    earnings_analysis = pd.read_sql_query("""
        SELECT 
            CASE 
                WHEN days_to_earnings IS NULL THEN 'NO_DATA'
                WHEN ABS(days_to_earnings) <= 1 THEN 'EARNINGS_1D'
                WHEN ABS(days_to_earnings) <= 3 THEN 'EARNINGS_3D'
                WHEN days_to_earnings > 0 AND days_to_earnings <= 7 THEN 'EARNINGS_NEXT_7D'
                WHEN days_to_earnings < 0 AND ABS(days_to_earnings) <= 7 THEN 'EARNINGS_PAST_7D'
                ELSE 'FAR_FROM_EARNINGS'
            END as proximity,
            COUNT(*) as n,
            SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN outcome='LOSS' THEN 1 ELSE 0 END) as losses,
            AVG(calibrated_confidence) as avg_conf,
            AVG(actual_1m_return) as avg_return
        FROM backtest_periods
        WHERE run_id = ?
        GROUP BY proximity
        ORDER BY n DESC
    """, conn, params=(run_id,))
    
    if not earnings_analysis.empty:
        L.append(f"{'Proximity':<22} {'N':>4} {'Win%':>6} {'AvgConf':>8} {'AvgRet':>8}")
        L.append("─" * 60)
        for _, row in earnings_analysis.iterrows():
            n = int(row['n'])
            d = int(row['wins'] + row['losses'])
            wr = int(row['wins']) / d * 100 if d > 0 else 0
            avg_c = row.get('avg_conf', 0) or 0
            avg_ret = row.get('avg_return', 0) or 0
            L.append(f"{row['proximity']:<22} {n:>4} {wr:>5.0f}% {avg_c:>7.1%} {avg_ret:>+7.2f}%")
    
    L.append("")
    L.append("=" * 80)
    
    return "\n".join(L)
