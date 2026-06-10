#!/usr/bin/env python3
"""
Hermes Alert Monitor - Main monitoring daemon
===========================================

Polls MariaDB alert_queue, triggers LLM analysis, responds via Discord.

Run as: python3 hermes_alert_monitor.py --daemon
Or via cron: hermes_alert_monitor.py --once
"""

import json
import logging
import os
import time
import argparse
from datetime import datetime

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from db_connector import get_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def process_pending_alert(conn, cursor, alert_row) -> bool:
    """
    Process a single alert - call LLM and write response.
    """
    alert_id = alert_row['id']
    symbol = alert_row['symbol']
    alert_type = alert_row['alert_type']  # Fixed: use alert_type column
    payload = json.loads(alert_row['payload'])
    
    # Get triggered_at timestamp from payload (when alert originally occurred)
    triggered_at = payload.get('triggered_at', alert_row.get('created_at', 'unknown'))
    
    # Build LLM prompt based on alert type
    prompt = build_llm_prompt(alert_type, symbol, payload)
    
    # Call LLM
    response = call_llm_for_alert(prompt)
    
    if response:
        # Write analysis to alert_responses
        cursor.execute("""
            INSERT INTO alert_responses (alert_id, response_text, response_type, responder, action_taken)
            VALUES (%s, %s, 'hermes', 'hermes_alert_monitor', %s)
        """, (alert_id, response, infer_action(response)))
        
        # Update alert status
        cursor.execute("""
            UPDATE alert_queue 
            SET status = 'completed', llm_analysis = %s, completed_at = NOW()
            WHERE id = %s
        """, (response[:500], alert_id))
        
        conn.commit()
        
        # Send Discord notification with trigger timestamp
        send_discord_response(symbol, alert_type, response, triggered_at)
        
        logger.info(f"Processed alert {alert_id} for {symbol}")
        return True
    
    return False


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
        
Transition: {payload.get('from')} → {payload.get('to')}{_to}

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


def send_discord_response(symbol: str, alert_type: str, response: str, triggered_at: str = None):
    """Send analysis to Discord channel."""
    try:
        from hermes_tools import send_message
        ts_info = f"\n\n> Triggered: {triggered_at}" if triggered_at else ""
        message = f"**{symbol} - {alert_type.replace('_', ' ').title()} Analysis**{ts_info}\n\n{response}"
        send_message(target='discord:#stock-sell-alerts', message=message)
    except Exception as e:
        logger.error(f"Discord send failed: {e}")


def monitor_loop(poll_interval: int = 120):
    """Main monitoring loop."""
    logger.info(f"Starting alert monitor (poll every {poll_interval}s)")
    
    while True:
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Find pending alerts requesting LLM analysis
            cursor.execute("""
                SELECT * FROM alert_queue 
                WHERE status = 'pending' AND request_llm_analysis = 1
                ORDER BY created_at ASC
                LIMIT 10
            """)
            
            alerts = cursor.fetchall()
            
            for alert in alerts:
                process_pending_alert(conn, cursor, alert)
                
            cursor.close()
            conn.close()
            
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
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM alert_queue WHERE status = 'pending' AND request_llm_analysis = 1")
        alerts = cursor.fetchall()
        for alert in alerts:
            process_pending_alert(conn, cursor, alert)
        conn.close()
        logger.info(f"Processed {len(alerts)} pending alerts")
        
    elif args.daemon:
        monitor_loop(args.interval)
        
    else:
        parser.print_help()


if __name__ == '__main__':
    main()