-- ============================================================================
-- KSF Stock Market — Schema v4 (Slim + Tax-Aware + Allocation)
-- ============================================================================
-- Changes from v3:
--   1. DROP 100 candlestick columns from ta_indicators (noise: |corr| < 0.02)
--   2. KEEP 120 useful indicators: RSI, MACD, Stoch, ATR, NATR, STDDEV, etc.
--   3. Add symbol_master: geography, sector, GDP weight, withholding tax rate
--   4. Add tax_parameters: CDN eligible dividend gross-up, DTC rates by bracket
--   5. Add allocation_strategies: geographic/sector/MVP definitions
--   6. Add after_tax_returns table for reporting
--   7. Partition stockprices by YEAR for query performance
-- ============================================================================

CREATE DATABASE IF NOT EXISTS ksfraser_stock_market;
USE ksfraser_stock_market;

-- ============================================================================
-- 1. SYMBOL MASTER — expanded universe from 404 HTML files + portfolio
-- ============================================================================
CREATE TABLE symbol_master (
    symbol VARCHAR(20) PRIMARY KEY,
    name VARCHAR(200),
    exchange VARCHAR(10),           -- TSX, NYSE, NASDAQ, etc.
    geography VARCHAR(10) NOT NULL, -- CA, US, EU, UK, JP, etc.
    sector VARCHAR(50),             -- GICS sector
    industry VARCHAR(80),
    gdp_weight DECIMAL(8,6),        -- country GDP weight for allocation
    market_cap_weight DECIMAL(8,6), -- within-region weight
    withholding_tax DECIMAL(5,2),   -- % tax on foreign dividends
    is_portfolio TINYINT DEFAULT 0, -- 1 = in Kevin's portfolio
    is_watchlist TINYINT DEFAULT 0,
    data_start DATE,                -- first date with OHLCV data
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_geo (geography),
    INDEX idx_sector (sector),
    INDEX idx_portfolio (is_portfolio)
) ENGINE=InnoDB;

-- ============================================================================
-- 2. STOCK PRICES — partitioned by year (~200 symbols × 10yr = ~500K rows)
-- ============================================================================
CREATE TABLE stockprices (
    id BIGINT AUTO_INCREMENT,
    symbol VARCHAR(20) NOT NULL,
    price_date DATE NOT NULL,
    open DECIMAL(12,4),
    high DECIMAL(12,4),
    low DECIMAL(12,4),
    close DECIMAL(12,4) NOT NULL,
    volume BIGINT,
    adj_close DECIMAL(12,4),
    dividend DECIMAL(10,6) DEFAULT 0,
    split_ratio DECIMAL(8,4) DEFAULT 1,
    PRIMARY KEY (id, price_date),
    UNIQUE KEY uk_sym_date (symbol, price_date),
    INDEX idx_symbol (symbol),
    INDEX idx_date (price_date)
) ENGINE=InnoDB
PARTITION BY RANGE (YEAR(price_date)) (
    PARTITION p2010 VALUES LESS THAN (2011),
    PARTITION p2011 VALUES LESS THAN (2012),
    PARTITION p2012 VALUES LESS THAN (2013),
    PARTITION p2013 VALUES LESS THAN (2014),
    PARTITION p2014 VALUES LESS THAN (2015),
    PARTITION p2015 VALUES LESS THAN (2016),
    PARTITION p2016 VALUES LESS THAN (2017),
    PARTITION p2017 VALUES LESS THAN (2018),
    PARTITION p2018 VALUES LESS THAN (2019),
    PARTITION p2019 VALUES LESS THAN (2020),
    PARTITION p2020 VALUES LESS THAN (2021),
    PARTITION p2021 VALUES LESS THAN (2022),
    PARTITION p2022 VALUES LESS THAN (2023),
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026),
    PARTITION pmax VALUES LESS THAN MAXVALUE
);

-- ============================================================================
-- 3. INDICATORS — only the 120 useful ones (dropped 100 candlesticks)
-- Grouped by type for readability
-- ============================================================================
CREATE TABLE indicators (
    id BIGINT AUTO_INCREMENT,
    symbol VARCHAR(20) NOT NULL,
    price_date DATE NOT NULL,

    -- Volatility (the ONLY strong predictors: NATR r=0.16)
    natr_7 DECIMAL(10,6),
    natr_14 DECIMAL(10,6),
    natr_20 DECIMAL(10,6),
    atr_7 DECIMAL(10,6),
    atr_14 DECIMAL(10,6),
    atr_20 DECIMAL(10,6),
    stddev_5 DECIMAL(10,6),
    stddev_10 DECIMAL(10,6),
    stddev_14 DECIMAL(10,6),
    trange DECIMAL(10,6),
    var_5 DECIMAL(10,6),
    var_10 DECIMAL(10,6),
    var_14 DECIMAL(10,6),

    -- Trend / Momentum
    adx_14 DECIMAL(10,6),
    adx_21 DECIMAL(10,6),
    adxr_14 DECIMAL(10,6),
    adxr_21 DECIMAL(10,6),
    ht_trendline DECIMAL(12,4),
    ht_trendmode TINYINT,

    -- Oscillators (weak standalone, useful in consensus)
    rsi_14 DECIMAL(8,4),
    rsi_21 DECIMAL(8,4),
    rsi_7 DECIMAL(8,4),
    macd_12_26_9_macd DECIMAL(10,6),
    macd_12_26_9_signal DECIMAL(10,6),
    macd_8_21_5_macd DECIMAL(10,6),
    macd_8_21_5_signal DECIMAL(10,6),
    macd_24_52_18_macd DECIMAL(10,6),
    macd_24_52_18_signal DECIMAL(10,6),
    stoch_14_3_3_k DECIMAL(8,4),
    stoch_14_3_3_d DECIMAL(8,4),
    stoch_5_3_3_k DECIMAL(8,4),
    stoch_5_3_3_d DECIMAL(8,4),
    stoch_21_5_5_k DECIMAL(8,4),
    stoch_21_5_5_d DECIMAL(8,4),

    -- Rate of Change
    roc_7 DECIMAL(10,6),
    roc_14 DECIMAL(10,6),
    roc_21 DECIMAL(10,6),
    rocp_7 DECIMAL(10,6),
    rocp_14 DECIMAL(10,6),
    rocp_21 DECIMAL(10,6),
    rocr_7 DECIMAL(10,6),
    rocr_14 DECIMAL(10,6),
    rocr_21 DECIMAL(10,6),
    rocr100_7 DECIMAL(10,4),
    rocr100_14 DECIMAL(10,4),
    rocr100_21 DECIMAL(10,4),
    mom_7 DECIMAL(12,4),
    mom_14 DECIMAL(12,4),
    mom_21 DECIMAL(12,4),

    -- Price Relative (inverse correlation — useful for mean reversion)
    avgprice DECIMAL(12,4),
    bop DECIMAL(10,6),
    ppo_7 DECIMAL(10,6),
    ppo_14 DECIMAL(10,6),
    ppo_21 DECIMAL(10,6),
    apo_7 DECIMAL(10,6),
    apo_14 DECIMAL(10,6),
    apo_21 DECIMAL(10,6),

    -- Moving Averages (multiple periods)
    sma_5 DECIMAL(12,4), ema_5 DECIMAL(12,4), wma_5 DECIMAL(12,4),
    tema_5 DECIMAL(12,4), dema_5 DECIMAL(12,4), trima_5 DECIMAL(12,4),
    sma_10 DECIMAL(12,4), ema_10 DECIMAL(12,4), wma_10 DECIMAL(12,4),
    tema_10 DECIMAL(12,4), dema_10 DECIMAL(12,4), trima_10 DECIMAL(12,4),
    sma_20 DECIMAL(12,4), ema_20 DECIMAL(12,4), wma_20 DECIMAL(12,4),
    tema_20 DECIMAL(12,4), dema_20 DECIMAL(12,4), trima_20 DECIMAL(12,4),
    sma_50 DECIMAL(12,4), ema_50 DECIMAL(12,4), wma_50 DECIMAL(12,4),
    tema_50 DECIMAL(12,4), dema_50 DECIMAL(12,4), trima_50 DECIMAL(12,4),
    sma_100 DECIMAL(12,4), ema_100 DECIMAL(12,4), wma_100 DECIMAL(12,4),
    sma_200 DECIMAL(12,4), ema_200 DECIMAL(12,4), wma_200 DECIMAL(12,4),

    -- Bollinger Bands (3 std dev settings × 3 bands = 9 cols per period)
    bb_5_2_0_upper DECIMAL(12,4), bb_5_2_0_mid DECIMAL(12,4), bb_5_2_0_lower DECIMAL(12,4),
    bb_5_2_5_upper DECIMAL(12,4), bb_5_2_5_mid DECIMAL(12,4), bb_5_2_5_lower DECIMAL(12,4),
    bb_10_2_0_upper DECIMAL(12,4), bb_10_2_0_mid DECIMAL(12,4), bb_10_2_0_lower DECIMAL(12,4),
    bb_10_2_5_upper DECIMAL(12,4), bb_10_2_5_mid DECIMAL(12,4), bb_10_2_5_lower DECIMAL(12,4),
    bb_20_2_0_upper DECIMAL(12,4), bb_20_2_0_mid DECIMAL(12,4), bb_20_2_0_lower DECIMAL(12,4),
    bb_20_2_5_upper DECIMAL(12,4), bb_20_2_5_mid DECIMAL(12,4), bb_20_2_5_lower DECIMAL(12,4),
    bb_50_1_5_upper DECIMAL(12,4), bb_50_1_5_mid DECIMAL(12,4), bb_50_1_5_lower DECIMAL(12,4),
    bb_50_2_0_upper DECIMAL(12,4), bb_50_2_0_mid DECIMAL(12,4), bb_50_2_0_lower DECIMAL(12,4),
    bb_50_2_5_upper DECIMAL(12,4), bb_50_2_5_mid DECIMAL(12,4), bb_50_2_5_lower DECIMAL(12,4),

    -- Linear Regression
    linreg_5 DECIMAL(12,4), linreg_10 DECIMAL(12,4), linreg_14 DECIMAL(12,4),
    linreg_intercept_5 DECIMAL(12,4), linreg_intercept_10 DECIMAL(12,4), linreg_intercept_14 DECIMAL(12,4),
    linreg_slope_10 DECIMAL(10,6), linreg_slope_14 DECIMAL(10,6),
    linreg_angle_10 DECIMAL(10,6), linreg_angle_14 DECIMAL(10,6),
    tsf_5 DECIMAL(12,4), tsf_10 DECIMAL(12,4), tsf_14 DECIMAL(12,4),

    -- KAMA
    kama_10 DECIMAL(12,4), kama_20 DECIMAL(12,4), kama_50 DECIMAL(12,4),

    -- Volume indicators
    obv BIGINT,
    ad DECIMAL(16,4),
    adosc DECIMAL(12,4),

    -- Hilbert Transform (trend cycle)
    ht_dcperiod DECIMAL(8,2),
    ht_dcphase DECIMAL(8,2),
    ht_phasor_inphase DECIMAL(10,6),
    ht_phasor_quadrature DECIMAL(10,6),
    ht_sine_sine DECIMAL(10,6),
    ht_sine_leadsine DECIMAL(10,6),

    PRIMARY KEY (id, price_date),
    UNIQUE KEY uk_sym_date (symbol, price_date),
    INDEX idx_symbol (symbol),
    INDEX idx_date (price_date)
) ENGINE=InnoDB
PARTITION BY RANGE (YEAR(price_date)) (
    PARTITION p2010 VALUES LESS THAN (2011),
    PARTITION p2011 VALUES LESS THAN (2012),
    PARTITION p2012 VALUES LESS THAN (2013),
    PARTITION p2013 VALUES LESS THAN (2014),
    PARTITION p2014 VALUES LESS THAN (2015),
    PARTITION p2015 VALUES LESS THAN (2016),
    PARTITION p2016 VALUES LESS THAN (2017),
    PARTITION p2017 VALUES LESS THAN (2018),
    PARTITION p2018 VALUES LESS THAN (2019),
    PARTITION p2019 VALUES LESS THAN (2020),
    PARTITION p2020 VALUES LESS THAN (2021),
    PARTITION p2021 VALUES LESS THAN (2022),
    PARTITION p2022 VALUES LESS THAN (2023),
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026),
    PARTITION pmax VALUES LESS THAN MAXVALUE
);

-- ============================================================================
-- 4. EVALUATION SUMMARY — one row per symbol-date (scoring engine output)
-- ============================================================================
CREATE TABLE evalsummary (
    id BIGINT AUTO_INCREMENT,
    symbol VARCHAR(20) NOT NULL,
    price_date DATE NOT NULL,
    close DECIMAL(12,4),
    consensus_signal TINYINT,  -- -1=strong_sell, -0.5=weak_sell, 0=neutral, 0.5=weak_buy, 1=strong_buy
    consensus_strength DECIMAL(5,4), -- 0-1, how many strategies agree
    atr_position_size DECIMAL(8,4),  -- shares to buy given ATR stop
    portfolio_weight DECIMAL(6,4),   -- recommended % of portfolio
    strategy_json JSON,              -- per-strategy signals
    PRIMARY KEY (id, price_date),
    UNIQUE KEY uk_sym_date (symbol, price_date),
    INDEX idx_symbol (symbol)
) ENGINE=InnoDB
PARTITION BY RANGE (YEAR(price_date)) (
    PARTITION p2010 VALUES LESS THAN (2011),
    PARTITION p2011 VALUES LESS THAN (2012),
    PARTITION p2012 VALUES LESS THAN (2013),
    PARTITION p2013 VALUES LESS THAN (2014),
    PARTITION p2014 VALUES LESS THAN (2015),
    PARTITION p2015 VALUES LESS THAN (2016),
    PARTITION p2016 VALUES LESS THAN (2017),
    PARTITION p2017 VALUES LESS THAN (2018),
    PARTITION p2018 VALUES LESS THAN (2019),
    PARTITION p2019 VALUES LESS THAN (2020),
    PARTITION p2020 VALUES LESS THAN (2021),
    PARTITION p2021 VALUES LESS THAN (2022),
    PARTITION p2022 VALUES LESS THAN (2023),
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026),
    PARTITION pmax VALUES LESS THAN MAXVALUE
);

-- ============================================================================
-- 5. CORRELATION RESULTS — cached from 222-indicator study
-- ============================================================================
CREATE TABLE indicator_correlation (
    id INT AUTO_INCREMENT PRIMARY KEY,
    indicator VARCHAR(60) NOT NULL,
    horizon_days INT NOT NULL,
    avg_correlation DECIMAL(10,6),
    std_correlation DECIMAL(10,6),
    pct_symbols_agree DECIMAL(5,2),
    min_correlation DECIMAL(10,6),
    max_correlation DECIMAL(10,6),
    n_symbols INT,
    avg_hit_rate DECIMAL(6,4),
    verdict VARCHAR(30),
    INDEX idx_verdict (verdict),
    INDEX idx_indicator (indicator)
) ENGINE=InnoDB;

-- ============================================================================
-- 6. TAX PARAMETERS — CDN tax brackets, dividend gross-up, DTC
-- 2024 rates for Alberta
-- ============================================================================
CREATE TABLE tax_parameters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    year INT NOT NULL,
    province VARCHAR(20) DEFAULT 'AB',
    bracket_name VARCHAR(30),
    taxable_income_min DECIMAL(10,2),
    taxable_income_max DECIMAL(10,2),
    federal_rate DECIMAL(5,4),
    provincial_rate DECIMAL(5,4),
    combined_rate DECIMAL(5,4),
    -- Dividend tax credit
    eligible_gross_up_rate DECIMAL(5,4),   -- 2024: 1.38
    eligible_fed_dtc_rate DECIMAL(5,4),    -- 2024: 15.0198%
    eligible_prov_dtc_rate DECIMAL(5,4),   -- 2024 Alberta: 8.12%
    eligible_combined_dtc DECIMAL(5,4),    -- total after gross-up
    -- Foreign withholding
    us_withholding DECIMAL(5,4),           -- 15% treaty rate
    UNIQUE KEY uk_bracket (year, province, bracket_name)
) ENGINE=InnoDB;

-- ============================================================================
-- 7. PORTFOLIO — Kevin's current holdings with tax-shelter awareness
-- ============================================================================
CREATE TABLE portfolio (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    account_type ENUM('TFSA','RRSP','MARGIN') NOT NULL,
    shares DECIMAL(10,2) NOT NULL,
    cost_basis DECIMAL(12,4) NOT NULL,
    cost_basis_total DECIMAL(12,2),
    entry_date DATE,
    strategy VARCHAR(50),         -- assigned allocation strategy
    trailing_stop_pct DECIMAL(5,2),
    last_signal TINYINT,
    last_eval_date DATE,
    notes VARCHAR(200),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_symbol (symbol),
    INDEX idx_account (account_type)
) ENGINE=InnoDB;

-- ============================================================================
-- 8. ALLOCATION STRATEGIES — geographic, sector, blended definitions
-- ============================================================================
CREATE TABLE allocation_strategies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(60) NOT NULL UNIQUE,
    description VARCHAR(300),
    type ENUM('geographic','sector','blended','mvp','equal_weight','custom') NOT NULL,
    -- Geographic weights stored as JSON: {"CA":0.70,"US":0.30}
    geo_weights JSON,
    sector_weights JSON,
    reweight_frequency VARCHAR(20), -- monthly, quarterly, annually
    tax_optimized TINYINT DEFAULT 1,
    include_bonds TINYINT DEFAULT 0,
    bond_pct DECIMAL(5,2) DEFAULT 0,
    max_single_position DECIMAL(5,2) DEFAULT 0.10,
    active TINYINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================================================
-- 9. AFTER-TAX RETURNS — for reporting/analysis
-- ============================================================================
CREATE TABLE after_tax_returns (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL,
    strategy_id INT,
    strategy_name VARCHAR(60),
    account_type ENUM('TFSA','RRSP','MARGIN'),
    -- Pre-tax
    total_return DECIMAL(10,6),
    capital_gain DECIMAL(10,6),
    eligible_div DECIMAL(10,6),
    foreign_div DECIMAL(10,6),
    -- Tax impact
    fed_tax DECIMAL(10,6),
    prov_tax DECIMAL(10,6),
    div_tax_credit DECIMAL(10,6),
    withholding_tax DECIMAL(10,6),
    -- After-tax
    after_tax_return DECIMAL(10,6),
    tax_drag_pct DECIMAL(6,4),
    FOREIGN KEY (strategy_id) REFERENCES allocation_strategies(id),
    INDEX idx_date (date),
    INDEX idx_strategy (strategy_id)
) ENGINE=InnoDB;
