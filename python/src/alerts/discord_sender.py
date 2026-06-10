#!/usr/bin/env python3
"""
Discord Alert Sender - Send alerts to #stock-sell-alerts channel
=============================================================

Uses Discord webhook API (no bot token needed for sending).
Hermes monitors the channel and responds.
"""

import os
import json
import requests
from datetime import datetime


def send_alert_to_discord(alert: dict, webhook_url: str = None) -> bool:
    """
    Send alert to Discord #stock-sell-alerts webhook.
    This is one-way - no response expected.
    """
    url = webhook_url or os.environ.get('DISCORD_ALERT_WEBHOOK')
    if not url:
        print("DISCORD_ALERT_WEBHOOK not configured")
        return False
        
    # Color coding
    colors = {
        'critical': 0xFF0000,
        'high': 0xFF6600,
        'medium': 0xFFFF00,
        'low': 0x00FF00
    }
    
    # Extract triggered_at from payload (when alert actually occurred)
    payload_data = alert.get('payload', {})
    triggered_at = payload_data.get('triggered_at', alert.get('timestamp', datetime.utcnow().isoformat()))
    
    payload = {
        'embeds': [{
            'title': f"📊 {alert.get('type', 'Alert').replace('_', ' ').title()}",
            'description': f"**{alert.get('symbol')}** - {alert.get('severity', 'medium')} severity",
            'color': colors.get(alert.get('severity'), 0x0099FF),
            'fields': [
                {'name': k.replace('_', ' ').title(), 'value': str(v), 'inline': True}
                for k, v in payload_data.items()
            ],
            'footer': {'text': f"Triggered: {triggered_at}"}
        }],
        'username': 'Stock Alert Bot',
        'avatar_url': 'https://ksfraser.ca/stockmarket/icon.png'
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 204
    except Exception as e:
        print(f"Failed to send Discord alert: {e}")
        return False


def send_analysis_response(symbol: str, alert_type: str, analysis: str, triggered_at: str = None, webhook_url: str = None) -> bool:
    """Send LLM analysis response back to Discord."""
    url = webhook_url or os.environ.get('DISCORD_ANALYSIS_WEBHOOK') or os.environ.get('DISCORD_ALERT_WEBHOOK')
    if not url:
        return False
        
    ts_info = f"\n\n> Triggered: {triggered_at}" if triggered_at else ""
    payload = {
        'content': f"**{symbol} - {alert_type.replace('_', ' ').title()} Analysis** 🔍{ts_info}\n\n{analysis}"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 204
    except Exception as e:
        print(f"Failed to send analysis: {e}")
        return False


if __name__ == '__main__':
    # Test alert
    test_alert = {
        'id': 'test_001',
        'type': 'volume_spike',
        'symbol': 'AAPL',
        'severity': 'high',
        'payload': {'volume': 5000000, 'avg_volume': 1000000, 'ratio': 5.0},
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Note: Webhook URL would be set in environment or vault
    print(f"Would send: {json.dumps(test_alert, indent=2)}")