-- ============================================================================
-- ksf_stockmarket — MariaDB 10.11 Schema
-- ============================================================================
-- Design goals:
--   1. Partition price data by year (backup-friendly)
--   2. Materialize Tier 2 indicators (SMA, EMA, BB, ATR) on insert/nightly
--   3. Backtests read pre-computed indicators (fast)
--   4. All InnoDB, utf8mb4, proper indexing
--   5. Compatible with MariaDB 10.5+ (local dev) and 10.11 (production pod)
-- ============================================================================

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

DROP DATABASE IF EXISTS ksf_stockmarket;
CREATE DATABASE ksf_stockmarket
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE ksf_stockmarket;

-- ============================================================================
-- SECTION 1: REFERENCE / LOOKUP TABLES
-- ============================================================================

-- Stock exchanges (TSX, NYSE, NASDAQ, etc.)
CREATE TABLE stockexchange (
    id              SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
    exchange_name   VARCHAR(45)       NOT NULL,
    yahoo_symbol    VARCHAR(45)       NOT NULL DEFAULT '',
    google_symbol   VARCHAR(45)       NOT NULL DEFAULT '',
    globe_symbol    VARCHAR(45)       NOT NULL DEFAULT '',
    country_code    CHAR(3)           NOT NULL DEFAULT 'CAD',
    timezone        VARCHAR(45)       NOT NULL DEFAULT 'America/Toronto',
    is_active       TINYINT(1)        NOT NULL DEFAULT 1,
    PRIMARY KEY (id),
    UNIQUE KEY uk_exchange_name (exchange_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Transaction types
CREATE TABLE transactiontype (
    type_code       VARCHAR(20)       NOT NULL,
    description     VARCHAR(100)      NOT NULL DEFAULT '',
    is_active       TINYINT(1)        NOT NULL DEFAULT 1,
    PRIMARY KEY (type_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Account types (RRSP, TFSA, INV, etc.)
CREATE TABLE accounttype (
    type_code       VARCHAR(20)       NOT NULL,
    description     VARCHAR(100)      NOT NULL DEFAULT '',
    is_active       TINYINT(1)        NOT NULL DEFAULT 1,
    PRIMARY KEY (type_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Bond rates (for Buffett valuation)
CREATE TABLE bondrate (
    id              SMALLINT UNSIGNED NOT NULL AUTO_ENUM AUTO_INCREMENT,
    calendar_year   YEAR              NOT NULL,
    bond_rate       DECIMAL(5,4)      NOT NULL DEFAULT 0.0300,
    created_at      TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_bondrate_year (calendar_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Alert types
CREATE TABLE alerttype (
    id              SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
    alert_name      VARCHAR(64)       NOT NULL,
    description     VARCHAR(255)      NOT NULL DEFAULT '',
    function_name   VARCHAR(45)       NOT NULL,
    is_active       TINYINT(1)        NOT NULL DEFAULT 1,
    PRIMARY KEY (id),
    UNIQUE KEY uk_alert_name (alert_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- SECTION 2: USER MANAGEMENT
-- ============================================================================

CREATE TABLE roles (
    id              SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
    role_name       VARCHAR(32)       NOT NULL,
    description     VARCHAR(255)      NOT NULL DEFAULT '',
    permissions     JSON              NULL,
    is_active       TINYINT(1)        NOT NULL DEFAULT 1,
    created_at      TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_role_name (role_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE users (
    id              INT UNSIGNED      NOT NULL AUTO_INCREMENT,
    username        VARCHAR(64)       NOT NULL,
    email           VARCHAR(255)      NULL,
    password_hash   VARCHAR(255)      NOT NULL,
    first_name      VARCHAR(64)       NULL,
    last_name       VARCHAR(64)       NULL,
    role_id         SMALLINT UNSIGNED NULL,
    is_active       TINYINT(1)        NOT NULL DEFAULT 1,
    last_login      TIMESTAMP         NULL,
    created_at      TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_username (username),
    UNIQUE KEY uk_email (email),
    KEY fk_users_role (role_id),
    CONSTRAINT fk_users_role FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- SECTION 3: SYMBOL / COMPANY MASTER DATA
-- ============================================================================

CREATE TABLE stockinfo (
    id              INT UNSIGNED      NOT NULL AUTO_INCREMENT,
    symbol          VARCHAR(16)       NOT NULL,
    exchange_id     SMALLINT UNSIGNED NULL,
    corporate_name  VARCHAR(255)      NOT NULL DEFAULT '',
    sector          VARCHAR(128)      NULL,
    industry        VARCHAR(128)      NULL,
    -- Price metadata (updated on each price refresh)
    year_high       DECIMAL(15,4)    NOT NULL DEFAULT 0,
    year_low        DECIMAL(15,4)    NOT NULL DEFAULT 99999,
    current_price   DECIMAL(15,4)    NOT NULL DEFAULT 0,
    previous_close  DECIMAL(15,4)    NULL,
    day_change      DECIMAL(15,4)    NULL,
    day_change_pct  DECIMAL(8,4)     NULL,
    volume          BIGINT UNSIGNED   NOT NULL DEFAULT 0,
    avg_volume      BIGINT UNSIGNED   NOT NULL DEFAULT 0,
    market_cap      BIGINT UNSIGNED   NULL,
    -- Fundamental data
    eps             DECIMAL(15,4)    NULL,
    pe_ratio        DECIMAL(10,4)    NULL,
    annual_dividend DECIMAL(10,4)    NULL,
    dividend_yield  DECIMAL(8,4)     NULL,
    shares_outstanding BIGINT UNSIGNED NULL,
    book_value      DECIMAL(15,4)    NULL,
    -- Status
    is_active       TINYINT(1)        NOT NULL DEFAULT 1 COMMENT '0=delisted',
    data_source     VARCHAR(32)       NULL,
    last_price_date DATE              NULL,
    -- Audit
    as_of_date      TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at      TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_stockinfo_symbol (symbol),
    KEY fk_stockinfo_exchange (exchange_id),
    KEY idx_stockinfo_sector (sector),
    KEY idx_stockinfo_active (is_active),
    KEY idx_stockinfo_name (corporate_name),
    CONSTRAINT fk_stockinfo_exchange FOREIGN KEY (exchange_id) REFERENCES stockexchange(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- SECTION 4: PRICE DATA (PARTITIONED BY YEAR)
-- ============================================================================

CREATE TABLE stockprices (
    symbol          VARCHAR(16)       NOT NULL,
    price_date      DATE              NOT NULL,
    price_year      SMALLINT UNSIGNED NOT NULL COMMENT 'Generated: YEAR(price_date) for partitioning',
    open_price      DECIMAL(15,4)    NOT NULL DEFAULT 0,
    high_price      DECIMAL(15,4)    NOT NULL DEFAULT 0,
    low_price       DECIMAL(15,4)    NOT NULL DEFAULT 0,
    close_price     DECIMAL(15,4)    NOT NULL DEFAULT 0,
    adj_close       DECIMAL(15,4)    NULL,
    volume          BIGINT UNSIGNED   NOT NULL DEFAULT 0,
    -- Source tracking
    source          VARCHAR(32)       NOT NULL DEFAULT 'csv' COMMENT 'csv, yfinance, manual',
    -- Audit
    created_at      TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, price_date),
    KEY idx_sp_date (price_date),
    KEY idx_sp_year (price_year),
    KEY idx_sp_symbol_date (symbol, price_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
PARTITION BY RANGE (price_year) (
    PARTITION p_pre2010 VALUES LESS THAN (2010),
    PARTITION p_2010    VALUES LESS THAN (2011),
    PARTITION p_2011    VALUES LESS THAN (2012),
    PARTITION p_2012    VALUES LESS THAN (2013),
    PARTITION p_2013    VALUES LESS THAN (2014),
    PARTITION p_2014    VALUES LESS THAN (2015),
    PARTITION p_2015    VALUES LESS THAN (2016),
    PARTITION p_2016    VALUES LESS THAN (2017),
    PARTITION p_2017    VALUES LESS THAN (2018),
    PARTITION p_2018    VALUES LESS THAN (2019),
    PARTITION p_2019    VALUES LESS THAN (2020),
    PARTITION p_2020    VALUES LESS THAN (2021),
    PARTITION p_2021    VALUES LESS THAN (2022),
    PARTITION p_2022    VALUES LESS THAN (2023),
    PARTITION p_2023    VALUES LESS THAN (2024),
    PARTITION p_2024    VALUES LESS THAN (2025),
    PARTITION p_2025    VALUES LESS THAN (2026),
    PARTITION p_2026    VALUES LESS THAN (2027),
    PARTITION p_future  VALUES LESS THAN MAXVALUE
);

-- Generated column for partitioning
ALTER TABLE stockprices
    ADD COLUMN price_year SMALLINT UNSIGNED NOT NULL
    GENERATED ALWAYS AS (YEAR(price_date)) STORED
    AFTER price_date;

-- ============================================================================
-- SECTION 5: DAILY INDICATORS (TIER 2 — MATERIALIZED)
-- ============================================================================
-- Calculated nightly by stored procedure after price inserts.
-- Backtest engine reads from here instead of computing on the fly.

CREATE TABLE daily_indicators (
    symbol          VARCHAR(16)       NOT NULL,
    price_date      DATE              NOT NULL,
    -- Price-based
    daily_return    DECIMAL(10,6)    NULL COMMENT '(close_t / close_t-1) - 1',
    log_return      DECIMAL(10,6)    NULL COMMENT 'LN(close_t / close_t-1)',
    gap_pct         DECIMAL(10,6)    NULL COMMENT '(open_t / close_t-1) - 1',
    true_range      DECIMAL(15,4)    NULL COMMENT 'MAX(high-low, |high-prev_close|, |low-prev_close|)',
    -- Simple Moving Averages
    sma_5           DECIMAL(15,4)    NULL,
    sma_10          DECIMAL(15,4)    NULL,
    sma_20          DECIMAL(15,4)    NULL,
    sma_50          DECIMAL(15,4)    NULL,
    sma_100         DECIMAL(15,4)    NULL,
    sma_200         DECIMAL(15,4)    NULL,
    -- Exponential Moving Averages
    ema_12          DECIMAL(15,4)    NULL,
    ema_26          DECIMAL(15,4)    NULL,
    -- Bollinger Bands (20-day, 2 std dev)
    bb_middle       DECIMAL(15,4)    NULL COMMENT 'SMA(20)',
    bb_std          DECIMAL(15,4)    NULL COMMENT 'STDDEV(20)',
    bb_upper        DECIMAL(15,4)    NULL COMMENT 'BB_MID + 2*BB_STD',
    bb_lower        DECIMAL(15,4)    NULL COMMENT 'BB_MID - 2*BB_STD',
    bb_width        DECIMAL(10,6)    NULL COMMENT '(UPPER-LOWER)/MIDDLE',
    bb_pct          DECIMAL(10,6)    NULL COMMENT '(CLOSE-LOWER)/(UPPER-LOWER)',
    -- ATR (14-day)
    atr_14          DECIMAL(15,4)    NULL,
    -- Volume indicators
    vol_sma_20      BIGINT UNSIGNED   NULL,
    vol_ratio       DECIMAL(10,4)    NULL COMMENT 'VOLUME / VOL_SMA_20',
    -- Trend signals
    sma_cross      VARCHAR(10)       NULL COMMENT 'GOLDEN_CROSS, DEATH_CROSS, or NULL',
    price_vs_sma20  DECIMAL(10,4)    NULL COMMENT '(CLOSE-SMA20)/SMA20 * 100',
    price_vs_sma50  DECIMAL(10,4)    NULL,
    price_vs_sma200 DECIMAL(10,4)    NULL,
    -- Metadata
    calc_date       TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, price_date),
    KEY idx_di_date (price_date),
    KEY idx_di_sma_cross (sma_cross),
    KEY idx_di_symbol_date (symbol, price_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
PARTITION BY RANGE (YEAR(price_date)) (
    PARTITION p_pre2020 VALUES LESS THAN (2020),
    PARTITION p_2020    VALUES LESS THAN (2021),
    PARTITION p_2021    VALUES LESS THAN (2022),
    PARTITION p_2022    VALUES LESS THAN (2023),
    PARTITION p_2023    VALUES LESS THAN (2024),
    PARTITION p_2024    VALUES LESS THAN (2025),
    PARTITION p_2025    VALUES LESS THAN (2026),
    PARTITION p_2026    VALUES LESS THAN (2027),
    PARTITION p_future  VALUES LESS THAN MAXVALUE
);

-- ============================================================================
-- SECTION 6: TECHNICAL ANALYSIS (TIER 3 — CANDLESTICK PATTERNS)
-- ============================================================================
-- Populated by Python/TA-Lib. Stores pattern recognition results.

CREATE TABLE technicalanalysis (
    id              INT UNSIGNED      NOT NULL AUTO_INCREMENT,
    symbol          VARCHAR(16)       NOT NULL,
    price_date      DATE              NOT NULL,
    -- Candlestick patterns (from TA-Lib)
    pattern_name    VARCHAR(64)       NULL COMMENT 'Doji, Hammer, Engulfing, etc.',
    pattern_bearish TINYINT(1)        NULL COMMENT '1=bearish, 0=bullish, NULL=neutral',
    pattern_strength DECIMAL(5,2)     NULL COMMENT '0-100 confidence',
    -- Moving averages (snapshot at this date)
    ma_50           DECIMAL(15,4)    NULL,
    ma_200          DECIMAL(15,4)    NULL,
    -- Trend
    trend           VARCHAR(10)       NULL COMMENT 'BULLISH, BEARISH, NEUTRAL',
    -- Metadata
    calc_date       TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_ta_symbol_date (symbol, price_date),
    KEY idx_ta_date (price_date),
    KEY idx_ta_pattern (pattern_name),
    KEY idx_ta_trend (trend)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
PARTITION BY RANGE (YEAR(price_date)) (
    PARTITION p_pre2020 VALUES LESS THAN (2020),
    PARTITION p_2020    VALUES LESS THAN (2021),
    PARTITION p_2021    VALUES LESS THAN (2022),
    PARTITION p_2022    VALUES LESS THAN (2023),
    PARTITION p_2023    VALUES LESS THAN (2024),
    PARTITION p_2024    VALUES LESS THAN (2025),
    PARTITION p_2025    VALUES LESS THAN (2026),
    PARTITION p_2026    VALUES LESS THAN (2027),
    PARTITION p_future  VALUES LESS THAN MAXVALUE
);

-- ============================================================================
-- SECTION 7: FUNDAMENTAL DATA
-- ============================================================================

CREATE TABLE fin_statement (
    id              INT UNSIGNED      NOT NULL AUTO_INCREMENT,
    stockinfo_id    INT UNSIGNED      NOT NULL,
    report_date     DATE              NOT NULL,
    report_type     ENUM('annual', 'quarterly') NOT NULL DEFAULT 'annual',
    -- Income statement
    revenue         DECIMAL(18,2)    NULL,
    net_income      DECIMAL(18,2)    NULL,
    depreciation    DECIMAL(18,2)    NULL,
    amortization    DECIMAL(18,2)    NULL,
    capital_expenses DECIMAL(18,2)   NULL,
    working_capital DECIMAL(18,2)    NULL,
    eps             DECIMAL(10,4)    NULL,
    eps_growth      DECIMAL(10,4)    NULL,
    revenue_growth  DECIMAL(10,4)    NULL,
    -- Balance sheet
    total_assets    DECIMAL(18,2)    NULL,
    total_liability DECIMAL(18,2)    NULL,
    total_equity    DECIMAL(18,2)    NULL,
    total_debt      DECIMAL(18,2)    NULL,
    retained_earnings DECIMAL(18,2)  NULL,
    -- Dividends
    dividend_per_share DECIMAL(10,4) NULL,
    shares_outstanding BIGINT UNSIGNED NULL,
    -- Owner earnings (Buffett metric)
    owner_earnings  DECIMAL(18,2)    NULL,
    -- Audit
    last_eval       TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    eval_user       VARCHAR(64)       NULL,
    created_at      TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_fs_stock_date_type (stockinfo_id, report_date, report_type),
    KEY idx_fs_stock (stockinfo_id),
    KEY idx_fs_date (report_date),
    CONSTRAINT fk_fs_stock FOREIGN KEY (stockinfo_id) REFERENCES stockinfo(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Financial ratios (computed from fin_statement)
CREATE TABLE ratios (
    id              INT UNSIGNED      NOT NULL AUTO_INCREMENT,
    stockinfo_id    INT UNSIGNED      NOT NULL,
    as_of_date      DATE              NOT NULL,
    -- Profitability
    roe             DECIMAL(10,4)    NULL COMMENT 'Return on Equity',
    roa             DECIMAL(10,4)    NULL COMMENT 'Return on Assets',
    roce            DECIMAL(10,4)    NULL COMMENT 'Return on Capital Employed',
    gross_margin    DECIMAL(10,4)    NULL,
    operating_margin DECIMAL(10,4)   NULL,
    net_margin      DECIMAL(10,4)    NULL,
    pretax_margin   DECIMAL(10,4)    NULL,
    -- Leverage
    debt_ratio      DECIMAL(10,4)    NULL COMMENT 'Total Debt / Total Assets',
    debt_to_equity  DECIMAL(10,4)    NULL,
    -- Valuation
    pe_ratio        DECIMAL(10,4)    NULL,
    price_to_book   DECIMAL(10,4)    NULL,
    price_to_sales  DECIMAL(10,4)    NULL,
    price_to_cashflow DECIMAL(10,4)  NULL,
    -- Buffett criteria flags
    roe_attractive  TINYINT(1)        NULL COMMENT 'ROE > 15%',
    low_cost_ops    TINYINT(1)        NULL COMMENT 'Operating margin > 10%',
    sustainable_debt TINYINT(1)       NULL COMMENT 'Debt covered by income',
    -- Audit
    calc_date       TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_ratios_stock_date (stockinfo_id, as_of_date),
    KEY idx_ratios_stock (stockinfo_id),
    CONSTRAINT fk_ratios_stock FOREIGN KEY (stockinfo_id) REFERENCES stockinfo(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- SECTION 8: PORTFOLIO MANAGEMENT
-- ============================================================================

CREATE TABLE portfolio (
    id              INT UNSIGNED      NOT NULL AUTO_INCREMENT,
    user_id         INT UNSIGNED      NOT NULL,
    symbol          VARCHAR(16)       NOT NULL,
    account_type    VARCHAR(20)       NOT NULL DEFAULT 'INV' COMMENT 'RRSP, TFSA, INV, LIRA',
    shares          DECIMAL(15,4)    NOT NULL DEFAULT 0,
    cost_basis      DECIMAL(15,4)    NOT NULL DEFAULT 0 COMMENT 'Total cost in CAD',
    book_value      DECIMAL(15,4)    NOT NULL DEFAULT 0,
    market_value    DECIMAL(15,4)    NOT NULL DEFAULT 0,
    current_price   DECIMAL(15,4)    NOT NULL DEFAULT 0,
    profit_loss     DECIMAL(15,4)    NOT NULL DEFAULT 0,
    pl_pct          DECIMAL(10,4)    NULL,
    dividend_yield  DECIMAL(8,4)     NULL,
    pct_of_portfolio DECIMAL(8,4)    NULL,
    last_update     TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at      TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_portfolio_user_symbol_account (user_id, symbol, account_type),
    KEY idx_portfolio_user (user_id),
    KEY idx_portfolio_symbol (symbol),
    KEY idx_portfolio_account (account_type),
    CONSTRAINT fk_portfolio_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_portfolio_symbol FOREIGN KEY (symbol) REFERENCES stockinfo(symbol) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE portfolio_history (
    id              BIGINT UNSIGNED   NOT NULL AUTO_INCREMENT,
    user_id         INT UNSIGNED      NOT NULL,
    snapshot_date   DATE              NOT NULL,
    total_book_value DECIMAL(15,2)   NOT NULL DEFAULT 0,
    total_market_value DECIMAL(15,2) NOT NULL DEFAULT 0,
    total_pl        DECIMAL(15,2)    NOT NULL DEFAULT 0,
    total_pl_pct    DECIMAL(10,4)    NULL,
    cash_balance    DECIMAL(15,2)    NOT NULL DEFAULT 0,
    num_positions   INT UNSIGNED      NOT NULL DEFAULT 0,
    created_at      TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_ph_user_date (user_id, snapshot_date),
    KEY idx_ph_date (snapshot_date),
    CONSTRAINT fk_ph_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `transaction` (
    id              INT UNSIGNED      NOT NULL AUTO_INCREMENT,
    user_id         INT UNSIGNED      NOT NULL,
    symbol          VARCHAR(16)       NOT NULL,
    account_type    VARCHAR(20)       NOT NULL DEFAULT 'INV',
    transaction_type VARCHAR(20)      NOT NULL,
    shares          DECIMAL(15,4)    NOT NULL DEFAULT 0,
    price           DECIMAL(15,4)    NOT NULL DEFAULT 0,
    commission      DECIMAL(10,2)    NOT NULL DEFAULT 0,
    total_amount    DECIMAL(15,2)    NOT NULL DEFAULT 0,
    currency        CHAR(3)           NOT NULL DEFAULT 'CAD',
    exchange_rate   DECIMAL(10,6)    NOT NULL DEFAULT 1.000000,
    cad_equivalent  DECIMAL(15,2)    NULL,
    transaction_date DATE             NOT NULL,
    notes           TEXT              NULL,
    created_at      TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_txn_user (user_id),
    KEY idx_txn_symbol (symbol),
    KEY idx_txn_date (transaction_date),
    KEY idx_txn_type (transaction_type),
    CONSTRAINT fk_txn_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_txn_symbol FOREIGN KEY (symbol) REFERENCES stockinfo(symbol) ON DELETE CASCADE,
    CONSTRAINT fk_txn_type FOREIGN KEY (transaction_type) REFERENCES transactiontype(type_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- SECTION 9: WATCHLISTS
-- ============================================================================

CREATE TABLE watchlists (
    id              INT UNSIGNED      NOT NULL AUTO_INCREMENT,
    user_id         INT UNSIGNED      NOT NULL,
    name            VARCHAR(64)       NOT NULL,
    description     TEXT              NULL,
    is_active       TINYINT(1)        NOT NULL DEFAULT 1,
    created_at      TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_watchlist_user_name (user_id, name),
    CONSTRAINT fk_watchlist_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE watchlist_symbols (
    watchlist_id    INT UNSIGNED      NOT NULL,
    symbol          VARCHAR(16)       NOT NULL,
    added_date      DATE              NOT NULL DEFAULT (CURRENT_DATE),
    notes           TEXT              NULL,
    alert_above     DECIMAL(15,4)    NULL,
    alert_below     DECIMAL(15,4)    NULL,
    PRIMARY KEY (watchlist_id, symbol),
    CONSTRAINT fk_ws_watchlist FOREIGN KEY (watchlist_id) REFERENCES watchlists(id) ON DELETE CASCADE,
    CONSTRAINT fk_ws_symbol FOREIGN KEY (symbol) REFERENCES stockinfo(symbol) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- SECTION 10: ALERTS
-- ============================================================================

CREATE TABLE alerts (
    id              INT UNSIGNED      NOT NULL AUTO_INCREMENT,
    user_id         INT UNSIGNED      NOT NULL,
    symbol          VARCHAR(16)       NOT NULL,
    alert_type_id   SMALLINT UNSIGNED NULL,
    alert_name      VARCHAR(64)       NOT NULL,
    condition_json  JSON              NULL COMMENT 'Flexible alert conditions',
    is_active       TINYINT(1)        NOT NULL DEFAULT 1,
    triggered_count INT UNSIGNED      NOT NULL DEFAULT 0,
    last_triggered  TIMESTAMP         NULL,
    created_at      TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_alerts_user (user_id),
    KEY idx_alerts_symbol (symbol),
    KEY idx_alerts_active (is_active),
    CONSTRAINT fk_alerts_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_alerts_symbol FOREIGN KEY (symbol) REFERENCES stockinfo(symbol) ON DELETE CASCADE,
    CONSTRAINT fk_alerts_type FOREIGN KEY (alert_type_id) REFERENCES alerttype(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE alertsraised (
    id              INT UNSIGNED      NOT NULL AUTO_INCREMENT,
    alert_id        INT UNSIGNED      NOT NULL,
    symbol          VARCHAR(16)       NOT NULL,
    trigger_price   DECIMAL(15,4)    NULL,
    trigger_value   DECIMAL(15,4)    NULL,
    is_cleared      TINYINT(1)        NOT NULL DEFAULT 0,
    raised_at       TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cleared_at      TIMESTAMP         NULL,
    notes           TEXT              NULL,
    PRIMARY KEY (id),
    KEY idx_ar_alert (alert_id),
    KEY idx_ar_symbol (symbol),
    KEY idx_ar_cleared (is_cleared),
    CONSTRAINT fk_ar_alert FOREIGN KEY (alert_id) REFERENCES alerts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- SECTION 11: BACKTESTING
-- ============================================================================

CREATE TABLE backtest_strategies (
    id              INT UNSIGNED      NOT NULL AUTO_INCREMENT,
    user_id         INT UNSIGNED      NOT NULL,
    name            VARCHAR(128)      NOT NULL,
    description     TEXT              NULL,
    -- Strategy configuration
    screen_type     VARCHAR(64)       NOT NULL DEFAULT 'combined' COMMENT 'motley_fool, buffett, combined, turtle',
    rebalance_freq  VARCHAR(20)       NOT NULL DEFAULT 'monthly' COMMENT 'weekly, monthly, quarterly, semi-annual',
    signal_threshold DECIMAL(5,4)    NOT NULL DEFAULT 0.5000,
    max_position_pct DECIMAL(5,4)    NOT NULL DEFAULT 0.0500,
    max_positions   INT UNSIGNED      NOT NULL DEFAULT 20,
    initial_capital DECIMAL(15,2)    NOT NULL DEFAULT 100000.00,
    trade_fee       DECIMAL(10,2)    NOT NULL DEFAULT 9.95,
    position_sizing VARCHAR(20)       NOT NULL DEFAULT 'equal' COMMENT 'equal, kelly, atr_based',
    -- Parameters as JSON for flexibility
    parameters      JSON              NULL,
    is_active       TINYINT(1)        NOT NULL DEFAULT 1,
    created_at      TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_bts_user (user_id),
    CONSTRAINT fk_bts_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE backtest_runs (
    id              INT UNSIGNED      NOT NULL AUTO_INCREMENT,
    strategy_id     INT UNSIGNED      NOT NULL,
    user_id         INT UNSIGNED      NOT NULL,
    status          ENUM('pending', 'running', 'complete', 'error') NOT NULL DEFAULT 'pending',
    -- Date range
    start_date      DATE              NOT NULL,
    end_date        DATE              NOT NULL,
    -- Results
    initial_capital DECIMAL(15,2)    NOT NULL DEFAULT 100000.00,
    final_value     DECIMAL(15,2)    NULL,
    total_return    DECIMAL(10,4)    NULL,
    annualized_return DECIMAL(10,4)  NULL,
    sharpe_ratio    DECIMAL(10,4)    NULL,
    max_drawdown    DECIMAL(10,4)    NULL,
    num_trades      INT UNSIGNED      NULL,
    win_rate        DECIMAL(5,4)     NULL,
    avg_win         DECIMAL(15,4)    NULL,
    avg_loss        DECIMAL(15,4)    NULL,
    profit_factor   DECIMAL(10,4)    NULL,
    -- Error tracking
    error_message   TEXT              NULL,
    -- Timing
    started_at      TIMESTAMP         NULL,
    completed_at    TIMESTAMP         NULL,
    duration_seconds INT UNSIGNED     NULL,
    created_at      TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_btr_strategy (strategy_id),
    KEY idx_btr_user (user_id),
    KEY idx_btr_status (status),
    CONSTRAINT fk_btr_strategy FOREIGN KEY (strategy_id) REFERENCES backtest_strategies(id) ON DELETE CASCADE,
    CONSTRAINT fk_btr_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE backtest_trades (
    id              BIGINT UNSIGNED   NOT NULL AUTO_INCREMENT,
    run_id          INT UNSIGNED      NOT NULL,
    symbol          VARCHAR(16)       NOT NULL,
    trade_type      ENUM('BUY', 'SELL') NOT NULL,
    trade_date      DATE              NOT NULL,
    price           DECIMAL(15,4)    NOT NULL,
    shares          DECIMAL(15,4)    NOT NULL,
    commission      DECIMAL(10,2)    NOT NULL DEFAULT 0,
    total_cost      DECIMAL(15,2)    NOT NULL,
    -- Signal context at time of trade
    signal          VARCHAR(10)       NULL,
    confidence      DECIMAL(5,4)     NULL,
    indicators_json JSON              NULL COMMENT 'Snapshot of indicators at trade time',
    -- P&L (for SELL trades)
    pl_amount       DECIMAL(15,4)    NULL,
    pl_pct          DECIMAL(10,4)    NULL,
    holding_days    INT UNSIGNED      NULL,
    created_at      TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_btt_run (run_id),
    KEY idx_btt_symbol (symbol),
    KEY idx_btt_date (trade_date),
    CONSTRAINT fk_btt_run FOREIGN KEY (run_id) REFERENCES backtest_runs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE backtest_positions (
    id              INT UNSIGNED      NOT NULL AUTO_INCREMENT,
    run_id          INT UNSIGNED      NOT NULL,
    symbol          VARCHAR(16)       NOT NULL,
    snapshot_date   DATE              NOT NULL,
    shares          DECIMAL(15,4)    NOT NULL,
    cost_basis      DECIMAL(15,4)    NOT NULL,
    current_price   DECIMAL(15,4)    NOT NULL,
    market_value    DECIMAL(15,2)    NOT NULL,
    unrealized_pl   DECIMAL(15,4)    NULL,
    unrealized_pl_pct DECIMAL(10,4)  NULL,
    weight_pct      DECIMAL(8,4)     NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_btp_run_symbol_date (run_id, symbol, snapshot_date),
    KEY idx_btp_run (run_id),
    KEY idx_btp_date (snapshot_date),
    CONSTRAINT fk_btp_run FOREIGN KEY (run_id) REFERENCES backtest_runs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- SECTION 12: SIGNAL WEIGHT OPTIMIZATION
-- ============================================================================

CREATE TABLE signal_weights (
    id              INT UNSIGNED      NOT NULL AUTO_INCREMENT,
    symbol          VARCHAR(16)       NOT NULL,
    strategy_id     INT UNSIGNED      NULL COMMENT 'NULL = global weights',
    -- Indicator weights (sum to 1.0)
    w_ma_align      DECIMAL(5,4)     NOT NULL DEFAULT 0.2000,
    w_rsi           DECIMAL(5,4)     NOT NULL DEFAULT 0.1500,
    w_macd          DECIMAL(5,4)     NOT NULL DEFAULT 0.1500,
    w_bollinger     DECIMAL(5,4)     NOT NULL DEFAULT 0.1000,
    w_volume        DECIMAL(5,4)     NOT NULL DEFAULT 0.1000,
    w_trend         DECIMAL(5,4)     NOT NULL DEFAULT 0.1500,
    w_fundamental   DECIMAL(5,4)     NOT NULL DEFAULT 0.1000,
    w_momentum      DECIMAL(5,4)     NOT NULL DEFAULT 0.0500,
    -- Performance tracking
    coherence_score DECIMAL(8,4)     NULL COMMENT '3-month win rate',
    total_signals   INT UNSIGNED      NOT NULL DEFAULT 0,
    correct_signals INT UNSIGNED      NOT NULL DEFAULT 0,
    last_optimized  TIMESTAMP         NULL,
    created_at      TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_sw_symbol_strategy (symbol, strategy_id),
    KEY idx_sw_symbol (symbol),
    KEY idx_sw_strategy (strategy_id),
    CONSTRAINT fk_sw_symbol FOREIGN KEY (symbol) REFERENCES stockinfo(symbol) ON DELETE CASCADE,
    CONSTRAINT fk_sw_strategy FOREIGN KEY (strategy_id) REFERENCES backtest_strategies(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- SECTION 13: DATA IMPORT LOG
-- ============================================================================

CREATE TABLE data_import_log (
    id              BIGINT UNSIGNED   NOT NULL AUTO_INCREMENT,
    import_type     ENUM('csv', 'yfinance', 'manual', 'migration', 'nightly_calc') NOT NULL,
    symbol          VARCHAR(16)       NULL,
    source          VARCHAR(255)      NULL,
    records_before  INT UNSIGNED      NULL,
    records_after   INT UNSIGNED      NULL,
    records_added   INT UNSIGNED      NULL,
    status          ENUM('started', 'complete', 'error') NOT NULL DEFAULT 'started',
    error_message   TEXT              NULL,
    duration_ms     INT UNSIGNED      NULL,
    created_at      TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_dil_type_date (import_type, created_at),
    KEY idx_dil_symbol (symbol),
    KEY idx_dil_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- SECTION 14: SYMBOL STATUS (for delisted detection)
-- ============================================================================

CREATE TABLE symbol_status (
    symbol          VARCHAR(16)       NOT NULL,
    resolved_symbol VARCHAR(16)       NULL COMMENT 'Yahoo Finance resolved ticker',
    status          ENUM('active', 'delisted', 'renamed', 'error') NOT NULL DEFAULT 'active',
    name            VARCHAR(255)      NULL,
    exchange        VARCHAR(32)       NULL,
    currency        CHAR(3)           NULL,
    last_price      DECIMAL(15,4)    NULL,
    last_check_date TIMESTAMP         NULL,
    first_delisted_date TIMESTAMP     NULL,
    error_message   TEXT              NULL,
    consecutive_failures TINYINT UNSIGNED NOT NULL DEFAULT 0,
    created_at      TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol),
    KEY idx_ss_status (status),
    KEY idx_ss_check_date (last_check_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- SECTION 15: STORED PROCEDURES
-- ============================================================================

DELIMITER //

-- --------------------------------------------------------------------------
-- Procedure: Calculate daily indicators for a symbol over a date range
-- Called nightly after price imports
-- --------------------------------------------------------------------------
CREATE PROCEDURE sp_calc_daily_indicators(
    IN p_symbol VARCHAR(16),
    IN p_start_date DATE,
    IN p_end_date DATE
)
BEGIN
    DECLARE v_error_msg TEXT DEFAULT NULL;
    
    -- Insert or update daily indicators using window functions
    INSERT INTO daily_indicators (
        symbol, price_date, daily_return, log_return, gap_pct, true_range,
        sma_5, sma_10, sma_20, sma_50, sma_100, sma_200,
        bb_middle, bb_std, bb_upper, bb_lower, bb_width, bb_pct,
        atr_14, vol_sma_20, vol_ratio,
        sma_cross, price_vs_sma20, price_vs_sma50, price_vs_sma200
    )
    WITH price_data AS (
        SELECT 
            sp.symbol,
            sp.price_date,
            sp.open_price,
            sp.high_price,
            sp.low_price,
            sp.close_price,
            sp.volume,
            LAG(sp.close_price) OVER (PARTITION BY sp.symbol ORDER BY sp.price_date) AS prev_close,
            LAG(sp.open_price) OVER (PARTITION BY sp.symbol ORDER BY sp.price_date) AS prev_open
        FROM stockprices sp
        WHERE sp.symbol = p_symbol
          AND sp.price_date BETWEEN p_start_date AND p_end_date
    ),
    with_indicators AS (
        SELECT
            symbol,
            price_date,
            open_price, high_price, low_price, close_price, volume, prev_close,
            -- Daily return
            (close_price / prev_close) - 1 AS daily_return,
            -- Log return
            LN(close_price / prev_close) AS log_return,
            -- Gap
            (open_price / prev_close) - 1 AS gap_pct,
            -- True range
            GREATEST(
                high_price - low_price,
                ABS(high_price - prev_close),
                ABS(low_price - prev_close)
            ) AS true_range,
            -- SMAs
            AVG(close_price) OVER (ORDER BY price_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) AS sma_5,
            AVG(close_price) OVER (ORDER BY price_date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS sma_10,
            AVG(close_price) OVER (ORDER BY price_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS sma_20,
            AVG(close_price) OVER (ORDER BY price_date ROWS BETWEEN 49 PRECEDING AND CURRENT ROW) AS sma_50,
            AVG(close_price) OVER (ORDER BY price_date ROWS BETWEEN 99 PRECEDING AND CURRENT ROW) AS sma_100,
            AVG(close_price) OVER (ORDER BY price_date ROWS BETWEEN 199 PRECEDING AND CURRENT ROW) AS sma_200,
            -- Bollinger
            AVG(close_price) OVER w20 AS bb_mid,
            STDDEV(close_price) OVER w20 AS bb_std,
            -- Volume
            AVG(volume) OVER w20 AS vol_sma_20
        FROM price_data
        WINDOW w20 AS (ORDER BY price_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW)
    )
    SELECT
        symbol, price_date,
        daily_return, log_return, gap_pct, true_range,
        sma_5, sma_10, sma_20, sma_50, sma_100, sma_200,
        bb_mid, bb_std,
        bb_mid + 2 * bb_std AS bb_upper,
        bb_mid - 2 * bb_std AS bb_lower,
        (bb_mid + 2 * bb_std - bb_mid + 2 * bb_std) / bb_mid AS bb_width,
        (close_price - (bb_mid - 2 * bb_std)) / (bb_mid + 2 * bb_std - (bb_mid - 2 * bb_std)) AS bb_pct,
        -- ATR(14) — simplified, uses current TR only
        true_range AS atr_14,
        vol_sma_20,
        volume / vol_sma_20 AS vol_ratio,
        -- SMA cross signals
        CASE
            WHEN sma_50 > sma_200 AND LAG(sma_50) OVER (ORDER BY price_date) <= LAG(sma_200) OVER (ORDER BY price_date)
                THEN 'GOLDEN_CROSS'
            WHEN sma_50 < sma_200 AND LAG(sma_50) OVER (ORDER BY price_date) >= LAG(sma_200) OVER (ORDER BY price_date)
                THEN 'DEATH_CROSS'
            ELSE NULL
        END AS sma_cross,
        (close_price - sma_20) / sma_20 * 100 AS price_vs_sma20,
        (close_price - sma_50) / sma_50 * 100 AS price_vs_sma50,
        (close_price - sma_200) / sma_200 * 100 AS price_vs_sma200
    FROM with_indicators
    ON DUPLICATE KEY UPDATE
        daily_return = VALUES(daily_return),
        log_return = VALUES(log_return),
        gap_pct = VALUES(gap_pct),
        true_range = VALUES(true_range),
        sma_5 = VALUES(sma_5),
        sma_10 = VALUES(sma_10),
        sma_20 = VALUES(sma_20),
        sma_50 = VALUES(sma_50),
        sma_100 = VALUES(sma_100),
        sma_200 = VALUES(sma_200),
        bb_middle = VALUES(bb_middle),
        bb_std = VALUES(bb_std),
        bb_upper = VALUES(bb_upper),
        bb_lower = VALUES(bb_lower),
        bb_width = VALUES(bb_width),
        bb_pct = VALUES(bb_pct),
        atr_14 = VALUES(atr_14),
        vol_sma_20 = VALUES(vol_sma_20),
        vol_ratio = VALUES(vol_ratio),
        sma_cross = VALUES(sma_cross),
        price_vs_sma20 = VALUES(price_vs_sma20),
        price_vs_sma50 = VALUES(price_vs_sma50),
        price_vs_sma200 = VALUES(price_vs_sma200),
        calc_date = CURRENT_TIMESTAMP;
    
    -- Log the import
    INSERT INTO data_import_log (import_type, symbol, records_added, status, duration_ms)
    VALUES ('nightly_calc', p_symbol, ROW_COUNT(), 'complete', 0);
    
END //

-- --------------------------------------------------------------------------
-- Procedure: Nightly batch — calculate indicators for all active symbols
-- --------------------------------------------------------------------------
CREATE PROCEDURE sp_nightly_indicator_calc()
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE v_symbol VARCHAR(16);
    DECLARE v_last_calc DATE;
    DECLARE v_start_date DATE;
    DECLARE v_end_date DATE DEFAULT CURDATE();
    
    -- Cursor over active symbols
    DECLARE cur CURSOR FOR 
        SELECT si.symbol, MAX(di.price_date)
        FROM stockinfo si
        LEFT JOIN daily_indicators di ON si.symbol = di.symbol
        WHERE si.is_active = 1
        GROUP BY si.symbol;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
    
    OPEN cur;
    read_loop: LOOP
        FETCH cur INTO v_symbol, v_last_calc;
        IF done THEN LEAVE read_loop; END IF;
        
        -- Calculate from last indicator date (or 200 days ago for new symbols)
        SET v_start_date = COALESCE(DATE_SUB(v_last_calc, INTERVAL 5 DAY), DATE_SUB(v_end_date, INTERVAL 210 DAY));
        
        BEGIN
            DECLARE CONTINUE HANDLER FOR SQLEXCEPTION
            BEGIN
                -- Log error but continue with next symbol
                INSERT INTO data_import_log (import_type, symbol, status, error_message)
                VALUES ('nightly_calc', v_symbol, 'error', 'Calculation failed');
            END;
            
            CALL sp_calc_daily_indicators(v_symbol, v_start_date, v_end_date);
        END;
        
    END LOOP;
    CLOSE cur;
    
END //

-- --------------------------------------------------------------------------
-- Trigger: On price insert, calculate basic indicators for that symbol
-- --------------------------------------------------------------------------
CREATE TRIGGER trg_after_price_insert
AFTER INSERT ON stockprices
FOR EACH ROW
BEGIN
    -- Calculate indicators for the last 210 days (enough for SMA 200)
    -- This is lightweight — only touches one symbol's recent data
    DECLARE v_start DATE;
    SET v_start = DATE_SUB(NEW.price_date, INTERVAL 210 DAY);
    
    -- Call the procedure for this symbol's recent window
    -- Note: In MariaDB, triggers can't call procedures that modify the same table
    -- So we use a scheduled event instead for the full recalc
    -- This trigger just logs that a recalc is needed
    INSERT INTO data_import_log (import_type, symbol, status, source)
    VALUES ('manual', NEW.symbol, 'started', 'price_insert_trigger')
    ON DUPLICATE KEY UPDATE created_at = CURRENT_TIMESTAMP;
END //

DELIMITER ;

-- ============================================================================
-- SECTION 16: SCHEDULED EVENTS
-- ============================================================================

-- Enable event scheduler
SET GLOBAL event_scheduler = ON;

-- Nightly indicator calculation (2:00 AM)
CREATE EVENT IF NOT EXISTS evt_nightly_indicators
ON SCHEDULE EVERY 1 DAY STARTS '2026-05-28 02:00:00'
DO
BEGIN
    CALL sp_nightly_indicator_calc();
END;

-- Weekly symbol status check (Sunday 3:00 AM)
CREATE EVENT IF NOT EXISTS evt_weekly_symbol_check
ON SCHEDULE EVERY 1 WEEK STARTS '2026-05-31 03:00:00'
DO
BEGIN
    -- Mark symbols that haven't been updated in 5 days as potentially stale
    UPDATE symbol_status ss
    JOIN stockinfo si ON ss.symbol = si.symbol
    SET ss.consecutive_failures = ss.consecutive_failures + 1,
        ss.updated_at = CURRENT_TIMESTAMP
    WHERE si.last_price_date < DATE_SUB(CURDATE(), INTERVAL 5 DAY)
      AND ss.status = 'active';
END;

-- ============================================================================
-- SECTION 17: VIEWS FOR BACKTEST ENGINE
-- ============================================================================

-- Complete price + indicator view (what backtest engine reads)
CREATE OR REPLACE VIEW v_backtest_data AS
SELECT
    sp.symbol,
    sp.price_date,
    sp.open_price,
    sp.high_price,
    sp.low_price,
    sp.close_price,
    sp.adj_close,
    sp.volume,
    di.daily_return,
    di.sma_5, di.sma_10, di.sma_20, di.sma_50, di.sma_200,
    di.bb_upper, di.bb_lower, di.bb_width, di.bb_pct,
    di.atr_14,
    di.vol_ratio,
    di.sma_cross,
    di.price_vs_sma20, di.price_vs_sma50, di.price_vs_sma200,
    ta.pattern_name, ta.pattern_bearish, ta.trend
FROM stockprices sp
LEFT JOIN daily_indicators di ON sp.symbol = di.symbol AND sp.price_date = di.price_date
LEFT JOIN technicalanalysis ta ON sp.symbol = ta.symbol AND sp.price_date = ta.price_date
WHERE sp.price_date >= '2020-01-01';

-- Portfolio summary view
CREATE OR REPLACE VIEW v_portfolio_summary AS
SELECT
    p.user_id,
    u.username,
    p.account_type,
    COUNT(*) AS num_positions,
    SUM(p.market_value) AS total_market_value,
    SUM(p.cost_basis) AS total_cost_basis,
    SUM(p.profit_loss) AS total_pl,
    SUM(p.market_value) / NULLIF(SUM(p.cost_basis), 0) - 1 AS total_pl_pct,
    SUM(p.market_value * p.dividend_yield) / NULLIF(SUM(p.market_value), 0) AS weighted_div_yield
FROM portfolio p
JOIN users u ON p.user_id = u.id
GROUP BY p.user_id, p.account_type;

-- ============================================================================
-- SECTION 18: SEED DATA
-- ============================================================================

INSERT INTO roles (role_name, description) VALUES
    ('admin', 'Full system access'),
    ('trader', 'Can manage portfolio and run backtests'),
    ('viewer', 'Read-only access');

INSERT INTO transactiontype (type_code, description) VALUES
    ('BUY', 'Purchase shares'),
    ('SELL', 'Sell shares'),
    ('DIVIDEND', 'Dividend payment'),
    ('SPLIT', 'Stock split'),
    ('TRANSFER', 'Transfer shares'),
    ('EXCHANGE', 'Exchange/convert shares'),
    ('TAKEOVER', 'Acquisition/takeover');

INSERT INTO accounttype (type_code, description) VALUES
    ('RRSP', 'Registered Retirement Savings Plan'),
    ('TFSA', 'Tax-Free Savings Account'),
    ('INV', 'Non-registered Investment Account'),
    ('LIRA', 'Locked-In Retirement Account'),
    ('LRSP', 'Locked-In Retirement Savings Plan');

INSERT INTO stockexchange (exchange_name, yahoo_symbol, country_code, timezone) VALUES
    ('Toronto Stock Exchange', 'TO', 'CAD', 'America/Toronto'),
    ('NYSE', '', 'USD', 'America/New_York'),
    ('NASDAQ', 'O', 'USD', 'America/New_York'),
    ('NYSE Arca', 'P', 'USD', 'America/New_York'),
    ('TSX Venture', 'V', 'CAD', 'America/Toronto');

INSERT INTO alerttype (alert_name, description, function_name) VALUES
    ('PRICE_ABOVE', 'Price rises above threshold', 'price_above'),
    ('PRICE_BELOW', 'Price falls below threshold', 'price_below'),
    ('PRICE_BETWEEN', 'Price between two values', 'price_between'),
    ('VOLUME_SPIKE', 'Volume exceeds average', 'volume_spike'),
    ('SMA_CROSS', 'SMA golden/death cross', 'sma_cross'),
    ('DELISTED', 'Symbol may be delisted', 'delisted_check');

-- Default admin user (password: changeme — CHANGE IN PRODUCTION)
INSERT INTO users (username, email, password_hash, first_name, last_name, role_id) VALUES
    ('admin', 'admin@ksfraser.ca', '$2y$12$placeholder_change_me', 'Admin', 'User', 1),
    ('kevin', 'kevin@ksfraser.ca', '$2y$12$placeholder_change_me', 'Kevin', 'Fraser', 1);
