#!/usr/bin/env python3
"""
Database Schema Expansion & 5-Year Monthly Backtest

New tables:
- portfolio_holdings: Full position data with cost basis, acquisition dates
- enquiry_sources: Links sources (Discord, email, etc.) to tickers being tracked
- backtest_periods_5y: Monthly backtest results going back 5 years
- signal_accuracy: Re-scored signal accuracy by month
- delivery_log: Track all report deliveries

CRITICAL: This script MUST use the full calibrated signal pipeline
(MacroRegimeFilter, MarketRelativeIndicators, VolumeProfileAnalyzer)
when generating historical signals. Using only the basic SignalGenerator
produces misleadingly high win rates (97-100%) due to bull market bias.
"""

import sys
import os
import json
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(__file__))

import yfinance as yf
from investment_monitor import (
    SymbolResolver, TechnicalAnalyzer, MacroRegimeFilter,
    MarketRelativeIndicators, VolumeProfileAnalyzer,
    SignalGenerator
)
from analysis_db import get_db


# ============================================================================
# DB SCHEMA EXPANSION
# ============================================================================

def expand_db_schema(conn: sqlite3.Connection):
    """Add new tables to the existing analysis_results.db."""
    
    conn.executescript("""
        -- Portfolio holdings with full position data
        CREATE TABLE IF NOT EXISTS portfolio_holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            resolved_ticker TEXT,
            shares REAL NOT NULL,
            cost_basis REAL,
            cost_basis_total REAL,
            acquisition_date TEXT,
            source TEXT DEFAULT 'manual',
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            active INTEGER DEFAULT 1,
            notes TEXT,
            UNIQUE(ticker)
        );
        
        -- Enquiry sources: who asked about what and when
        CREATE TABLE IF NOT EXISTS enquiry_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_platform TEXT NOT NULL,
            source_id TEXT,
            source_name TEXT,
            ticker TEXT NOT NULL,
            resolved_ticker TEXT,
            enquiry_type TEXT,
            message_text TEXT,
            response_sent INTEGER DEFAULT 0,
            response_channel TEXT,
            UNIQUE(source_platform, source_id, ticker, timestamp)
        );
        
        -- 5-year monthly backtest periods
        CREATE TABLE IF NOT EXISTS backtest_periods_5y (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            resolved_ticker TEXT,
            signal_date TEXT NOT NULL,
            signal TEXT NOT NULL,
            raw_confidence REAL,
            calibrated_confidence REAL,
            strength TEXT,
            buy_score REAL,
            sell_score REAL,
            price_at_signal REAL,
            price_1m_future REAL,
            price_3m_future REAL,
            price_6m_future REAL,
            actual_1m_return REAL,
            actual_3m_return REAL,
            actual_6m_return REAL,
            outcome_1m TEXT,
            outcome_3m TEXT,
            outcome_6m TEXT,
            timing_bucket TEXT,
            macro_regime TEXT,
            vix_value REAL,
            UNIQUE(ticker, signal_date)
        );
        
        -- Re-scored signal accuracy by time period
        CREATE TABLE IF NOT EXISTS signal_accuracy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            period_start TEXT,
            period_end TEXT,
            total_signals INTEGER,
            wins_1m INTEGER,
            losses_1m INTEGER,
            holds_1m INTEGER,
            win_rate_1m REAL,
            wins_3m INTEGER,
            losses_3m INTEGER,
            win_rate_3m REAL,
            wins_6m INTEGER,
            losses_6m INTEGER,
            win_rate_6m REAL,
            avg_confidence REAL,
            avg_win_confidence REAL,
            avg_loss_confidence REAL,
            spread_1m REAL,
            spread_3m REAL,
            spread_6m REAL,
            calibration TEXT,
            UNIQUE(ticker, period_start, period_end)
        );
        
        -- Delivery log: track what was sent where
        CREATE TABLE IF NOT EXISTS delivery_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            run_id INTEGER,
            delivery_target TEXT NOT NULL,
            delivery_type TEXT,
            ticker TEXT,
            signal TEXT,
            confidence REAL,
            message_preview TEXT,
            success INTEGER DEFAULT 1,
            error TEXT
        );
        
        CREATE INDEX IF NOT EXISTS idx_enquiry_ticker ON enquiry_sources(ticker);
        CREATE INDEX IF NOT EXISTS idx_enquiry_source ON enquiry_sources(source_platform, source_id);
        CREATE INDEX IF NOT EXISTS idx_enquiry_timestamp ON enquiry_sources(timestamp);
        CREATE INDEX IF NOT EXISTS idx_5y_ticker ON backtest_periods_5y(ticker);
        CREATE INDEX IF NOT EXISTS idx_5y_date ON backtest_periods_5y(signal_date);
        CREATE INDEX IF NOT EXISTS idx_accuracy_ticker ON signal_accuracy(ticker);
        CREATE INDEX IF NOT EXISTS idx_delivery_run ON delivery_log(run_id);
    """)
    
    print("DB schema expanded successfully")


# ============================================================================
# PORTFOLIO HOLDINGS IMPORT
# ============================================================================

def import_portfolio(conn: sqlite3.Connection, portfolio_data: Dict, source: str = 'manual'):
    """Import portfolio holdings into the DB."""
    resolver = SymbolResolver()
    
    for ticker, data in portfolio_data.items():
        resolved = resolver.resolve(ticker)
        
        if isinstance(data, (int, float)):
            shares = float(data)
            cost_basis = None
            cost_basis_total = None
        elif isinstance(data, dict):
            shares = data.get('shares', 0)
            cost_basis = data.get('cost_basis')
            cost_basis_total = data.get('cost_basis_total')
        else:
            continue
        
        conn.execute("""
            INSERT OR REPLACE INTO portfolio_holdings 
            (ticker, resolved_ticker, shares, cost_basis, cost_basis_total, source, last_updated, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """, (ticker, resolved, shares, cost_basis, cost_basis_total, source, datetime.now().isoformat()))
    
    conn.commit()
    print(f"Imported {len(portfolio_data)} portfolio holdings")


# ============================================================================
# 5-YEAR MONTHLY BACKTEST ENGINE (CALIBRATED)
# ============================================================================

class FiveYearBacktestEngine:
    """
    Runs monthly backtest signals going back 5 years.
    
    CRITICAL: Uses the FULL calibrated signal pipeline:
    - MacroRegimeFilter for regime-based confidence adjustment
    - MarketRelativeIndicators for relative strength
    - VolumeProfileAnalyzer for volume-based levels
    - SignalGenerator.generate() with all optional params
    
    This prevents the bull market bias that caused 97-100% win rates
    when using the basic SignalGenerator alone.
    """
    
    def __init__(self):
        self.resolver = SymbolResolver()
    
    def generate_monthly_dates(self, years: int = 5) -> List[str]:
        """Generate month-end dates going back N years."""
        dates = []
        today = date.today()
        
        for month_offset in range(years * 12):
            d = today - timedelta(days=month_offset * 30)
            if d.month == 12:
                month_end = date(d.year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(d.year, d.month + 1, 1) - timedelta(days=1)
            
            date_str = str(month_end)
            if date_str not in dates:
                dates.append(date_str)
        
        return sorted(dates)
    
    def run_ticker(self, ticker: str, monthly_dates: List[str],
                   vix_hist: Optional[pd.DataFrame] = None,
                   spy_hist: Optional[pd.DataFrame] = None) -> List[Dict]:
        """Run 5-year backtest for a single ticker using calibrated signals."""
        results = []
        resolved = self.resolver.resolve(ticker)
        
        try:
            # Fetch 6+ years of history (need 5y + buffer for forward returns)
            stock = yf.Ticker(resolved)
            hist = stock.history(period='7y')
            
            if hist.empty or len(hist) < 250:
                print(f"  {ticker}: Insufficient history ({len(hist) if not hist.empty else 0} days)")
                return results
            
            # Normalize index to plain dates (remove timezone)
            if hist.index.tz:
                hist.index = hist.index.tz_localize(None)
            
            # Fetch sector ETF for relative indicators
            sector_etf_map = {
                'RY': 'XLF', 'CM': 'XLF', 'TD': 'XLF', 'BNS': 'XLF', 'BMO': 'XLF',
                'CNR': 'XLI', 'ENB': 'XLE', 'TRP': 'XLE', 'SU': 'XLE',
                'MTY': 'XLY', 'TFII': 'XLI', 'QSR': 'XLY', 'ATD': 'XLY',
                'FEZ': 'EZU', 'IEV': 'EZU', 'SPEU': 'SPY', 'RGLD': 'GLD',
                'UL': 'XLP', 'WJX': 'XLI', 'PDC': 'XLE', 'PZA': 'XLRE',
                'CDZ': 'XLRE', 'BPF.UN': 'XLRE', 'SRV.UN': 'XLRE', 'KEG.UN': 'XLRE',
                'MX': 'XLI', 'RUS': 'XLI',
            }
            sector_etf = sector_etf_map.get(ticker, 'SPY')
            try:
                sector_hist = yf.Ticker(sector_etf).history(period='7y')
                if not sector_hist.empty and sector_hist.index.tz:
                    sector_hist.index = sector_hist.index.tz_localize(None)
            except:
                sector_hist = None
            
            for date_str in monthly_dates:
                target_date = pd.Timestamp(date_str)
                if target_date.tzinfo:
                    target_date = target_date.tz_localize(None)
                
                # Find nearest trading day <= target
                valid_dates = hist.index[hist.index <= target_date]
                if len(valid_dates) == 0:
                    continue
                target_date_actual = valid_dates[-1]
                
                idx = hist.index.get_indexer([target_date_actual], method='nearest')[0]
                if idx < 200:  # Need enough history for indicators
                    continue
                
                # Data up to this point (NO future data leak)
                hist_at_date = hist.iloc[:idx+1].copy()
                
                # Calculate base technical indicators
                indicators = TechnicalAnalyzer.calculate(hist_at_date)
                if not indicators:
                    continue
                
                # === CALIBRATED PIPELINE ===
                # 1. MacroRegimeFilter
                vix_value = None
                macro = None
                if vix_hist is not None and not vix_hist.empty:
                    vix_valid = vix_hist.index[vix_hist.index <= target_date_actual]
                    if len(vix_valid) > 0:
                        vix_value = float(vix_hist.loc[vix_valid[-1], 'Close'])
                
                market_for_macro = spy_hist if spy_hist is not None else hist_at_date
                macro = MacroRegimeFilter.analyze(hist_at_date, vix_value=vix_value, market_hist=market_for_macro)
                
                # 2. MarketRelativeIndicators
                relative = None
                if sector_hist is not None and not sector_hist.empty:
                    sector_valid = sector_hist.index[sector_hist.index <= target_date_actual]
                    if len(sector_valid) > 0:
                        sector_at_date = sector_hist.iloc[:sector_valid.get_loc(sector_valid[-1])+1]
                        relative = MarketRelativeIndicators.analyze(ticker, hist_at_date, sector_etf_hist=sector_at_date)
                
                # 3. VolumeProfileAnalyzer
                volume_profile = VolumeProfileAnalyzer.analyze(hist_at_date, lookback=min(60, len(hist_at_date)))
                
                # 4. Generate CALIBRATED signal
                signal = SignalGenerator.generate(
                    indicators,
                    macro=macro,
                    relative=relative,
                    volume_profile=volume_profile
                )
                
                # Price at signal
                price_at_signal = float(hist['Close'].iloc[idx])
                
                # Forward returns (using actual future data from the full history)
                price_1m = None
                price_3m = None
                price_6m = None
                ret_1m = None
                ret_3m = None
                ret_6m = None
                outcome_1m = None
                outcome_3m = None
                outcome_6m = None
                
                idx_1m = min(idx + 21, len(hist) - 1)
                idx_3m = min(idx + 63, len(hist) - 1)
                idx_6m = min(idx + 126, len(hist) - 1)
                
                if idx_1m > idx:
                    price_1m = float(hist['Close'].iloc[idx_1m])
                    ret_1m = ((price_1m / price_at_signal) - 1) * 100
                    outcome_1m = self._evaluate_outcome(signal['signal'], ret_1m)
                
                if idx_3m > idx:
                    price_3m = float(hist['Close'].iloc[idx_3m])
                    ret_3m = ((price_3m / price_at_signal) - 1) * 100
                    outcome_3m = self._evaluate_outcome(signal['signal'], ret_3m)
                
                if idx_6m > idx:
                    price_6m = float(hist['Close'].iloc[idx_6m])
                    ret_6m = ((price_6m / price_at_signal) - 1) * 100
                    outcome_6m = self._evaluate_outcome(signal['signal'], ret_6m)
                
                macro_regime = macro.get('regime', 'NEUTRAL') if macro else 'NEUTRAL'
                
                results.append({
                    'ticker': ticker,
                    'resolved_ticker': resolved,
                    'signal_date': date_str,
                    'signal': signal['signal'],
                    'raw_confidence': signal['confidence'],
                    'calibrated_confidence': signal['confidence'],
                    'strength': signal.get('strength', 'UNKNOWN'),
                    'buy_score': signal.get('buy_score', 0),
                    'sell_score': signal.get('sell_score', 0),
                    'price_at_signal': price_at_signal,
                    'price_1m_future': price_1m,
                    'price_3m_future': price_3m,
                    'price_6m_future': price_6m,
                    'actual_1m_return': ret_1m,
                    'actual_3m_return': ret_3m,
                    'actual_6m_return': ret_6m,
                    'outcome_1m': outcome_1m,
                    'outcome_3m': outcome_3m,
                    'outcome_6m': outcome_6m,
                    'timing_bucket': 'MONTH_END',
                    'macro_regime': macro_regime,
                    'vix_value': vix_value,
                })
            
            print(f"  {ticker}: {len(results)} monthly periods")
            
        except Exception as e:
            print(f"  {ticker}: Error — {e}")
            import traceback
            traceback.print_exc()
        
        return results
    
    def _evaluate_outcome(self, signal: str, actual_return: float) -> str:
        if signal == 'BUY':
            return 'WIN' if actual_return > 0 else 'LOSS'
        elif signal == 'SELL':
            return 'WIN' if actual_return < 0 else 'LOSS'
        return 'HOLD'
    
    def run_all(self, tickers: List[str], conn: sqlite3.Connection):
        """Run 5-year backtest for all tickers and store in DB."""
        monthly_dates = self.generate_monthly_dates(years=5)
        print(f"Running 5-year CALIBRATED backtest: {len(monthly_dates)} month-end dates × {len(tickers)} tickers")
        
        # Pre-fetch VIX and SPY for macro regime (done once for efficiency)
        print("Fetching VIX history...")
        try:
            vix_hist = yf.Ticker('^VIX').history(period='7y')
            if not vix_hist.empty and vix_hist.index.tz:
                vix_hist.index = vix_hist.index.tz_localize(None)
        except:
            vix_hist = None
        
        print("Fetching SPY history...")
        try:
            spy_hist = yf.Ticker('SPY').history(period='7y')
            if not spy_hist.empty and spy_hist.index.tz:
                spy_hist.index = spy_hist.index.tz_localize(None)
        except:
            spy_hist = None
        
        all_results = []
        for ticker in tickers:
            results = self.run_ticker(ticker, monthly_dates, vix_hist=vix_hist, spy_hist=spy_hist)
            all_results.extend(results)
        
        # Store in DB
        for r in all_results:
            conn.execute("""
                INSERT OR REPLACE INTO backtest_periods_5y
                (ticker, resolved_ticker, signal_date, signal, raw_confidence, calibrated_confidence,
                 strength, buy_score, sell_score, price_at_signal, price_1m_future, price_3m_future,
                 price_6m_future, actual_1m_return, actual_3m_return, actual_6m_return,
                 outcome_1m, outcome_3m, outcome_6m, timing_bucket, macro_regime, vix_value)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                r['ticker'], r['resolved_ticker'], r['signal_date'], r['signal'],
                r['raw_confidence'], r['calibrated_confidence'], r['strength'],
                r['buy_score'], r['sell_score'], r['price_at_signal'],
                r['price_1m_future'], r['price_3m_future'], r['price_6m_future'],
                r['actual_1m_return'], r['actual_3m_return'], r['actual_6m_return'],
                r['outcome_1m'], r['outcome_3m'], r['outcome_6m'],
                r['timing_bucket'], r['macro_regime'], r['vix_value']
            ))
        
        conn.commit()
        print(f"\nStored {len(all_results)} backtest periods")
        
        # Sanity check
        df = pd.DataFrame(all_results)
        if not df.empty:
            directional = df[df['signal'] != 'HOLD']
            if len(directional) > 0:
                overall_wr = (directional['outcome_1m'] == 'WIN').mean() * 100
                print(f"Overall 1M win rate: {overall_wr:.1f}%")
                if overall_wr > 90:
                    print("⚠️  WARNING: Win rate >90% suggests calibrated pipeline may not be working correctly!")
                    print("   Expected range: 40-70% depending on tickers and market regime.")
                else:
                    print(f"✅ Win rate in expected range ({overall_wr:.1f}%)")
        
        # Compute and store accuracy summaries
        self._compute_accuracy(all_results, conn)
    
    def _compute_accuracy(self, results: List[Dict], conn: sqlite3.Connection):
        """Compute signal accuracy by ticker and time period."""
        df = pd.DataFrame(results)
        if df.empty:
            return
        
        for ticker in df['ticker'].unique():
            tdf = df[df['ticker'] == ticker]
            
            for period, outcome_col in [('1m', 'outcome_1m'), ('3m', 'outcome_3m'), ('6m', 'outcome_6m')]:
                valid = tdf[tdf[outcome_col].notna() & (tdf[outcome_col] != 'HOLD')]
                if len(valid) == 0:
                    continue
                
                wins = len(valid[valid[outcome_col] == 'WIN'])
                losses = len(valid[valid[outcome_col] == 'LOSS'])
                holds = len(tdf[tdf[outcome_col] == 'HOLD'])
                total = wins + losses
                
                if total == 0:
                    continue
                
                win_rate = wins / total * 100
                
                win_conf = valid[valid[outcome_col] == 'WIN']['calibrated_confidence'].mean()
                loss_conf = valid[valid[outcome_col] == 'LOSS']['calibrated_confidence'].mean()
                spread = (win_conf - loss_conf) * 100 if not pd.isna(win_conf) and not pd.isna(loss_conf) else 0
                
                if win_rate >= 70 and spread > 5:
                    calibration = 'WELL_CALIBRATED'
                elif win_rate >= 50 and spread > 0:
                    calibration = 'ACCEPTABLE'
                elif win_rate < 50 and spread < 0:
                    calibration = 'POOR'
                else:
                    calibration = 'MIXED'
                
                conn.execute("""
                    INSERT OR REPLACE INTO signal_accuracy
                    (ticker, period_start, period_end, total_signals,
                     wins_1m, losses_1m, holds_1m, win_rate_1m,
                     wins_3m, losses_3m, win_rate_3m,
                     wins_6m, losses_6m, win_rate_6m,
                     avg_confidence, avg_win_confidence, avg_loss_confidence,
                     spread_1m, spread_3m, spread_6m, calibration)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ticker,
                    tdf['signal_date'].min(),
                    tdf['signal_date'].max(),
                    len(tdf),
                    wins if period == '1m' else 0,
                    losses if period == '1m' else 0,
                    holds if period == '1m' else 0,
                    win_rate if period == '1m' else 0,
                    wins if period == '3m' else 0,
                    losses if period == '3m' else 0,
                    win_rate if period == '3m' else 0,
                    wins if period == '6m' else 0,
                    losses if period == '6m' else 0,
                    win_rate if period == '6m' else 0,
                    float(tdf['calibrated_confidence'].mean()),
                    float(win_conf) if not pd.isna(win_conf) else 0,
                    float(loss_conf) if not pd.isna(loss_conf) else 0,
                    spread if period == '1m' else 0,
                    spread if period == '3m' else 0,
                    spread if period == '6m' else 0,
                    calibration,
                ))
        
        conn.commit()
        print("Accuracy summaries computed and stored")


# ============================================================================
# MAIN
# ============================================================================

def main():
    db_path = os.path.expanduser('~/.hermes/cache/analysis_results.db')
    conn = get_db()
    
    # 1. Expand schema
    print("=" * 80)
    print("EXPANDING DB SCHEMA")
    print("=" * 80)
    expand_db_schema(conn)
    
    # 2. Import portfolio
    print("\n" + "=" * 80)
    print("IMPORTING PORTFOLIO")
    print("=" * 80)
    with open('/tmp/portfolio_from_email.json', 'r') as f:
        portfolio = json.load(f)
    import_portfolio(conn, portfolio, source='email_import')
    
    # 3. Run 5-year CALIBRATED backtest
    print("\n" + "=" * 80)
    print("RUNNING 5-YEAR CALIBRATED BACKTEST")
    print("=" * 80)
    tickers = list(portfolio.keys())
    engine = FiveYearBacktestEngine()
    engine.run_all(tickers, conn)
    
    # 4. Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    for table in ['portfolio_holdings', 'backtest_periods_5y', 'signal_accuracy']:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count} records")
    
    print("\nSignal accuracy (1-month):")
    rows = conn.execute("""
        SELECT ticker, total_signals, win_rate_1m, spread_1m, calibration
        FROM signal_accuracy
        ORDER BY win_rate_1m DESC
    """).fetchall()
    
    print(f"  {'Ticker':<10} {'N':>4} {'Win%':>6} {'Spread':>8} {'Calibration'}")
    for r in rows:
        print(f"  {r[0]:<10} {r[1]:>4} {r[2]:>5.0f}% {r[3]:>+7.1f}% {r[4]}")
    
    conn.close()
    print(f"\nDatabase: {db_path}")


if __name__ == '__main__':
    main()
