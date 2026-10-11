"""Database configuration (placeholder for legacy support)."""

import os

def get_mariadb_config():
    return {
        'host': 'ksfraser.ca',
        'user': 'ksfraser_stockmarket',
        'db': 'ksfraser_stock_market',
        'password': os.environ.get('MYSQL_PASSWORD', ''),
    }
