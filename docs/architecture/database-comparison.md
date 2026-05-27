# Investment Agent DB vs ksf_stockmarket — Comparison & Migration Plan

## Current State: Three Separate Databases

### 1. analysis_results.db (SQLite) — The investment-agent workspace
**38 tables** covering:
- **Portfolio data**: `portfolio_holdings`, `portfolio_holdings_v2`, `user_trades`, `transactions`
- **Market data**: `etf_price_history`, `ticker_summaries`, `dividend_history`
- **Analysis**: `analysis_runs`, `phase1_results`, `phase2_results`, `phase4_results`, `signals`, `weight_updates`, `signal_weights`, `signal_accuracy`, `signal_coherence`, `timing_buckets`
- **Screening**: `etf_backtest_results`, `etf_scores`, `etf_metadata`
- **Monitoring**: `corporate_events`, `news_events`, `price_alerts`, `stop_loss_tracker`, `trailing_stops`, `volume_snapshots`, `volume_spikes`, `volume_daily_summary`
- **Watchlists**: `watchlist`, `ticker_relationships`
- **Backtest**: `backtest_periods`, `backtest_periods_5y`
- **Misc**: `contacts`, `delivery_log`, `enquiry_sources`, `indicator_accuracy`, `indicator_relationships`, `insider_trades`, `journal_entries`, `journal_reviews`, `monitor_state`, `portfolios`, `risk_metrics_log`, `sector_limits`, `signal_type_accuracy`

### 2. seg_funds.db (SQLite) — Segregated fund carrier data
**6 tables**: `carriers`, `fund_codes`, `fund_families`, `fund_series`, `funds`, `performance_history`, `scrape_log`, `screening_presets`

### 3. backtest_results.db (SQLite) — Backtest engine output
**6 tables**: `backtest_performance`, `backtest_portfolio`, `backtest_positions`, `backtest_screens`, `backtest_strategies`, `backtest_trades`

### 4. ksf_stockmarket (MariaDB) — The legacy PHP app
**Original tables** (from stocks.sql, ~2009):
- `portfolio` — symbol, shares, cost, user
- `stockinfo` — symbol, exchange, name, 52w high/low
- `transaction` — seq, user, symbol, qty, type, dollar, date
- `transactiontype` — valid types (BUY, SELL, DIVIDEND, etc.)
- `users` — username, name, email, password, role
- `roles` — role descriptions
- `tenets` — Motley Fool evaluation scores per symbol (13 criteria)
- *(no price history table — prices were in CSV files)*

**New tables** (from our Phase 1 schema):
- `stockprices` — OHLCV data (symbol, date, open, high, low, close, volume)
- `dividends` — dividend records
- `portfolio_history` — portfolio value snapshots
- `watchlists` / `watchlist_symbols` — user watchlists
- `backtest_runs` / `backtest_trades` — backtest results
- `fa_transfers` — FA journal entries for transfers
- `data_import_log` — import operation tracking

## Key Differences

| Aspect | investment-agent (SQLite) | ksf_stockmarket (MariaDB) |
|--------|--------------------------|--------------------------|
| **Price data** | `etf_price_history`, CSV files in `currentdata/` | `stockprices` table (new), CSV backups |
| **Portfolio** | `portfolio_holdings` (multi-user, multi-account) | `portfolio` (simple, single-user) |
| **Transactions** | `user_trades` | `transaction` |
| **Analysis** | 15+ analysis/signal tables | `tenets` (MF scores only) |
| **TA data** | Computed on-the-fly | `technicalanalysis` SQL file (33MB of precomputed patterns) |
| **Backtest** | Separate DB (`backtest_results.db`) | `backtest_runs` / `backtest_trades` (new schema) |
| **Seg funds** | Separate DB (`seg_funds.db`) | Not present |
| **Watchlists** | `watchlist` table | `watchlists` / `watchlist_symbols` (new) |
| **Users** | Not present (single-user) | `users` table with RBAC |
| **Data volume** | ~50MB total | 177M CSV + 33MB TA SQL |

## The Backup Problem (Kevin's 2013 trauma)

The old monolithic `mysqldump` approach generated one file. When price data + TA data + other tables exceeded 4GB, the filesystem truncated the backup, losing wiki and app data.

### Solution: Per-Table Backup Strategy

```
ksf_stockmarket database backup strategy:
│
├── Critical tables (daily backup, small):
│   ├── portfolio          ~few KB
│   ├── transaction        ~few MB
│   ├── users/roles        ~few KB
│   └── stockinfo          ~few MB
│
├── Price data (weekly backup, large):
│   └── stockprices        ~hundreds of MB
│       └── PARTITION BY YEAR (see below)
│
├── Analysis data (monthly backup, regenerable):
│   ├── tenets             ~few MB
│   ├── backtest_runs      ~few MB
│   └── backtest_trades    ~few MB
│
└── Static/reference (backup once):
    ├── transactiontype    ~1 KB
    └── turtledata         ~4 KB
```

### Per-Table Partitioning for Price Data

**stockprices** gets partitioned by year to keep individual backup files small:

```sql
-- Instead of one massive stockprices table:
CREATE TABLE stockprices (
    symbol      CHAR(16)        NOT NULL,
    price_date  DATE            NOT NULL,
    open        DECIMAL(15,4)   NOT NULL,
    high        DECIMAL(15,4)   NOT NULL,
    low         DECIMAL(15,4)   NOT NULL,
    close       DECIMAL(15,4)   NOT NULL,
    volume      BIGINT UNSIGNED NOT NULL,
    adj_close   DECIMAL(15,4)   NULL,
    source      VARCHAR(32)     NULL DEFAULT 'csv',
    updated_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, price_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
PARTITION BY RANGE (YEAR(price_date)) (
    PARTITION p_pre2020 VALUES LESS THAN (2020),
    PARTITION p_2020 VALUES LESS THAN (2021),
    PARTITION p_2021 VALUES LESS THAN (2022),
    PARTITION p_2022 VALUES LESS THAN (2023),
    PARTITION p_2023 VALUES LESS THAN (2024),
    PARTITION p_2024 VALUES LESS THAN (2025),
    PARTITION p_2025 VALUES LESS THAN (2026),
    PARTITION p_2026 VALUES LESS THAN (2027),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);
```

**Benefits:**
- Back up each year partition separately: `mysqldump ... stockprices --where "price_date >= '2025-01-01'"`
- Old partitions are read-only → back up once, archive, done
- Drop old partitions instantly: `ALTER TABLE stockprices DROP PARTITION p_pre2020`
- Query performance: planner skips irrelevant partitions

### Moving investment-agent Data into ksf_stockmarket

**Phase 1: Price data (highest volume)**
- Import `currentdata/` CSV files (177MB, ~2000 symbols) into `stockprices`
- Import `etf_price_history` from analysis_results.db into `stockprices`
- Add `source` column to track origin (csv, yfinance, etc.)

**Phase 2: Portfolio holdings**
- Migrate `portfolio_holdings` → ksf_stockmarket `portfolio` + `user_trades`
- Add account_type column (RRSP, TFSA, INV, LIRA)

**Phase 3: Analysis tables**
- Port `signals`, `analysis_runs`, `weight_updates` → ksf_stockmarket
- Keep `tenets` table from original schema (Motley Fool scores)

**Phase 4: Backtest data**
- Merge `backtest_results.db` tables into ksf_stockmarket `backtest_runs` / `backtest_trades`

**Phase 5: Monitoring**
- Port `corporate_events`, `news_events`, `price_alerts` → ksf_stockmarket
- Port `volume_snapshots`, `volume_spikes` → ksf_stockmarket

**Not migrating (stay in SQLite or separate DB):**
- `seg_funds.db` — separate carrier data, different domain
- `etf_metadata`, `etf_scores`, `etf_backtest_results` — investment-agent specific
- `indicator_accuracy`, `signal_coherence`, `weight_updates` — ML training data

## Refactoring Approach

### Step 1: Create the per-table backup script
### Step 2: Partition stockprices by year
### Step 3: Import currentdata CSV → stockprices
### Step 4: Migrate portfolio data
### Step 5: Set up FA module tables (users, watchlists, backtest)
### Step 6: Build the Python→API→PHP bridge
### Step 7: Decommission SQLite files (or keep as cache layer)
