#!/usr/bin/env python3
"""Initialize system_settings table and seed from .env file."""
import os
import sys
sys.path.insert(0, '/home/ksf_stockmarket/ksf_stockmarket/python')

from db_connector import get_connection

def init_system_settings():
    """Create system_settings table and seed initial values."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            setting_key VARCHAR(100) NOT NULL UNIQUE,
            setting_value TEXT,
            setting_type ENUM('string', 'text', 'password', 'integer', 'float') DEFAULT 'string',
            description VARCHAR(255),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX KEY_IDX (setting_key)
        )
    """)
    
    # Default settings (seed from .env)
    defaults = [
        ('discord_webhook_url', '', 'text', 'Discord webhook URL for #stock-sell-alerts channel'),
        ('discord_alert_webhook', '', 'text', 'Discord webhook for alert messages (specific channel)'),
        ('discord_bot_token', '', 'password', 'Discord bot token for sending messages'),
        ('llm_provider', 'openrouter', 'string', 'LLM provider: openrouter, ollama, google, openai'),
        ('llm_model', 'anthropic/claude-sonnet-4', 'string', 'Default LLM model identifier'),
        ('llm_api_key', '', 'password', 'API key for LLM provider (if not using OpenRouter)'),
        ('llm_base_url', '', 'string', 'Custom base URL for LLM provider'),
        ('ta_run_frequency', 'daily', 'string', 'TA indicator run frequency: daily, twice_daily, intraday'),
        ('alert_check_frequency', '15min', 'string', 'Price/volume alert check frequency'),
        ('max_symbols_per_run', '100', 'integer', 'Maximum symbols to process per cron run'),
    ]
    
    # Seed from .env
    env_path = '/root/.hermes/.env'
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            env_content = f.read()
        
        # Extract DISCORD_ALERT_WEBHOOK
        import re
        match = re.search(r'DISCORD_ALERT_WEBHOOK=(.+)', env_content)
        if match:
            defaults[1] = ('discord_alert_webhook', match.group(1).strip(), 'text', 'Discord webhook for alert messages')
        
        match = re.search(r'DISCORD_BOT_TOKEN=(.+)', env_content)
        if match:
            defaults[2] = ('discord_bot_token', match.group(1).strip(), 'password', 'Discord bot token')
    
    # Insert defaults
    for key, val, typ, desc in defaults:
        cursor.execute("""
            INSERT IGNORE INTO system_settings (setting_key, setting_value, setting_type, description)
            VALUES (%s, %s, %s, %s)
        """, (key, val, typ, desc))
    
    conn.commit()
    conn.close()
    print("✓ system_settings table initialized")

if __name__ == '__main__':
    init_system_settings()