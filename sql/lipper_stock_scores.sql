-- Lipper-style peer-relative risk-adjusted scoring for stocks (by sector) + portfolio effectiveness.
-- Implements the "meaningful part" of Lipper: Total Return, Preservation (loss avoidance),
-- and Consistent Return (risk-adjusted). Each is percentile-ranked within the stock's
-- GICS-style sector peer group and expressed as a 1-5 Lipper Leader-style score; the
-- composite score is the average of the three. Advisor portfolios (portfolio table) are
-- then aggregated, weighted by market value, to measure effectiveness.

CREATE TABLE IF NOT EXISTS lipper_stock_scores (
  symbol            VARCHAR(20)  NOT NULL,
  sector            VARCHAR(100),
  industry          VARCHAR(100),
  as_of             DATE,
  ret_1y            DECIMAL(8,4),
  ret_3y            DECIMAL(8,4),
  ret_5y            DECIMAL(8,4),
  ret_10y           DECIMAL(8,4),
  ytd               DECIMAL(8,4),
  volatility_3y     DECIMAL(8,4),
  downside_dev      DECIMAL(8,4),
  sharpe_3y         DECIMAL(8,4),
  sortino_3y        DECIMAL(8,4),
  preservation_score TINYINT,
  total_return_score TINYINT,
  consistent_score   TINYINT,
  composite_score    TINYINT,
  sector_rank_pct    DECIMAL(5,2),
  PRIMARY KEY (symbol),
  INDEX (sector),
  INDEX (composite_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS portfolio_lipper_effectiveness (
  user_id            INT(11),
  strategy           VARCHAR(50),
  n_holdings         INT,
  scored_holdings    INT,
  avg_composite      DECIMAL(4,2),
  pct_leaders        DECIMAL(5,2),
  avg_preservation   DECIMAL(4,2),
  avg_total_return   DECIMAL(4,2),
  avg_consistent     DECIMAL(4,2),
  total_market_value DECIMAL(14,2),
  as_of              DATE,
  PRIMARY KEY (user_id, strategy)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
