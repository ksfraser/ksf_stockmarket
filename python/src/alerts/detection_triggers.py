#!/usr/bin/env python3
"""
Alert Triggers - Detection functions that queue for LLM analysis
===========================================================

Uses existing infrastructure:
- llm_analyzer.py for LLM calls
- db_connector.py for MariaDB
- Discord webhook/email for notifications
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, List

# Import from existing codebase
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from db_connector import get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Alert types and their configurations
ALERT_CONFIG = {
    'volume_spike': {
        'threshold_ratio': 3.0,
        'critical_ratio': 5.0,
        'description': 'Unusual volume detected'
    },
    'natr_spike': {
        'threshold_ratio': 2.0,
        'description': 'Volatility spike (NATR)'
    },
    'oscillator_extreme': {
        'rsi_overbought': 70,
        'rsi_oversold': 30,
        'description': 'RSI overbought/oversold'
    },
    'gap_up': {
        'threshold_pct': 0.02,
        'description': 'Gap up opening'
    },
    'regime_change': {
        'description': 'Market regime transition detected'
    }
}


def check_volume_spike(cursor, symbol: str, date: str) -> Optional[Dict]:
    """
    Check if current volume is 3x+ average.
    Returns alert dict if triggered.
    """
    cursor.execute("""
        SELECT v.volume, s.avg_volume_30d
        FROM stockprices v
        JOIN stockinfo s ON s.stocksymbol = v.symbol
        WHERE v.symbol = %s AND v.date = %s
    """, (symbol, date))
    
    row = cursor.fetchone()
    if not row or not row.get('avg_volume_30d'):
        return None
        
    ratio = row['volume'] / row['avg_volume_30d']
    if ratio >= ALERT_CONFIG['volume_spike']['threshold_ratio']:
        severity = 'critical' if ratio >= ALERT_CONFIG['volume_spike']['critical_ratio'] else 'high'
        return {
            'id': f"volume_spike_{symbol}_{datetime.now().strftime('%Y%m%d%H%M')}",
            'timestamp': datetime.now().isoformat(),
            'type': 'volume_spike',
            'symbol': symbol,
            'severity': severity,
            'payload': {
                'current_volume': row['volume'],
                'avg_volume': row['avg_volume_30d'],
                'ratio': round(ratio, 2)
            },
            'request_llm_analysis': True
        }
    return None


def check_natr_spike(cursor, symbol: str, date: str) -> Optional[Dict]:
    """
    Check NATR (Normalized Average True Range) spike.
    From correlation study: NATR only predictive indicator (r=0.16@20d).
    """
    cursor.execute("""
        SELECT natr_20d, natr_avg_20d
        FROM technical_indicators 
        WHERE symbol = %s AND date = %s
    """, (symbol, date))
    
    row = cursor.fetchone()
    if not row or not row.get('natr_avg_20d'):
        return None
        
    ratio = row['natr_20d'] / row['natr_avg_20d'] if row['natr_avg_20d'] > 0 else 0
    if ratio >= ALERT_CONFIG['natr_spike']['threshold_ratio']:
        return {
            'id': f"natr_spike_{symbol}_{datetime.now().strftime('%Y%m%d%H%M')}",
            'timestamp': datetime.now().isoformat(),
            'type': 'natr_spike',
            'symbol': symbol,
            'severity': 'medium',
            'payload': {
                'natr_20d': row['natr_20d'],
                'natr_avg': row['natr_avg_20d'],
                'ratio': round(ratio, 2)
            },
            'request_llm_analysis': True  # NATR is predictive - worth LLM analysis
        }
    return None


def check_oscillator_extremes(cursor, symbol: str, date: str) -> Optional[Dict]:
    """
    Check RSI for overbought/oversold conditions.
    Oscillators = regime filters not direction (from study).
    """
    cursor.execute("""
        SELECT rsi_20d, stoch_k, stoch_d
        FROM technical_indicators 
        WHERE symbol = %s AND date = %s
    """, (symbol, date))
    
    row = cursor.fetchone()
    if not row:
        return None
        
    rsi = row.get('rsi_20d', 50)
    cfg = ALERT_CONFIG['oscillator_extreme']
    
    extreme = None
    if rsi >= cfg['rsi_overbought']:
        extreme = 'overbought'
    elif rsi <= cfg['rsi_oversold']:
        extreme = 'oversold'
        
    if extreme:
        return {
            'id': f"osc_extreme_{symbol}_{datetime.now().strftime('%Y%m%d%H%M')}",
            'timestamp': datetime.now().isoformat(),
            'type': 'oscillator_extreme',
            'symbol': symbol,
            'severity': 'low',  # Not predictive, just informational
            'payload': {
                'rsi_20d': rsi,
                'stoch_k': row.get('stoch_k'),
                'stoch_d': row.get('stoch_d'),
                'extreme': extreme
            },
            'request_llm_analysis': False  # Just notify, no LLM needed
        }
    return None


def check_gap_opening(cursor, symbol: str, date: str) -> Optional[Dict]:
    """
    Check for gap up/down at market open.
    """
    cursor.execute("""
        SELECT p.open_price, p.prev_close
        FROM stockprices p
        WHERE p.symbol = %s AND p.date = %s
    """, (symbol, date))
    
    row = cursor.fetchone()
    if not row or not row.get('prev_close'):
        return None
        
    gap_pct = (row['open_price'] - row['prev_close']) / row['prev_close']
    if abs(gap_pct) >= ALERT_CONFIG['gap_up']['threshold_pct']:
        return {
            'id': f"gap_{symbol}_{datetime.now().strftime('%Y%m%d%H%M')}",
            'timestamp': datetime.now().isoformat(),
            'type': 'gap_up',
            'symbol': symbol,
            'severity': 'high',
            'payload': {
                'open_price': row['open_price'],
                'prev_close': row['prev_close'],
                'gap_pct': round(gap_pct * 100, 2)
            },
            'request_llm_analysis': True
        }
    return None


def write_alert_to_queue(conn, alert: Dict) -> bool:
    """
    Write alert to MariaDB alert_queue table.
    Uses SQL schema from sql/alert_system.sql
    """
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO alert_queue 
            (id, alert_type, symbol, severity, payload, status, request_llm_analysis)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            severity = VALUES(severity),
            payload = VALUES(payload),
            status = VALUES(status)
        """, (
            alert['id'],
            alert['type'],
            alert['symbol'],
            alert['severity'],
            json.dumps(alert['payload']),
            alert['status'],
            alert['request_llm_analysis']
        ))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to write alert to queue: {e}")
        return False


def send_discord_webhook(alert: Dict, webhook_url: str = None) -> bool:
    """
    Send alert to Discord webhook (non-blocking).
    Hermes monitors and responds.
    """
    try:
        import requests
        
        # Use webhook URL from config or environment
        url = webhook_url or os.environ.get('DISCORD_ALERT_WEBHOOK')
        if not url:
            logger.warning("No Discord webhook URL configured")
            return False
            
        # Format for Discord
        embed = {
            'embeds': [{
                'title': f"📊 {alert['type'].replace('_', ' ').title()}",
                'description': f"**{alert['symbol']}** - {alert['severity']} severity",
                'color': 0xFF0000 if alert['severity'] in ['critical', 'high'] else 0xFFFF00,
                'fields': [
                    {'name': k, 'value': str(v), 'inline': True}
                    for k, v in alert['payload'].items()
                ],
                'timestamp': alert['timestamp']
            }]
        }
        
        requests.post(url, json=embed, timeout=5)
        return True
    except Exception as e:
        logger.error(f"Failed to send Discord webhook: {e}")
        return False


def run_all_triggers(symbols: List[str] = None, date: str = None):
    """
    Run all detection triggers for given symbols.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    if not symbols:
        cursor.execute("SELECT stocksymbol FROM stockinfo WHERE is_active = 1 LIMIT 50")
        symbols = [row['stocksymbol'] for row in cursor.fetchall()]
    
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
        
    alerts_triggered = []
    
    for symbol in symbols:
        # Check all triggers
        for trigger_fn in [check_volume_spike, check_natr_spike, check_oscillator_extremes, check_gap_opening]:
            alert = trigger_fn(cursor, symbol, date)
            if alert:
                alert['triggered_at'] = datetime.now().isoformat()  # Add trigger timestamp
                if write_alert_to_queue(conn, alert):
                    alerts_triggered.append(alert)
                    if alert['request_llm_analysis']:
                        send_discord_webhook(alert)
                        logger.info(f"Alert queued: {alert['type']} for {symbol}")
    
    cursor.close()
    conn.close()
    
    return alerts_triggered


if __name__ == '__main__':
    # Test run
    alerts = run_all_triggers(['AAPL', 'MSFT', 'RY.TO'], '2025-01-15')
    print(f"Alerts triggered: {len(alerts)}")