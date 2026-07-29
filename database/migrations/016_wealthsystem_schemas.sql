-- Migration 016: Add WealthSystem-aligned fundamental/analysis schemas
-- Ports applicable schema + thresholds from WealthSystem Stock-Analysis-Extension

-- --------------------------------------------------------------------------
-- Stock fundamentals: per-symbol fundamental metrics (updated over time)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stock_fundamentals (
    symbol                 CHAR(16)    NOT NULL PRIMARY KEY,
    company_name           VARCHAR(255) NULL,
    sector                 VARCHAR(100) NULL,
    industry               VARCHAR(100) NULL,
    market_cap_bigint      BIGINT       NULL COMMENT 'Market cap in dollars',
    enterprise_value       BIGINT       NULL,
    pe_ratio               DECIMAL(8,2) NULL COMMENT 'Price/Earnings',
    peg_ratio              DECIMAL(8,2) NULL COMMENT 'PEG',
    price_to_book          DECIMAL(8,2) NULL,
    price_to_sales         DECIMAL(8,2) NULL,
    debt_to_equity         DECIMAL(8,2) NULL,
    return_on_equity       DECIMAL(8,4) NULL COMMENT 'ROE %',
    return_on_assets       DECIMAL(8,4) NULL COMMENT 'ROA %',
    profit_margin          DECIMAL(8,4) NULL COMMENT 'Net margin %',
    operating_margin       DECIMAL(8,4) NULL,
    gross_margin           DECIMAL(8,4) NULL,
    dividend_yield         DECIMAL(8,4) NULL COMMENT 'Dividend yield %',
    payout_ratio           DECIMAL(8,2) NULL,
    beta                   DECIMAL(8,4) NULL,
    revenue_growth         DECIMAL(8,2) NULL COMMENT 'YoY revenue growth %',
    earnings_growth        DECIMAL(8,2) NULL COMMENT 'YoY earnings growth %',
    current_ratio          DECIMAL(8,2) NULL,
    quick_ratio            DECIMAL(8,2) NULL,
    cash_per_share         DECIMAL(8,2) NULL,
    book_value_per_share   DECIMAL(8,2) NULL,
    analyst_rating         VARCHAR(20)  NULL,
    target_price           DECIMAL(10,4) NULL,
    last_updated           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_sector (sector),
    INDEX idx_pe_ratio (pe_ratio),
    INDEX idx_market_cap (market_cap_bigint)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------
-- Evaluation breakdown tables: business, financial, management, market
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evalbusiness (
    idevalbusiness INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    symbol         CHAR(16)    NOT NULL,
    score          INT         NOT NULL DEFAULT 0,
    summary        TEXT        NULL,
    lasteval       TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS evalfinancial (
    idevalfinancial INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    symbol           CHAR(16)    NOT NULL,
    score            INT         NOT NULL DEFAULT 0,
    summary          TEXT        NULL,
    lasteval         TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS evalmanagement (
    idevalmanagement INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    symbol            CHAR(16)    NOT NULL,
    score             INT         NOT NULL DEFAULT 0,
    summary           TEXT        NULL,
    lasteval          TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS evalmarket (
    idevalmarket INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    symbol       CHAR(16)    NOT NULL,
    score        INT         NOT NULL DEFAULT 0,
    summary      TEXT        NULL,
    lasteval     TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------
-- Evaluation summary: aggregated weighted score
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evalsummary (
    symbol          CHAR(16)    NOT NULL PRIMARY KEY,
    totalscore      INT         NOT NULL DEFAULT -1,
    reviseddate     TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    marginsafety    FLOAT(11)   NOT NULL DEFAULT -999999,
    ratioscore      INT         NULL DEFAULT 0,
    iplacecalcscore INT         NULL DEFAULT 0,
    managementscore INT         NOT NULL DEFAULT -1,
    financialscore  INT         NOT NULL DEFAULT -1,
    businessscore   INT         NOT NULL DEFAULT -1,
    reviseduser     VARCHAR(45) NOT NULL DEFAULT '',
    INDEX idx_updated (reviseddate)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------
-- IPlace (InvestorPlace) calculated scores
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS iplace_calc (
    idiplacecalc    INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    symbol          CHAR(16)    NOT NULL,
    composite_score INT         NOT NULL DEFAULT 0,
    recommendation  VARCHAR(32) NULL,
    criteria_json   JSON        NULL COMMENT 'Breakdown by criterion',
    date_calculated DATE        NOT NULL,
    updated_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_symbol_date (symbol, date_calculated)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------
-- LLM qualitative analysis: management openness, candor, moat durability, etc.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS llm_analysis (
    idllmanalysis   INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    symbol          CHAR(16)    NOT NULL,
    analysis_date   DATE        NOT NULL,
    provider        VARCHAR(32) NULL COMMENT 'openai, ollama, openrouter, etc.',
    model           VARCHAR(64) NULL,
    management_openness TINYINT(1) NULL COMMENT '1=transparent/candid, 0=opaque',
    candor_score    TINYINT(1)   NULL COMMENT '1=forthcoming in filings/calls, 0=evasive',
    moat_durability TINYINT(1)   NULL COMMENT '1=durable competitive advantage',
    risk_factors    TEXT        NULL COMMENT 'LLM-identified key risks',
    opportunities   TEXT        NULL COMMENT 'LLM-identified growth vectors',
    summary         TEXT        NULL COMMENT 'LLM 3-5 sentence thesis',
    raw_response    JSON        NULL COMMENT 'Full LLM response for audit',
    created_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_symbol_date_provider (symbol, analysis_date, provider(32)),
    INDEX idx_symbol_date (symbol, analysis_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------
-- Technical indicators: modern TA time-series per symbol/date
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stock_technical_indicators (
    id                 INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    symbol             CHAR(16)    NOT NULL,
    date               DATE        NOT NULL,
    sma_20             DECIMAL(10,4) NULL,
    sma_50             DECIMAL(10,4) NULL,
    sma_200            DECIMAL(10,4) NULL,
    ema_12             DECIMAL(10,4) NULL,
    ema_26             DECIMAL(10,4) NULL,
    macd               DECIMAL(10,4) NULL,
    macd_signal        DECIMAL(10,4) NULL,
    macd_histogram     DECIMAL(10,4) NULL,
    rsi_14             DECIMAL(8,2)  NULL,
    bollinger_upper    DECIMAL(10,4) NULL,
    bollinger_middle   DECIMAL(10,4) NULL,
    bollinger_lower    DECIMAL(10,4) NULL,
    stochastic_k       DECIMAL(8,2)  NULL,
    stochastic_d       DECIMAL(8,2)  NULL,
    williams_r         DECIMAL(8,2)  NULL,
    atr                DECIMAL(10,4) NULL,
    obv                BIGINT        NULL,
    vwap               DECIMAL(10,4) NULL,
    golden_cross       TINYINT(1)    NULL DEFAULT 0,
    death_cross        TINYINT(1)    NULL DEFAULT 0,
    created_at         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_symbol_date (symbol, date),
    INDEX idx_symbol (symbol),
    INDEX idx_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------------------------
-- Motley Fool criteria (10 criteria)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS motleyfool (
    idmotleyfool      INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    symbol            CHAR(16)    NOT NULL,
    simplebusiness    TINYINT(1)  NULL DEFAULT 0,
    reasonablevaluation TINYINT(1) NULL DEFAULT 0,
    corefocus         TINYINT(1)  NULL DEFAULT 0,
    doubledigitsales  TINYINT(1)  NULL DEFAULT 0,
    risingcashflow    TINYINT(1)  NULL DEFAULT 0,
    risingbookvalue   TINYINT(1)  NULL DEFAULT 0,
    improvingmargins  TINYINT(1)  NULL DEFAULT 0,
    risingroe         TINYINT(1)  NULL DEFAULT 0,
    insiderownership  TINYINT(1)  NULL DEFAULT 0,
    regulardividend   TINYINT(1)  NULL DEFAULT 0,
    score             INT         NOT NULL DEFAULT 0,
    lastupdate        TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_symbol (symbol),
    INDEX idx_score (score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
