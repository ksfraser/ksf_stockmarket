-- ============================================================================
-- Public-facing AI advisor personas (v1)
-- ============================================================================

CREATE TABLE IF NOT EXISTS advisor_accounts (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id INT UNSIGNED NOT NULL,
  slug VARCHAR(64) NOT NULL,
  display_name VARCHAR(128) NOT NULL,
  strategy VARCHAR(64) NOT NULL,
  start_date DATE NOT NULL,
  starting_capital DECIMAL(12,2) NOT NULL DEFAULT 100000.00,
  current_balance DECIMAL(14,2) NOT NULL,
  currency CHAR(3) NOT NULL DEFAULT 'CAD',
  profile_json JSON NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_slug (slug),
  UNIQUE KEY uk_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS portfolio_visibilities (
  user_id INT UNSIGNED NOT NULL,
  visibility ENUM('private','public','unlisted') NOT NULL DEFAULT 'private',
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS advisor_runs (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  advisor_slug VARCHAR(64) NOT NULL,
  user_id INT UNSIGNED NOT NULL,
  trade_date DATE NOT NULL,
  status ENUM('queued','running','complete','failed') NOT NULL DEFAULT 'queued',
  started_at TIMESTAMP NULL,
  completed_at TIMESTAMP NULL,
  result_json JSON NULL,
  error_message TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_advisor_date (advisor_slug, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS advisor_trades (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  advisor_slug VARCHAR(64) NOT NULL,
  user_id INT UNSIGNED NOT NULL,
  trade_date DATE NOT NULL,
  symbol VARCHAR(16) NOT NULL,
  action ENUM('BUY','SELL','HOLD') NOT NULL,
  shares DECIMAL(14,4) NOT NULL,
  price DECIMAL(10,2) NOT NULL,
  commission DECIMAL(10,2) NOT NULL DEFAULT 9.95,
  notes TEXT NULL,
  news_impact_json JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_advisor_symbol_date (advisor_slug, symbol, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- Advisor statistical validation rules (Layer 3: human/advisor override)
-- ============================================================================
-- Maps (strategy_type, test_type) to a required/minimum significance level.
-- Pipeline runs these tests on top of the automatic Layer 1 baseline.

CREATE TABLE IF NOT EXISTS advisor_stat_rules (
  id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
  strategy_type  VARCHAR(64)  NOT NULL,
  test_type      VARCHAR(64)  NOT NULL,
  min_p_value    FLOAT        NOT NULL DEFAULT 0.05,
  required       TINYINT(1)   NOT NULL DEFAULT 1,
  description    VARCHAR(255) NULL DEFAULT NULL,
  is_active      TINYINT(1)   NOT NULL DEFAULT 1,
  created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_strategy_test (strategy_type, test_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Seed rows for the existing sleeve strategies
INSERT INTO advisor_stat_rules (strategy_type, test_type, min_p_value, required, description)
  VALUES
  ('core_buffett',      't_test',        0.05, 1, 'Always require significant mean return before buying core'),
  ('core_buffett',      'adf_stationarity', 0.05, 0, 'Log stationarity flag; warning if non-stationary'),
  ('tactical_swing',    't_test',        0.05, 1, 'Tactical sleeve requires significant trend signal'),
  ('tactical_swing',    'adf_stationarity', 0.05, 0, 'ADF helps confirm mean-reversion vs trend'),
  ('tactical_swing',    'jarque_bera',   0.05, 0, 'Normality check for stop-loss calibration'),
  ('income_dividend',   't_test',        0.10, 1, 'Looser threshold — income is steady, less about alpha'),
  ('satellite_spec',    'jarque_bera',   0.05, 1, 'Speculative names must show non-normal fat tails'),
  ('satellite_spec',    'kelly_position', 0.00, 1, 'Half-Kelly always required for satellite sizing')
  ON DUPLICATE KEY UPDATE description = VALUES(description);
