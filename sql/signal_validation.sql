-- signal_validation.sql
-- Stores statistical validation results per symbol per scoring run.
-- Layer 1: automatic baseline — run every scoring cycle.

CREATE TABLE IF NOT EXISTS `signal_validation` (
  `id`               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `symbol`           VARCHAR(16)    NOT NULL,
  `run_date`         DATE           NOT NULL,
  `t_stat`           FLOAT          NULL DEFAULT NULL,
  `p_value`          FLOAT          NULL DEFAULT NULL,
  `is_significant`   TINYINT(1)     NULL DEFAULT 0,
  `normality_p_value`FLOAT          NULL DEFAULT NULL,
  `is_normal`        TINYINT(1)     NULL DEFAULT 0,
  `adf_stat`         FLOAT          NULL DEFAULT NULL,
  `adf_p_value`      FLOAT          NULL DEFAULT NULL,
  `is_stationary`    TINYINT(1)     NULL DEFAULT 0,
  `kelly_pct`        FLOAT          NULL DEFAULT NULL,
  `validation_json`  JSON           NULL DEFAULT NULL,
  `created_at`       TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_symbol_date` (`symbol`, `run_date`),
  UNIQUE KEY `uk_symbol_date` (`symbol`, `run_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
