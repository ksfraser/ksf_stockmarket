#!/usr/bin/env python3
"""
Daily Investment Monitor — Fully Standalone
=============================================
No LLM. No skill loading. Just Python.
Runs technical analysis on all portfolio holdings and outputs a formatted report.

Usage:
  python3 daily_monitor_standalone.py
  python3 daily_monitor_standalone.py --output /tmp/report.txt
  python3 daily_monitor_standalone.py --ticker RY
  python3 daily_monitor_standalone.py --optimize-only
"""

import sys
import os
import json
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta

# ── Path setup ──────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Project root must be on the path so `config` (config/db.py) is importable,
# since src/db/connection.py does `from config.db import get_mariadb_config`.
sys.path.insert(0, SCRIPT_DIR)
for p in ['src', 'src/indicators', 'src/delivery', 'src/analysis', 'src/db', 'src/optimization']:
    sys.path.insert(0, os.path.join(SCRIPT_DIR, p))

# ── Imports ──────────────────────────────────────────────────────────────────
from common.market_data import get_ohlcv, get_info

from investment_monitor import SymbolResolver, TechnicalAnalyzer
from analysis_db import get_db
from weight_optimizer import (
    WeightedSignalGenerator, WeightOptimizer, RollingCoherenceScorer,
    init_weight_tables, DEFAULT_WEIGHTS
)

# ── Portfolio ────────────────────────────────────────────────────────────────
PORTFOLIO_TICKERS = [
    'RY', 'CM', 'CNR', 'BPF.UN', 'SRV.UN', 'CDZ', 'PZA',
    'WJX', 'MTY', 'TFII', 'RUS', 'PDC',
    'FEZ', 'IEV', 'SPEU', 'MX', 'RGLD', 'UL'
]

MIN_CONFIDENCE = 50.0


def fetch_price_data(ticker, period='6mo'):
    """Fetch price data for a ticker."""
    resolver = SymbolResolver()
    resolved = resolver.resolve(ticker)
    try:
        hist = get_ohlcv(resolved, period)
        if hist.empty or len(hist) < 30:
            return None
        hist.index = hist.index.tz_localize(None) if hist.index.tz else hist.index
        info = get_info(resolved)
        return {
            'ticker': ticker,
            'resolved': resolved,
            'hist': hist,
            'name': info.get('longName', ticker),
            'price': info.get('currentPrice', info.get('regularMarketPrice', hist['Close'].iloc[-1])),
            'currency': info.get('currency', 'CAD'),
        }
    except Exception as e:
        return {'ticker': ticker, 'error': str(e)}


def analyze_ticker(ticker, db_conn):
    """Run full technical analysis on a ticker."""
    data = fetch_price_data(ticker)
    if data is None or 'error' in data:
        return {'ticker': ticker, 'signal': 'ERROR', 'confidence': 0,
                'error': data.get('error', 'No data') if data else 'Fetch failed'}

    hist = data['hist']
    price = data['price']

    # Technical indicators
    indicators = TechnicalAnalyzer.calculate(hist)

    # Weighted signal
    weights = WeightedSignalGenerator(db_conn).get_weights(ticker)
    signal_result = generate_signal(indicators, weights)

    # Build result
    change_1d = ((hist['Close'].iloc[-1] / hist['Close'].iloc[-2]) - 1) * 100 if len(hist) >= 2 else 0

    return {
        'ticker': ticker,
        'name': data['name'],
        'price': round(price, 2),
        'change_1d': round(change_1d, 2),
        'signal': signal_result['signal'],
        'confidence': round(signal_result['confidence'], 1),
        'strength': signal_result.get('strength', ''),
        'reasons': signal_result.get('reasons', []),
        'buy_score': round(signal_result.get('buy_score', 0), 3),
        'sell_score': round(signal_result.get('sell_score', 0), 3),
    }


def generate_signal(indicators, weights):
    """Generate buy/sell signal from indicators and weights."""
    buy_score = 0.0
    sell_score = 0.0
    reasons = []

    # MA Alignment
    align = indicators.get('ma_alignment', '')
    align_dur = indicators.get('ma_alignment_duration', 0)
    w = weights.get('MA_ALIGN', DEFAULT_WEIGHTS.get('MA_ALIGN', 0.30))
    if align_dur < 20:
        w *= 0.7
    if align == 'BULLISH':
        c = min(w + align_dur / 200, w * 1.5)
        buy_score += c
        reasons.append(f"Bullish MA alignment ({align_dur}d)")
    elif align == 'BEARISH':
        c = min(w + align_dur / 200, w * 1.5)
        sell_score += c
        reasons.append(f"Bearish MA alignment ({align_dur}d)")

    # RSI
    rsi = indicators.get('rsi')
    if rsi and not np.isnan(rsi):
        w = weights.get('RSI', DEFAULT_WEIGHTS.get('RSI', 0.15))
        if rsi < 30:
            buy_score += w
            reasons.append(f"RSI oversold ({rsi:.1f})")
        elif rsi > 70:
            sell_score += w
            reasons.append(f"RSI overbought ({rsi:.1f})")

    # MACD
    macd = indicators.get('macd')
    macd_sig = indicators.get('macd_signal')
    if macd is not None and macd_sig is not None:
        w = weights.get('MACD', DEFAULT_WEIGHTS.get('MACD', 0.12))
        if macd > macd_sig:
            buy_score += w * 0.5
            reasons.append("MACD bullish")
        else:
            sell_score += w * 0.5
            reasons.append("MACD bearish")

    # SMA200
    sma200 = indicators.get('sma_200')
    sma20 = indicators.get('sma_20')
    if sma200 and sma20 and not np.isnan(sma200) and not np.isnan(sma20):
        w = weights.get('SMA200', DEFAULT_WEIGHTS.get('SMA200', 0.10))
        if sma20 > sma200:
            buy_score += w * 0.5
            reasons.append("Price above SMA200")
        else:
            sell_score += w * 0.5
            reasons.append("Price below SMA200")

    # Determine signal
    total = buy_score + sell_score
    if total == 0:
        signal = 'HOLD'
        confidence = 50.0
    elif buy_score > sell_score * 1.5:
        signal = 'BUY'
        confidence = min(buy_score / (total + 0.01) * 100, 95)
    elif sell_score > buy_score * 1.5:
        signal = 'SELL'
        confidence = min(sell_score / (total + 0.01) * 100, 95)
    else:
        signal = 'HOLD'
        confidence = 50.0

    # Strength
    if confidence >= 75:
        strength = 'STRONG'
    elif confidence >= 60:
        strength = 'MODERATE'
    else:
        strength = 'WEAK'

    return {
        'signal': signal,
        'confidence': confidence,
        'strength': strength,
        'buy_score': buy_score,
        'sell_score': sell_score,
        'reasons': reasons,
    }


def format_report(results):
    """Format results into a readable report."""
    lines = []
    lines.append(f"═══ DAILY INVESTMENT MONITOR — {datetime.now().strftime('%Y-%m-%d %H:%M')} ═══")
    lines.append(f"   {len(results)} holdings scanned")
    lines.append("")

    # Signals
    signals = [r for r in results if r.get('signal') in ('BUY', 'SELL') and r.get('confidence', 0) >= MIN_CONFIDENCE]
    errors = [r for r in results if r.get('signal') == 'ERROR']
    delisted_results = [r for r in results if r.get('signal') == 'DELISTED']

    if signals:
        lines.append(f"─── {len(signals)} SIGNAL(S) ≥ {MIN_CONFIDENCE}% ───")
        for s in sorted(signals, key=lambda x: x.get('confidence', 0), reverse=True):
            emoji = "🟢" if s['signal'] == 'BUY' else "🔴"
            lines.append(f"  {emoji} {s['ticker']:8s}  {s['signal']:4s}  {s.get('confidence', 0):.0f}%  ${s.get('price', 0):.2f}  {s.get('strength', '')}")
            for r in s.get('reasons', [])[:3]:
                lines.append(f"         • {r}")
        lines.append("")

    if delisted_results:
        lines.append(f"─── DELISTED ({len(delisted_results)}) ───")
        for d in delisted_results:
            lines.append(f"  🔴 {d['ticker']}")
        lines.append("")

    if errors:
        lines.append(f"─── ERRORS ({len(errors)}) ───")
        for e in errors:
            lines.append(f"  ⚠️  {e['ticker']}: {e.get('error', 'Unknown')}")
        lines.append("")

    # Full table
    lines.append("─── ALL HOLDINGS ───")
    lines.append(f"  {'Ticker':8s} {'Signal':7s} {'Conf':>5s} {'Price':>8s} {'1D%':>7s}")
    lines.append(f"  {'─'*8} {'─'*7} {'─'*5} {'─'*8} {'─'*7}")
    for r in sorted(results, key=lambda x: x.get('confidence', 0), reverse=True):
        if r.get('signal') == 'DELISTED':
            lines.append(f"  {r['ticker']:8s} 🔴 DELISTED")
            continue
        if r.get('signal') == 'ERROR':
            lines.append(f"  {r['ticker']:8s} ⚠️  ERROR")
            continue
        sig = r.get('signal', 'HOLD')
        emoji = "🟢" if sig == 'BUY' else ("🔴" if sig == 'SELL' else "⚪")
        lines.append(f"  {r['ticker']:8s} {emoji}{sig:6s} {r.get('confidence', 0):4.0f}%  ${r.get('price', 0):7.2f}  {r.get('change_1d', 0):+.1f}%")

    lines.append("")
    lines.append(f"── {datetime.now().strftime('%H:%M:%S')} ──")
    return '\n'.join(lines)


def optimize_weights(db_conn):
    """Update per-ticker weights."""
    init_weight_tables(db_conn)
    optimizer = WeightOptimizer(db_conn)
    changes = optimizer.optimize_all(PORTFOLIO_TICKERS, months_back=12)
    print(f"Weight optimization complete — {len(changes)} ticker(s) adjusted")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=str, help='Output file path')
    parser.add_argument('--ticker', type=str, help='Single ticker')
    parser.add_argument('--optimize-only', action='store_true')
    parser.add_argument('--min-confidence', type=float, default=MIN_CONFIDENCE)
    args = parser.parse_args()

    db_conn = get_db()

    if args.optimize_only:
        optimize_weights(db_conn)
        db_conn.close()
        return

    tickers = [args.ticker] if args.ticker else PORTFOLIO_TICKERS

    # ── Filter out confirmed delisted symbols ────────────────────────────────
    delisted = set()
    try:
        delisted_rows = db_conn.execute(
            "SELECT symbol FROM symbol_status WHERE status = 'delisted'"
        ).fetchall()
        delisted = set(r[0] for r in delisted_rows)
    except Exception:
        pass  # Table may not exist yet
    
    skipped = [t for t in tickers if t in delisted]
    active_tickers = [t for t in tickers if t not in delisted]
    
    if skipped:
        print(f"  Skipping {len(skipped)} delisted: {', '.join(skipped)}", file=sys.stderr)

    # ── Run analysis on active symbols ──────────────────────────────────────
    results = []
    for ticker in active_tickers:
        result = analyze_ticker(ticker, db_conn)
        results.append(result)
        status = result.get('signal', '?')
        conf = result.get('confidence', 0)
        print(f"  {ticker:8s} → {status:4s} {conf:.0f}%", file=sys.stderr)

    # Add skipped tickers as DELISTED in results
    for ticker in skipped:
        results.append({'ticker': ticker, 'signal': 'DELISTED', 'confidence': 0})

    db_conn.close()

    report = format_report(results)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"Report saved to {args.output} ({len(results)} tickers)", file=sys.stderr)

    print(report)


if __name__ == '__main__':
    main()
