#!/usr/bin/env python3
"""
Async Alert Engine - Detect unusual conditions and request LLM analysis
=====================================================================

Architecture:
1. Detection scripts find anomalies (volume spikes, gap-ups, regime changes)
2. Write to `alert_queue` table with analysis request
3. Hermes monitors Discord/email channels
4. LLM/Hermes processes alerts and writes results to DB

Non-blocking: Detection → Queue → Notification → Async processing
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional


def create_alert(
    alert_type: str,
    symbol: str,
    severity: str = 'medium',
    payload: Dict = None,
    request_llm_analysis: bool = True
) -> Dict:
    """
    Create an alert that can be processed by Hermes/LLM.
    
    Args:
        alert_type: 'volume_spike', 'gap_up', 'regime_change', 'price_anomaly'
        symbol: The affected symbol
        severity: 'low', 'medium', 'high', 'critical'
        payload: Additional data (price, volume, indicators, etc.)
        request_llm_analysis: If True, send to queue for LLM examination
    """
    alert = {
        'id': f"{alert_type}_{symbol}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        'timestamp': datetime.now().isoformat(),
        'type': alert_type,
        'symbol': symbol,
        'severity': severity,
        'payload': payload or {},
        'status': 'pending',
        'request_llm_analysis': request_llm_analysis
    }
    
    # In a real implementation, write to MariaDB alert_queue table
    # and send notification via webhook/email
    
    return alert


def check_volume_anomaly(conn, symbol: str, current_volume: int, avg_volume: int) -> Optional[Dict]:
    """
    Check if volume is 3x+ normal and request LLM analysis.
    """
    ratio = current_volume / avg_volume if avg_volume > 0 else 0
    if ratio >= 3.0:
        return create_alert(
            alert_type='volume_spike',
            symbol=symbol,
            severity='high' if ratio >= 5 else 'medium',
            payload={'current_volume': current_volume, 'avg_volume': avg_volume, 'ratio': round(ratio, 2)},
            request_llm_analysis=True
        )
    return None


def check_gap_up(conn, symbol: str, open_price: float, prev_close: float) -> Optional[Dict]:
    """
    Check for gap-up opening (>2% above previous close).
    """
    gap_pct = (open_price - prev_close) / prev_close * 100 if prev_close > 0 else 0
    if gap_pct > 2.0:
        return create_alert(
            alert_type='gap_up',
            symbol=symbol,
            severity='high',
            payload={'open_price': open_price, 'prev_close': prev_close, 'gap_pct': round(gap_pct, 2)},
            request_llm_analysis=True
        )
    return None


def check_regime_change(current_regime: str, previous_regime: str, symbol: str) -> Optional[Dict]:
    """
    Check for regime change (Bull/Bear/Sideways transition).
    """
    if current_regime != previous_regime:
        return create_alert(
            alert_type='regime_change',
            symbol=symbol,
            severity='medium',
            payload={'from': previous_regime, 'to': current_regime},
            request_llm_analysis=True
        )
    return None


def send_to_hermes(alert: Dict, channel: str = 'discord') -> bool:
    """
    Send alert to Hermes-monitored channel.
    
    This is a one-way call - alert is written, Hermes observes and processes.
    No blocking wait for response.
    """
    # Would send via:
    # - Discord webhook to #stock-alerts
    # - Email to hermes@ksfraser.ca  
    # - Database insert to alert_queue
    
    # For now, log to file which can be monitored
    alert_file = f"/tmp/hermes_alerts/{alert['id']}.json"
    os.makedirs(os.path.dirname(alert_file), exist_ok=True)
    with open(alert_file, 'w') as f:
        json.dump(alert, f)
    
    return True


if __name__ == '__main__':
    print("Async Alert Engine Test")
    print("=" * 50)
    
    # Simulate a volume spike
    alert = check_volume_anomaly(None, 'AAPL', 5000000, 1000000)
    if alert:
        print(f"Alert triggered: {alert['type']} for {alert['symbol']}")
        print(f"Severity: {alert['severity']}")
        print(f"Payload: {alert['payload']}")
        print(f"Request LLM: {alert['request_llm_analysis']}")