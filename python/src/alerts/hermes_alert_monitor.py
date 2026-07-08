#!/usr/bin/env python3
"""
Hermes Alert Monitor - Main monitoring daemon
============================================

Polls local SQLite staging for pending alerts, triggers LLM analysis,
promotes completed alerts into MariaDB.

Run as: python3 hermes_alert_monitor.py --daemon
Or via cron: hermes_alert_monitor.py --once
"""

import json
import logging
import os
import pymysql
import time
import argparse
from datetime import datetime

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from alerts.sqlite_staging import fetch_pending_staging, mark_completed_staging
from alerts.repository import promote_to_mariadb

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


DB_CONFIG = {
    'host': 'ksfraser.ca',
    'user': 'ksfraser_stockmarket',
    'password': os.environ.get('DB_PASSWORD', 'Zaqwsx9sm1@'),
    'database': 'ksfraser_stock_market',
}


def get_mariadb_connection():
    return pymysql.connect(**DB_CONFIG)


def process_pending_alert(alert_row) -> bool:
    """
    Process a single alert from staging - call LLM only if needed,
    then promote final result into MariaDB.
    """
    alert_id = alert_row['id']
    symbol = alert_row['symbol']
    alert_type = alert_row['alert_type']
    payload_raw = alert_row['payload']
    payload = json.loads(payload_raw) if isinstance(payload_raw, str) else (payload_raw or {})

    triggered_at = payload.get('triggered_at', alert_row.get('created_at', 'unknown'))

    prompt = build_llm_prompt(alert_type, symbol, payload)
    response = call_llm_for_alert(prompt)

    if response:
        conn = get_mariadb_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO alert_responses (alert_id, response_text, response_type, responder)
                VALUES (%s, %s, 'hermes', 'hermes_alert_monitor')
            """, (alert_id, response))
            cursor.execute("""
                UPDATE alert_queue
                SET status = 'completed', llm_analysis = %s, completed_at = NOW()
                WHERE id = %s
            """, (response[:500], alert_id))
            conn.commit()
        finally:
            cursor.close()
            conn.close()

        send_discord_response(symbol, alert_type, response, triggered_at)

        # Promote staging row -> MariaDB and mark staging complete
        promote_to_mariadb(alert_row, response)
        mark_completed_staging(alert_id)

        logger.info("Processed alert %s for %s", alert_id, symbol)
        return True

    logger.warning("LLM call failed for alert %s, sending basic alert", alert_id)

    conn = get_mariadb_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE alert_queue
            SET status = 'completed', completed_at = NOW()
            WHERE id = %s
        """, (alert_id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    send_discord_response(symbol, alert_type, None, triggered_at, payload)
    mark_completed_staging(alert_id)
    return True


def build_llm_prompt(alert_type: str, symbol: str, payload: dict) -> str:
    """Build appropriate LLM prompt for alert type."""

    prompts = {
        'volume_spike': f"""Analyze {symbol} unusual volume alert.

Volume ratio: {payload.get('ratio', 'N/A')}x average ({payload.get('current_volume', 'N/A')} vs {payload.get('avg_volume', 'N/A')})

Return brief analysis (2-3 sentences) on:
1. What this volume spike likely indicates
2. Any immediate action to consider
3. Risk assessment""",
        
        'natr_spike': f"""Analyze {symbol} volatility spike.

NATR ratio: {payload.get('ratio', 'N/A')}x average ({payload.get('natr_20d', 'N/A')} vs {payload.get('natr_avg', 'N/A')})

From research, NATR (Normalized Average True Range) is the only predictive indicator (r=0.16@20d).
Assess: 1) Implied volatility regime change, 2) Timing implications for next 20 days, 3) Risk management.

Return 2-3 sentences with actionable insight.""",
        
        'gap_up': f"""Analyze {symbol} gap up.

Gap: {payload.get('gap_pct', 'N/A')}% (open: {payload.get('open_price')}, prev close: {payload.get('prev_close')})

1) Likely catalysts (earnings, news, sector rotation)
2) Trade setup assessment
3) Entry/exit levels if applicable

Return brief actionable analysis.""",
        
        'regime_change': f"""Market regime changed for {symbol}.

Transition: {payload.get('from')} → {payload.get('to')}

Assess implications for portfolio positioning and trading strategy.
Return 2-3 sentences.""",
        
        'oscillator_extreme': f"""{symbol} oscillator extreme detected.

RSI: {payload.get('rsi_20d')} ({payload.get('extreme')}, Stoch K: {payload.get('stoch_k')}, Stoch D: {payload.get('stoch_d')})

Remember: oscillators = regime filters, not direction indicators.
Brief assessment: is this noise or meaningful divergence?"""
    }
    
    return prompts.get(alert_type, f"Analyze {symbol} alert: {alert_type}")


def call_llm_for_alert(prompt: str) -> str:
    """Call LLM (reuse existing infrastructure)."""
    try:
        from llm_analyzer import call_llm, get_llm_client
        client_type, client = get_llm_client()
        if client_type:
            return call_llm(client_type, client, prompt, model='gpt-4o-mini')
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
    return ""


def infer_action(response: str) -> str:
    """Infer action from LLM response."""
    if 'buy' in response.lower():
        return 'buy'
    elif 'sell' in response.lower():
        return 'sell'
    return 'hold'


def send_discord_response(symbol: str, alert_type: str, response: str, triggered_at: str = None, payload: dict = None):
    """Send analysis to Discord channel. Falls back to basic alert if no LLM response."""
    try:
        from hermes_tools import send_message
        ts_info = f"\n\n> Triggered: {triggered_at}" if triggered_at else ""
        
        if response:
            # LLM analysis available
            message = f"**{symbol} - {alert_type.replace('_', ' ').title()} Analysis**{ts_info}\n\n{response}"
        else:
            # Basic fallback alert - show payload data
            details = ""
            if payload:
                for k, v in payload.items():
                    if k != 'triggered_at':
                        details += f"\n{k}: {v}"
            message = f"**{symbol} - {alert_type.replace('_', ' ').title()} Alert**{ts_info}{details}\n\n*LLM analysis unavailable*"
        
        send_message(target='discord:#stock-sell-alerts', message=message)
    except Exception as e:
        logger.error(f"Discord send failed: {e}")


def monitor_loop(poll_interval: int = 120):
    """Main monitoring loop."""
    logger.info(f"Starting alert monitor (poll every {poll_interval}s)")
    
    while True:
        try:
            alerts = list(fetch_pending_staging(limit=10))
            
            for alert in alerts:
                process_pending_alert(alert)
                
        except Exception as e:
            logger.error(f"Monitor loop error: {e}")
            
        time.sleep(poll_interval)


def main():
    parser = argparse.ArgumentParser(description='Hermes Alert Monitor')
    parser.add_argument('--once', action='store_true', help='Process once and exit')
    parser.add_argument('--daemon', action='store_true', help='Run continuously')
    parser.add_argument('--interval', type=int, default=120, help='Poll interval seconds')
    
    args = parser.parse_args()
    
    if args.once:
        alerts = list(fetch_pending_staging(limit=10))
        for alert in alerts:
            process_pending_alert(alert)
        logger.info(f"Processed {len(alerts)} pending alerts")
        
    elif args.daemon:
        monitor_loop(args.interval)
        
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
