-- 020_llm_fundamental_tables.sql
-- LLM fundamental analysis tables: llm_insider_trading, llm_news_events,
-- llm_product_dev, llm_regulatory, plus advisor_llm_profiles for per-advisor
-- LLM config assignment. Also seeds the new system_settings keys for
-- primary/secondary/fallback LLM endpoints.

-- ---------------------------------------------------------------------------
-- 1. llm_insider_trading — forward guidance, executive transactions,
--    insider sentiment per symbol.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS llm_insider_trading (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL COMMENT 'Ticker symbol',
    event_date DATE NOT NULL COMMENT 'Date of the insider event',
    as_of DATE NOT NULL COMMENT 'Data freshness date',
    source VARCHAR(255) DEFAULT NULL COMMENT 'Source URL or feed name',
    headline VARCHAR(500) DEFAULT NULL COMMENT 'Brief title',
    details TEXT DEFAULT NULL COMMENT 'Full description',
    confidence TINYINT UNSIGNED DEFAULT NULL COMMENT 'LLM confidence 0-100',
    conviction_score DECIMAL(5,2) DEFAULT NULL COMMENT 'Sentiment -100.00 to +100.00',
    is_verified TINYINT UNSIGNED DEFAULT 0 COMMENT 'Human-verified flag',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_llm_insider_symbol_date (symbol, event_date),
    INDEX idx_llm_insider_conviction (conviction_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='LLM-tracked insider trading and forward guidance events';

-- ---------------------------------------------------------------------------
-- 2. llm_news_events — structured news releases, earnings surprises,
--    product launches, regulatory actions, spin-offs.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS llm_news_events (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    event_date DATE NOT NULL,
    as_of DATE NOT NULL,
    source VARCHAR(255) DEFAULT NULL,
    headline VARCHAR(500) DEFAULT NULL,
    details TEXT DEFAULT NULL,
    category ENUM('earnings','product_launch','regulatory','executive','financial','market','other')
        DEFAULT 'other' COMMENT 'Event category',
    confidence TINYINT UNSIGNED DEFAULT NULL COMMENT 'LLM confidence 0-100',
    sentiment_score DECIMAL(5,2) DEFAULT NULL COMMENT 'Sentiment -100.00 to +100.00',
    conviction_score DECIMAL(5,2) DEFAULT NULL COMMENT 'Conviction -100.00 to +100.00',
    is_verified TINYINT UNSIGNED DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_llm_news_symbol_date (symbol, event_date),
    INDEX idx_llm_news_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='LLM-tracked news events and sentiment';

-- ---------------------------------------------------------------------------
-- 3. llm_product_dev — product development lifecycle stages per product line.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS llm_product_dev (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    product_name VARCHAR(255) DEFAULT NULL COMMENT 'Product or product line name',
    lifecycle_stage ENUM('concept','prototype','production_rollout','market_launch','modification','end_of_life')
        NOT NULL COMMENT 'Current lifecycle stage',
    event_date DATE NOT NULL,
    as_of DATE NOT NULL,
    source VARCHAR(255) DEFAULT NULL,
    headline VARCHAR(500) DEFAULT NULL,
    details TEXT DEFAULT NULL,
    expected_impact ENUM('positive','neutral','negative') DEFAULT 'neutral',
    confidence TINYINT UNSIGNED DEFAULT NULL COMMENT 'LLM confidence 0-100',
    conviction_score DECIMAL(5,2) DEFAULT NULL COMMENT 'Conviction -100.00 to +100.00',
    is_verified TINYINT UNSIGNED DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_llm_pd_symbol_stage (symbol, lifecycle_stage),
    INDEX idx_llm_pd_date (event_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='LLM-tracked product development lifecycle';

-- ---------------------------------------------------------------------------
-- 4. llm_regulatory — regulatory approvals, pending reviews, industry changes.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS llm_regulatory (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    event_date DATE NOT NULL,
    as_of DATE NOT NULL,
    source VARCHAR(255) DEFAULT NULL,
    headline VARCHAR(500) DEFAULT NULL,
    details TEXT DEFAULT NULL,
    regulatory_type ENUM('approval','pending_review','industry_change','compliance_action','investigation','other')
        DEFAULT 'other' COMMENT 'Type of regulatory event',
    jurisdiction VARCHAR(100) DEFAULT NULL COMMENT 'Country or regulatory body',
    status ENUM('approved','pending','rejected','withdrawn','ongoing') DEFAULT 'pending',
    confidence TINYINT UNSIGNED DEFAULT NULL COMMENT 'LLM confidence 0-100',
    conviction_score DECIMAL(5,2) DEFAULT NULL COMMENT 'Conviction -100.00 to +100.00',
    is_verified TINYINT UNSIGNED DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_llm_reg_symbol_type (symbol, regulatory_type),
    INDEX idx_llm_reg_date (event_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='LLM-tracked regulatory approvals and actions';

-- ---------------------------------------------------------------------------
-- 5. advisor_llm_profiles — per-advisor LLM config assignment.
--    Links advisor user_id to one of the three LLM config sets
--    (primary / secondary / fallback).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS advisor_llm_profiles (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    advisor_id BIGINT UNSIGNED NOT NULL COMMENT 'users.id of the advisor',
    llm_profile ENUM('primary','secondary','fallback') NOT NULL DEFAULT 'primary'
        COMMENT 'Which LLM config set this advisor uses',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE INDEX idx_llm_profile_advisor (advisor_id),
    INDEX idx_llm_profile_type (llm_profile)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Per-advisor LLM profile assignment';

-- ---------------------------------------------------------------------------
-- 6. Seed new system_settings keys for primary/secondary/fallback LLM.
--    Existing llm_* keys from earlier migrations are left as-is for
--    backward compatibility. The new keys follow the naming convention
--    llm_{primary,secondary,fallback}_{url,model,token}.
-- ---------------------------------------------------------------------------
INSERT INTO system_settings (setting_key, setting_value) VALUES
    ('llm_primary_url', ''),
    ('llm_primary_model', ''),
    ('llm_primary_token', ''),
    ('llm_secondary_url', ''),
    ('llm_secondary_model', ''),
    ('llm_secondary_token', ''),
    ('llm_fallback_url', ''),
    ('llm_fallback_model', ''),
    ('llm_fallback_token', '')
ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value);
