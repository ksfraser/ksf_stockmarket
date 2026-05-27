-- ============================================================================
-- KSF Stock Market — Modernized Database Schema
-- ============================================================================
-- Compatible with: MariaDB 10.6+, MySQL 8.0+
-- Character set: utf8mb4
-- Engine: InnoDB
--
-- This schema PRESERVES all original tables for backward compatibility
-- and adds new tables for modernized features.
-- ============================================================================

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

DROP DATABASE IF EXISTS ksf_stockmarket;
CREATE DATABASE ksf_stockmarket
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE ksf_stockmarket;

-- ============================================================================
-- PRESERVED TABLES (from original stocks.sql)
-- These maintain backward compatibility with the existing PHP app.
-- ============================================================================

-- --------------------------------------------------------------------------
-- Portfolio: Current holdings
-- --------------------------------------------------------------------------
CREATE TABLE portfolio (
    symbol      CHAR(16)        NOT NULL,
    number      INT UNSIGNED    NOT NULL DEFAULT 0,
    cost        INT UNSIGNED    NOT NULL DEFAULT 0,
    user        VARCHAR(64)     NOT NULL DEFAULT 'default',
    updated_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------
-- Stock info: Company metadata
-- --------------------------------------------------------------------------
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

-- --------------------------------------------------------------------------
-- Transactions: Buy/sell history
-- --------------------------------------------------------------------------
CREATE TABLE transaction (
    sequence        INT             NOT NULL AUTO_INCREMENT,
    user            VARCHAR(64)     NOT NULL DEFAULT '',
    stocksymbol     CHAR(16)        NOT NULL DEFAULT '',
    number          INT             NOT NULL DEFAULT 0,
    transactiontype VARCHAR(32)     NOT NULL DEFAULT '',
    dollar          DECIMAL(15,4)  NOT NULL DEFAULT 0,
    trade_date      DATE            NOT NULL DEFAULT (CURRENT_DATE),
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (sequence),
    INDEX idx_symbol (stocksymbol),
    INDEX idx_user (user),
    INDEX idx_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------
-- Transaction types: Valid transaction categories
-- --------------------------------------------------------------------------
CREATE TABLE transactiontype (
    transactiontype VARCHAR(32) NOT NULL,
    description     VARCHAR(255) NULL,
    PRIMARY KEY (transactiontype)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------
-- Stock prices: OHLCV data (if not using stockprices from legacy)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stockprices (
    symbol      CHAR(16)        NOT NULL,
    price_date  DATE            NOT NULL,
    open        DECIMAL(15,4)  NOT NULL DEFAULT 0,
    high        DECIMAL(15,4)  NOT NULL DEFAULT 0,
    low         DECIMAL(15,4)  NOT NULL DEFAULT 0,
    close       DECIMAL(15,4)  NOT NULL DEFAULT 0,
    volume      BIGINT UNSIGNED NOT NULL DEFAULT 0,
    adj_close   DECIMAL(15,4)  NULL,
    source      VARCHAR(32)     NULL DEFAULT 'csv',
    updated_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, price_date),
    INDEX idx_date (price_date),
    INDEX idx_symbol_date (symbol, price_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------
-- Dividends: Dividend records
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dividends (
    id          INT             NOT NULL AUTO_INCREMENT,
    symbol      CHAR(16)        NOT NULL,
    ex_date     DATE            NOT NULL,
    amount      DECIMAL(15,4)  NOT NULL DEFAULT 0,
    currency    CHAR(3)         NOT NULL DEFAULT 'CAD',
    created_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_symbol_date (symbol, ex_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------
-- Portfolio history: Portfolio value over time
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS portfolio_history (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user            VARCHAR(64)     NOT NULL,
    snapshot_date   DATE            NOT NULL,
    total_value     DECIMAL(15,2)  NOT NULL DEFAULT 0,
    cash_balance    DECIMAL(15,2)  NOT NULL DEFAULT 0,
    num_positions   INT             NOT NULL DEFAULT 0,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_user_date (user, snapshot_date),
    INDEX idx_date (snapshot_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------
-- Tenets: Motley Fool evaluation scores (per symbol)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenets (
    symbol              CHAR(16)    NOT NULL,
    simple              INT UNSIGNED NOT NULL DEFAULT 0,
    consistent          INT UNSIGNED NOT NULL DEFAULT 0,
    longterm            INT UNSIGNED NOT NULL DEFAULT 0,
    rationalmanager     INT UNSIGNED NOT NULL DEFAULT 0,
    candid              INT UNSIGNED NOT NULL DEFAULT 0,
    resistinstitute     INT UNSIGNED NOT NULL DEFAULT 0,
    focusroe            INT UNSIGNED NOT NULL DEFAULT 0,
    ownerearnings       INT UNSIGNED NOT NULL DEFAULT 0,
    highprofitmargin    INT UNSIGNED NOT NULL DEFAULT 0,
    retainedtomarket    INT UNSIGNED NOT NULL DEFAULT 0,
    valueofbusiness     INT UNSIGNED NOT NULL DEFAULT 0,
    discounted          INT UNSIGNED NOT NULL DEFAULT 0,
    updated_at          TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------
-- Roles: Permission roles
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS roles (
    sequence    INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    roledesc    VARCHAR(64)     NOT NULL DEFAULT 'SET ME',
    rolenumber  INT UNSIGNED    NOT NULL DEFAULT 0,
    PRIMARY KEY (sequence)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- NEW TABLES (modernized features)
-- ============================================================================

-- --------------------------------------------------------------------------
-- Users: Modern user accounts with RBAC
-- --------------------------------------------------------------------------
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

-- --------------------------------------------------------------------------
-- Watchlists: User-defined symbol groups
-- --------------------------------------------------------------------------
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

-- --------------------------------------------------------------------------
-- Watchlist symbols: Symbols in each watchlist
-- --------------------------------------------------------------------------
CREATE TABLE watchlist_symbols (
    watchlist_id    INT UNSIGNED    NOT NULL,
    symbol          CHAR(16)        NOT NULL,
    added_date      DATE            NOT NULL DEFAULT (CURRENT_DATE),
    notes           TEXT            NULL,
    PRIMARY KEY (watchlist_id, symbol),
    CONSTRAINT fk_ws_watchlist
        FOREIGN KEY (watchlist_id) REFERENCES watchlists(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------
-- Backtest runs: Strategy backtesting results
-- --------------------------------------------------------------------------
CREATE TABLE backtest_runs (
    id                  INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    user_id             INT UNSIGNED    NOT NULL,
    strategy            VARCHAR(64)     NOT NULL,
    parameters          JSON            NULL,
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

-- --------------------------------------------------------------------------
-- Backtest trades: Individual trades within a backtest run
-- --------------------------------------------------------------------------
CREATE TABLE backtest_trades (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    backtest_id     INT UNSIGNED    NOT NULL,
    symbol          CHAR(16)        NOT NULL,
    trade_type      ENUM('BUY', 'SELL') NOT NULL,
    trade_date      DATE            NOT NULL,
    price           DECIMAL(15,4)  NOT NULL,
    quantity        INT UNSIGNED    NOT NULL,
    commission      DECIMAL(10,2)  NOT NULL DEFAULT 0,
    total_cost      DECIMAL(15,2)  NOT NULL,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_backtest (backtest_id),
    CONSTRAINT fk_bt_backtest
        FOREIGN KEY (backtest_id) REFERENCES backtest_runs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------
-- FrontAccounting transfers: Savings → Brokerage tracking
-- --------------------------------------------------------------------------
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

-- --------------------------------------------------------------------------
-- Data import log: Track data refresh operations
-- --------------------------------------------------------------------------
CREATE TABLE data_import_log (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    import_type     ENUM('csv', 'yfinance', 'manual', 'migration') NOT NULL,
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

-- Transaction types
INSERT INTO transactiontype (transactiontype, description) VALUES
    ('BUY', 'Purchase shares'),
    ('SELL', 'Sell shares'),
    ('DIVIDEND', 'Dividend payment'),
    ('SPLIT', 'Stock split'),
    ('TRANSFER', 'Transfer shares'),
    ('EXCHANGE', 'Exchange/convert shares'),
    ('TAKEOVER', 'Acquisition/takeover');

-- Default roles
INSERT INTO roles (roledesc, rolenumber) VALUES
    ('Administrator', 1),
    ('Trader', 2),
    ('Viewer', 3);

-- Default admin user (password: changeme — CHANGE IN PRODUCTION)
INSERT INTO users (username, email, password_hash, role, first_name, last_name) VALUES
    ('admin', 'admin@ksfraser.ca', '$2y$12$placeholder_change_me', 'admin', 'Admin', 'User'),
    ('kevin', 'kevin@ksfraser.ca', '$2y$12$placeholder_change_me', 'admin', 'Kevin', 'Fraser');
