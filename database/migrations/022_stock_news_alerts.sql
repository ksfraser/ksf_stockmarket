-- Migration 022: stock_news_alerts table
--
-- PURPOSE: track symbols that need human attention for news/data gaps.
--   - Symbols with no recent news (data feed may be broken)
--   - Symbols whose earnings calendar has gaps
--   - LLM analysis queue entries that failed or are stale
--
-- Fields track: what's wrong, when it was first seen, who's responsible,
-- how many times it's been flagged (to avoid alert fatigue on recurring)
-- issues, and whether it's been acknowledged.

CREATE TABLE IF NOT EXISTS stock_news_alerts (
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    symbol        VARCHAR(20)  NOT NULL COMMENT 'Symbol that needs attention',
    alert_type    ENUM('no_recent_news','earnings_calendar_gap','news_analysis_failed',
                       'price_feed_stale','competitor_missing','name_mismatch') NOT NULL,
    severity      ENUM('info','warning','critical') NOT NULL DEFAULT 'warning',
    message       TEXT         NOT NULL COMMENT 'Human-readable description of the issue',
    details       JSON         DEFAULT NULL COMMENT 'Structured extra info (e.g. missing dates, competitor list)',

    -- Tracking
    first_seen    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen     DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    flag_count    INT UNSIGNED NOT NULL DEFAULT 1 COMMENT 'Incremented each time this alert fires for the same symbol+type',

    -- Resolution
    status        ENUM('open','investigating','resolved','false_positive') NOT NULL DEFAULT 'open',
    owner         VARCHAR(64)  DEFAULT NULL COMMENT 'Who is working on it (e.g. "hermes", "kevin")',
    resolved_at   DATETIME    DEFAULT NULL,
    resolved_by   VARCHAR(64)  DEFAULT NULL,
    resolution    TEXT         DEFAULT NULL COMMENT 'What was done to fix it',

    -- Metadata
    source        VARCHAR(64)  DEFAULT NULL COMMENT 'What detected this (e.g. "stock_analysis_writer.py", "news_monitor.py")',
    created_by    VARCHAR(64)  DEFAULT NULL,

    UNIQUE KEY u_symbol_type (symbol, alert_type),
    INDEX idx_open_alerts (status, severity, last_seen),
    INDEX idx_first_seen (first_seen)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Flags symbols needing human attention — news gaps, calendar gaps, failed analyses';

