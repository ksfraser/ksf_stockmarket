-- Migration 021: Stock Competitors + Stock Analysis Write-ups
--
-- PURPOSE:
--   stock_competitors: maps each symbol to its sector/industry competitors
--     (used by the stock detail page and the analysis writer to compare
--     performance, valuation, and news against peer companies).
--
--   stock_analysis: stores periodic write-ups (pre-earnings, post-earnings,
--     ATR sweep, etc.) as rows so we can see historical analysis over time
--     and display the latest write-up on the stock detail page.
--
-- Tables:
--   stock_competitors  — symbol → competitor_symbol (many-to-many per sector/industry)
--   stock_analysis     — one row per write-up, linked to symbol + period

CREATE TABLE IF NOT EXISTS stock_competitors (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    symbol      VARCHAR(20)  NOT NULL COMMENT 'The stock being analyzed',
    competitor  VARCHAR(20)  NOT NULL COMMENT 'A competitor or peer company symbol',
    is_primary  TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '1 = direct competitor, 0 = same sector peer',
    notes       VARCHAR(255) DEFAULT NULL COMMENT 'Why this competitor (e.g. "direct QSR rival", "same sub-industry")',
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY u_symbol_competitor (symbol, competitor),
    INDEX idx_competitor (competitor)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Competitor/peer mappings for stock detail pages and analysis scripts';


CREATE TABLE IF NOT EXISTS stock_analysis (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    symbol          VARCHAR(20)  NOT NULL COMMENT 'Stock this write-up is about',
    period_type     ENUM('pre_earnings','post_earnings','atr_sweep','quarterly_check','custom') NOT NULL COMMENT 'What kind of analysis this is',
    period_date     DATE         NOT NULL COMMENT 'The date the analysis was written / effective date',
    earnings_date   DATE         DEFAULT NULL COMMENT 'If tied to earnings: the report date (for pre/post)',
    earnings_ticker VARCHAR(20) DEFAULT NULL COMMENT 'If tied to earnings: the ticker that reported',
    title           VARCHAR(255) DEFAULT NULL COMMENT 'Short title for the write-up',

    -- Captured data snapshot at time of write-up (so historical write-ups stay stable)
    close_price     DECIMAL(12,4) DEFAULT NULL,
    prev_close      DECIMAL(12,4) DEFAULT NULL,
    atr_14          DECIMAL(12,4) DEFAULT NULL,
    atr_factor      DECIMAL(8,4)  DEFAULT NULL COMMENT 'ATR multiple recommended by sweep',
    bounce_rate     DECIMAL(6,4)  DEFAULT NULL COMMENT 'ATR bounce-back rate if from sweep',

    -- Analyst snapshot
    consensus_target DECIMAL(12,4) DEFAULT NULL,
    num_analysts     INT UNSIGNED  DEFAULT NULL,
    avg_pe_ttm       DECIMAL(8,2)  DEFAULT NULL,
    avg_pe_fwd       DECIMAL(8,2)  DEFAULT NULL,
    div_yield        DECIMAL(6,2)  DEFAULT NULL,

    -- Body
    body_md         TEXT         NOT NULL COMMENT 'Markdown body of the write-up',
    body_html       LONGTEXT     DEFAULT NULL COMMENT 'Optional pre-rendered HTML',

    -- Metadata
    generated_by    VARCHAR(64)  DEFAULT NULL COMMENT 'Script name or "manual"',
    word_count      INT UNSIGNED  DEFAULT NULL,
    source_symbols  JSON         DEFAULT NULL COMMENT 'Symbols referenced in the analysis (competitors, sector peers)',

    created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_symbol_period (symbol, period_type, period_date),
    INDEX idx_symbol_latest (symbol, period_type, period_date DESC),
    INDEX idx_period_date (period_type, period_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Periodic stock analysis write-ups (pre/post earnings, ATR sweep, quarterly checks)';

