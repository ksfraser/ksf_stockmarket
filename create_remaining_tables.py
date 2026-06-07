#!/usr/bin/env python3
import pymysql

MDB = pymysql.connect(host='ksfraser.ca', user='ksfraser_stockmarket', password='Zaqwsx9sm1@', database='ksfraser_stock_market')
cur = MDB.cursor()

# Tables to create
sqls = [
    """CREATE TABLE IF NOT EXISTS layer1_signals (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        backtest_id BIGINT,
        symbol VARCHAR(50),
        signal_date DATE,
        signal_type VARCHAR(20),
        strength DOUBLE,
        reason TEXT
    )""",
    
    """CREATE TABLE IF NOT EXISTS layer2_positions (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        backtest_id BIGINT,
        symbol VARCHAR(50),
        entry_date DATE,
        exit_date DATE,
        entry_price DOUBLE,
        exit_price DOUBLE,
        position_size DOUBLE,
        stop_loss DOUBLE
    )""",
    
    """CREATE TABLE IF NOT EXISTS layer3_candidates (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        backtest_id BIGINT,
        symbol VARCHAR(50),
        score DOUBLE,
        momentum_score DOUBLE,
        volatility_score DOUBLE,
        correlation_score DOUBLE
    )""",
    
    """CREATE TABLE IF NOT EXISTS layer3_portfolios (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        backtest_id BIGINT,
        symbol VARCHAR(50),
        target_weight DOUBLE,
        current_weight DOUBLE
    )""",
    
    """CREATE TABLE IF NOT EXISTS pipeline_v2_results (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        symbol VARCHAR(50),
        run_date DATE,
        momentum_score DOUBLE,
        volatility_score DOUBLE,
        correlation_score DOUBLE,
        composite_score DOUBLE
    )""",
    
    """CREATE TABLE IF NOT EXISTS pipeline_v3_walkforward (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        symbol VARCHAR(50),
        period_start DATE,
        period_end DATE,
        in_sample_score DOUBLE,
        out_sample_score DOUBLE
    )""",
    
    """CREATE TABLE IF NOT EXISTS data_import_log (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        file_name TEXT,
        import_type TEXT,
        records_added BIGINT,
        import_date TEXT,
        status TEXT
    )""",
    
    """CREATE TABLE IF NOT EXISTS strategy_performance (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        strategy_name TEXT,
        symbol VARCHAR(50),
        period_start DATE,
        period_end DATE,
        sharpe_ratio DOUBLE,
        max_drawdown DOUBLE,
        total_return DOUBLE
    )""",
    
    """CREATE TABLE IF NOT EXISTS full_correlation_results (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        symbol_a VARCHAR(50),
        symbol_b VARCHAR(50),
        correlation DOUBLE,
        calculated_date DATE
    )""",
    
    """CREATE TABLE IF NOT EXISTS strategy_pipeline_results (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        backtest_id BIGINT,
        layer1_count BIGINT,
        layer2_count BIGINT,
        layer3_count BIGINT,
        final_positions TEXT,
        metrics TEXT
    )""",
]

for sql in sqls:
    table_name = sql.split('CREATE TABLE IF NOT EXISTS ')[1].split(' ')[0]
    cur.execute(sql)
    cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='ksfraser_stock_market' AND table_name=%s", (table_name,))
    print(f"Created {table_name}" if cur.fetchone()[0] else f"FAILED {table_name}")

MDB.commit()
MDB.close()
print("Done")