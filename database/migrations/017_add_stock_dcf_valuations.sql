-- Migration 017: Add stock_dcf_valuations persistence table for valuation_dcf.php
-- Mirrors the 26-column CSV output so every DCF run can be stored and re-queried.
-- Run: mysql -u <user> -p <database> < database/migrations/017_add_stock_dcf_valuations.sql

CREATE TABLE IF NOT EXISTS stock_dcf_valuations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Identity
    symbol CHAR(16) NOT NULL,
    as_of_date DATE NOT NULL,
    fiscal_year INT NOT NULL,

    -- Assumption inputs
    base_revenue        DECIMAL(15,2)  NULL,
    revenue_cagr        DECIMAL(8,4)   NULL,
    ebitda_margin       DECIMAL(8,4)   NULL,
    da_pct              DECIMAL(8,4)   NULL,
    capex_pct           DECIMAL(8,4)   NULL,
    nwc_pct             DECIMAL(8,4)   NULL,
    tax_rate            DECIMAL(8,4)   NULL,
    wacc                DECIMAL(8,4)   NULL,
    terminal_growth     DECIMAL(8,4)   NULL,
    net_debt            DECIMAL(15,2)  NULL,
    shares_outstanding  BIGINT         NULL,
    assumptions_notes   TEXT           NULL,

    -- Computed outputs (26 CSV columns)
    terminal_value             DECIMAL(15,2)  NULL,
    pv_fcf_1                   DECIMAL(15,2)  NULL,
    pv_fcf_2                   DECIMAL(15,2)  NULL,
    pv_fcf_3                   DECIMAL(15,2)  NULL,
    pv_fcf_4                   DECIMAL(15,2)  NULL,
    pv_fcf_5                   DECIMAL(15,2)  NULL,
    sum_pv_fcf                 DECIMAL(15,2)  NULL,
    enterprise_value           DECIMAL(15,2)  NULL,
    equity_value               DECIMAL(15,2)  NULL,
    intrinsic_value_per_share  DECIMAL(10,4)  NULL,
    current_price              DECIMAL(10,4)  NULL,
    upside_pct                 DECIMAL(8,2)   NULL,
    recommendation             VARCHAR(32)    NULL,

    -- Audit
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_sym_date_fy (symbol, as_of_date, fiscal_year),
    INDEX idx_symbol (symbol),
    INDEX idx_as_of_date (as_of_date),
    INDEX idx_fiscal_year (fiscal_year),
    INDEX idx_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
