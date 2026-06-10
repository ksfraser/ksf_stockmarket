
#!/usr/bin/env python3
"""
Stock Alert Monitor - Complete async LLM alert system
===================================================

1. Detection scripts queue alerts (non-blocking)
2. This script polls MariaDB for pending alerts
3. Calls LLM for analysis
4. Responds to Discord #stock-sell-alerts channel
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Optional

import pymysql

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Configuration
DB_CONFIG = {
    "host": "ksfraser.ca",
    "user": "ksfraser_stockmarket",
    "password": os.environ.get("DB_PASSWORD", "Zaqwsx9sm1@"),
    "database": "ksfraser_stock_market",
}

DISCORD_CHANNEL = os.environ.get("DISCORD_ALERT_CHANNEL", "#stock-sell-alerts")


def get_connection():
    return pymysql.connect(**DB_CONFIG)


def call_llm(prompt: str, symbol: str) -> Optional[str]:
    """Call LLM using existing infrastructure."""
    try:
        # Try OpenAI first
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a financial analyst. Be concise, 2-3 sentences max."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=300,
            )
            return resp.choices[0].message.content
            
        # Fallback to Ollama
        import requests
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": False},
            timeout=60,
        )
        if resp.status_code == 200:
            return resp.json().get("response", "")
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
    return None


def build_prompt(alert_type: str, symbol: str, payload: dict) -> str:
    prompts = {
        "volume_spike": f"""{symbol} unusual volume: {payload.get("ratio", "N/A")}x average. Brief analysis: What does this indicate? Any action needed?""",
        "natr_spike": f"""{symbol} volatility spike (NATR {payload.get("ratio", "N/A")}x avg). From research, NATR is the only predictive indicator (r=0.16@20d). Regime assessment?""",
        "oscillator_extreme": f"""{symbol} RSI {payload.get("rsi_20d")} ({payload.get("extreme")}). Oscillators = regime filters, not direction. Brief assessment?""",
        "gap_up": f"""{symbol} gap up {payload.get("gap_pct", "N/A")}%. Catalysts and trade setup?"""
    }
    return prompts.get(alert_type, f"Analyze {symbol} alert: {alert_type}")


def process_alert(conn, alert_row):
    """Process single alert with LLM analysis."""
    alert_id = alert_row["id"]
    symbol = alert_row["symbol"]
    alert_type = alert_row["alert_type"]
    payload = json.loads(alert_row["payload"]) if isinstance(alert_row["payload"], str) else alert_row["payload"]
    
    prompt = build_prompt(alert_type, symbol, payload)
    response = call_llm(prompt, symbol)
    
    if response:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO alert_responses (alert_id, response_text, response_type, responder) VALUES (%s, %s, %s, %s)",
            (alert_id, response[:1000], "hermes", "alert_monitor")
        )
        cursor.execute(
            "UPDATE alert_queue SET status = %s, completed_at = NOW() WHERE id = %s",
            ("completed", alert_id)
        )
        conn.commit()
        
# Send to Discord
        try:
            from hermes_tools import send_message
            formatted_type = alert_type.replace("_", " ").title()
            send_message(
                target=f"discord:{DISCORD_CHANNEL}",
                message=f"**{symbol} - {formatted_type} Analysis**\n\n{response}"
            )
        except:
            logger.info(f"Alert processed: {symbol} - {alert_type}")
            
        return True
    return False


def monitor_once():
    """Process all pending alerts once."""
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        cursor.execute("""
            SELECT * FROM alert_queue 
            WHERE status = 'pending' AND request_llm_analysis = 1
            ORDER BY created_at ASC LIMIT 10
        """)
        
        alerts = cursor.fetchall()
        
        for alert in alerts:
            process_alert(conn, alert)
            
        conn.close()
        logger.info(f"Processed {len(alerts)} alerts")
        
    except Exception as e:
        logger.error(f"Monitor error: {e}")


def monitor_daemon(interval: int = 120):
    """Run continuous monitoring loop."""
    logger.info(f"Starting daemon, polling every {interval}s")
    while True:
        monitor_once()
        time.sleep(interval)


if __name__ == "__main__":
    import sys
    if "--daemon" in sys.argv:
        monitor_daemon()
    else:
        monitor_once()
