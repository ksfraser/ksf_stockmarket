# ksf_stockmarket — Complete Schema Design for MariaDB 10.11

## Source Analysis

Two backup dumps provided the table definitions:

### MYSQL.stock_market.sql (1.2GB, 19 tables)
Legacy tables from the original PHP app (pre-2013):
- `accounttype`, `alerts`, `bondrate`, `cash`, `dividendpayment`, `dividends`
- `fin_statement`, `fin_statement_bak`, `fxprices`, `gnclock`, `hedgefolios`
- `heikanashi`, `indices`, `iplace_calc`, `jobspool`, `log`, `logjob`, `msgqueue`, `portfolio`

### MYSQL.back_finance.sql (214MB, 49 tables)
More complete backup including backtesting engine tables:
- **Core**: `stockprices`, `stockinfo`, `stockexchange`, `portfolio`, `transaction`, `transactiontype`, `dividends`, `users`, `roles`
- **Analysis**: `technicalanalysis`, `tenets`, `teneteval`, `ratios`
- **Fundamental**: `fin_statement`, `quarter_statement`, `investorplace`, `iplace_calc`
- **Evaluation**: `evalbusiness`, `evalfinancial`, `evalmanagement`, `evalmarket`, `evalsummary`
- **Backtest**: `hedgefolios`, `beancounter`
- **Portfolio**: `portfolio_history`, `cash`, `bondrate`
- **Alerts**: `alerts`, `alertsraised`, `stockalert`
- **Workflow**: `statearc`, `statecase`, `stateflowrole`, `stateplace`, `statetoken`, `statetransition`, `stateworkflow`, `stateworkitem`
- **Misc**: `jobspool`, `log`, `logjob`, `msgqueue`, `tasks`, `taxstatus`, `userpref`, `userpref_txl`

### Local MariaDB Version: 10.5.18
Production (FA pod): 10.11 (from `mariadb:10.11` image)

### Key Compatibility Notes for 10.5/10.11:
- ✅ Window functions (10.2+) — AVAILABLE
  - `ROW_NUMBER()`, `RANK()`, `DENSE_RANK()`
  - `LAG()`, `LEAD()`, `FIRST_VALUE()`, `LAST_VALUE()`
  - Windowed aggregates: `AVG() OVER`, `STDDEV() OVER`, `SUM() OVER`
  - Named windows with `WINDOW` clause
  - Frame specification: `ROWS BETWEEN N PRECEDING AND CURRENT ROW`
- ✅ CTEs (10.2+) — AVAILABLE
- ✅ JSON data type (10.2+) — AVAILABLE
- ✅ Sequences (10.3+) — AVAILABLE
- ✅ SYSTEM VERSIONING (temporal tables) — AVAILABLE
- ✅ `CHECK` constraints enforced (10.2+) — AVAILABLE
- ❌ `INTERSECT`/`EXCEPT` (10.3+) — AVAILABLE
- ❌ Invisible columns (10.3+) — AVAILABLE
- ❌ `PERIOD FOR SYSTEM_TIME` — AVAILABLE

## Architecture: Materialized Tier 2 Indicators

Instead of computing indicators on every query, we:
1. **On price INSERT** → trigger calculates basic metrics (daily return, gap, true range)
2. **Nightly batch** → stored procedure calculates SMA/EMA/Bollinger/ATR and stores in `daily_indicators`
3. **On indicator table INSERT** → trigger calculates signal crossings (SMA crossovers, RSI extremes)
4. **Weekly batch** → recalculates all indicators for data integrity

This means backtest queries read pre-computed indicators — fast, no Python overhead.

## Schema Design Principles

1. **InnoDB only** (no more MyISAM — transactional safety, row-level locking)
2. **utf8mb4 charset** (supports full Unicode, future-proof)
3. **Partition stockprices by year** (backup-friendly, query pruning)
4. **No foreign keys on high-volume tables** (stockprices, technicalanalysis) — app-level integrity
5. **Use generated columns for computed values** (e.g., year from date, for partitioning)
6. **Proper composite primary keys** (symbol + date for price data)
7. **Auto-audit columns** (`created_at`, `updated_at`, `created_by`) on all user-facing tables
