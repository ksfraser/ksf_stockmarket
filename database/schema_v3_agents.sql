-- ============================================================================
-- Agent System Tables — for multi-agent ensemble trading system
-- ============================================================================
-- Depends on: schema_v2_partitioned.sql (users, stockprices, signal_weights, etc.)
--
-- Tables:
--   agent_runs          — tracks every agent execution (status, timing, results)
--   nn_predictions      — LSTM directional predictions per symbol per day
--   rl_signals          — reinforcement learning policy decisions
--   ga_results          — genetic algorithm weight optimization runs
--   portfolio_orders    — final blended trade orders from the blender
--   agent_configs       — per-agent configuration (weights, hyperparameters)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Agent run tracking — every agent execution is logged here
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_runs (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    agent_type      ENUM('ga', 'nn', 'rl', 'blender', 'orchestrator') NOT NULL,
    run_name        VARCHAR(128)    NULL COMMENT 'Human-readable label, e.g. "GA_Tier1_Holdings"',
    priority        TINYINT         NOT NULL DEFAULT 5 COMMENT '1=highest, 9=lowest',
    machine_id      VARCHAR(64)     NULL COMMENT 'Hostname or worker ID for distributed tracking',
    status          ENUM('queued', 'running', 'complete', 'failed', 'cancelled') NOT NULL DEFAULT 'queued',
    symbol_target   CHAR(16)        NULL COMMENT 'NULL = portfolio-wide, else specific symbol',
    region          ENUM('CDN', 'USA', 'EURO', 'EMERGING', 'GLOBAL') NULL,
    started_at      TIMESTAMP       NULL,
    completed_at    TIMESTAMP       NULL,
    duration_sec    INT UNSIGNED    NULL COMMENT 'Actual runtime in seconds',
    reward_score    DECIMAL(10,6)  NULL COMMENT 'Fitness/Sharpe/return metric produced by this run',
    result_json     JSON            NULL COMMENT 'Arbitrary result payload (weights, predictions, etc.)',
    error_message   TEXT            NULL,
    parent_run_id   BIGINT UNSIGNED NULL COMMENT 'Links sub-runs to orchestrator parent',
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_agent_type (agent_type),
    INDEX idx_status (status),
    INDEX idx_symbol (symbol_target),
    INDEX idx_priority_status (priority, status),
    INDEX idx_parent (parent_run_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------------------------
-- Neural Net predictions — LSTM directional forecasts per symbol per day
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS nn_predictions (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    symbol          CHAR(16)        NOT NULL,
    prediction_date DATE            NOT NULL COMMENT 'The date this prediction was made for',
    model_version   VARCHAR(32)     NULL COMMENT 'Model snapshot identifier, e.g. "lstm_v3"',
    agent_run_id    BIGINT UNSIGNED NULL COMMENT 'Links back to agent_runs',

    -- Direction prediction
    direction       ENUM('STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL') NOT NULL,
    confidence      DECIMAL(5,4)   NOT NULL COMMENT '0.0 to 1.0 probability',
    predicted_return_5d  DECIMAL(10,6) NULL COMMENT 'Predicted 5-day return %',
    predicted_return_20d DECIMAL(10,6) NULL COMMENT 'Predicted 20-day return %',

    -- Position sizing
    raw_weight       DECIMAL(7,4)   NULL COMMENT 'NN recommended weight before user cap',
    user_cap_weight  DECIMAL(7,4)   NULL COMMENT 'Weight after applying user_position_caps (min of the two)',

    -- Feature snapshot (key indicators that drove the prediction)
    feature_json    JSON            NULL COMMENT 'Snapshot of key TA values at prediction time',

    -- Ground truth — filled in later when known
    actual_return_5d     DECIMAL(10,6) NULL,
    actual_return_20d    DECIMAL(10,6) NULL,
    was_correct     TINYINT(1)      NULL COMMENT '1 if direction matched actual',

    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_symbol_date_model (symbol, prediction_date, model_version),
    INDEX idx_symbol_date (symbol, prediction_date),
    INDEX idx_direction (direction),
    INDEX idx_confidence (confidence),
    INDEX idx_run (agent_run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
PARTITION BY RANGE (YEAR(prediction_date)) (
    PARTITION p_early VALUES LESS THAN (2010),
    PARTITION p2010 VALUES LESS THAN (2014),
    PARTITION p2014 VALUES LESS THAN (2018),
    PARTITION p2018 VALUES LESS THAN (2022),
    PARTITION p2022 VALUES LESS THAN (2026),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- ----------------------------------------------------------------------------
-- RL signals — reinforcement learning policy decisions
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rl_signals (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    symbol          CHAR(16)        NOT NULL,
    signal_date     DATE            NOT NULL,
    model_version   VARCHAR(32)     NULL COMMENT 'Policy version, e.g. "ppo_v2"',
    agent_run_id    BIGINT UNSIGNED NULL,

    -- Action from RL policy
    action          ENUM('BUY', 'SELL', 'HOLD', 'INCREASE', 'DECREASE') NOT NULL,
    target_weight   DECIMAL(7,4)   NULL COMMENT 'Target portfolio weight (0.0-1.0)',
    current_weight  DECIMAL(7,4)   NULL COMMENT 'Current weight before action',
    confidence      DECIMAL(5,4)   NULL COMMENT 'Policy confidence',
    expected_reward DECIMAL(10,6)  NULL COMMENT 'Q-value or expected return',

    -- State snapshot
    state_json      JSON            NULL COMMENT 'Portfolio state + market context at decision time',

    -- Outcome
    realized_pnl    DECIMAL(10,4)  NULL COMMENT 'Actual P&L after action taken',
    reward_signal   DECIMAL(10,6)  NULL COMMENT 'Computed reward for this action',

    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_symbol_date_model (symbol, signal_date, model_version),
    INDEX idx_symbol_date (symbol, signal_date),
    INDEX idx_action (action),
    INDEX idx_run (agent_run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
PARTITION BY RANGE (YEAR(signal_date)) (
    PARTITION p_early VALUES LESS THAN (2010),
    PARTITION p2010 VALUES LESS THAN (2014),
    PARTITION p2014 VALUES LESS THAN (2018),
    PARTITION p2018 VALUES LESS THAN (2022),
    PARTITION p2022 VALUES LESS THAN (2026),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- ----------------------------------------------------------------------------
-- GA results — genetic algorithm weight optimization
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ga_results (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    agent_run_id    BIGINT UNSIGNED NULL,
    symbol          CHAR(16)        NOT NULL,
    generation      INT UNSIGNED    NOT NULL COMMENT 'Which GA generation this is',

    -- The chromosome (flattened weight set)
    weights_json    JSON            NOT NULL COMMENT 'All scoring weights and correlation multipliers',

    -- Fitness
    fitness_sharpe  DECIMAL(10,6)  NULL,
    fitness_return  DECIMAL(10,6)  NULL COMMENT 'Total return % from backtest',
    fitness_maxdd   DECIMAL(10,6)  NULL COMMENT 'Max drawdown % (lower is better)',
    fitness_composite DECIMAL(10,6) NULL COMMENT 'Combined multi-objective fitness',

    -- Convergence tracking
    is_best         TINYINT(1)      NOT NULL DEFAULT 0 COMMENT 'Is this the best chromosome in this run?',
    backtest_trades INT UNSIGNED    NULL COMMENT 'Number of trades in backtest',

    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_symbol_gen (symbol, generation),
    INDEX idx_fitness (fitness_composite),
    INDEX idx_run (agent_run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------------------------
-- Portfolio orders — final blended trade decisions from the blender agent
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS portfolio_orders (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    order_date      DATE            NOT NULL,
    agent_run_id    BIGINT UNSIGNED NULL,
    blender_run_id  BIGINT UNSIGNED NULL COMMENT 'The blender execution that produced this',

    symbol          CHAR(16)        NOT NULL,
    action          ENUM('BUY', 'SELL', 'HOLD', 'INCREASE', 'DECREASE') NOT NULL,

    -- Position sizing
    target_shares   INT UNSIGNED    NULL COMMENT 'Exact shares to hold after this order',
    target_weight   DECIMAL(7,4)   NULL COMMENT 'Target portfolio weight',
    trade_shares    INT UNSIGNED    NULL COMMENT 'Shares to trade (+buy, -sell)',
    estimated_price DECIMAL(10,2)  NULL COMMENT 'Price at time of order',
    estimated_cost  DECIMAL(12,2)  NULL COMMENT 'Total estimated cost/proceeds',

    -- Agent consensus
    ga_signal       VARCHAR(16)     NULL COMMENT 'GA agent recommendation',
    nn_signal       VARCHAR(16)     NULL COMMENT 'NN agent recommendation',
    rl_signal       VARCHAR(16)     NULL COMMENT 'RL agent recommendation',
    consensus_pct   DECIMAL(5,2)   NULL COMMENT '% of agents agreeing (0-100)',

    -- Status
    status          ENUM('pending', 'approved', 'rejected', 'executed', 'expired') NOT NULL DEFAULT 'pending',
    approved_by     VARCHAR(64)     NULL COMMENT 'User or "auto" for automated execution',
    executed_at     TIMESTAMP       NULL,

    -- Outcome tracking
    executed_price  DECIMAL(10,2)  NULL,
    actual_pnl      DECIMAL(10,4)  NULL,

    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_order_date (order_date),
    INDEX idx_symbol (symbol),
    INDEX idx_status (status),
    INDEX idx_blender (blender_run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------------------------
-- Agent configuration — tunable parameters per agent, versioned
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_configs (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    agent_type      ENUM('ga', 'nn', 'rl', 'blender', 'orchestrator') NOT NULL,
    config_key      VARCHAR(128)    NOT NULL,
    config_value    TEXT            NOT NULL,
    value_type      ENUM('int', 'float', 'string', 'json', 'bool') NOT NULL DEFAULT 'string',
    description     TEXT            NULL,
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,
    version         INT UNSIGNED    NOT NULL DEFAULT 1,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_agent_key_active (agent_type, config_key, is_active),
    INDEX idx_agent_type (agent_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------------------------
-- User position sizing caps — per-symbol, per-region, per-sector hard limits
-- Blender respects these as: effective_weight = min(agent_recommended, user_cap)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_position_caps (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    cap_type        ENUM('symbol', 'region', 'sector', 'account', 'global') NOT NULL DEFAULT 'symbol',
    cap_target      VARCHAR(64)     NOT NULL COMMENT 'Symbol ticker, region code, sector name, or account_id',
    max_position_pct DECIMAL(7,4)  NOT NULL COMMENT 'Maximum portfolio weight (0.0-1.0)',
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,
    notes           TEXT            NULL COMMENT 'Why this cap exists',
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_type_target (cap_type, cap_target),
    INDEX idx_cap_type (cap_type),
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Seed default position caps (conservative defaults — user adjusts via UI/API)
INSERT INTO user_position_caps (cap_type, cap_target, max_position_pct, is_active, notes) VALUES
('global',      'default',    0.10, 1, 'Default max 10% per position across all accounts'),
('region',      'CDN',        0.15, 1, 'Canadian equities max 15% per position'),
('region',      'USA',        0.15, 1, 'US equities max 15% per position'),
('region',      'EURO',       0.08, 1, 'European equities max 8% per position (more volatile FX)'),
('region',      'EMERGING',   0.05, 1, 'Emerging markets max 5% per position (highest risk)'),
('account',     'TFSA',       0.10, 1, 'TFSA account max 10% per position'),
('account',     'RRSP',       0.10, 1, 'RRSP account max 10% per position'),
('account',     'MARGIN',     0.15, 1, 'Margin account max 15% per position')
ON DUPLICATE KEY UPDATE
    max_position_pct = VALUES(max_position_pct),
    notes = VALUES(notes),
    updated_at = CURRENT_TIMESTAMP;

-- ----------------------------------------------------------------------------
-- Seed default configurations
-- ----------------------------------------------------------------------------
INSERT INTO agent_configs (agent_type, config_key, config_value, value_type, description) VALUES
-- GA Agent defaults
('ga', 'population_size', '100', 'int', 'Number of chromosomes per generation'),
('ga', 'num_generations', '50', 'int', 'Maximum generations to evolve'),
('ga', 'mutation_rate', '0.15', 'float', 'Probability of weight mutation'),
('ga', 'crossover_rate', '0.8', 'float', 'Probability of crossover'),
('ga', 'elitism_pct', '0.1', 'float', 'Top % carried unchanged to next generation'),
('ga', 'tournament_size', '5', 'int', 'Tournament selection size'),
('ga', 'weight_min', '-5.0', 'float', 'Minimum allowed weight value'),
('ga', 'weight_max', '5.0', 'float', 'Maximum allowed weight value'),
('ga', 'fitness_objective', 'sharpe_return_combo', 'string', 'Objective: sharpe, return, maxdd, or sharpe_return_combo'),
('ga', 'multiclass_weights', '{"STRONG_BUY":2.0,"BUY":1.0,"HOLD":0.0,"SELL":-1.0,"STRONG_SELL":-2.0}', 'json', 'Signal-to-numeric mapping for fitness'),
('ga', 'backtest_years', '3', 'int', 'Years of historical data for backtest fitness eval'),

-- NN Agent defaults
('nn', 'sequence_length', '60', 'int', 'Days of history fed as input sequence'),
('nn', 'hidden_size', '128', 'int', 'LSTM hidden state dimension'),
('nn', 'num_layers', '2', 'int', 'Number of LSTM layers'),
('nn', 'dropout', '0.2', 'float', 'Dropout rate for regularization'),
('nn', 'learning_rate', '0.001', 'float', 'Adam optimizer learning rate'),
('nn', 'batch_size', '64', 'int', 'Training batch size'),
('nn', 'epochs', '100', 'int', 'Maximum training epochs'),
('nn', 'early_stopping_patience', '10', 'int', 'Epochs without improvement before early stop'),
('nn', 'train_split', '0.8', 'float', 'Fraction of data for training (rest for validation)'),
('nn', 'confidence_threshold', '0.6', 'float', 'Minimum confidence to generate actionable signal'),
('nn', 'max_recommended_weight', '0.15', 'float', 'Maximum position weight NN agent can recommend (before user cap)'),
('nn', 'min_recommended_weight', '0.01', 'float', 'Minimum position weight NN agent can recommend'),

-- RL Agent defaults
('rl', 'algorithm', 'PPO', 'string', 'RL algorithm: PPO, A2C, DDPG'),
('rl', 'lookback_days', '120', 'int', 'Trading days of history per episode'),
('rl', 'max_episodes', '200', 'int', 'Maximum training episodes'),
('rl', 'gamma', '0.99', 'float', 'Discount factor'),
('rl', 'lambda_gae', '0.95', 'float', 'GAE lambda for advantage estimation'),
('rl', 'clip_epsilon', '0.2', 'float', 'PPO clipping parameter'),
('lr', 'initial_position_pct', '0.05', 'float', 'Default initial position size %'),
('rl', 'max_position_pct', '0.15', 'float', 'Maximum single position weight'),
('rl', 'transaction_cost', '0.001', 'float', 'Simulated transaction cost %'),

-- Blender defaults
('blender', 'ga_weight', '0.30', 'float', 'Weight given to GA agent signal in final vote'),
('blender', 'nn_weight', '0.35', 'float', 'Weight given to NN agent signal in final vote'),
('blender', 'rl_weight', '0.35', 'float', 'Weight given to RL agent signal in final vote'),
('blender', 'consensus_threshold', '60.0', 'float', 'Minimum % agreement to generate trade'),
('blender', 'max_positions', '20', 'int', 'Maximum simultaneous positions'),
('blender', 'risk_per_trade_pct', '1.0', 'float', 'Max portfolio % risked per trade'),
('blender', 'review_frequency_days', '7', 'int', 'Days between blender portfolio reviews'),

-- Orchestrator defaults
('orchestrator', 'tier1_symbols_per_run', '50', 'int', 'Max holdings to process per nightly run'),
('orchestrator', 'tier2_symbols_per_run', '100', 'int', 'Max buy recommendations per run'),
('orchestrator', 'exploration_symbols_per_run', '200', 'int', 'Max exploration symbols per weekly run'),
('orchestrator', 'run_timeout_sec', '3600', 'int', 'Max seconds per agent run before timeout'),
('orchestrator', 'retry_count', '3', 'int', 'Retries on agent failure'),
('orchestrator', 'parallel_workers', '4', 'int', 'Max concurrent agent workers')
ON DUPLICATE KEY UPDATE
    config_value = VALUES(config_value),
    updated_at = CURRENT_TIMESTAMP;
