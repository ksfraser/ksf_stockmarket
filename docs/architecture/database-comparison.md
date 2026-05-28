# Database Schema Comparison: Legacy vs. Modernized

## Source Systems

| Property | `stock_market` (old) | `back_finance` (new) | `ksf_stockmarket` (git) |
|---|---|---|---|
| Origin | Original web app | Finance/trading module | Modernized PHP app |
| Tables | ~130 (FA + legacy SQL) | 21 tables | 16 tables |
| Engine | MyISAM / InnoDB mix | MyISAM mostly | InnoDB |
| Charset | latin1 | latin1 | utf8mb4 |
| Partitioned | No | No | **Yes** (prices, indicators) |

## Legacy `stock_market` Tables (selected)

Tables from the `stock_market.sql` dump that are relevant to the refactoring:

| Table | Columns | Purpose | Migrate To |
|---|---|---|---|
| `stockprices` | 12 | OHLCV daily prices | `stockprices` (partitioned) |
| `stockinfo` | 10+ | Company metadata | `stockinfo` |
| `stockexchange` | ~6 | Exchange definitions | `stockexchange` |
| `transaction` | 16 | Trade history | `user_trades` |
| `transactiontype` | 2 | Transaction categories | `transactiontype` |
| `portfolio` | ~21 | Current holdings | `portfolio` (modernized) |
| `portfolio_history` | ~21 | Historical snapshots | `portfolio_history` |
| `dividends` | ~8 | Dividend records | `dividends` |
| `stockalert` | ~5 | Price alerts | `alerts` |
| `tenets` | 14 | Motley Fool scores | Gone (Python handles) |
| `evalsummary` | ~10 | Evaluation summaries | Gone (Python handles) |
| `evalbusiness` | 226 | Fundamental analysis | Gone (Python handles) |
| `ratios` | ~60 | Financial ratios | Gone (Python handles) |
| `quarter_statement` | ~60 | Quarterly financials | Gone (Python handles) |
| `technicalanalysis` | ~20 | Precomputed TA | Replaced by tier tables |
| `candlestickactions` | ~8 | Candlestick patterns | Gone (Python/TA-Lib) |
| `motleyfool` | ~8 | MF screening | Gone (Python handles) |
| `investorplace` | ~8 | IP screening | Gone (Python handles) |
| `heikanashi` | ~8 | Candlestick data | Gone (Python/TA-Lib) |
| `fxprices` | ~5 | Forex prices | Separate module |
| `bondrate` | ~3 | Bond rates | Not migrated |
| `indices` | ~5 | Market indices | Not migrated |
| `taxstatus` | 76 | Tax lot tracking | `taxstatus` (simplified) |
| `hedgefolios` | ~8 | Hedge portfolio data | Not migrated |
| `turtledata` | ~8 | Turtle trading system | Not migrated |

## Key Differences: `stock_market` vs `back_finance`

### `stockprices` table

| Column | `stock_market` (old) | `back_finance` (new) | Modern schema |
|---|---|---|---|
| symbol | varchar(11) | varchar(12) | **CHAR(16)** |
| date | date | date | **DATE** |
| day_open | float | float | **DECIMAL(15,4)** |
| day_high | float | float | **DECIMAL(15,4)** |
| day_low | float | float | **DECIMAL(15,4)** |
| day_close | float | float | **DECIMAL(15,4)** |
| previous_close | float | float | **DECIMAL(15,4)** |
| day_change | float | float | **DECIMAL(15,4)** |
| adj_close | float | — | **DECIMAL(15,4)** |
| volume | int(11) | int(11) | **BIGINT UNSIGNED** |
| bid | float | float | **DECIMAL(15,4)** |
| ask | float | float | **DECIMAL(15,4)** |
| idstockinfo | — | int(11) | **Removed** (join via symbol) |
| source | — | — | **VARCHAR(32)** |
| updated_at | — | — | **TIMESTAMP** |
| **PRIMARY KEY** | (none!) | (none!) | **(symbol, price_date)** |
| **Engine** | MyISAM | MyISAM | **InnoDB** |
| **Partitioned** | No | No | **By YEAR** |

**Critical note**: Neither legacy schema has a PRIMARY KEY on stockprices!
This means duplicate rows are possible. The migration script needs
`INSERT IGNORE` or `ON DUPLICATE KEY UPDATE`.

### `stockinfo` table

| Column | `stock_market` | `back_finance` | Modern schema |
|---|---|---|---|
| stocksymbol | CHAR(16) | varchar(12) | CHAR(16) |
| exchange | VARCHAR(32) | varchar(45) | VARCHAR(32) |
| corporatename | — | varchar(255) | VARCHAR(255) |
| `52high` | — | float | DOUBLE |
| `52low` | — | float | DOUBLE |
| sector | — | — | VARCHAR(128) |
| industry | — | — | VARCHAR(128) |
| market_cap | — | — | BIGINT UNSIGNED |

## Migration Plan

### Phase 1: Schema + Import (current)
1. Deploy `schema_v2_partitioned.sql`
2. Import CSV data into partitioned `stockprices` (~177MB, ~2000 symbols)
3. Run Tier 2 event to populate `daily_tier2` for recent dates
4. Verify trigger works on new inserts
5. Benchmark query performance

### Phase 2: PHP Integration
1. Update `Database.php` to use modern schema
2. Update `Portfolio.php` to use new `portfolio` table
3. Add API endpoints for `v_stock_analysis`
4. Port FA module tables

### Phase 3: Python Bridge
1. CSV import script → partitioned table
2. Tier 2 refresh as Python cron (alternative to MySQL event)
3. Backtesting reads from `v_stock_analysis`
4. Signal weights written back to `signal_weights` table
