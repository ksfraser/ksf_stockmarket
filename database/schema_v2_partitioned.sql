-- ============================================================================
-- KSF Stock Market — Partitioned Schema with Tier 2 Materialized Tables
-- ============================================================================
-- Compatible with: MariaDB 10.6+ (tested on 10.5.18)
-- Character set: utf8mb4
-- Engine: InnoDB
--
-- STRATEGY:
--   1. stockprices: partitioned BY RANGE(YEAR(date)) — ~8-10 partitions
--   2. daily_indicators: Tier 1 via trigger on INSERT (return, gap, SMA)
--   3. daily_tier2: Tier 2 materialized table (BB, ATR, vol-avg) — populated
--      once per day by event scheduler or cron, NOT on every INSERT
--   4. v_with_indicators: VIEW joining price + both indicator tiers
--
-- BACKUP: Each partition backed up separately via:
--   mysqldump --single-transaction --where "YEAR(date)=2025" ksf_stockmarket stockprices
--   (Avoids the 4GB monolithic dump trauma from 2013)
-- ============================================================================

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

DROP DATABASE IF EXISTS ksf_stockmarket;
CREATE DATABASE ksf_stockmarket
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE ksf_stockmarket;

-- Enable event scheduler for Tier 2 refresh
SET GLOBAL event_scheduler = ON;

-- ============================================================================
-- CORE TABLES (preserved from legacy)
-- ============================================================================

CREATE TABLE users (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    username        VARCHAR(64)     NOT NULL,
    email           VARCHAR(255)    NULL,
    password_hash   VARCHAR(255)    NOT NULL,
    role            ENUM('admin', 'trader', 'viewer') NOT NULL DEFAULT 'viewer',
    first_name      VARCHAR(64)     NULL,
    last_name       VARCHAR(64)     NULL,
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,
    last_login      TIMESTAMP       NULL,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_username (username),
    UNIQUE KEY uk_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE stockinfo (
    stocksymbol     CHAR(16)        NOT NULL,
    exchange        VARCHAR(32)     NOT NULL DEFAULT '',
    corporatename   VARCHAR(255)    NOT NULL DEFAULT '',
    `52high`        DOUBLE          NOT NULL DEFAULT 0,
    `52low`         DOUBLE          NOT NULL DEFAULT 0,
    high            DOUBLE          NOT NULL DEFAULT 0,
    low             DOUBLE          NOT NULL DEFAULT 0,
    sector          VARCHAR(128)    NULL,
    industry        VARCHAR(128)    NULL,
    market_cap      BIGINT UNSIGNED NULL,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (stocksymbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE transactiontype (
    transactiontype VARCHAR(32) NOT NULL,
    description     VARCHAR(255) NULL,
    PRIMARY KEY (transactiontype)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE stockexchange (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    exchange_name   VARCHAR(64)     NOT NULL,
    country         CHAR(2)         NULL,
    currency        CHAR(3)         NOT NULL DEFAULT 'CAD',
    PRIMARY KEY (id),
    UNIQUE KEY uk_exchange_name (exchange_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE taxstatus (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    symbol          CHAR(16)        NOT NULL,
    tax_year        YEAR            NOT NULL,
    gain_loss       DECIMAL(15,2)  NULL,
    PRIMARY KEY (id),
    INDEX idx_symbol_year (symbol, tax_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- PARTITIONED STOCK PRICES (the big one)
-- ============================================================================
-- Partitioned by YEAR(date) for ~8-10 partitions covering 2009-2026.
-- Partition pruning makes backtest queries transparent and fast.
-- Each partition can be backed up independently.

CREATE TABLE stockprices (
    symbol      CHAR(16)        NOT NULL,
    price_date  DATE            NOT NULL,
    day_open    DECIMAL(15,4)  NOT NULL DEFAULT 0,
    day_high    DECIMAL(15,4)  NOT NULL DEFAULT 0,
    day_low        DECIMAL(15,4)  NOT NULL DEFAULT 0,
    day_close   DECIMAL(15,4)  NOT NULL DEFAULT 0,
    previous_close DECIMAL(15,4) NULL,
    day_change  DECIMAL(15,4)  NULL,
    adj_close   DECIMAL(15,4)  NULL,
    volume      BIGINT UNSIGNED NOT NULL DEFAULT 0,
    bid         DECIMAL(15,4)  NULL,
    ask         DECIMAL(15,4)  NULL,
    source      VARCHAR(32)     NULL DEFAULT 'csv',
    updated_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, price_date),
    INDEX idx_date (price_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
PARTITION BY RANGE (YEAR(price_date)) (
    PARTITION p_early VALUES LESS THAN (2010),
    PARTITION p2010 VALUES LESS THAN (2012),
    PARTITION p2012 VALUES LESS THAN (2014),
    PARTITION p2014 VALUES LESS THAN (2016),
    PARTITION p2016 VALUES LESS THAN (2018),
    PARTITION p2018 VALUES LESS THAN (2020),
    PARTITION p2020 VALUES LESS THAN (2022),
    PARTITION p2022 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2026),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- ============================================================================
-- TIER 1: DAILY INDICATORS (trigger-calculated on INSERT)
-- ============================================================================
-- These are cheap to calculate per-row: daily return, gap, SMA-50, SMA-200.
-- Populated by AFTER INSERT trigger on stockprices.

CREATE TABLE daily_indicators (
    symbol          CHAR(16)        NOT NULL,
    price_date      DATE            NOT NULL,
    daily_return    DECIMAL(10,6)  COMMENT '(close - prev_close) / prev_close',
    gap_pct         DECIMAL(10,6)  COMMENT '(open - prev_close) / prev_close',
    sma_20          DECIMAL(15,4)  NULL COMMENT '20-day simple moving average',
    sma_50          DECIMAL(15,4)  NULL COMMENT '50-day simple moving average',
    sma_200         DECIMAL(15,4)  NULL COMMENT '200-day simple moving average',
    volume_sma_20   BIGINT UNSIGNED NULL COMMENT '20-day average volume',
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, price_date),
    INDEX idx_symbol_date (symbol, price_date),
    -- Foreign key is not enforced on partitioned tables in MariaDB,
    -- but we document the relationship:
    -- FK: (symbol, price_date) REFERENCES stockprices(symbol, price_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
PARTITION BY RANGE (YEAR(price_date)) (
    PARTITION p_early VALUES LESS THAN (2010),
    PARTITION p2010 VALUES LESS THAN (2012),
    PARTITION p2012 VALUES LESS THAN (2014),
    PARTITION p2014 VALUES LESS THAN (2016),
    PARTITION p2016 VALUES LESS THAN (2018),
    PARTITION p2018 VALUES LESS THAN (2020),
    PARTITION p2020 VALUES LESS THAN (2022),
    PARTITION p2022 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2026),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- ============================================================================
-- TIER 2: DAILY INDICATORS (materialized once per day via event/cron)
-- ============================================================================
-- These are expensive to calculate: Bollinger Bands, ATR.
-- WINDOW FUNCTIONS require looking at 20-14 rows per symbol, which is
-- expensive to do on every INSERT. Instead, we calculate once per day
-- for all symbols, after the data refresh completes.
--
-- KEY INSIGHT: Indicator weightings change slowly (weeks/months), so
-- daily refresh is more than sufficient. This avoids recalculating on
-- every single price insert, which would be O(n_symbols) per insert.

CREATE TABLE daily_tier2 (
    symbol          CHAR(16)        NOT NULL,
    price_date      DATE            NOT NULL,
    -- Bollinger Bands (20-day, 2 std dev)
    bb_middle       DECIMAL(15,4)  NULL COMMENT 'SMA-20',
    bb_upper        DECIMAL(15,4)  NULL COMMENT 'SMA-20 + 2*STDDEV-20',
    bb_lower        DECIMAL(15,4)  NULL COMMENT 'SMA-20 - 2*STDDEV-20',
    bb_width        DECIMAL(10,4)  NULL COMMENT '(upper - lower) / middle',
    bb_pct          DECIMAL(10,4)  NULL COMMENT '(close - lower) / (upper - lower)',
    -- ATR (14-day)
    atr_14          DECIMAL(15,4)  NULL COMMENT 'Average True Range (14-day)',
    atr_pct         DECIMAL(10,4)  NULL COMMENT 'ATR / close * 100',
    -- Volume trends
    vol_ratio_20    DECIMAL(10,4)  NULL COMMENT 'Volume / 20-day avg volume',
    vol_ratio_50    DECIMAL(10,4)  NULL COMMENT 'Volume / 50-day avg volume',
    -- Trend classification
    trend_50_200    CHAR(8)         NULL COMMENT 'GOLDEN_CROSS, DEATH_CROSS, BULLISH, BEARISH',
    -- Signal classification
    signal_strength TINYINT         NULL COMMENT '-100 to +100 composite score',
    signal_reasons  VARCHAR(512)    NULL COMMENT 'Comma-separated signal codes',
    -- Metadata
    calc_method     ENUM('trigger', 'daily_event', 'manual', 'python') NOT NULL DEFAULT 'daily_event',
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, price_date),
    INDEX idx_symbol_date (symbol, price_date),
    INDEX idx_date_trend (price_date, trend_50_200)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
PARTITION BY RANGE (YEAR(price_date)) (
    PARTITION p_early VALUES LESS THAN (2010),
    PARTITION p2010 VALUES LESS THAN (2012),
    PARTITION p2012 VALUES LESS THAN (2014),
    PARTITION p2014 VALUES LESS THAN (2016),
    PARTITION p2016 VALUES LESS THAN (2018),
    PARTITION p2018 VALUES LESS THAN (2020),
    PARTITION p2020 VALUES LESS THAN (2022),
    PARTITION p2022 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2026),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- ============================================================================
-- TIER 1 TRIGGER: Calculate simple indicators on INSERT
-- ============================================================================
-- This trigger calculates daily_return, gap_pct, and SMA values
-- for the newly inserted row. It uses a self-join to get the
-- previous close and the prior rows needed for SMA.

DELIMITER //

CREATE TRIGGER trg_stockprices_after_insert
AFTER INSERT ON stockprices
FOR EACH ROW
BEGIN
    DECLARE v_prev_close DECIMAL(15,4);
    DECLARE v_sma_20 DECIMAL(15,4);
    DECLARE v_sma_50 DECIMAL(15,4);
    DECLARE v_sma_200 DECIMAL(15,4);
    DECLARE v_vol_sma_20 BIGINT UNSIGNED;
    DECLARE v_daily_ret DECIMAL(10,6);
    DECLARE v_gap DECIMAL(10,6);

    -- Get previous close
    SELECT day_close INTO v_prev_close
    FROM stockprices
    WHERE symbol = NEW.symbol AND price_date < NEW.price_date
    ORDER BY price_date DESC
    LIMIT 1;

    -- Calculate daily return
    IF v_prev_close IS NOT NULL AND v_prev_close > 0 THEN
        SET v_daily_ret = (NEW.day_close - v_prev_close) / v_prev_close;
        SET v_gap = (NEW.day_open - v_prev_close) / v_prev_close;
    ELSE
        SET v_daily_ret = NULL;
        SET v_gap = NULL;
    END IF;

    -- Calculate SMA-20
    SELECT AVG(day_close) INTO v_sma_20
    FROM (
        SELECT day_close
        FROM stockprices
        WHERE symbol = NEW.symbol AND price_date <= NEW.price_date
        ORDER BY price_date DESC
        LIMIT 20
    ) t;

    -- Calculate SMA-50
    SELECT AVG(day_close) INTO v_sma_50
    FROM (
        SELECT day_close
        FROM stockprices
        WHERE symbol = NEW.symbol AND price_date <= NEW.price_date
        ORDER BY price_date DESC
        LIMIT 50
    ) t;

    -- Calculate SMA-200
    SELECT AVG(day_close) INTO v_sma_200
    FROM (
        SELECT day_close
        FROM stockprices
        WHERE symbol = NEW.symbol AND price_date <= NEW.price_date
        ORDER BY price_date DESC
        LIMIT 200
    ) t;

    -- Calculate Volume SMA-20
    SELECT AVG(volume) INTO v_vol_sma_20
    FROM (
        SELECT volume
        FROM stockprices
        WHERE symbol = NEW.symbol AND price_date <= NEW.price_date
        ORDER BY price_date DESC
        LIMIT 20
    ) t;

    -- Insert into Tier 1 table
    INSERT INTO daily_indicators
        (symbol, price_date, daily_return, gap_pct, sma_20, sma_50, sma_200, volume_sma_20)
    VALUES
        (NEW.symbol, NEW.price_date, v_daily_ret, v_gap, v_sma_20, v_sma_50, v_sma_200, v_vol_sma_20);
END//

DELIMITER ;

-- ============================================================================
-- TIER 2 EVENT: Calculate complex indicators once per day
-- ============================================================================
-- This event runs after data refresh (e.g., 6 PM ET, after market close).
-- It uses window functions for efficient batch calculation across all symbols.
-- Runs once per day, NOT per insert = O(n_symbols) per day instead of
-- O(n_symbols * n_new_prices_per_day).

DELIMITER //

CREATE EVENT IF NOT EXISTS evt_refresh_tier2
ON SCHEDULE EVERY 1 DAY
STARTS '2026-05-27 22:00:00'  -- 10 PM ET, after data refresh + delay
ON COMPLETION PRESERVE
ENABLE
DO
BEGIN
    -- Delete today's data to allow re-run
    DELETE FROM daily_tier2 WHERE price_date = CURDATE();

    -- Insert Tier 2 indicators using window functions
    INSERT INTO daily_tier2
        (symbol, price_date, bb_middle, bb_upper, bb_lower, bb_width, bb_pct,
         atr_14, atr_pct, vol_ratio_20, vol_ratio_50,
         trend_50_200, calc_method)
    WITH price_data AS (
        SELECT
            sp.symbol,
            sp.price_date,
            sp.day_open,
            sp.day_high,
            sp.day_low,
            sp.day_close,
            sp.volume,
            LAG(sp.day_close) OVER (PARTITION BY sp.symbol ORDER BY sp.price_date) as prev_close,
            -- Bollinger Band components
            AVG(sp.day_close) OVER (
                PARTITION BY sp.symbol
                ORDER BY sp.price_date
                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
            ) as sma20,
            STDDEV(sp.day_close) OVER (
                PARTITION BY sp.symbol
                ORDER BY sp.price_date
                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
            ) as std20,
            -- ATR components
            AVG(
                GREATEST(
                    sp.day_high - sp.day_low,
                    ABS(sp.day_high - LAG(sp.day_close) OVER (PARTITION BY sp.symbol ORDER BY sp.price_date)),
                    ABS(sp.day_low - LAG(sp.day_close) OVER (PARTITION BY sp.symbol ORDER BY sp.price_date))
                )
            ) OVER (
                PARTITION BY sp.symbol
                ORDER BY sp.price_date
                ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
            ) as atr14,
            -- Volume averages
            AVG(sp.volume) OVER (
                PARTITION BY sp.symbol
                ORDER BY sp.price_date
                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
            ) as vol_avg20,
            AVG(sp.volume) OVER (
                PARTITION BY sp.symbol
                ORDER BY sp.price_date
                ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
            ) as vol_avg50,
            -- Trend detection
            AVG(sp.day_close) OVER (
                PARTITION BY sp.symbol
                ORDER BY sp.price_date
                ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
            ) as sma50,
            AVG(sp.day_close) OVER (
                PARTITION BY sp.symbol
                ORDER BY sp.price_date
                ROWS BETWEEN 199 PRECEDING AND CURRENT ROW
            ) as sma200,
            -- Row count to ensure we have enough data
            COUNT(*) OVER (
                PARTITION BY sp.symbol
                ORDER BY sp.price_date
                ROWS BETWEEN 199 PRECEDING AND CURRENT ROW
            ) as row_cnt
        FROM stockprices sp
        WHERE sp.price_date >= DATE_SUB(CURDATE(), INTERVAL 250 DAY)
    )
    SELECT
        symbol,
        price_date,
        -- Bollinger Bands
        ROUND(sma20, 4),
        ROUND(sma20 + 2 * std20, 4),
        ROUND(sma20 - 2 * std20, 4),
        CASE WHEN sma20 > 0 THEN ROUND((4 * std20) / sma20 * 100, 4) ELSE NULL END,
        CASE WHEN (sma20 + 2 * std20) - (sma20 - 2 * std20) > 0
             THEN ROUND((day_close - (sma20 - 2 * std20)) / ((sma20 + 2 * std20) - (sma20 - 2 * std20)) * 100, 4)
             ELSE NULL END,
        -- ATR
        ROUND(atr14, 4),
        CASE WHEN day_close > 0 THEN ROUND(atr14 / day_close * 100, 4) ELSE NULL END,
        -- Volume ratios
        CASE WHEN vol_avg20 > 0 THEN ROUND(volume / vol_avg20, 4) ELSE NULL END,
        CASE WHEN vol_avg50 > 0 THEN ROUND(volume / vol_avg50, 4) ELSE NULL END,
        -- Trend
        CASE
            WHEN row_cnt < 200 THEN 'INSUFFICIENT_DATA'
            WHEN sma50 > sma200 AND prev_close <= sma200 THEN 'GOLDEN_CROSS'
            WHEN sma50 < sma200 AND prev_close >= sma200 THEN 'DEATH_CROSS'
            WHEN sma50 > sma200 THEN 'BULLISH'
            ELSE 'BEARISH'
        END,
        'daily_event'
    FROM price_data
    WHERE price_date = CURDATE()
      AND row_cnt >= 20;  -- Need at least 20 rows for meaningful BB
END//

DELIMITER ;

-- ============================================================================
-- UNIFIED VIEW: All prices + indicators
-- ============================================================================
-- For backtesting: query this view and partition pruning handles the rest.
-- The WHERE clause on date range automatically limits which partitions
-- are scanned — no need for separate per-symbol tables or per-year views.

CREATE OR REPLACE VIEW v_stock_analysis AS
SELECT
    sp.symbol,
    sp.price_date,
    sp.day_open,
    sp.day_high,
    sp.day_low,
    sp.day_close,
    sp.volume,
    sp.adj_close,
    -- Tier 1 (trigger-calculated)
    ti.daily_return,
    ti.gap_pct,
    ti.sma_20,
    ti.sma_50,
    ti.sma_200,
    ti.volume_sma_20,
    -- Tier 2 (daily batch-calculated)
    t2.bb_middle,
    t2.bb_upper,
    t2.bb_lower,
    t2.bb_width,
    t2.bb_pct,
    t2.atr_14,
    t2.atr_pct,
    t2.vol_ratio_20,
    t2.vol_ratio_50,
    t2.trend_50_200,
    t2.signal_strength,
    t2.signal_reasons,
    -- Derived: price position relative to MAs
    CASE
        WHEN ti.sma_50 IS NOT NULL AND ti.sma_200 IS NOT NULL THEN
            CASE
                WHEN sp.day_close > ti.sma_50 AND ti.sma_50 > ti.sma_200 THEN 'STRONG_BULL'
                WHEN sp.day_close > ti.sma_200 THEN 'BULLISH'
                WHEN sp.day_close < ti.sma_50 AND ti.sma_50 < ti.sma_200 THEN 'STRONG_BEAR'
                WHEN sp.day_close < ti.sma_200 THEN 'BEARISH'
                ELSE 'SIDEWAYS'
            END
        ELSE NULL
    END as trend_position,
    YEAR(sp.price_date) as price_year
FROM stockprices sp
LEFT JOIN daily_indicators ti
    ON sp.symbol = ti.symbol AND sp.price_date = ti.price_date
LEFT JOIN daily_tier2 t2
    ON sp.symbol = t2.symbol AND sp.price_date = t2.price_date;

-- ============================================================================
-- BACKTEST TABLES
-- ============================================================================

CREATE TABLE backtest_runs (
    id                  INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    user_id             INT UNSIGNED    NOT NULL,
    strategy            VARCHAR(64)     NOT NULL,
    parameters          JSON            NULL COMMENT 'Strategy parameters as JSON',
    start_date          DATE            NULL,
    end_date            DATE            NULL,
    initial_capital     DECIMAL(15,2)  NOT NULL DEFAULT 100000.00,
    final_value         DECIMAL(15,2)  NULL,
    total_return        DECIMAL(8,4)  NULL,
    annualized_return   DECIMAL(8,4)  NULL,
    sharpe_ratio        DECIMAL(8,4)  NULL,
    max_drawdown        DECIMAL(8,4)  NULL,
    num_trades          INT UNSIGNED    NULL,
    win_rate            DECIMAL(5,4)  NULL,
    profit_factor       DECIMAL(8,4)  NULL,
    status              ENUM('pending', 'running', 'complete', 'error') NOT NULL DEFAULT 'pending',
    error_message       TEXT            NULL,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at        TIMESTAMP       NULL,
    PRIMARY KEY (id),
    INDEX idx_user_status (user_id, status),
    INDEX idx_strategy (strategy),
    CONSTRAINT fk_backtest_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE backtest_trades (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    backtest_id     INT UNSIGNED    NOT NULL,
    symbol          CHAR(16)        NOT NULL,
    trade_type      ENUM('BUY', 'SELL') NOT NULL,
    trade_date      DATE            NOT NULL,
    price           DECIMAL(15,4)  NOT NULL,
    quantity        INT UNSIGNED    NOT NULL,
    commission      DECIMAL(10,2)  NOT NULL DEFAULT 9.95,
    total_cost      DECIMAL(15,2)  NOT NULL,
    signal_reasons  VARCHAR(512)    NULL COMMENT 'Which signals triggered this trade',
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_backtest (backtest_id),
    CONSTRAINT fk_bt_backtest
        FOREIGN KEY (backtest_id) REFERENCES backtest_runs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Signal weights for strategy optimization (per-symbol, evolves over time)
CREATE TABLE signal_weights (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    symbol          CHAR(16)        NOT NULL,
    signal_type     VARCHAR(64)     NOT NULL COMMENT 'e.g., RSI_OVERSOLD, MACD_CROSS, BB_TOUCH',
    weight          DECIMAL(8,4)  NOT NULL DEFAULT 1.0 COMMENT 'Optimized weight for this signal',
    default_weight  DECIMAL(8,4)  NOT NULL DEFAULT 1.0,
    
    -- Performance tracking
    win_rate        DECIMAL(5,4)  NULL COMMENT 'Historical win rate for this signal',
    n_trades        INT UNSIGNED    NULL,
    avg_return      DECIMAL(10,6) NULL COMMENT 'Average return when this signal fires',
    
    -- Correlation & lead/lag analysis
    avg_lead_days   DECIMAL(5,1)  NULL COMMENT 'Avg days between signal and price move (+ = leads, - = lags)',
    is_pre_indicator TINYINT(1)   DEFAULT 0 COMMENT '1 if signal consistently leads price action',
    correlation     DECIMAL(5,4)  NULL COMMENT 'Correlation with future 5-day return',
    correlates_with JSON          NULL COMMENT 'JSON: [{"signal": "MACD_CROSS", "corr": 0.72, "lag_days": 3}]',
    
    -- Weight modulation
    weight_boosted  DECIMAL(8,4)  NULL COMMENT 'Effective weight when pre-indicator confirmed by follow-on',
    boost_condition VARCHAR(255)  NULL COMMENT 'Condition that triggers boost (e.g., MACD_CROSS within 5 days)',
    
    last_updated    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    updated_by      ENUM('backtest', 'manual', 'python_ml', 'correlation_analysis') NOT NULL DEFAULT 'manual',
    PRIMARY KEY (id),
    UNIQUE KEY uk_symbol_signal (symbol, signal_type),
    INDEX idx_symbol (symbol),
    INDEX idx_correlation (correlation),
    INDEX idx_pre_indicator (is_pre_indicator)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- PORTFOLIO TABLES
-- ============================================================================

CREATE TABLE portfolio (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    user_id         INT UNSIGNED    NOT NULL,
    symbol          CHAR(16)        NOT NULL,
    shares          DECIMAL(15,4)  NOT NULL DEFAULT 0,
    cost_basis      DECIMAL(15,4)  NOT NULL DEFAULT 0,
    cost_total      DECIMAL(15,2)  NOT NULL DEFAULT 0,
    account_type    ENUM('RRSP', 'TFSA', 'MARGIN', 'RESP', 'CASH') NOT NULL DEFAULT 'CASH',
    acquisition_date DATE           NULL,
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_user_symbol_account (user_id, symbol, account_type),
    INDEX idx_user_active (user_id, is_active),
    CONSTRAINT fk_portfolio_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE portfolio_history (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id         INT UNSIGNED    NOT NULL,
    snapshot_date   DATE            NOT NULL,
    total_value     DECIMAL(15,2)  NOT NULL DEFAULT 0,
    cash_balance    DECIMAL(15,2)  NOT NULL DEFAULT 0,
    num_positions   INT             NOT NULL DEFAULT 0,
    total_return_pct DECIMAL(8,4)  NULL,
    benchmark_return_pct DECIMAL(8,4)  NULL COMMENT 'TSX Composite return for comparison',
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_user_date (user_id, snapshot_date),
    INDEX idx_date (snapshot_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE user_trades (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id         INT UNSIGNED    NOT NULL,
    symbol          CHAR(16)        NOT NULL,
    action          ENUM('BUY', 'SELL', 'DIVIDEND', 'SPLIT', 'TRANSFER') NOT NULL,
    shares          DECIMAL(15,4)  NOT NULL,
    price           DECIMAL(15,4)  NOT NULL,
    commission      DECIMAL(10,2)  NOT NULL DEFAULT 9.95,
    total_amount    DECIMAL(15,2)  NOT NULL,
    account_type    ENUM('RRSP', 'TFSA', 'MARGIN', 'RESP', 'CASH') NOT NULL DEFAULT 'CASH',
    trade_date      DATE            NOT NULL,
    notes           TEXT            NULL,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_user_date (user_id, trade_date),
    INDEX idx_symbol (symbol),
    CONSTRAINT fk_trades_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- WATCHLIST & ALERTS
-- ============================================================================

CREATE TABLE watchlists (
    id          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    user_id     INT UNSIGNED    NOT NULL,
    name        VARCHAR(64)     NOT NULL,
    description TEXT            NULL,
    created_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_user_name (user_id, name),
    CONSTRAINT fk_watchlist_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE watchlist_symbols (
    watchlist_id    INT UNSIGNED    NOT NULL,
    symbol          CHAR(16)        NOT NULL,
    added_date      DATE            NOT NULL DEFAULT (CURRENT_DATE),
    notes           TEXT            NULL,
    PRIMARY KEY (watchlist_id, symbol),
    CONSTRAINT fk_ws_watchlist
        FOREIGN KEY (watchlist_id) REFERENCES watchlists(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE alerts (
    id                  INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    symbol              CHAR(16)        NOT NULL,
    alert_type          VARCHAR(64)     NOT NULL COMMENT 'PRICE_ABOVE, PRICE_BELOW, RSI_OVERBOUGHT, etc.',
    threshold_value     DECIMAL(15,4)  NULL,
    comparison          ENUM('GT', 'LT', 'EQ', 'GTE', 'LTE', 'BETWEEN') NOT NULL DEFAULT 'GT',
    secondary_value     DECIMAL(15,4)  NULL COMMENT 'For BETWEEN comparison',
    is_active           TINYINT(1)      NOT NULL DEFAULT 1,
    triggered_count     INT UNSIGNED    NOT NULL DEFAULT 0,
    last_triggered      TIMESTAMP       NULL,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_symbol_active (symbol, is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE alerts_raised (
    id                  INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    alert_id            INT UNSIGNED    NOT NULL,
    symbol              CHAR(16)        NOT NULL,
    triggered_value     DECIMAL(15,4)  NOT NULL,
    triggered_at        TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_cleared          TINYINT(1)      NOT NULL DEFAULT 0,
    cleared_at          TIMESTAMP       NULL,
    PRIMARY KEY (id),
    INDEX idx_alert (alert_id),
    INDEX idx_symbol_date (symbol, triggered_at),
    CONSTRAINT fk_raised_alert
        FOREIGN KEY (alert_id) REFERENCES alerts(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- DIVIDENDS & CORPORATE EVENTS
-- ============================================================================

CREATE TABLE dividends (
    id          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    symbol      CHAR(16)        NOT NULL,
    ex_date     DATE            NOT NULL,
    pay_date    DATE            NULL,
    amount      DECIMAL(15,4)  NOT NULL DEFAULT 0,
    currency    CHAR(3)         NOT NULL DEFAULT 'CAD',
    div_type    ENUM('CASH', 'STOCK', 'SPECIAL', 'RETURN_OF_CAPITAL') NOT NULL DEFAULT 'CASH',
    created_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_symbol_date (symbol, ex_date),
    UNIQUE KEY uk_symbol_exdate (symbol, ex_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE corporate_events (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    symbol          CHAR(16)        NOT NULL,
    event_type      ENUM('SPLIT', 'MERGER', 'ACQUISITION', 'DELISTING', 'NAME_CHANGE', 'SYMBOL_CHANGE') NOT NULL,
    event_date      DATE            NOT NULL,
    ratio           DECIMAL(10,4)  NULL COMMENT 'For splits: new/old ratio',
    description     TEXT            NULL,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_symbol_date (symbol, event_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- FA INTEGRATION
-- ============================================================================

CREATE TABLE fa_transfers (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    fa_journal_id   INT UNSIGNED    NULL,
    from_account    VARCHAR(32)     NOT NULL,
    to_account      VARCHAR(32)     NOT NULL,
    amount          DECIMAL(15,2)  NOT NULL,
    trade_date      DATE            NOT NULL,
    description     TEXT            NULL,
    reconciled      TINYINT(1)      NOT NULL DEFAULT 0,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_date (trade_date),
    INDEX idx_reconciled (reconciled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- DATA IMPORT LOG
-- ============================================================================

CREATE TABLE data_import_log (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    import_type     ENUM('csv', 'yfinance', 'manual', 'migration', 'api') NOT NULL,
    symbol          CHAR(16)        NULL,
    source          VARCHAR(255)    NULL,
    records_before  INT UNSIGNED    NULL,
    records_after   INT UNSIGNED    NULL,
    records_added   INT UNSIGNED    NULL,
    status          ENUM('started', 'complete', 'error') NOT NULL DEFAULT 'started',
    error_message   TEXT            NULL,
    duration_ms     INT UNSIGNED    NULL,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_type_date (import_type, created_at),
    INDEX idx_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- SEED DATA
-- ============================================================================

INSERT INTO transactiontype (transactiontype, description) VALUES
    ('BUY', 'Purchase shares'),
    ('SELL', 'Sell shares'),
    ('DIVIDEND', 'Dividend payment'),
    ('SPLIT', 'Stock split'),
    ('TRANSFER', 'Transfer shares'),
    ('EXCHANGE', 'Exchange/convert shares'),
    ('TAKEOVER', 'Acquisition/takeover');

INSERT INTO stockexchange (exchange_name, country, currency) VALUES
    ('TSX', 'CA', 'CAD'),
    ('TSXV', 'CA', 'CAD'),
    ('NYSE', 'US', 'USD'),
    ('NASDAQ', 'US', 'USD'),
    ('CBOE', 'CA', 'CAD'),
    ('LSE', 'GB', 'GBP');

INSERT INTO users (username, email, password_hash, role, first_name, last_name) VALUES
    ('admin', 'admin@ksfraser.ca', '$2y$12$placeholder_change_me', 'admin', 'Admin', 'User'),
    ('kevin', 'kevin@ksfraser.ca', '$2y$12$placeholder_change_me', 'admin', 'Kevin', 'Fraser');

-- ============================================================================
-- SCORING & STRATEGY TABLES (preserved from legacy, enhanced for LLM)
-- ============================================================================
-- These tables represent the investment thesis scoring system.
-- Python/LLM populates them by analyzing press releases, 10-K/10-Q filings,
-- earnings call transcripts, and financial data.
--
-- Three categories:
--   1. Quantitative (ratios): Python calculates from financial data
--   2. Rule-based qualitative (motleyfool, investorplace): LLM checks criteria
--   3. Subjective qualitative (tenets, evalbusiness, evalsummary): LLM assists,
--      human has final say
--
-- All scoring tables include source attribution (what document was analyzed)
-- and user tracking (who populated/overrode the score).

-- --------------------------------------------------------------------------
-- Motley Fool screening criteria (Rule Breakers / Stock Advisor)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS motleyfool (
    symbol          CHAR(16)    NOT NULL,
    doubledigitrisingsales  TINYINT(1)  NULL COMMENT 'Sales growth >= 10%',
    risingfreecashflow      TINYINT(1)  NULL COMMENT 'Free cash flow rising',
    risingbookvalue         TINYINT(1)  NULL COMMENT 'Book value rising',
    improvingmargin         TINYINT(1)  NULL COMMENT 'Margins improving',
    risingreturnonequity    TINYINT(1)  NULL COMMENT 'ROE rising',
    insiderownership        TINYINT(1)  NULL COMMENT 'Executive ownership significant',
    regulardividends        TINYINT(1)  NULL COMMENT 'Consistent dividend payments',
    mf_score                INT         NULL COMMENT 'Composite MF score',
    source                  VARCHAR(255) NULL COMMENT 'Data source (10-K, earnings, etc.)',
    source_date             DATE        NULL COMMENT 'Date of source document',
    is_llm_generated        TINYINT(1)  NOT NULL DEFAULT 0 COMMENT '1 if LLM-populated',
    llm_confidence          DECIMAL(5,4) NULL COMMENT 'LLM confidence 0-1',
    llm_reasoning           TEXT        NULL COMMENT 'LLM explanation for scores',
    human_overridden        TINYINT(1)  NOT NULL DEFAULT 0 COMMENT '1 if human changed LLM score',
    created_at              TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol),
    INDEX idx_mf_score (mf_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------
-- InvestorPlace screening criteria
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS investorplace (
    id                  INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    symbol              CHAR(16)        NOT NULL,
    seventyfivepercent  TINYINT(1)      NULL COMMENT 'Domestic sales >= 75%',
    earningsgrowth      TINYINT(1)      NULL COMMENT 'Earnings growing',
    earningsaccel       TINYINT(1)      NULL COMMENT 'Earnings growth accelerating',
    pe                  DECIMAL(10,2)  NULL COMMENT 'P/E ratio',
    tradingvolume       INT UNSIGNED    NULL COMMENT 'Trading volume',
    institutioninterest DECIMAL(5,2)   NULL COMMENT 'Institutional ownership %',
    orderimbalance      TINYINT(1)      NULL COMMENT 'Buy/sell order balance',
    shortinterest       TINYINT(1)      NULL COMMENT 'High short interest',
    volatility          DECIMAL(10,4)  NULL COMMENT 'Share volatility',
    dividendearningratio DECIMAL(10,4) NULL COMMENT 'Dividend/earnings ratio',
    newproductline      TINYINT(1)      NULL COMMENT 'Innovations / new products',
    restructuring       TINYINT(1)      NULL COMMENT 'Cost-cutting restructuring',
    reengineering       TINYINT(1)      NULL COMMENT 'Business reengineering',
    sharebuyback        TINYINT(1)      NULL COMMENT 'Share buyback program',
    headcountcuts       TINYINT(1)      NULL COMMENT 'Announced staff reductions',
    spinoffs            TINYINT(1)      NULL COMMENT 'Business spin-offs',
    reducedrd           TINYINT(1)      NULL COMMENT 'Reducing R&D',
    extracash           TINYINT(1)      NULL COMMENT 'Cash on hand',
    shareholderprofitgoal TINYINT(1)    NULL COMMENT 'Management focused on shareholder profit',
    dividendincreases   TINYINT(1)      NULL COMMENT 'Track record of dividend increases',
    ip_score            INT             NULL COMMENT 'Composite IP score',
    source              VARCHAR(255)    NULL COMMENT 'Data source',
    source_date         DATE            NULL COMMENT 'Date of source document',
    is_llm_generated    TINYINT(1)      NOT NULL DEFAULT 0,
    llm_confidence      DECIMAL(5,4)   NULL,
    llm_reasoning       TEXT            NULL,
    human_overridden    TINYINT(1)      NOT NULL DEFAULT 0,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_symbol (symbol),
    INDEX idx_ip_score (ip_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------
-- Business quality assessment (Buffett-style business tenets)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evalbusiness (
    id                  INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    symbol              CHAR(16)        NOT NULL,
    summary             INT             NULL COMMENT 'Summary score (out of 5)',
    simple              TINYINT(1)      NULL COMMENT 'Simple business model',
    consistent_history  TINYINT(1)      NULL COMMENT 'Consistent performance history',
    neededproduct       TINYINT(1)      NULL COMMENT 'Product is needed',
    noclosesubstitute   TINYINT(1)      NULL COMMENT 'No close substitute',
    regulated           TINYINT(1)      NULL COMMENT 'Regulated industry (moat)',
    source              VARCHAR(255)    NULL COMMENT 'Data source',
    source_date         DATE            NULL,
    is_llm_generated    TINYINT(1)      NOT NULL DEFAULT 0,
    llm_confidence      DECIMAL(5,4)   NULL,
    llm_reasoning       TEXT            NULL,
    human_overridden    TINYINT(1)      NOT NULL DEFAULT 0,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------
-- Management & business tenets (Buffett-style, detailed)
-- --------------------------------------------------------------------------
-- Note: legacy "tenets" table had per-symbol rows with integer scores.
-- This enhanced version adds LLM support and source attribution.
CREATE TABLE IF NOT EXISTS tenets (
    id                  INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    symbol              CHAR(16)        NOT NULL,
    simple              INT             NULL COMMENT 'Simple business (0-10)',
    consistent          INT             NULL COMMENT 'Consistent performance (0-10)',
    longterm            INT             NULL COMMENT 'Long-term prospects (0-10)',
    rationalmanager     INT             NULL COMMENT 'Rational management (0-10)',
    candid              INT             NULL COMMENT 'Candid with shareholders (0-10)',
    resistinstitution   INT             NULL COMMENT 'Resists institutional pressures (0-10)',
    focusroe            INT             NULL COMMENT 'Focuses on ROE, not EPS (0-10)',
    ownerearnings       INT             NULL COMMENT 'Calculates owner earnings (0-10)',
    highprofitmargin    INT             NULL COMMENT 'High profit margins (0-10)',
    retainedtomarket    INT             NULL COMMENT 'Retained earnings → market value (0-10)',
    valueofbusiness     INT             NULL COMMENT 'Intrinsic value calculation (0-10)',
    discounted          INT             NULL COMMENT 'Purchased at discount (0-10)',
    total_score         INT             NULL COMMENT 'Sum of all tenet scores',
    source              VARCHAR(255)    NULL COMMENT 'Data source (annual letter, proxy, etc.)',
    source_date         DATE            NULL,
    is_llm_generated    TINYINT(1)      NOT NULL DEFAULT 0,
    llm_confidence      DECIMAL(5,4)   NULL,
    llm_reasoning       TEXT            NULL,
    human_overridden    TINYINT(1)      NOT NULL DEFAULT 0,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_symbol (symbol),
    INDEX idx_total_score (total_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------
-- Financial ratio analysis with attractiveness scoring
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ratios (
    id                  INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    symbol              CHAR(16)        NOT NULL,
    -- Raw ratio values
    roe                 DECIMAL(10,4)  NULL COMMENT 'Return on Equity',
    roa                 DECIMAL(10,4)  NULL COMMENT 'Return on Assets',
    roce                DECIMAL(10,4)  NULL COMMENT 'Return on Capital Employed',
    grossprofitmargin   DECIMAL(10,4)  NULL COMMENT 'Gross Profit Margin',
    pretaxmargin        DECIMAL(10,4)  NULL COMMENT 'Pre-tax Margin',
    netmargin           DECIMAL(10,4)  NULL COMMENT 'Net Margin',
    operatingmargin     DECIMAL(10,4)  NULL COMMENT 'Operating Margin',
    debtratio           DECIMAL(10,4)  NULL COMMENT 'Debt Ratio (debt/assets)',
    acceptabledebtratio DECIMAL(10,4)  NULL COMMENT 'Acceptable Debt Ratio',
    peratio             DECIMAL(10,4)  NULL COMMENT 'P/E Ratio',
    -- Attractiveness scores (1 = meets threshold, 0 = doesn't)
    roeattractive       TINYINT(1)      NULL COMMENT 'ROE > 15%',
    attractiveroa       TINYINT(1)      NULL COMMENT 'ROA attractive',
    attractiveroce      TINYINT(1)      NULL COMMENT 'ROCE attractive',
    attractivegross     TINYINT(1)      NULL COMMENT 'Gross margin attractive',
    attractivepretax    TINYINT(1)      NULL COMMENT 'Pre-tax margin attractive',
    attractivenet       TINYINT(1)      NULL COMMENT 'Net margin attractive',
    lowcost             TINYINT(1)      NULL COMMENT 'Low cost operations (opmargin > 10%)',
    sustaindebtratio    TINYINT(1)      NULL COMMENT 'Debt covered by income long-term',
    attractivesum       INT             NULL COMMENT 'Sum of all attractive scores',
    -- Source tracking
    source              VARCHAR(255)    NULL COMMENT 'Data source (10-K, 10-Q)',
    source_date         DATE            NULL,
    is_llm_generated    TINYINT(1)      NOT NULL DEFAULT 0,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_symbol (symbol),
    INDEX idx_attractivesum (attractivesum)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------
-- Quarterly financial statements
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS quarter_statement (
    id                  INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    symbol              CHAR(16)        NOT NULL,
    fiscal_year         YEAR            NOT NULL,
    fiscal_quarter      TINYINT         NOT NULL COMMENT '1-4',
    -- Income statement
    revenue             DECIMAL(15,2)  NULL,
    revenuegrowth       DECIMAL(10,4)  NULL COMMENT 'YoY revenue growth %',
    revenuegrowth2      DECIMAL(10,4)  NULL COMMENT '2-year revenue growth %',
    revenuegrowth3      DECIMAL(10,4)  NULL COMMENT '3-year revenue growth %',
    netincome           DECIMAL(15,2)  NULL,
    incomegrowth        DECIMAL(10,4)  NULL COMMENT 'YoY income growth %',
    earningpershare     DECIMAL(10,4)  NULL,
    -- Balance sheet
    totalasset          DECIMAL(15,2)  NULL,
    totalliability      DECIMAL(15,2)  NULL,
    totalequity         DECIMAL(15,2)  NULL,
    totaldebt           DECIMAL(15,2)  NULL,
    retainedearnings    DECIMAL(15,2)  NULL,
    -- Cash flow
    ownerearnings       DECIMAL(15,2)  NULL,
    capitalexpenses     DECIMAL(15,2)  NULL,
    depletion           DECIMAL(15,2)  NULL,
    amortization        DECIMAL(15,2)  NULL,
    workingcapital      DECIMAL(15,2)  NULL,
    -- Other
    outstandingshares   BIGINT UNSIGNED NULL,
    dividendpershare    DECIMAL(10,4)  NULL,
    -- Source tracking
    source              VARCHAR(255)    NULL COMMENT '10-Q filing, etc.',
    source_date         DATE            NULL,
    is_llm_generated    TINYINT(1)      NOT NULL DEFAULT 0,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_symbol_year_qtr (symbol, fiscal_year, fiscal_quarter),
    INDEX idx_symbol (symbol),
    INDEX idx_year_qtr (fiscal_year, fiscal_quarter)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------
-- Management evaluation
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evalmanagement (
    id                  INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    symbol              CHAR(16)        NOT NULL,
    management_score    INT             NULL COMMENT 'Composite management score',
    source              VARCHAR(255)    NULL,
    source_date         DATE            NULL,
    is_llm_generated    TINYINT(1)      NOT NULL DEFAULT 0,
    llm_confidence      DECIMAL(5,4)   NULL,
    llm_reasoning       TEXT            NULL,
    human_overridden    TINYINT(1)      NOT NULL DEFAULT 0,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------
-- Market evaluation
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evalmarket (
    id                  INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    symbol              CHAR(16)        NOT NULL,
    market_score        INT             NULL COMMENT 'Composite market evaluation score',
    source              VARCHAR(255)    NULL,
    source_date         DATE            NULL,
    is_llm_generated    TINYINT(1)      NOT NULL DEFAULT 0,
    llm_confidence      DECIMAL(5,4)   NULL,
    llm_reasoning       TEXT            NULL,
    human_overridden    TINYINT(1)      NOT NULL DEFAULT 0,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------
-- Value assessment
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evalvalue (
    id                  INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    symbol              CHAR(16)        NOT NULL,
    value_score         INT             NULL COMMENT 'Composite value score',
    intrinsic_value     DECIMAL(15,2)  NULL COMMENT 'Calculated intrinsic value',
    margin_of_safety    DECIMAL(10,4)  NULL COMMENT 'Margin of safety %',
    source              VARCHAR(255)    NULL,
    source_date         DATE            NULL,
    is_llm_generated    TINYINT(1)      NOT NULL DEFAULT 0,
    llm_confidence      DECIMAL(5,4)   NULL,
    llm_reasoning       TEXT            NULL,
    human_overridden    TINYINT(1)      NOT NULL DEFAULT 0,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------
-- Composite evaluation summary (the "final score" per symbol)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evalsummary (
    symbol              CHAR(16)        NOT NULL,
    totalscore          INT             NULL COMMENT 'Total of all scores (out of 36)',
    marginsafety        DECIMAL(10,4)  NULL COMMENT 'Margin of safety (%)',
    ratioscore          INT             NULL COMMENT 'Score from ratios table (out of 8)',
    iplacecalcscore     INT             NULL COMMENT 'InvestorPlace score (out of 10)',
    managementscore     INT             NULL COMMENT 'Management tenets score (out of 9)',
    financialscore      INT             NULL COMMENT 'Financial tenets score (out of 4)',
    businessscore       INT             NULL COMMENT 'Business tenets score (out of 5)',
    mf_score            INT             NULL COMMENT 'Motley Fool score',
    ip_score            INT             NULL COMMENT 'InvestorPlace score',
    tenet_score         INT             NULL COMMENT 'Tenets total score',
    value_score         INT             NULL COMMENT 'Value assessment score',
    -- LLM analysis summary
    llm_summary         TEXT            NULL COMMENT 'LLM-generated investment thesis summary',
    llm_confidence      DECIMAL(5,4)   NULL,
    llm_recommendation  ENUM('STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL') NULL,
    -- Human override
    human_recommendation ENUM('STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL') NULL,
    human_notes         TEXT            NULL COMMENT 'Human analyst notes',
    -- Source tracking
    last_eval_date      DATE            NULL,
    last_eval_source    VARCHAR(255)    NULL COMMENT 'What triggered the last evaluation',
    is_llm_generated    TINYINT(1)      NOT NULL DEFAULT 0,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol),
    INDEX idx_totalscore (totalscore),
    INDEX idx_llm_rec (llm_recommendation),
    INDEX idx_human_rec (human_recommendation)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------
-- Scoring history (track how scores change over time)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scoring_history (
    id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    symbol              CHAR(16)        NOT NULL,
    scored_at           DATE            NOT NULL,
    table_name          VARCHAR(64)     NOT NULL COMMENT 'Which scoring table was updated',
    field_name          VARCHAR(64)     NOT NULL COMMENT 'Which field changed',
    old_value           VARCHAR(255)    NULL,
    new_value           VARCHAR(255)    NULL,
    source              VARCHAR(255)    NULL COMMENT 'What document triggered the change',
    is_llm_generated    TINYINT(1)      NOT NULL DEFAULT 0,
    llm_confidence      DECIMAL(5,4)   NULL,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_symbol_date (symbol, scored_at),
    INDEX idx_table_field (table_name, field_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- BACKUP PROCEDURES (documented — run via cron or manually)
-- ============================================================================
--
-- 1. Full backup (dumps each partition separately):
--    for year in $(seq 2008 2026); do
--      mysqldump --single-transaction \
--        --where "YEAR(price_date)=${year}" \
--        ksf_stockmarket stockprices stockprices_${year}.sql
--    done
--
-- 2. Incremental (today's partition only):
--    mysqldump --single-transaction \
--      --where "YEAR(price_date)=YEAR(CURDATE())" \
--      ksf_stockmarket stockprices > stockprices_current.sql
--
-- 3. Tier tables (small, full dump):
--    mysqldump --single-transaction ksf_stockmarket daily_indicators daily_tier2 > indicators.sql
--
-- 4. Full database (excludes partitioned price data for speed):
--    mysqldump --ignore-table=ksf_stockmarket.stockprices ksf_stockmarket > schema_and_small_tables.sql
--
-- 5. Signal weights (portable across environments):
--    mysqldump ksf_stockmarket signal_weights > signal_weights.sql
--
-- 6. Scoring tables (investment thesis — portable):
--    mysqldump ksf_stockmarket evalsummary motleyfool investorplace tenets \
--      evalbusiness ratios quarter_statement evalmanagement evalmarket evalvalue \
--      scoring_history > scoring_tables.sql
--
-- 7. TA values (exotic indicators — name-value pairs):
--    mysqldump ksf_stockmarket ta_values > ta_values.sql

-- ============================================================================
-- TIER 3: TA VALUES (Python/TA-Lib, name-value storage)
-- ============================================================================
-- ~315 exotic indicators stored as name-value pairs.
-- Common indicators (Tier 1+2) are in wide columns for fast queries.
-- Exotic indicators (candlestick patterns, custom TA) are here.

CREATE TABLE IF NOT EXISTS ta_values (
    symbol      CHAR(16)        NOT NULL,
    price_date  DATE            NOT NULL,
    indicator   VARCHAR(64)     NOT NULL COMMENT 'e.g., RSI_14, MACD, CDL_DOJI',
    value       DECIMAL(15,8)  NULL,
    signal      ENUM('BUY', 'SELL', 'HOLD', 'N/A') NULL COMMENT 'Signal direction for pattern indicators',
    source      VARCHAR(32)     NULL DEFAULT 'ta_lib' COMMENT 'ta_lib, pandas_ta, custom',
    updated_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, price_date, indicator),
    INDEX idx_symbol_date (symbol, price_date),
    INDEX idx_indicator (indicator),
    INDEX idx_signal (signal)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
PARTITION BY RANGE (YEAR(price_date)) (
    PARTITION p_early VALUES LESS THAN (2010),
    PARTITION p2010 VALUES LESS THAN (2012),
    PARTITION p2012 VALUES LESS THAN (2014),
    PARTITION p2014 VALUES LESS THAN (2016),
    PARTITION p2016 VALUES LESS THAN (2018),
    PARTITION p2018 VALUES LESS THAN (2020),
    PARTITION p2020 VALUES LESS THAN (2022),
    PARTITION p2022 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2026),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);
--
