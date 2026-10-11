#!/usr/bin/env python3
"""
Timing-Aware Backtest Analysis
Runs the portfolio backtest, classifies each period by timing bucket,
stores results in the analysis DB, and generates a timing report.
"""

import sys
import json
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from investment_monitor import InvestmentMonitor, SymbolResolver
from analysis_db import (
    get_db, classify_timing_bucket, compute_timing_analysis,
    compute_ticker_calibration, generate_timing_report
)
import yfinance as yf

def main():
    # Load portfolio
    with open('/tmp/portfolio_from_email.json', 'r') as f:
        portfolio_shares = json.load(f)
    
    portfolio = {sym: {'shares': s, 'cost_basis': 0} for sym, s in portfolio_shares.items()}
    
    # Initialize monitor and fetch data
    monitor = InvestmentMonitor()
    monitor.portfolio = portfolio
    tickers = list(portfolio.keys())
    
    print(f"Analyzing {len(tickers)} positions...")
    monitor.fetch_all_data(tickers)
    monitor.run_backtests(tickers)
    
    # Get earnings dates for timing classification
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
    
    # Store in DB
    conn = get_db()
    
    # Create analysis run record
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
        'v4',
        hash(frozenset(portfolio.keys())) % 100000,
        json.dumps({'lookback_months': [12, 9, 6, 3, 2, 1], 'timing_aware': True}),
        len(tickers),
        macro_regime,
        vix_value,
        'Timing-aware backtest with earnings, month-end, quarter-end, tax season classification'
    ))
    run_id = cursor.lastrowid
    print(f"Analysis run ID: {run_id}")
    
    # Store backtest periods with timing classification
    for ticker in tickers:
        bt = monitor.backtest_data.get(ticker, {})
        if not bt or 'error' in bt or not bt.get('periods'):
            continue
        
        earnings_dates = earnings_map.get(ticker, [])
        
        for p in bt['periods']:
            timing = classify_timing_bucket(p['date'], earnings_dates)
            
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
                p['confidence'],  # raw
                p['confidence'],  # calibrated (same for now, will be updated)
                1.0,  # multiplier
                macro_regime,
                'UNKNOWN',  # strength from backtest
                p.get('buy_score', 0),
                p.get('sell_score', 0),
                p['actual_1m_return'],
                p['outcome'],
                timing['timing_bucket'],
                timing['days_to_earnings'],
                timing['days_to_month_end'],
                timing['is_tax_season']
            ))
    
    # Store current signals
    report = monitor.generate_report()
    for ticker, h in report.get('holdings', {}).items():
        sig = h.get('signal', {})
        conn.execute("""
            INSERT OR REPLACE INTO signals
            (run_id, ticker, signal_date, signal, confidence, strength, buy_score, sell_score,
             macro_regime, confidence_multiplier, relative_strength, market_correlation,
             volume_poc, volume_vwap, price_vs_vwap, trend_duration, has_divergence_conflict,
             min_alignment_met, reasons_json, details_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            ticker,
            datetime.now().strftime('%Y-%m-%d'),
            sig.get('signal', 'HOLD'),
            sig.get('confidence', 0),
            sig.get('strength', 'UNKNOWN'),
            sig.get('buy_score', 0),
            sig.get('sell_score', 0),
            sig.get('macro_regime', 'UNKNOWN'),
            sig.get('confidence_multiplier', 1.0),
            h.get('market_relative', {}).get('relative_strength', 'UNKNOWN') if h.get('market_relative') else 'UNKNOWN',
            h.get('market_relative', {}).get('correlation_60d') if h.get('market_relative') else None,
            h.get('volume_profile', {}).get('poc') if h.get('volume_profile') else None,
            h.get('volume_profile', {}).get('vwap') if h.get('volume_profile') else None,
            h.get('volume_profile', {}).get('price_vs_vwap') if h.get('volume_profile') else None,
            sig.get('indicators', {}).get('ma_alignment_duration', 0),
            1 if any('CONFLICT' in d for d in sig.get('details', [])) else 0,
            1 if (sig.get('indicators', {}).get('ma_alignment_duration', 0) or 0) >= 20 else 0,
            json.dumps(sig.get('reasons', [])),
            json.dumps(sig.get('details', []))
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
    
    # Store ticker summaries
    ticker_df = compute_ticker_calibration(conn, run_id)
    for _, row in ticker_df.iterrows():
        # Find best/worst timing buckets for this ticker
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
    
    conn.commit()
    
    # Generate and print timing report
    report_text = generate_timing_report(conn, run_id)
    print(report_text)
    
    # Save report
    with open('/tmp/timing_analysis_report.txt', 'w') as f:
        f.write(report_text)
    
    print(f"\nReport saved to /tmp/timing_analysis_report.txt")
    print(f"Database: ~/.hermes/cache/analysis_results.db (run_id={run_id})")
    
    conn.close()


if __name__ == '__main__':
    import pandas as pd  # needed for timing report
    main()
