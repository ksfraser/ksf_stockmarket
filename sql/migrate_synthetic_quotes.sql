-- Synthetic "fake exchange" for instruments with no real market quote
-- (money-market funds, private series, etc.). Symbols registered here resolve
-- to a static local NAV instead of being sent to yfinance (which raises
-- "Quote not found"). See python/src/synthetic_quotes.py and
-- sql/seed_synthetic_quotes.sql.
CREATE TABLE IF NOT EXISTS `synthetic_quotes` (
  `id`         INT          AUTO_INCREMENT PRIMARY KEY,
  `symbol`     VARCHAR(32)  NOT NULL,
  `name`       VARCHAR(255) DEFAULT NULL,
  `price`      DECIMAL(18,4) NOT NULL,
  `currency`   CHAR(3)      DEFAULT 'CAD',
  `exchange`   VARCHAR(16)  DEFAULT 'MMF',
  `asset_type` VARCHAR(64)  DEFAULT 'Money Market Fund',
  `asof_date`  DATE         DEFAULT NULL,
  `is_active`  TINYINT(1)   DEFAULT 1,
  UNIQUE KEY `uq_synthetic_symbol` (`symbol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
