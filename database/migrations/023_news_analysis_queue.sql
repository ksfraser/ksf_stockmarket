-- Migration 023: news_analysis_queue
--
-- PURPOSE: queue news items for LLM analysis with per-symbol rate limiting.
--   Every news row inserted into news_feeds (or symbol_news) gets queued here
--   for an LLM to analyze. The queue enforces a 2-day throttle per symbol so
--   that all news for a stock in a window is batched into a single analysis run
--   rather than firing one LLM call per headline.

CREATE TABLE IF NOT EXISTS news_analysis_queue (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    news_id     INT UNSIGNED  NOT NULL COMMENT 'FK to news_feeds.id (or symbol_news.id — store which table in news_source_table)',
    news_source_table VARCHAR(30) NOT NULL DEFAULT 'news_feeds' COMMENT 'Which table the news_id comes from: news_feeds or symbol_news',
    symbol      VARCHAR(20)  NOT NULL COMMENT 'Symbol this news is about',
    status      ENUM('pending','in_progress','completed','failed') NOT NULL DEFAULT 'pending',
    attempt_count INT UNSIGNED NOT NULL DEFAULT 0 COMMENT 'Number of LLM call attempts',

    prompt_sent    TEXT     DEFAULT NULL COMMENT 'The prompt sent to the LLM (for debugging/replay)',
    response_text  LONGTEXT DEFAULT NULL COMMENT 'Raw LLM response',
    response_summary TEXT   DEFAULT NULL COMMENT 'Parsed summary stored back to news_feeds.summary or symbol_news.summary',
    response_classification VARCHAR(50) DEFAULT NULL COMMENT 'Classification category (if applicable)',
    response_sentiment VARCHAR(20) DEFAULT NULL COMMENT 'Sentiment label (if applicable)',
    response_recommendation VARCHAR(20) DEFAULT NULL COMMENT 'Buy/hold/sell/watch (if applicable)',
    response_confidence DECIMAL(4,2) DEFAULT NULL COMMENT 'LLM confidence 0-100',

    error_message TEXT DEFAULT NULL COMMENT 'If status=failed, what went wrong',

    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at  DATETIME DEFAULT NULL,
    completed_at DATETIME DEFAULT NULL,

    UNIQUE KEY u_news_id (news_id, news_source_table),
    INDEX idx_symbol_status (symbol, status),
    INDEX idx_pending (status, created_at),
    INDEX idx_symbol_pending (symbol, status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Queue for LLM news analysis with per-symbol 2-day rate limiting';

