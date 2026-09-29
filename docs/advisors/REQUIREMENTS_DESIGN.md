# Public-Facing AI Advisor Personas — Requirements and Design

**Document status**: Extended 2026-09-18 to include LLM fundamental data (FR-11), Research Wizard formula-based picking (FR-12), timing-aware trading (FR-16), and LLM admin console with fallback chain (FR-11.6).

---

## Use Cases

### 1. Public Reference Portfolios
Show independent model portfolios run by personas that mimic known styles (Buffett, Lynch) and systematic strategies (index regions/sectors, day/week/month/bi-annual trading). Regular users can view them without logging in. Each advisor may use:
- Hand-coded picking criteria (existing `IStrategy::score()` pattern)
- Zacks Research Wizard `.und` screen imports (FR-14)
- Research Wizard formula-based criteria parsed by `RwFormulaParser` (FR-12)

### 2. Simulation Evidence
Each advisor runs with the same portfolio tables as regular users, so results are comparable. Advisors start from the same initial conditions and execute trades via the same mechanics (mid-price fills on daily bars).

### 3. Strategy Comparison
Index advisors isolate regional/sector exposures. Trader advisors isolate frequency/time-horizon effects. This produces actionable comparison data.

### 4. LLM-Powered Fundamental Analysis (NEW — FR-11)
The LLM analyzer maintains structured tables of forward guidance, news events, regulatory actions, and product developments for each symbol. Advisors read these tables when scoring candidates. If the LLM discovers new information not yet in the tables, it writes it. The LLM admin console (FR-11.6) configures the provider fallback chain.

### 5. Timing-Aware Trading (NEW — FR-16)
Each advisor can declare preferred trading timing (day-of-week, day-of-month period, month-end avoidance, options expiry proximity). The backtest engine captures timing dimensions for every simulated trade and reports per-bucket performance so optimal timing can be determined empirically and persisted per advisor.

---

## Requirements

### Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-1 | Each advisor is a user-level account with a portfolio in the `portfolio` table. | High |
| FR-2 | Advisor portfolios are public; regular user portfolios private by default. | High |
| FR-3 | Start date is fixed to 2025-01-02 with an initial cash balance of 100,000 CAD. | High |
| FR-4 | Advisor trades are priced at the day's mid price (approximate from open/high/low/close). | High |
| FR-5 | Strategy modules map to advisor accounts (see Advisor Strategy Mapping below). | High |
| FR-6 | Day trader executes daily; weekly once per week; monthly once per month; bi-annual twice per year. | High |
| FR-7 | Strategies may pull ideas from TradingView via MCP and news + LLM impact notes for volume/range anomalies. | High |
| FR-8 | Advisor run metadata is recorded for each trade date/run. | High |
| FR-9 | Advisors may use hand-coded picking criteria (`IStrategy::score()`), Zacks RW `.und` screen imports, or Research Wizard formula-based criteria (`RwFormulaParser` + `ZacksFieldResolver`). | High |
| FR-10 | Research Wizard formula criteria support field refs with time-lag offsets (`i95 > i95[Recent-4Q]`), MovingMean/N period calls, scoped refs (`i13[,qqq]>0`), AND/OR connective grouping, and coalesce fallback chains. | High |
| FR-11 | LLM fundamental data tables exist: `llm_guidance`, `llm_news`, `llm_regulatory`, `llm_product_dev`, `llm_analysis_sessions`. Advisors read these; LLM writes new findings. | High |
| FR-12 | Admin screen configures LLM provider chain: primary/secondary/fallback provider, model, API key, base URL per slot; fallback mode (failover/round_robin/primary_only). | High |
| FR-13 | Timing-aware backtesting captures day_of_week, day_of_month, period_of_month, month_of_year, near_month_end, near_options_expiry per trade; reports per-bucket win rate, return, turnover. | High |
| FR-14 | Each advisor has configurable timing preferences persisted in `advisor_accounts.profile_json`; running portfolios respect these preferences on each rebalance. | High |
| FR-15 | Market-cap and sector position limits apply in backtests and running portfolios: large position caps on small-cap names, sector concentration limits. | High |

### Non-Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| NFR-1 | Use existing schema where possible; avoid duplicate portfolio logic. | High |
| NFR-2 | Minimal UI changes; public flag implemented at data layer only. | High |
| NFR-3 | All new database objects are backward compatible with existing code. | High |
| NFR-4 | LLM admin screen requires admin role; API keys never exposed in UI or logs. | High |
| NFR-5 | Timing bucket aggregation queries must complete in < 5 seconds for a 1000-trade backtest. | Medium |

---

## Database Design

### New Tables

#### LLM Fundamental Data (FR-11)

```sql
CREATE TABLE IF NOT EXISTS llm_guidance (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  symbol VARCHAR(16) NOT NULL,
  guidance_text TEXT NOT NULL,
  source VARCHAR(128) NULL,
  source_date DATE NULL,
  sentiment ENUM('positive','negative','neutral') NOT NULL DEFAULT 'neutral',
  confidence TINYINT UNSIGNED NOT NULL DEFAULT 50,
  llm_model VARCHAR(64) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_llm_guidance_symbol (symbol),
  KEY idx_llm_guidance_date (source_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS llm_news (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  symbol VARCHAR(16) NOT NULL,
  headline VARCHAR(512) NOT NULL,
  source VARCHAR(128) NULL,
  event_date DATE NOT NULL,
  summary TEXT NULL,
  material_impact ENUM('none','low','medium','high') NOT NULL DEFAULT 'none',
  llm_analysis TEXT NULL,
  llm_model VARCHAR(64) NOT NULL,
  analyzed_at TIMESTAMP NULL,
  is_analyzed TINYINT(1) NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_llm_news_symbol (symbol),
  KEY idx_llm_news_date (event_date),
  KEY idx_llm_news_analyzed (is_analyzed)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS llm_regulatory (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  symbol VARCHAR(16) NOT NULL,
  event_type VARCHAR(64) NOT NULL,
  description TEXT NOT NULL,
  status ENUM('pending','approved','denied','withdrawn','unknown') NOT NULL DEFAULT 'pending',
  expected_date DATE NULL,
  actual_date DATE NULL,
  material_impact ENUM('none','low','medium','high') NOT NULL DEFAULT 'none',
  llm_analysis TEXT NULL,
  llm_model VARCHAR(64) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_llm_regulatory_symbol (symbol),
  KEY idx_llm_regulatory_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS llm_product_dev (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  symbol VARCHAR(16) NOT NULL,
  product_name VARCHAR(256) NOT NULL,
  stage VARCHAR(64) NULL,
  description TEXT NULL,
  expected_date DATE NULL,
  actual_date DATE NULL,
  material_impact ENUM('none','low','medium','high') NOT NULL DEFAULT 'none',
  llm_analysis TEXT NULL,
  llm_model VARCHAR(64) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_llm_pd_symbol (symbol),
  KEY idx_llm_pd_expected (expected_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS llm_analysis_sessions (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  session_id VARCHAR(64) NOT NULL,
  trigger ENUM('scheduled','manual','advisor','backtest') NOT NULL,
  symbols_analyzed INT UNSIGNED NOT NULL DEFAULT 0,
  total_findings INT UNSIGNED NOT NULL DEFAULT 0,
  findings_written INT UNSIGNED NOT NULL DEFAULT 0,
  provider_used VARCHAR(64) NULL,
  model_used VARCHAR(64) NULL,
  started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at TIMESTAMP NULL,
  error TEXT NULL,
  PRIMARY KEY (id),
  KEY idx_llm_sessions_trigger (trigger),
  KEY idx_llm_sessions_started (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### Timing Data (FR-16)

The existing `timing_buckets` table is extended with new timing dimension columns (see `docs/architecture/architecture-document.md` §3.5). The `advisor_accounts.profile_json` stores per-advisor timing preferences.

---

## Advisor Strategy Mapping

| Advisor | Strategy module | Frequency | Picking method | Timing |
|---|---|---|---|---|
| warren-buffet | value_investor | monthly | Hand-coded `IStrategy` | Monthly, mid-period preferred |
| peter-lynch | grow_at_reasonable_price | weekly | Hand-coded `IStrategy` | Weekly, Thursday entry preferred |
| index-canada | cdn_index | bi_annual | Index weights, no picking | Bi-annual rebalance |
| index-usa | us_index | bi_annual | Index weights, no picking | Bi-annual rebalance |
| index-euro | euro_index | bi_annual | Index weights, no picking | Bi-annual rebalance |
| index-cad-us | cad_us_balanced_index | bi_annual | Index weights, no picking | Bi-annual rebalance |
| index-energy | sector_index_energy | monthly | Sector index, no picking | Monthly |
| index-essentials | sector_index_essentials | monthly | Sector index, no picking | Monthly |
| index-tech | sector_index_tech | monthly | Sector index, no picking | Monthly |
| index-bio | sector_index_bio | monthly | Sector index, no picking | Monthly |
| aggressive-day-trader | momentum_day | daily | Hand-coded momentum + LLM news | Daily, avoid month-end |
| weekly-trader | swing | weekly | RW formula or hand-coded | Weekly, Tuesday exit preferred |
| monthly-trader | position | monthly | RW screen import or hand-coded | Monthly, mid-month entry |
| bi-annual-trader | long_hold | bi_annual | Long-hold quality screen | Bi-annual |
| zacks-rw-1 | rw_screen_1 | weekly | RW .und screen import | Weekly |
| zacks-rw-2 | rw_screen_2 | monthly | RW .und screen import | Monthly |
| llm-strategic | llm_strategic | monthly | LLM fundamental analysis + hand-coded | Monthly, LLM timing-aware |

---

## Execution Rules

- For any daily-bar strategy, execution price = mid price = (high + low + close) / 3 unless only close/open exist, then use day mid price approximation.
- All buys/sells reserve cash in portfolio `portfolio` table by updating cash position; sell first before buy.
- Timing preferences: if an advisor has `preferred_entry_day` set, the rebalance only executes on that day-of-week (or nearest available). If `avoid_month_end_entry` is true, entries within 3 days of month-end are skipped.
- Market-cap limits: if `max_position_pct_of_micro_cap` is set in profile_json, any single position in a stock with market cap < $300M is capped at that percentage of portfolio.
- Sector limits: if `max_sector_pct` is set, no single sector may exceed that percentage of portfolio.

---

## LLM Admin Screen (FR-11.6 / BR-16)

### Settings

The admin screen (`?action=admin_settings&tab=llm`) exposes the following settings, stored in `system_settings`:

| Setting key | Type | Purpose |
|---|---|---|
| `llm_primary_provider` | string | Primary LLM provider (openrouter, openai, ollama, custom) |
| `llm_primary_model` | string | Primary model name (e.g. anthropic/claude-sonnet-4) |
| `llm_primary_key` | password | Primary API key |
| `llm_primary_url` | string | Primary base URL (e.g. https://api.openrouter.ai/v1) |
| `llm_secondary_provider` | string | Secondary LLM provider (fallback) |
| `llm_secondary_model` | string | Secondary model name |
| `llm_secondary_key` | password | Secondary API key |
| `llm_secondary_url` | string | Secondary base URL |
| `llm_fallback_provider` | string | Fallback LLM provider (local Ollama) |
| `llm_fallback_model` | string | Fallback model name (e.g. qwen3.5:latest) |
| `llm_fallback_key` | password | Fallback API key (if required) |
| `llm_fallback_url` | string | Fallback base URL (e.g. http://localhost:11434) |
| `llm_fallback_mode` | string | Failover mode: failover, round_robin, primary_only |
| `llm_analysis_schedule` | string | Cron schedule for LLM fundamental analysis (e.g. daily, weekly) |

### LLMService Refactoring

`LLMService` must be refactored to:
1. Maintain a prioritized list of provider configs from settings
2. Attempt completion on primary; on failure/rate-limit (HTTP 429), try secondary; then fallback
3. Track which provider served each request (`provider_used` in response and in `llm_analysis_sessions`)
4. Expose `getActiveProvider()` for logging/debugging
5. Support the `llm_fallback_mode`:
   - `failover`: try primary → secondary → fallback on failure
   - `round_robin`: cycle through providers on each request
   - `primary_only`: only use primary; no fallback

---

## LLM Fundamental Data Flow

```
Scheduled (or advisor-triggered) LLM analysis run:
1. Start session in llm_analysis_sessions (trigger='scheduled')
2. Read all unanalyzed rows from llm_news (is_analyzed=0)
3. Read recent guidance/regulatory/product_dev entries not yet analyzed
4. For each item, call LLM with context (symbol, sector, current scores, item details)
5. LLM returns: material_impact, suggested_action, reasoning
6. Store analysis in llm_analysis fields; mark is_analyzed=1
7. If LLM discovers new items not in tables, write them to llm_news/llm_guidance/etc.
8. Update llm_analysis_sessions with counts and provider_used
9. Commit session

Advisor picking:
1. Advisor strategy scores candidates using standard indicators
2. LLM fundamental overlay: for each candidate, read llm_guidance (ポジティブ/negative sentiment), llm_news (recent material_impact), llm_regulatory (pending approvals), llm_product_dev (upcoming milestones)
3. Adjust score: positive guidance + high material news → boost; pending adverse regulatory → reduce; upcoming product launch → boost
4. Final score = base_score × (1 + llm_overlay_factor)
5. Pick top N by final score; write advisor_trades
```

---

## Timing-Aware Trading Flow

```
Backtest engine (timing-aware):
1. For each rebalance date in the simulation:
   a. If advisor has timing preferences, check if date matches preferred entry day/period
   b. If not preferred, skip this rebalance (hold existing positions) or use fallback timing
   c. Run picking strategy to get candidate symbols
   d. Apply market-cap and sector limits
   e. For each trade, record timing dimensions in timing_buckets:
      - day_of_week, day_of_month, period_of_month, month_of_year
      - near_month_end, near_options_expiry
   f. Execute trades; record outcome
2. After simulation, aggregate timing_buckets by bucket type:
   - Win rate by day_of_week (Mon-Fri)
   - Average return by period_of_month (early/mid/late)
   - Win rate by near_month_end / near_options_expiry
3. Store aggregated results in backtest run metadata
4. Report best/worst timing buckets to advisor tuning UI

Running advisor portfolio:
1. On each rebalance, check advisor timing preferences
2. If date doesn't match preferred timing, skip or use fallback
3. Execute trades; record timing dimensions in advisor_trades (via timing_buckets extension)
4. Accumulate timing-aware running stats in advisor_runs.result_json
```

---

## Implementation Approach

1. Add LLM fundamental data tables (migration script)
2. Add LLM admin screen tab to `AdminSettingsController` (new settings + save logic)
3. Refactor `LLMService` for multi-provider fallback chain
4. Build `LLMFundamentalAnalyzer` (Python) — reads unanalyzed items, calls LLM, writes findings
5. Add `RwFormulaParser` integration to advisor picking pipeline (PHP: `RwFormulaService`; Python: `rw_formula_engine.py`)
6. Extend `timing_buckets` table with timing dimension columns (migration script)
7. Build `TimingService` (PHP) for timing preference management and aggregation
8. Refactor backtest engine to capture timing dimensions and report per-bucket performance
9. Add timing preferences to `advisor_accounts.profile_json` and respect in running portfolios
10. Add market-cap and sector position limits to backtest and running portfolio engines
11. Add timing performance API endpoint (`/api/timing/performance`)
12. Add LLM analysis API endpoint (`/api/llm/analyze`)

---

## Research Wizard Formula Integration (FR-12)

### Formula Syntax

The `RwFormulaParser` (from `ksfraser/research-wizard-reader`) parses formulas like:

```
# Field ref with time-lag offset
i95 > i95[Recent-4Q]

# MovingMean period call
MovingMean2(i5) > MovingMean4(i5)

# Scoped reference (compare to index)
i13[,qqq] > 0

# AND/OR connective grouping
i22 >= i22[Recent-1W] And i22[Recent-1W] >= i22[Recent-2W]

# Coalesce fallback chain
(1/(i192=1)) | (3/(i192=2)) | (5.5/(i192=3))
```

### Binding to Live Data

`ZacksFieldResolver::spec()` maps each RW field code to a live data source:
- `source`: which dataset (base, price, fund, win, vol20, formula)
- `key`: which column/field in that dataset
- `approx`: whether the binding is an approximation of the RW semantic

Fields absent from SPECS are skipped with a report, not silently ignored.

### Advisor Picking with Formulas

1. Advisor strategy defines picking criteria as a formula string (e.g. `i158 + 0.75*i159 > 50`)
2. `RwFormulaParser::parse()` produces an AST
3. `ZacksFieldResolver` binds each field code in the AST to a live data source
4. For each candidate symbol, the formula engine evaluates the AST against the symbol's data
5. Symbols that satisfy the formula are selected; formulas referencing unavailable fields are skipped with a report
6. The advisor's `profile_json` stores the formula string and which fields it references, so the UI can show what data the advisor needs

---

## Public Exposure Rules

- Public route `/advisors/{slug}` or equivalent should expose:
  - Current holdings
  - Trade history
  - Run history
  - Timing preferences (if any)
  - LLM analysis summary (if advisor uses LLM)
- Hidden fields for regular users should continue to remain private unless explicitly public.

---

## Implementation Approach

1. Add the SQL migration for LLM fundamental data tables
2. Add bootstrap script to create advisor users and cash start position
3. Add advisor strategy engine to run scheduled simulations
4. Add LLM admin screen tab to AdminSettingsController
5. Refactor LLMService for fallback chain
6. Build LLMFundamentalAnalyzer
7. Integrate RwFormulaParser into advisor picking
8. Extend timing_buckets and build TimingService
9. Refactor backtest engine for timing-aware simulation
10. Add timing + LLM API endpoints
