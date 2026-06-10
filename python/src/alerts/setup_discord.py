#!/usr/bin/env python3
"""
Setup script for Discord alert webhooks
======================================

1. Get webhook URL from Discord channel settings
2. Store in environment or vault
3. Test connectivity
"""

import os
import json

# Configuration for stock-sell-alerts channel
# Channel ID: 1497324630212345957

DISCORD_SETUP = {
    'server_name': 'Kevin Fraser Server',
    'channel_name': 'stock-sell-alerts',
    'channel_id': '1497324630212345957',
    'webhook_instructions': '''
To set up Discord alerts:

1. Go to your Discord server
2. Right-click #stock-sell-alerts channel → Edit Channel
3. Go to Integrations → Webhooks → New Webhook
4. Name it "Stock Alerts"
5. Copy the webhook URL - it looks like:
   https://discord.com/api/webhooks/123456789012345678/abcdef...
6. Set environment variable:
   export DISCORD_ALERT_WEBHOOK=https://discord.com/...
   
Or add to group_vars/vault.yml:
   discord_alert_webhook: "https://discord.com/api/webhooks/..."
''',
    'hermes_channels': {
        'stock_sell_alerts': {
            'id': '1497324630212345957',
            'name': 'stock-sell-alerts',
            'purpose': 'LLM analysis responses and alerts',
            'webhook_url_env': 'DISCORD_ALERT_WEBHOOK'
        },
        'bot_home': {
            'id': '1497324628295811164',
            'name': 'Home',
            'purpose': 'General bot messages'
        }
    }
}

def create_env_setup():
    """Generate shell commands for environment setup."""
    print("Environment setup commands:")
    print("=" * 50)
    print("# Add to ~/.bashrc or ~/.zshrc:")
    print("export OPENAI_API_KEY=sk-your-key-here")
    print("export DISCORD_ALERT_WEBHOOK=https://discord.com/api/webhooks/YOUR_WEBHOOK")
    print("")
    print("# Or create .env file in project root:")
    env_content = """OPENAI_API_KEY=sk-your-key-here
DISCORD_ALERT_WEBHOOK=https://discord.com/api/webhooks/YOUR_WEBHOOK
"""
    print(env_content)

if __name__ == '__main__':
    print(DISCORD_SETUP['webhook_instructions'])
    create_env_setup()