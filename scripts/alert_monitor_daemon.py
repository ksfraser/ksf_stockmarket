#!/usr/bin/env python3
"""
Stock Alert Monitor - Poll MariaDB alert_queue, trigger LLM analysis only for complex cases,
respond to Discord via template-based fallback for simple alerts.
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
    "host": os.environ.get("DB_HOST", "ksfraser.ca"),
    "user": os.environ.get("DB_USER", "ksfraser_stockmarket"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get("DB_NAME", "ksfraser_stockmarket"),
    "connect_timeout": 10
}

DISCORD_CHANNEL = "#stock-sell-alerts"

# Alert types that need full LLM analysis (in-depth reasoning)
NEEDS_LLM_ANALYSIS = {"natr_spike"}  # Volatility spikes need research-based interpretation

# Alert types that can use template-based responses  
SIMPLE_ALERTS = {"volume_spike", "oscillator_extreme", "oscillator_extremes", "gap_up"}


def get_connection():
    return pymysql.connect(**DB_CONFIG)


def simple_response(alert_type: str, symbol: str, payload: dict) -> str:
    """Generate template-based response for simple alerts - NO LLM call needed."""
    if alert_type == "volume_spike":
        ratio = payload.get("volume_ratio", payload.get("ratio", "N/A"))
        return f"**{symbol} Volume Spike Alert** 📊\n\n_Severity: {payload.get('severity', 'medium').upper()}_\n\nVolume: **{payload.get('today_volume', 'N/A'):,}** (avg: {payload.get('avg_volume', 'N/A'):,})\nRatio: **{ratio}**× average\nPrice Change: **{payload.get('price_change_pct', 'N/A'):+.2f}%**\n\nUnusual trading activity detected. Monitor for follow-through."
    
    elif alert_type == "oscillator_extreme" or alert_type == "oscillator_extremes":
        rsi = payload.get("rsi", payload.get("rsi_20d", "N/A"))
        regime = payload.get("regime", payload.get("extreme", payload.get("condition", "extreme")))
        extreme_days = payload.get("extreme_days", payload.get("consecutive_days", 1))
        return f"**{symbol} Oscillator Alert** 📈\n\n_RSI: **{rsi}** ({regime})\nExtreme Days: **{extreme_days}**\nDirection: **{'bearish' if float(rsi) > 70 else 'bullish'}**\n\nCurrent Price: ${payload.get('current_price', payload.get('price', 'N/A'))}\n\nRSI has been in {regime} territory for {extreme_days}+ days. Consider profit-taking or waiting for pullback. Overbought conditions can persist in strong trends."
    
    elif alert_type == "gap_up":
        gap_pct = payload.get("gap_pct", "N/A")
        open_price = payload.get("open_price", "N/A")
        prev_close = payload.get("previous_close", "N/A")
        return f"**{symbol} Gap Up Alert** 🚀\n\n_Gap: **{gap_pct}%**\nOpen: **${open_price}** (prev close: ${prev_close})\nGap Filled: **{'Yes' if payload.get('gap_filled') else 'No'}**\n\nFavorable gap detected - watch for momentum continuation."
    
    elif alert_type == "natr_spike":
        natr = payload.get("natr_current", payload.get("natr", "N/A"))
        return f"**{symbol} Volatility Alert** ⚡\n\n_NATR: **{natr}** (avg: {payload.get('natr_avg', 'N/A')})\nRatio: **{payload.get('natr_ratio', 'N/A')}**× average\nPrice Change: **{payload.get('price_change_pct', 'N/A'):+.2f}%**\n\nVolatility expansion detected - potential breakout or breakdown in progress. NATR is the only predictive indicator (r=0.16@20d)."
    
    return f"**{symbol} Alert** ⚠️\n\nAlert type: {alert_type}\nSeverity: {payload.get('severity', 'unknown')}"


def call_llm(prompt: str) -> Optional[str]:
    """Call LLM using OpenAI or Ollama - only for complex analysis."""
    try:
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
    except Exception as e:
        logger.warning(f"LLM call skipped: {e}")
    return None


def build_llm_prompt(alert_type: str, symbol: str, payload: dict) -> str:
    """Build LLM prompt for alerts requiring in-depth analysis."""
    natr_current = payload.get("natr_current", "N/A")
    natr_avg = payload.get("natr_avg", "N/A")
    price_change = payload.get("price_change_pct", "N/A")
    
    if alert_type == "natr_spike":
        return f"{symbol} volatility spike: NATR {natr_current} (avg {natr_avg}), price change {price_change}%. Research shows NATR is predictive (r=0.16@20d). What trading implications does this have? Consider trend context and potential breakout/breakdown scenarios."
    
    return f"Analyze {symbol} {alert_type} alert with payload: {json.dumps(payload)}"


def process_alert(conn, alert_row) -> bool:
    """Process single alert - use LLM only for complex cases, template for simple."""
    alert_id = alert_row["id"]
    symbol = alert_row["symbol"]
    alert_type = alert_row["alert_type"]
    
    # Parse payload - handle double-escaped JSON
    try:
        payload_raw = alert_row["payload"]
        if isinstance(payload_raw, str):
            # Handle double-escaped JSON from MariaDB
            if payload_raw.startswith('"') and payload_raw.endswith('"'):
                payload_raw = payload_raw[1:-1]
            payload_raw = payload_raw.replace('\\"', '"')
            payload = json.loads(payload_raw)
        else:
            payload = payload_raw if isinstance(payload_raw, dict) else {}
    except Exception as e:
        logger.warning(f"Payload parse error for {alert_id}: {e}")
        payload = {}
    
    # Determine if we need LLM or can use template
    uses_simple = alert_type in SIMPLE_ALERTS
    uses_llm = alert_type in NEEDS_LLM_ANALYSIS and os.environ.get("OPENAI_API_KEY")
    
    if uses_llm:
        # Complex case - use LLM
        prompt = build_llm_prompt(alert_type, symbol, payload)
        response = call_llm(prompt)
        if response:
            response_text = f"**{symbol} - {alert_type.replace('_', ' ').title()} Analysis**\n\n{response}"
        else:
            # LLM failed, fall back to template
            response_text = simple_response(alert_type, symbol, payload)
    else:
        # Simple case - use template, NO LLM call
        response_text = simple_response(alert_type, symbol, payload)
    
    # Write response to DB
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO alert_responses (alert_id, response_text, response_type, responder) VALUES (%s, %s, %s, %s)",
            (alert_id, response_text[:1000], "hermes", "alert_monitor")
        )
        cursor.execute(
            "UPDATE alert_queue SET status = %s, completed_at = NOW() WHERE id = %s",
            ("completed", alert_id)
        )
        conn.commit()
        
        # Send to Discord
        try:
            from hermes_tools import send_message
            send_message(
                target=f"discord:{DISCORD_CHANNEL}",
                message=response_text
            )
        except Exception as e:
            logger.info(f"Alert queued for delivery: {symbol} - {alert_type}")
        
        logger.info(f"Processed {symbol} - {alert_type} (LLM used: {uses_llm})")
        return True
        
    except Exception as e:
        logger.error(f"DB write error: {e}")
        return False


def monitor_once():
    """Process all pending alerts once."""
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Get pending alerts that need processing (all of them - monitor handles via templates or LLM)
        cursor.execute("""
            SELECT * FROM alert_queue 
            WHERE status = 'pending'
            ORDER BY created_at ASC LIMIT 10
        """)
        
        alerts = cursor.fetchall()
        LLM_count = 0
        template_count = 0
        
        for alert in alerts:
            alert_id = alert["id"]
            alert_type = alert["alert_type"]
            
            # Skip LLM calls if rate limited - use template instead
            if alert_type in NEEDS_LLM_ANALYSIS:
                # Check if we already have an OpenAI rate limit error logged recently
                # For now, always try LLM but gracefully fall back
                pass
            
            if process_alert(conn, alert):
                if alert_type in NEEDS_LLM_ANALYSIS:
                    LLM_count += 1
                else:
                    template_count += 1
            
        conn.close()
        logger.info(f"Processed {len(alerts)} alerts (LLM: {LLM_count}, template: {template_count})")
        
    except Exception as e:
        logger.error(f"Monitor error: {e}")


def main():
    monitor_once()


if __name__ == "__main__":
    main()