#!/usr/bin/env python3
"""Create monitoring tables in MariaDB."""

import os
import pymysql

conn = pymysql.connect(
    host=os.environ.get('DB_HOST', 'ksfraser.ca'),
    port=int(os.environ.get('DB_PORT', '3306')),
    user=os.environ.get('DB_USER', 'ksfraser_stockmarket'),
    password=os.environ.get('DB_PASSWORD', 'Zaqwsx9sm1@'),
    database=os.environ.get('DB_NAME', 'ksfraser_stock_market'),
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=True,
)

cur = conn.cursor()

# Create monitoring_runs table
cur.execute("""
    CREATE TABLE IF NOT EXISTS monitoring_runs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        job_name VARCHAR(50) NOT NULL,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP NULL,
        status ENUM('success', 'error', 'no_data', 'running') NOT NULL,
        symbol_count INT DEFAULT 0,
        alert_count INT DEFAULT 0,
        details JSON,
        INDEX idx_job_time (job_name, started_at DESC)
    )
""")
print("✓ Created monitoring_runs table")

# Create volume_snapshots table
cur.execute("""
    CREATE TABLE IF NOT EXISTS volume_snapshots (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        date DATE NOT NULL,
        time TIME NOT NULL,
        price DECIMAL(12,4),
        volume BIGINT,
        volume_5d_avg BIGINT,
        volume_ratio DECIMAL(6,2),
        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_symbol_date (symbol, date),
        INDEX idx_symbol_time (symbol, recorded_at),
        INDEX idx_ratio (volume_ratio DESC),
        INDEX idx_date (date)
    )
""")
print("✓ Created volume_snapshots table")

# Create price_alerts table
cur.execute("""
    CREATE TABLE IF NOT EXISTS price_alerts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ticker VARCHAR(20) NOT NULL,
        alert_type ENUM('BELOW', 'ABOVE', 'TRAILING_STOP') NOT NULL,
        threshold_value DECIMAL(12,4),
        trailing_stop_price DECIMAL(12,4),
        trailing_limit_price DECIMAL(12,4),
        active BOOLEAN DEFAULT 1,
        triggered_count INT DEFAULT 0,
        last_triggered TIMESTAMP NULL,
        notes TEXT,
        source_file VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_active (active),
        INDEX idx_ticker (ticker)
    )
""")
print("✓ Created price_alerts table")

# Create symbol_status table
cur.execute("""
    CREATE TABLE IF NOT EXISTS symbol_status (
        symbol VARCHAR(20) PRIMARY KEY,
        resolved_symbol VARCHAR(20),
        status ENUM('active', 'delisted', 'renamed', 'exchange_changed', 'error') DEFAULT 'active',
        name VARCHAR(255),
        exchange VARCHAR(50),
        currency CHAR(3),
        last_price DECIMAL(12,4),
        last_check_date DATE,
        first_delisted_date DATE NULL,
        error_message TEXT,
        consecutive_failures INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_status (status)
    )
""")
print("✓ Created symbol_status table")

conn.close()
print("\nAll monitoring tables created.")