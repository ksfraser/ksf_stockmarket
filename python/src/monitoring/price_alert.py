#!/usr/bin/env python3
"""
Price Alert Monitor — Modular Version
====================================
Checks current prices against configured thresholds.
"""

import sys
import os
import json
import argparse
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import yfinance as yf
from database import get_connection, log_monitoring_run


def get_active_alerts() -> List[Dict]:
    """Fetch all active price alerts from database."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, ticker, alert_type, threshold_value, trailing_stop_price, 
                       trailing_limit_price, notes
                FROM price_alerts 
                WHERE active = 1
                ORDER BY ticker
            """)
            return cur.fetchall()
    finally:
        conn.close()


def check_alert(alert: Dict) -> Optional[Dict]:
    """Check if an alert condition is triggered."""
    try:
        ticker = alert['ticker']
        stock = yf.Ticker(ticker.replace('.UN', '-UN.TO') if '.UN' in ticker else ticker)
        hist = stock.history(period='1d', interval='1d')
        
        if hist.empty:
            return None
        
        current_price = float(hist['Close'].iloc[-1])
        
        # Check alert type
        if alert['alert_type'] == 'ABOVE' and current_price > alert['threshold_value']:
            return {'triggered': True, 'price': current_price, 'alert': alert}
        elif alert['alert_type'] == 'BELOW' and current_price < alert['threshold_value']:
            return {'triggered': True, 'price': current_price, 'alert': alert}
        elif alert['alert_type'] == 'TRAILING_STOP':
            # Trailing stop logic would go here
            pass
            
        return {'triggered': False, 'price': current_price, 'alert': alert}
    except Exception as e:
        return {'triggered': False, 'error': str(e), 'alert': alert}


def run_price_alert_check() -> int:
    """Run price alert check. Returns exit code."""
    alerts = get_active_alerts()
    
    run_id = log_monitoring_run('price_alert', 'running', symbol_count=len(alerts))
    
    results = []
    triggered = []
    
    for alert in alerts:
        result = check_alert(alert)
        if result:
            results.append(result)
            if result.get('triggered'):
                triggered.append(result)
    
    log_monitoring_run(run_id, 'success', alert_count=len(triggered))
    
    if triggered:
        print(f"🔴 PRICE ALERT — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        for t in triggered:
            print(f"   {t['alert']['ticker']}: ${t['price']:.2f} "
                  f"(threshold: ${t['alert']['threshold_value']})")
        return 1
    
    print(f"✅ No price alerts triggered — {datetime.now().strftime('%H:%M')}")
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Price Alert Monitor')
    parser.add_argument('--json', action='store_true', help='Output JSON')
    args = parser.parse_args()
    
    run_price_alert_check()