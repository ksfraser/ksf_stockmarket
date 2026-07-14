#!/usr/bin/env python3
"""
Stock Alert Detection Triggers
Non-blocking detection scripts that queue alerts to MariaDB for async LLM processing.
"""

import argparse
import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict

import pandas as pd
import numpy as np
import pymysql
import yfinance as yf
import ta


def _find_config() -> str:
    for candidate in [
        os.path.join(os.path.dirname(__file__), '..', 'config.yaml'),
        os.path.join(os.path.dirname(__file__), '..', '..', 'config.yaml'),
        os.environ.get('KFSF_CONFIG', ''),
    ]:
        if candidate and os.path.isfile(candidate):
            return candidate
    return os.environ.get('KFSF_CONFIG', 'config.yaml')


def _secrets() -> Dict[str, Any]:
    try:
        from python.config_loader import Config
    except Exception:
        try:
            from config_loader import Config
        except Exception:
            return {}
    cfg = Config(_find_config())
    return dict(getattr(cfg, 'secrets', {}) or {})


MYSQL = {
    'host': os.environ.get('DB_HOST', 'ksfraser.ca'),
    'user': os.environ.get('DB_USER', 'ksfraser_stockmarket'),
    'password': (
        _secrets().get('db_password')
        or _secrets().get('db_pass')
        or os.environ.get('DB_PASSWORD')
        or os.environ.get('MYSQL_PASSWORD')
        or os.environ.get('DB_PASS', '')
    ),
    'database': os.environ.get('DB_NAME', 'ksfraser_stock_market'),
    'charset': 'utf8mb4',
}
if not MYSQL['password']:
    raise RuntimeError(
        "MariaDB password is not set. Provide DB_PASSWORD/DB_PASS in env, or store db_password in Ansible Vault/config.yaml."
    )

# Known ticker sets for TSX/NYSE disambiguation
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


def resolve_ticker(symbol: str) -> str:
    """Resolve symbol to proper format for yfinance."""
    from symbol_resolver import resolve_for_yfinance
    return resolve_for_yfinance(symbol)


def check_volume_spike(symbol: str, threshold: float = 3.0) -> dict:
    """
    Check for volume spike.
    Compares today's volume vs 5-day average (excluding today).
    Returns payload with volume_ratio, today_volume, avg_volume, current_price, price_change_pct.
    """
    try:
        ticker = resolve_ticker(symbol)
        stock = yf.Ticker(ticker)
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


def check_natr_spike(symbol: str, multiplier: float = 2.0) -> dict:
    """
    Check for NATR spike.
    NATR = (ATR / Close) * 100
    Fetches 60-day history for 30-day average baseline.
    Threshold: current NATR >= 2x average (predictive strength r=0.16@20d).
    """
    try:
        ticker = resolve_ticker(symbol)
        stock = yf.Ticker(ticker)
        hist = stock.history(period='60d', interval='1d')
        
        if len(hist) < 35:
            return None
        
        high = hist['High']
        low = hist['Low']
        close = hist['Close']
        
        # Calculate True Range
        prev_close = close.shift(1)
        tr = pd.DataFrame({
            'hl': high - low,
            'hc': (high - prev_close).abs(),
            'lc': (low - prev_close).abs()
        }).max(axis=1)
        
        # Calculate ATR (14-day)
        atr = tr.rolling(window=14).mean()
        
        # Calculate NATR
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


def check_oscillator_extremes(symbol: str) -> dict:
    """
    Check for oscillator extremes (RSI).
    Triggers when RSI > 70 (overbought) or < 30 (oversold).
    Also tracks extreme_days (consecutive days in extreme zone).
    Includes regime filter: price within 3% of SMA20 for favorable mean-reversion.
    """
    try:
        ticker = resolve_ticker(symbol)
        stock = yf.Ticker(ticker)
        hist = stock.history(period='30d', interval='1d')
        
        if len(hist) < 20:
            return None
        
        close = hist['Close']
        
        # Calculate RSI(14)
        rsi = ta.momentum.RSIIndicator(close, window=14).rsi()
        rsi_current = float(rsi.iloc[-1])
        
        # Count consecutive extreme days
        extreme_days = 0
        for r in reversed(rsi.iloc[-10:].values):
            if r > 70 or r < 30:
                extreme_days += 1
            else:
                break
        
        # Calculate SMA20 for regime filter
        sma20 = close.rolling(window=20).mean()
        current_price = float(close.iloc[-1])
        distance_from_sma20 = abs(current_price - float(sma20.iloc[-1])) / float(sma20.iloc[-1]) * 100
        
        # Regime filter: only trigger if within 3% of SMA20
        if distance_from_sma20 > 3:
            return None
        
        regime = 'overbought' if rsi_current > 70 else 'oversold'
        
        if (rsi_current > 70 or rsi_current < 30):
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


def check_gap_opening(symbol: str, gap_threshold: float = 2.0) -> dict:
    """
    Check for gap opening.
    Compares current open vs previous close.
    Triggers on gap_pct >= threshold (default 2%).
    """
    try:
        ticker = resolve_ticker(symbol)
        stock = yf.Ticker(ticker)
        hist = stock.history(period='5d', interval='1d')
        
        if len(hist) < 2:
            return None
        
        open_price = float(hist['Open'].iloc[-1])
        previous_close = float(hist['Close'].iloc[-2])
        gap_pct = ((open_price - previous_close) / previous_close) * 100
        current_price = float(hist['Close'].iloc[-1])
        
        if gap_pct >= gap_threshold:
            # Check if gap has been filled
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


def write_alert_to_db(alert: dict) -> bool:
    """Write alert to MariaDB alert_queue table."""
    try:
        conn = pymysql.connect(**MYSQL)
        cur = conn.cursor()
        
        alert_id = f"{alert['symbol']}_{alert['alert_type']}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        payload = dict(alert.get('payload', {}) or {})
        payload['triggered_at'] = datetime.now().isoformat()
        
        cur.execute("""
            INSERT INTO alert_queue (id, alert_type, symbol, severity, payload, status, request_llm_analysis)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                severity = VALUES(severity),
                payload = VALUES(payload),
                status = 'pending'
        """, (
            alert_id,
            alert['alert_type'],
            alert['symbol'],
            alert['severity'],
            json.dumps(payload, default=str),
            'pending',
            1  # All alert types should be queued for LLM analysis
        ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error writing alert to DB: {e}")
        return False


def get_watchlist() -> list:
    """Get list of symbols to monitor."""
    # Combined watchlist of TSX and US tickers
    symbols = list(KNOWN_TSX) + list(KNOWN_US)
    return symbols


def main():
    parser = argparse.ArgumentParser(description='Stock alert detection triggers')
    parser.add_argument('--volume', action='store_true', help='Run volume spike detection')
    parser.add_argument('--natr', action='store_true', help='Run NATR spike detection')
    parser.add_argument('--oscillator', action='store_true', help='Run oscillator extremes detection')
    parser.add_argument('--gap', action='store_true', help='Run gap opening detection')
    parser.add_argument('--all', action='store_true', help='Run all detection triggers')
    parser.add_argument('--symbols', nargs='+', help='Specific symbols to check (default: all watchlist)')
    args = parser.parse_args()
    
    # Determine which triggers to run
    run_all = args.all or not (args.volume or args.natr or args.oscillator or args.gap)
    
    symbols = args.symbols if args.symbols else get_watchlist()
    
    alerts_found = []
    
    for symbol in symbols:
        if run_all or args.volume:
            alert = check_volume_spike(symbol)
            if alert:
                if write_alert_to_db(alert):
                    alerts_found.append(f"[{symbol}] Volume spike: {alert['payload']['volume_ratio']}x avg ({alert['severity']})")
        
        if run_all or args.natr:
            alert = check_natr_spike(symbol)
            if alert:
                if write_alert_to_db(alert):
                    alerts_found.append(f"[{symbol}] NATR spike: {alert['payload']['natr_ratio']}x avg ({alert['severity']})")
        
        if run_all or args.oscillator:
            alert = check_oscillator_extremes(symbol)
            if alert:
                if write_alert_to_db(alert):
                    alerts_found.append(f"[{symbol}] Oscillator: RSI={alert['payload']['rsi']} ({alert['payload']['regime']}) ({alert['severity']})")
        
        if run_all or args.gap:
            alert = check_gap_opening(symbol)
            if alert:
                if write_alert_to_db(alert):
                    alerts_found.append(f"[{symbol}] Gap up: {alert['payload']['gap_pct']}% ({alert['severity']})")
    
    if alerts_found:
        print("\nAlerts queued:")
        for alert in alerts_found:
            print(f"  {alert}")
    else:
        print("No alerts detected.")


if __name__ == '__main__':
    main()