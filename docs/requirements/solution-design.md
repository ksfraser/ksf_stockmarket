# Solution Design Document
## KSF Stock Market Analysis System
### BABOK Format — Solution Architecture

---

## 1. Architecture Overview

**Pattern**: Hybrid PHP + Python + MariaDB

```
[Browser] → [Apache 2.4 + PHP 8.1] → [MariaDB 10.6+]
                ↓ mod_proxy
           [Python Flask :5000]
                ↓
           [yfinance / TA-Lib / LLM]
```

## 2. Database Design

### 2.1 Partitioning Strategy
- **stockprices**, **daily_indicators**, **daily_tier2**, **ta_values**: Partitioned by `YEAR(price_date)`
- 10 partitions covering 2008–2026+ (~8-10 years of data per partition)
- Partition pruning for backtest queries (WHERE on date range → only relevant partitions scanned)
- Per-year backup via `mysqldump --where "YEAR(date)=2025"`

### 2.2 Data Store Strategy: SQLite for Intraday, MariaDB for Daily+

| Store | Purpose | Granularity | Writer | Reader |
|---|---|---|---|---|
| SQLite `price_intraday` | Ephemeral intraday/sub-day cache | Day-trade bars, 15-min sync | `sync_stock_prices --sqlite`, fetcher crons | detection_triggers, calculators |
| MariaDB `stockprices` | Daily history, partitioned by year | Daily OHLCV | sync jobs, backfills, migrations | TA, backtest, strategies, UI |
| SQLite `alert_queue` | Ephemeral alert staging | Trigger-level events | detection_triggers --sqlite | alert dispatcher → MariaDB EOD sync |
| MariaDB `alert_queue` | Canonical alert log | Historical alerts | EOD sync from SQLite | UI, LLM analysis |

**Rule**: sub-day checks read SQLite. Daily+ lookbacks (>1 day window) read MariaDB.
If data is stale, calculators return `stale` state; an external fetcher service refreshes SQLite/MariaDB independently.

### 2.4 Fetcher → Repository Pattern

External data sources (yFinance, Google Finance, SEDAR, SEC) write **only** to DTOs.
Repositories own all SQL. This separation:
- Makes every worker idempotent (same DTO save = same DB state)
- Enables distributed execution (fetcher container → shared DB → calculator container)
- Centralizes column mapping in one place per backend
- Lets us add sources without touching calculators

```
Fetcher (YFinanceFetcher)
  → List[StockPriceDTO]
    → Repository.save_all(dtos)  # SQLite intraday or MariaDB daily+
```

**Staleness contract**: calculators call `repository.is_stale(symbol, max_age_hours)`.
If stale, they emit `STALE_DATA` event instead of computing; a fetcher worker
picks it up and refreshes the store. Fetchers never run inline inside calculators.

### 2.4 Scoring System Design

| Table | Purpose | LLM Role |
|---|---|---|
| evalsummary | Composite score (out of 36) | Investment thesis summary, recommendation |
| motleyfool | MF screening criteria | Check criteria against 10-K data |
| investorplace | IP screening (24 criteria) | Analyze press releases for restructuring, buybacks |
| tenets | 12 Buffett-style tenets | Analyze annual letters, proxy statements |
| evalbusiness | Business quality | Evaluate business model, competitive moat |
| ratios | Financial ratios + attractiveness | Python calculates, LLM assesses quality |
| quarter_statement | Quarterly financials | Extract from 10-Q filings |
| evalmanagement | Management quality | Analyze MD&A, proxy statements |
| evalmarket | Market evaluation | Assess market conditions |
| evalvalue | Intrinsic value | Assist with qualitative value factors |
| scoring_history | Audit trail | Track LLM vs human changes |

**LLM Integration Pattern** (all scoring tables):
- `source` / `source_date`: What document was analyzed
- `is_llm_generated`: Whether LLM populated this score
- `llm_confidence`: Confidence level (0-1)
- `llm_reasoning`: LLM explanation
- `human_overridden`: Human changed the LLM's score
- `human_recommendation`: Human analyst's recommendation

### 2.5 Signal Weight Correlation Design

**Problem**: Signals fire at different times — some lead, some lag, some coincide.

**Solution**: `signal_weights` table tracks correlation and lead/lag:
- `avg_lead_days`: Days between signal and price move (+ leads, - lags)
- `is_pre_indicator`: 1 if signal consistently leads
- `correlation`: Correlation with future 5-day return
- `correlates_with`: JSON of correlated signals with lag times
- `weight_boosted`: Effective weight when pre-indicator confirmed

**Boost Formula**:
```
effective_weight = base_weight × (1 + correlation × 0.5) × recency_factor
```

**Example**: RSI_OVERSOLD (55% win rate alone) → 1.36x weight when MACD_CROSS hasn't confirmed (78% win rate for sequence).

## 3. Application Design

### 3.1 PHP Layer (Presentation)
- PSR-4 autoloading under `Ksf\StockMarket\`
- Front controller pattern (index.php dispatcher)
- Twig templates
- PDO for database access (no ORM)
- PythonBridge HTTP client to Flask API

### 3.2 Python Layer (Analysis)
- Flask REST API on :5000
- TA-Lib for vectorized indicator calculation
- pandas for data manipulation
- yfinance for market data
- LLM integration for qualitative scoring
- Cron jobs for daily processing

### 3.3 Data Flow

```text
Intraday/market-hours:
  Fetcher cron (every 15 min)
    → YFinanceFetcher → StockPriceDTOs → SQLitePriceRepository
    → price_intraday (sub-day cache)
  Detection cron
    → detection_triggers --sqlite
    → reads price_intraday (no yfinance calls)
    → SQLitePriceRepository.upsert alerts
    → alert_queue (SQLite)

EOD/historical:
  Fetcher cron (daily)
    → YFinanceFetcher → StockPriceDTOs → MariaDBStockPriceRepository
    → stockprices (daily+ history)
  Calculator cron
    → reads stockprices via Repository
    → writes indicators to MariaDB
  EOD sync
    → SQLite alert_queue → MariaDB alert_queue
```

**Rule**: Fetchers write, calculators read. If a calculator finds stale data,
it emits `STALE_DATA` and exits. Fetcher workers handle refresh asynchronously.

## 4. Migration Strategy

### Phase 1: Schema + Foundation
- Deploy partitioned schema
- Import legacy data via migration scripts
- Verify triggers and events

### Phase 2: Scoring Engine
- Python scripts populate scoring tables
- LLM analyzes filings for qualitative criteria
- Human review workflow

### Phase 3: PHP Modernization
- Port legacy classes to PSR-4
- Build UI for scoring dashboard
- FA module integration

### Phase 4: Optimization
- Signal weight correlation analysis
- Backtesting with optimized weights
- Performance tuning

## 5. Advisor Recommendations & Notifications

### 5.1 Flow
```
Cron: run_advisor_recommendations.py --date=YYYY-MM-DD
  ├─ load_active_advisors()
  ├─ for advisor in advisors:
  │   ├─ strategy.generate_signals()
  │   ├─ users = user_advisors.where(advisor_id, is_active=1)
  │   ├─ for user in users:
  │   │   ├─ queue recommendation into advisor_recommendations
  │   │   ├─ load user_settings notification prefs
  │   │   ├─ send_email / discord_dm / discord_channel / whatsapp
  │   │   └─ mark sent flags
  │   └─ if no users hired: skip
  └─ log run result

API (python/api/app.py):
  GET  /api/advisor/recommendations?user_id=N
  GET/POST /api/advisor/preferences?user_id=N
  POST /api/advisor/notifications/whatsapp/send
  POST /api/advisor/notifications/whatsapp/status

### 5.2 Knowledge Base Integration
- KB articles served via `?action=knowledge_base` and `?action=kb_article&slug=...`
- Optional risk rules stored in `strategy_rules.risk_rules.optional_rules` JSON:
  - `min_reward_risk_ratio` — asymmetric risk/reward floor
  - `emergency_buffer_target_pct` — cash reserve floor
  - `emergency_buffer_grace_days` — days buffer can stay below target before blocking buys
  - `max_leverage_ratio` — max (portfolio/cash) before blocking
  - `max_margin_utilization_pct` — max margin utilization
  - `margin_call_buffer_pct` — cash floor as % of equity
  - `margin_call_grace_hours` — hours buffer can stay breached
  - `blacklist_asset_classes` — excluded asset classes/symbols
- rules_backtest enforces optional rules before entries; zero values = disabled.

### 5.3 Multi-Gateway Delivery
- Email: SMTP via advisor_notifier._send_email()
- Discord: bot token + channel webhook; DM + private channel supported
- WhatsApp: HTTP POST to {WHATSAPP_GATEWAY_URL}/v1/send with E.164 normalization
- Recommendation format: "Buy 100 ABC at $12 max 12.45 stop limit 10.92 etc."
