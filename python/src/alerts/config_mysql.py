"""Shared DB config for the alerts package to break circular imports."""
import os

MYSQL = {
    'host': 'ksfraser.ca',
    'user': 'ksfraser_stockmarket',
    'port': 3306,
    'password': os.environ.get('DB_PASSWORD', 'Zaqwsx9sm1@'),
    'database': 'ksfraser_stock_market',
    'charset': 'utf8mb4',
    'connect_timeout': 10,
}
