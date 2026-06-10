#!/usr/bin/env python3
"""
Discord Alert Handler - Bridge between app alerts and LLM processing
==================================================================

This bot monitors Discord channels for alerts and can:
1. Receive alert notifications from the app
2. Trigger LLM analysis via call_llm
3. Write results back to MariaDB
4. Respond with analysis findings

Setup:
- Set DISCORD_BOT_TOKEN environment variable
- Bot needs read/write access to #stock-alerts and #bot-commands
"""

import os
import json
import logging
from datetime import datetime

try:
    import discord
    from discord import Intents
except ImportError:
    print("discord.py not installed. Install with: pip install discord.py")
    exit(1)

# Import existing LLM infrastructure
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from llm_analyzer import call_llm, get_llm_client, write_llm_scores
from db_connector import get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlertBot(discord.Client):
    def __init__(self):
        intents = Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.llm_type, self.llm_client = get_llm_client()
        
    async def on_ready(self):
        logger.info(f"AlertBot logged in as {self.user}")
        
    async def on_message(self, message):
        if message.author.bot:
            return
            
        # Handle alert commands
        if message.content.startswith('!analyze'):
            await self.handle_analyze_command(message)
            
        elif message.content.startswith('!alert'):
            await self.handle_alert_notification(message)
            
    async def handle_analyze_command(self, message):
        """!analyze SYMBOL - Run LLM analysis on demand"""
        parts = message.content.split()
        if len(parts) < 2:
            await message.channel.send("Usage: !analyze SYMBOL")
            return
            
        symbol = parts[1].upper()
        if not self.llm_type:
            await message.channel.send("LLM not available (set OPENAI_API_KEY or run Ollama)")
            return
            
        await message.channel.send(f"🔍 Analyzing {symbol}...")
        
        # Run tenets analysis
        scores = analyze_tenets_llm(symbol, self.llm_type, self.llm_client)
        if scores:
            conn = get_connection()
            write_llm_scores(conn, symbol, 'tenets', scores, 'discord_alert', 0.85)
            conn.close()
            await message.channel.send(f"✅ LLM analysis complete for {symbol}")
        else:
            await message.channel.send(f"❌ Failed to analyze {symbol}")
            
    async def handle_alert_notification(self, message):
        """Process structured alerts from app"""
        try:
            data = json.loads(message.content.replace('!alert ', '', 1))
            alert_type = data.get('type')
            symbol = data.get('symbol')
            
            if alert_type and symbol:
                # Trigger appropriate LLM analysis
                if alert_type in ['volume_spike', 'gap_up', 'regime_change']:
                    await self.trigger_alert_analysis(message.channel, symbol, alert_type, data)
        except json.JSONDecodeError:
            pass
            
    async def trigger_alert_analysis(self, channel, symbol: str, alert_type: str, alert_data: dict):
        """Run LLM analysis and update alert status"""
        analysis_prompt = f"""
        {alert_type.replace('_', ' ').title()} detected for {symbol}.
        
        Alert data: {json.dumps(alert_data, indent=2)}
        
        Provide brief analysis (3-5 sentences) focusing on:
        - What this means for the stock
        - Whether to consider buying/selling
        - Risk assessment
        """
        
        response = call_llm(self.llm_type, self.llm_client, analysis_prompt)
        await channel.send(f"**{symbol} - {alert_type} Analysis:**\n{response}")


def analyze_tenets_llm(symbol: str, client_type, client, model=None):
    """Import from llm_analyzer - handles the actual analysis"""
    from llm_analyzer import analyze_tenets_llm as _analyze
    return _analyze(symbol, client_type, client, model)


def main():
    token = os.environ.get('DISCORD_BOT_TOKEN')
    if not token:
        logger.error("Set DISCORD_BOT_TOKEN environment variable")
        return
        
    bot = AlertBot()
    bot.run(token)


if __name__ == '__main__':
    main()