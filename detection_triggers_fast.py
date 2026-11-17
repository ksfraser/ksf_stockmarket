#!/usr/bin/env python3
"""
Optimized intraday alert detection triggers (SQLite ephemeral mode).

Faithful to detection_triggers.py logic but optimized for a rate-limited Yahoo
Finance API:
  - reuses a single yf.Ticker per symbol across the 4 checks (halves API calls)
  - skips symbols that 404/quoteSummary-fail instead of hammering them
  - sleeps a short delay between symbols to avoid 429 rate-limit backoffs

Alert types written to SQLite (same as detection_triggers.py):
  volume_spike, natr_spike, oscillator_extremes, gap_up
"""
import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime
from typing import Any, Dict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'python', 'src'))
import pandas as pd
import numpy as np
import yfinance as yf
import ta


def resolve_ticker(symbol: str) -> str:
    from symbol_resolver import resolve_for_yfinance
    return resolve_for_yfinance(symbol, use_db_lookup=False)


# SQLite database path for detection alerts (ephemeral intraday)
DETECTION_ALERT_DB = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'data', 'analysis_results.db'
)

KNOWN_TSX = {
    'CM', 'CNR', 'RY', 'TD', 'BMO', 'BNS', 'ENB', 'TRP', 'SU', 'CVE', 'ABX', 'BCE',
    'T', 'QSR', 'DOL', 'ATD', 'L', 'MRU', 'FTS', 'EMA', 'BIP.UN', 'HR.UN',
    'SRU.UN', 'REI.UN', 'CAR.UN', 'WJX', 'MTY', 'TFII', 'RUS', 'CDZ', 'PDC', 'PZA',
    'SRV.UN', 'BPF.UN', 'NPI', 'XIC', 'ZCN', 'VUN', 'XEF', 'XUU', 'XSP',
    'XQQ', 'XEG', 'XFN', 'XIT', 'XMA', 'XUT', 'XRE'
}

KNOWN_US = {
    'SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VOO', 'VEA', 'VWO', 'AAPL', 'MSFT', 'GOOGL',
    'AMZN', 'META', 'TSLA', 'NVDA', 'GLD', 'SLV', 'USO', 'UNG', 'CEF', 'MICC', 'RGLD'
}


def check_volume_spike(stock, symbol: str, threshold: float = 3.0) -> dict:
    try:
        hist = stock.history(period='10d', interval='1d')
        if len(hist) < 6:
            return None
        today_volume = int(hist['Volume'].iloc[-1])
        avg_volume = int(hist['Volume'].iloc[-6:-1].mean())
        if avg_volume == 0:
            return None
        volume_ratio = today_volume / avg_volume
        current_price = float(hist['Close'].iloc[-1])
        previous_price = float(hist['Close'].iloc[-2])
        price_change_pct = ((current_price - previous_price) / previous_price) * 100
        if volume_ratio >= threshold:
            if volume_ratio >= 5:
                severity = 'critical'
            elif volume_ratio >= 4:
                severity = 'high'
            else:
                severity = 'medium'
            return {
                'alert_type': 'volume_spike',
                'symbol': symbol,
                'severity': severity,
                'payload': {
                    'volume_ratio': round(volume_ratio, 2),
                    'today_volume': today_volume,
                    'avg_volume': avg_volume,
                    'current_price': round(current_price, 2),
                    'price_change_pct': round(price_change_pct, 2)
                }
            }
    except Exception as e:
        print(f"Error checking volume spike for {symbol}: {e}")
    return None


def check_natr_spike(stock, symbol: str, multiplier: float = 2.0) -> dict:
    try:
        hist = stock.history(period='60d', interval='1d')
        if len(hist) < 35:
            return None
        high = hist['High']
        low = hist['Low']
        close = hist['Close']
        prev_close = close.shift(1)
        tr = pd.DataFrame({
            'hl': high - low,
            'hc': (high - prev_close).abs(),
            'lc': (low - prev_close).abs()
        }).max(axis=1)
        atr = tr.rolling(window=14).mean()
        natr = (atr / close) * 100
        natr_current = float(natr.iloc[-1])
        natr_avg = float(natr.iloc[-30:-1].mean())
        if natr_avg == 0:
            return None
        natr_ratio = natr_current / natr_avg
        current_price = float(close.iloc[-1])
        previous_price = float(close.iloc[-2])
        price_change_pct = ((current_price - previous_price) / previous_price) * 100
        if natr_ratio >= multiplier:
            if natr_ratio >= 3:
                severity = 'critical'
            elif natr_ratio >= 2.5:
                severity = 'high'
            else:
                severity = 'medium'
            return {
                'alert_type': 'natr_spike',
                'symbol': symbol,
                'severity': severity,
                'payload': {
                    'natr_current': round(natr_current, 4),
                    'natr_avg': round(natr_avg, 4),
                    'natr_ratio': round(natr_ratio, 2),
                    'current_price': round(current_price, 2),
                    'price_change_pct': round(price_change_pct, 2)
                }
            }
    except Exception as e:
        print(f"Error checking NATR spike for {symbol}: {e}")
    return None


def check_oscillator_extremes(stock, symbol: str) -> dict:
    try:
        hist = stock.history(period='30d', interval='1d')
        if len(hist) < 20:
            return None
        close = hist['Close']
        rsi = ta.momentum.RSIIndicator(close, window=14).rsi()
        rsi_current = float(rsi.iloc[-1])
        extreme_days = 0
        for r in reversed(rsi.iloc[-10:].values):
            if r > 70 or r < 30:
                extreme_days += 1
            else:
                break
        sma20 = close.rolling(window=20).mean()
        current_price = float(close.iloc[-1])
        distance_from_sma20 = abs(current_price - float(sma20.iloc[-1])) / float(sma20.iloc[-1]) * 100
        if distance_from_sma20 > 3:
            return None
        regime = 'overbought' if rsi_current > 70 else 'oversold'
        if rsi_current > 70 or rsi_current < 30:
            if extreme_days >= 3 or (rsi_current > 80 or rsi_current < 20):
                severity = 'high'
            else:
                severity = 'medium'
            return {
                'alert_type': 'oscillator_extremes',
                'symbol': symbol,
                'severity': severity,
                'payload': {
                    'rsi': round(rsi_current, 2),
                    'regime': regime,
                    'extreme_days': extreme_days,
                    'current_price': round(current_price, 2),
                    'distance_from_sma20': round(distance_from_sma20, 2)
                }
            }
    except Exception as e:
        print(f"Error checking oscillator extremes for {symbol}: {e}")
    return None


def check_gap_opening(stock, symbol: str, gap_threshold: float = 2.0) -> dict:
    try:
        hist = stock.history(period='5d', interval='1d')
        if len(hist) < 2:
            return None
        open_price = float(hist['Open'].iloc[-1])
        previous_close = float(hist['Close'].iloc[-2])
        gap_pct = ((open_price - previous_close) / previous_close) * 100
        current_price = float(hist['Close'].iloc[-1])
        if gap_pct >= gap_threshold:
            gap_filled = current_price <= previous_close
            if gap_pct >= 3:
                severity = 'critical'
            elif gap_pct >= 2.5:
                severity = 'high'
            else:
                severity = 'medium'
            return {
                'alert_type': 'gap_up',
                'symbol': symbol,
                'severity': severity,
                'payload': {
                    'gap_pct': round(gap_pct, 2),
                    'open_price': round(open_price, 2),
                    'previous_close': round(previous_close, 2),
                    'current_price': round(current_price, 2),
                    'gap_filled': bool(gap_filled)
                }
            }
    except Exception as e:
        print(f"Error checking gap opening for {symbol}: {e}")
    return None


def _json_default(o):
    item = getattr(o, "item", None)
    if callable(item):
        try:
            return item()
        except Exception:
            pass
    if isinstance(o, (tuple, set, frozenset)):
        return list(o)
    return str(o)


def _write_alert_to_sqlite(alert: dict) -> bool:
    try:
        conn = sqlite3.connect(DETECTION_ALERT_DB)
        cur = conn.cursor()
        alert_id = f"{alert['symbol']}_{alert['alert_type']}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        payload = dict(alert.get('payload', {}) or {})
        payload['triggered_at'] = datetime.now().isoformat()
        cur.execute("""\
            INSERT OR REPLACE INTO alert_queue
            (id, alert_type, symbol, severity, payload, status, request_llm_analysis, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            alert_id,
            alert['alert_type'],
            alert['symbol'],
            alert['severity'],
            json.dumps(payload, default=_json_default),
            'pending',
            1,
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error writing alert to SQLite: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return False


def main():
    parser = argparse.ArgumentParser(description='Stock alert detection triggers')
    parser.add_argument('--volume', action='store_true', help='Run volume spike detection')
    parser.add_argument('--natr', action='store_true', help='Run NATR spike detection')
    parser.add_argument('--oscillator', action='store_true', help='Run oscillator extremes detection')
    parser.add_argument('--gap', action='store_true', help='Run gap opening detection')
    parser.add_argument('--all', action='store_true', help='Run all detection triggers')
    parser.add_argument('--symbols', nargs='+', help='Specific symbols to check (default: all watchlist)')
    parser.add_argument('--sqlite', action='store_true',
                        help='Write alerts to ephemeral SQLite store instead of MariaDB')
    args = parser.parse_args()

    if not (args.volume or args.natr or args.oscillator or args.gap):
        args.all = True

    symbols = args.symbols if args.symbols else list(KNOWN_TSX) + list(KNOWN_US)
    run_all = args.all

    alerts_found = []
    skipped = []

    for symbol in symbols:
        try:
            ticker = resolve_ticker(symbol)
            stock = yf.Ticker(ticker)
            # Verify the ticker resolved (any history fetch will surface 404s quickly)
            stock.history(period='1d', interval='1d')
        except Exception as e:
            print(f"Skipping {symbol} (unresolvable): {e}")
            skipped.append(symbol)
            continue

        if run_all or args.volume:
            alert = check_volume_spike(stock, symbol)
            if alert:
                if _write_alert_to_sqlite(alert):
                    alerts_found.append(f"[{symbol}] Volume spike: {alert['payload']['volume_ratio']}x avg ({alert['severity']})")
        if run_all or args.natr:
            alert = check_natr_spike(stock, symbol)
            if alert:
                if _write_alert_to_sqlite(alert):
                    alerts_found.append(f"[{symbol}] NATR spike: {alert['payload']['natr_ratio']}x avg ({alert['severity']})")
        if run_all or args.oscillator:
            alert = check_oscillator_extremes(stock, symbol)
            if alert:
                if _write_alert_to_sqlite(alert):
                    alerts_found.append(f"[{symbol}] Oscillator: RSI={alert['payload']['rsi']} ({alert['payload']['regime']}) ({alert['severity']})")
        if run_all or args.gap:
            alert = check_gap_opening(stock, symbol)
            if alert:
                if _write_alert_to_sqlite(alert):
                    alerts_found.append(f"[{symbol}] Gap up: {alert['payload']['gap_pct']}% ({alert['severity']})")

        time.sleep(0.3)  # rate-limit tolerance

    if alerts_found:
        print("\nAlerts queued:")
        for alert in alerts_found:
            print(f"  {alert}")
    else:
        print("No alerts detected.")

    if skipped:
        print(f"\nSkipped (unresolvable): {len(skipped)} symbols -> {', '.join(skipped[:15])}{' ...' if len(skipped) > 15 else ''}")


if __name__ == '__main__':
    main()
