-- Lipper-style peer-relative stock scoring (extensible by peer group: sector/industry/style_box)
-- + advisor portfolio effectiveness.
-- Implements the meaningful Lipper measures: Total Return, Preservation (loss avoidance),
-- Consistent Return (risk-adjusted). Each is percentile-ranked within the stock's peer group
-- and expressed as a 1-5 Lipper Leader-style score; composite = avg of the three.
-- Adding a new peer dimension = new rows (peer_group_type), NOT new columns.

DROP TABLE IF EXISTS lipper_stock_scores;

CREATE TABLE IF NOT EXISTS lipper_scores (
  symbol            VARCHAR(20)  NOT NULL,
  peer_group_type   VARCHAR(20)  NOT NULL,
  peer_group_value  VARCHAR(100),
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
  PRIMARY KEY (symbol, peer_group_type),
  INDEX (peer_group_type, peer_group_value),
  INDEX (symbol)
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
