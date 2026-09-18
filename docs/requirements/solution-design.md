# Solution Design Document
## KSF Stock Market Analysis System
### BABOK Format -- Solution Architecture

---

## 1. Architecture Overview

**Pattern**: Hybrid PHP + Python + MariaDB

```
[Browser] -> [Apache 2.4 + PHP 8.1] -> [MariaDB 10.6+]
                v mod_proxy
           [Python Flask :5000]
                v
           [yfinance / TA-Lib / LLM]
```

## 2. Database Design

### 2.1 Partitioning Strategy
- **stockprices**, **daily_indicators**, **daily_tier2**, **ta_values**: Partitioned by `YEAR(price_date)`
- 10 partitions covering 2008-2026+ (~8-10 years of data per partition)
- Partition pruning for backtest queries (WHERE on date range -> only relevant partitions scanned)
- Per-year backup via `mysqldump --where "YEAR(date)=2025"`

### 2.2 Three-Tier Indicator Architecture

|| Tier | When | How | Storage | Indicators |
|---|---|---|---|---|---|
| 1 | Per INSERT | MySQL trigger | Wide columns in `daily_indicators` | daily_return, gap, SMA-20/50/200, vol_sma_20 |
| 2 | Daily batch | MySQL event (window functions) | Wide columns in `daily_tier2` | Bollinger, ATR-14, vol ratios, trend |
| 3 | Daily batch | Python cron (TA-Lib vectorized) | Name-value in `ta_values` | RSI, MACD, candlestick patterns, custom |

**Rationale**: 
- Tier 1 is O(1) per row -- cheap enough for trigger
- Tier 2 needs 14-20 row window -- expensive per insert, cheap once daily
- Tier 3 needs full array (250+ rows) -- only efficient as batch vectorized operation

### 2.3 Scoring System Design

10 scoring tables preserved from legacy, enhanced with LLM integration:

|| Table | Purpose | LLM Role |
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

### 2.4 Signal Weight Correlation Design

**Problem**: Signals fire at different times -- some lead, some lag, some coincide.

**Solution**: `signal_weights` table tracks correlation and lead/lag:
- `avg_lead_days`: Days between signal and price move (+ leads, - lags)
- `is_pre_indicator`: 1 if signal consistently leads
- `correlation`: Correlation with future 5-day return
- `correlates_with`: JSON of correlated signals with lag times
- `weight_boosted`: Effective weight when pre-indicator confirmed

**Boost Formula**:
```
effective_weight = base_weight x (1 + correlation x 0.5) x recency_factor
```

**Example**: RSI_OVERSOLD (55% win rate alone) -> 1.36x weight when MACD_CROSS hasn't confirmed (78% win rate for sequence).

## 3. Application Design

### 3.1 PHP Layer
- PSR-4 autoloading under `Ksf\StockMarket\`
- Front controller pattern (index.php dispatcher)
- Twig templates
- PDO for database access
- PythonBridge HTTP client to Flask API
- Admin settings screen for LLM config (FR-13)

### 3.2 Python Layer
- Flask REST API on :5000
- TA-Lib for vectorized indicator calculation
- pandas for data manipulation
- yfinance for market data
- LLM integration for qualitative scoring
- Cron jobs for daily processing
- LLM Fundamental Analyzer service (FR-11)
- Research Wizard Formula Parser service (FR-12)
- Timing-aware backtest engine (FR-16)

### 3.3 Data Flow

```
Daily Processing Flow:
1. Market closes (4 PM ET)
2. yfinance fetches latest prices -> stockprices (trigger fires Tier 1)
3. MySQL event runs Tier 2 (window functions)
4. Python cron runs Tier 3 (TA-Lib vectorized batch)
5. Python cron runs scoring analysis (LLM + fundamental)
6. Python cron updates signal_weights (correlation analysis)
7. Results available for UI and monitoring
```

### 3.4 LLM Fundamental Analysis Data Flow (NEW -- FR-11)

```
LLM Fundamental Analysis Flow:
1. LLM-enabled advisor starts analysis session
2. Reads llm_insider_trading, llm_news_events, llm_product_dev, llm_regulatory tables for target symbols
3. Fetches current news/guidance/regulatory data from external sources (if enabled)
4. LLM analyzes: forward guidance changes, news sentiment, product lifecycle stage, regulatory status
5. Updates tables with new findings (inserts new events, updates conviction scores)
6. Produces investment thesis summary with conviction score
7. Coordinates with scoring tables (evalsummary, evalbusiness, evalmanagement, evalvalue)
8. Results feed into backtest and recommendation engines
```

### 3.5 Research Wizard Formula Integration Data Flow (NEW -- FR-12)

```
RW Formula Integration Flow:
1. User (or advisor config) selects/pastes RW pre-defined filter formula
2. Formula parser validates syntax and resolves field references to DB columns
3. Parser produces executable filter conditions (SQL WHERE or Python filter chain)
4. Advisor loads formula as its screening criteria
5. On screener run: parser executes against symbol_master + scoring tables
6. Results cached per run (FR-12.4)
7. UI formula editor allows preview of matching stocks before saving
```

### 3.6 External Provider Auth Architecture

**Pattern**: OAuth 2.0 Authorization Code + PKCE-ready

```
[Browser] -> [Apache/PHP] -> Reddit OAuth endpoint
                v
         [Callback handler]
                v
         [external_auth_tokens DB]
                v
         [research_agent.py reads token]
                v
         [Authenticated Reddit API]
```

**Security**:
- Client secrets stored as `password` type in `system_settings`
- Access/refresh tokens stored as `password` semantics in `external_auth_tokens`
- Never logged -- controller uses `[REDACTED]` in all error messages
- Unique per user/provider -- supports multi-user token isolation

**Extensibility**:
- Add new provider by extending `ExternalAuthController::$map` (scopes, endpoints)
- Register new provider in `external_auth.json`
- Admin adds credentials via Admin Settings

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

### Phase 5: Paperclip Zero-Human Trading Firm (2026-07)
- Research Agent: internal + external brief generation
- Risk Gate: pre-trade Sharpe/drawdown checks
- External Provider Auth: Reddit OAuth, TradingView/arXiv API keys
- Hermes Skill + Nightly Cron: automated brief generation at 02:00
- Paper-only execution via advisor_backtest.php

### Phase 6: LLM Fundamental Analysis + RW Formula Integration + Timing-Aware Backtesting (NEW -- 2026-09-18)

#### 6.1 LLM Fundamental Analysis Tables (FR-11)
- Create 4 new tables: `llm_insider_trading`, `llm_news_events`, `llm_product_dev`, `llm_regulatory`
- Each table: `id, symbol, event_date, as_of, source, headline, details, confidence, conviction_score, is_verified, created_at, updated_at`
- Backfill existing known events from historical data (earnings surprises, product launches, regulatory actions)
- Wire LLM advisor reads to these tables at session start
- Wire LLM advisor writes to update tables when new info found

#### 6.2 Research Wizard Formula Parser (FR-12)
- Implement RW formula parser: GT, LT, GTE, LTE, EQ, NEQ, AND, OR, parentheses, field refs, literals
- Field reference resolver: map RW field names to DB columns / computed values
- Formula cache per screener run
- Formula editor UI: paste/select formula, preview matching stocks

#### 6.3 Timing-Aware Backtest Extension (FR-16)
- Extend backtest engine to accept timing configurations:
  - `entry_day_of_week`: preferred day for entries (0=Monday ... 4=Friday)
  - `exit_day_of_week`: preferred day for exits
  - `entry_week_of_month`: week-of-month bias for entries (1=first ... 5=last)
  - `exit_week_of_month`: week-of-month bias for exits
  - `market_cap_position_limit`: base position % scaled by market cap tier
  - `sector_rotation_enabled`: whether sector momentum timing is active
- Backtest engine reports: win rate, Sharpe, max drawdown, total return by timing scenario
- Advisor control plane exposes timing preferences per advisor

#### 6.4 LLM Admin Screen (FR-13)
- Admin UI: `/admin/llm-console` (or `?action=admin&view=llm-config`)
- Fields: primary_url, primary_model, primary_token, secondary_url, secondary_model, secondary_token, fallback_url, fallback_model, fallback_token
- Per-advisor LLM profile dropdown (maps advisor -> LLM config set)
- Connection health test button (ping each endpoint, report latency/success)
- Credential storage: hashed/encrypted, never logged

## 5. Security Design

### 5.1 Authentication & Authorization
- User authentication via username/password (bcrypt/argon2 hashing)
- RBAC: admin, trader, viewer roles
- Session management with secure cookies
- API token authentication for Python service

### 5.2 Data Security
- PDO prepared statements (SQL injection prevention)
- Twig auto-escaping (XSS prevention)
- Password fields stored as hashed values
- No plaintext credentials in logs or code
- HTTPS required in production

### 5.3 LLM Credential Security (NEW -- FR-13.5)
- LLM API tokens stored encrypted in `system_settings` (password-type DB fields)
- Tokens never logged -- `[REDACTED]` in all error messages and logs
- Admin screen requires admin role to access
- Fallback chain tested without exposing tokens

## 6. LLM Fundamental Analysis Design (NEW -- FR-11)

### 6.1 LLM-Enabled Advisor Architecture

```
                    ++++++++++++++++++++++++++++
                    +   LLM-Enabled Advisor     +
                    +   (fundamental analyst)   +
                    ++++++++++++++++++++++++++++
                                 + reads
                    +++++++++++++v++++++++++++++
                    +  llm_* tables (4 tables)  +
                    +  - insider_trading         +
                    +  - news_events             +
                    +  - product_dev             +
                    +  - regulatory              +
                    ++++++++++++++++++++++++++++
                                 + fetches
                    +++++++++++++v++++++++++++++
                    +  External Sources         +
                    +  - News APIs              +
                    +  - SEC filings            +
                    +  - Regulatory databases   +
                    +  - Product announcements  +
                    ++++++++++++++++++++++++++++
                                 + analyzes
                    +++++++++++++v++++++++++++++
                    +  LLM Service              +
                    +  (primary -> secondary ->   +
                    +   fallback chain)         +
                    ++++++++++++++++++++++++++++
                                 + produces
                    +++++++++++++v++++++++++++++
                    +  Conviction Scores +      +
                    +  Investment Thesis        +
                    +  (updates llm_* tables)   +
                    ++++++++++++++++++++++++++++
                                 + feeds
                    +++++++++++++v++++++++++++++
                    +  Scoring Tables +          +
                    +  Backtest Engine           +
                    +++++++++++++++++++++++++++++
```

### 6.2 LLM Table Schemas

**llm_insider_trading**:
```sql
CREATE TABLE llm_insider_trading (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    event_date DATE NOT NULL,
    as_of DATE NOT NULL,
    source VARCHAR(255),
    headline VARCHAR(500),
    details TEXT,
    confidence TINYINT UNSIGNED,  -- 0-100
    conviction_score DECIMAL(5,2), -- -100 to +100
    is_verified TINYINT UNSIGNED DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_symbol_date (symbol, event_date),
    INDEX idx_conviction (conviction_score)
);
```

**llm_news_events**:
```sql
CREATE TABLE llm_news_events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    event_date DATE NOT NULL,
    as_of DATE NOT NULL,
    source VARCHAR(255),
    headline VARCHAR(500),
    details TEXT,
    category ENUM('earnings', 'product_launch', 'regulatory', 'executive', 'financial', 'market', 'other'),
    confidence TINYINT UNSIGNED,
    sentiment_score DECIMAL(5,2), -- -100 to +100
    conviction_score DECIMAL(5,2), -- -100 to +100
    is_verified TINYINT UNSIGNED DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_symbol_date (symbol, event_date),
    INDEX idx_category (category)
);
```

**llm_product_dev**:
```sql
CREATE TABLE llm_product_dev (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    product_name VARCHAR(255),
    lifecycle_stage ENUM('concept', 'prototype', 'production_rollout', 'market_launch', 'modification', 'end_of_life') NOT NULL,
    event_date DATE NOT NULL,
    as_of DATE NOT NULL,
    source VARCHAR(255),
    headline VARCHAR(500),
    details TEXT,
    expected_impact ENUM('positive', 'neutral', 'negative'),
    confidence TINYINT UNSIGNED,
    conviction_score DECIMAL(5,2),
    is_verified TINYINT UNSIGNED DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_symbol_stage (symbol, lifecycle_stage),
    INDEX idx_date (event_date)
);
```

**llm_regulatory**:
```sql
CREATE TABLE llm_regulatory (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    event_date DATE NOT NULL,
    as_of DATE NOT NULL,
    source VARCHAR(255),
    headline VARCHAR(500),
    details TEXT,
    regulatory_type ENUM('approval', 'pending_review', 'industry_change', 'compliance_action', 'investigation', 'other'),
    jurisdiction VARCHAR(100),
    status ENUM('approved', 'pending', 'rejected', 'withdrawn', 'ongoing'),
    confidence TINYINT UNSIGNED,
    conviction_score DECIMAL(5,2),
    is_verified TINYINT UNSIGNED DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_symbol_type (symbol, regulatory_type),
    INDEX idx_date (event_date)
);
```

### 6.3 LLM Fundamental Analyzer Service

The LLM Fundamental Analyzer is a Python service that:

1. **Reads** the 4 llm_* tables for target symbols at session start
2. **Fetches** current data from external sources (news APIs, SEC EDGAR, regulatory databases)
3. **Analyzes** using LLM (primary -> secondary -> fallback chain):
   - Forward guidance changes vs. prior guidance
   - News sentiment and conviction
   - Product lifecycle stage transitions
   - Regulatory approval/pending status
4. **Updates** llm_* tables with new findings (new rows + conviction score updates)
5. **Produces** investment thesis summary (1-3 paragraphs) with conviction score (-100 to +100)
6. **Coordinates** with scoring tables: updates evalsummary.llm_recommendation, evalbusiness, evalmanagement, evalvalue

### 6.4 LLM Fallback Chain

```
Primary LLM Endpoint (configured URL + model + token)
       v (timeout / error / rate limit / 5xx)
Secondary LLM Endpoint (configured URL + model + token)
       v (timeout / error / rate limit / 5xx)
Fallback LLM Endpoint (configured URL + model + token)
       v (all failed)
Return error / use cached data / skip analysis
```

Admin screen (FR-13) configures the 3 endpoints and per-advisor assignment.

## 7. Research Wizard Formula Integration Design (NEW -- FR-12)

### 7.1 Formula Syntax

Research Wizard pre-defined filters use a simple declarative syntax:

```
// Comparison operators
price GT 10          // price > 10
price LT 50          // price < 50
price GTE 25         // price >= 25
price LTE 100        // price <= 100
price EQ 30          // price = 30
price NEQ 0          // price != 0

// Logical operators
AND, OR, NOT, (, )

// Field references (resolved to DB columns / computed values)
price, open, high, low, close, volume, avg_volume
market_cap, pe_ratio, eps, dividend_yield, beta
sma_50, sma_200, rsi_14, macd, bollinger_upper, bollinger_lower
zacks_rank, zacks_consensus, zacks_eps_change

// Literals
10, 50.5, "string", TRUE, FALSE

// Examples from RW pre-defined filters:
// "Stock Price > 10" -> price GT 10
// "Price to Sales Ratio < 1.5" -> price_to_sales LT 1.5
// "Relative Volume > 1.5" -> relative_volume GT 1.5
```

### 7.2 Formula Parser Design

```
Input: RW formula string
  v
Lexer: tokenize into tokens (FIELD, OP, LITERAL, LOGIC, PAREN)
  v
Parser: build AST from tokens
  v
Resolver: map field names to DB columns / computed values
  v
Code generator: produce executable filter (SQL WHERE clause or Python lambda)
  v
Cache: store parsed result per formula hash (FR-12.4)
```

### 7.3 Field Reference Resolution

|| RW Field Name | DB Source / Computation |
|---|---|---|
| price | stockprices.close (latest) |
| open, high, low | stockprices (latest bar) |
| volume | stockprices.volume (latest) |
| avg_volume | Computed: AVG(volume) over lookback |
| market_cap | symbol_master.market_cap or computed |
| pe_ratio | Computed: close / eps or from fundamentals |
| eps | fundamentals.eps or zacks_eps |
| dividend_yield | Computed: annual_dividend / price |
| beta | Computed or from symbol_master |
| sma_50, sma_200 | daily_indicators or ta_values |
| rsi_14 | ta_values |
| macd | ta_values |
| bollinger_upper, bollinger_lower | daily_tier2 |
| zacks_rank | zacks_broker_recommendations or zacks_rank |
| zacks_consensus | zacks_broker_recommendations |
| zacks_eps_change | fundamentals.zacks_eps_change_f1_4w |

### 7.4 Advisor Integration

Each newsletter-style advisor (FR-14) can adopt an RW formula as its screening criteria:

```python
class RwFormulaAdvisor:
    def __init__(self, formula_text, trade_day="Monday"):
        self.parser = RwFormulaParser()
        self.filter = self.parser.parse(formula_text)
        self.trade_day = trade_day
    
    def screen(self, universe):
        """Return stocks matching the RW formula."""
        return self.filter.evaluate(universe)
    
    def pick(self, screen_results, portfolio):
        """Pick from screened stocks using advisor's trade logic."""
        # ... advisor-specific pick logic ...
```

### 7.5 Performance Targets (NEW -- Sec.7.5)

- Formula parse: < 100ms per formula (one-time cost, cached)
- Formula evaluate (screen 2000 symbols): < 30 seconds
- Formula cache hit: < 5 seconds for full screen
- Formula editor preview (UI): < 5 seconds for preview

## 8. Timing-Aware Trading Design (NEW -- FR-16)

### 8.1 Timing Variables

| Variable | Scope | Description |
|---|---|---|
| `entry_day_of_week` | Per-advisor | Day of week to prefer for entries (0=Mon ... 4=Fri) |
| `exit_day_of_week` | Per-advisor | Day of week to prefer for exits |
| `entry_week_of_month` | Per-advisor | Week-of-month bias for entries (1=first ... 5=last) |
| `exit_week_of_month` | Per-advisor | Week-of-month bias for exits |
| `market_cap_position_limit` | Per-advisor | Base position % scaled by market cap tier (e.g., large cap = 5%, small cap = 2%) |
| `sector_rotation_enabled` | Per-advisor | Whether sector momentum timing signals are active |

### 8.2 Backtest Engine Extension

The backtest engine (`src/backtest/optimize.py`, `five_year_backtest.py`) extends to:

1. **Accept timing configuration** per advisor/scenario
2. **Filter trades** by timing rules:
   - Only allow entries on preferred entry day (or within N days of it)
   - Only allow exits on preferred exit day
   - Only allow entries during preferred week-of-month
3. **Apply market-cap-aware position sizing**:
   - Compute market cap tier for each stock (micro < $300M, small < $2B, mid < $10B, large >= $10B)
   - Scale position % by tier (capped at advisor max)
4. **Apply sector rotation timing** (if enabled):
   - Compute sector momentum (e.g., 50-day SMA of sector ETF)
   - Only allow entries in sectors with confirmed momentum
   - Reduce/exit positions in sectors with fading momentum
5. **Report** per-scenario metrics:
   - Win rate, Sharpe ratio, max drawdown, total return
   - By timing configuration (so user can compare scenarios)

### 8.3 Timing Optimization

Backtest engine supports scanning timing configurations:

```python
# Example: scan day-of-week for entries
for entry_dow in range(5):  # Mon-Fri
    for exit_dow in range(5):
        config = TimingConfig(entry_dow=entry_dow, exit_dow=exit_dow)
        result = backtest.run(config=config)
        results.append((entry_dow, exit_dow, result.sharpe, result.win_rate))
```

## 9. LLM Admin Screen Design (NEW -- FR-13)

### 9.1 Admin Screen Layout

```
URL: /admin/llm-config (or ?action=admin&view=llm-config)
Role: admin only

+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
+ LLM Provider Configuration                                    +
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
+ Primary Endpoint                                              +
+   URL:    [_________________________]                        +
+   Model:  [_________________________]                        +
+   Token:  [_________________________]  (password field)     +
+   [Test Connection]                                           +
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
+ Secondary Endpoint (fallback)                                +
+   URL:    [_________________________]                        +
+   Model:  [_________________________]                        +
+   Token:  [_________________________]  (password field)     +
+   [Test Connection]                                           +
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
+ Fallback Endpoint (last resort)                              +
+   URL:    [_________________________]                        +
+   Model:  [_________________________]                        +
+   Token:  [_________________________]  (password field)     +
+   [Test Connection]                                           +
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
+ Per-Advisor LLM Profile Assignment                           +
+   [Advisor dropdown] -> [LLM config set dropdown]            +
+   [Add mapping] [Remove mapping]                             +
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
+ Connection Health Dashboard                                   +
+   Primary:    [OK] Online (120ms) / [FAIL] Offline (error)          +
+   Secondary:  [OK] Online (150ms) / [FAIL] Offline (error)          +
+   Fallback:   [OK] Online (200ms) / [FAIL] Offline (error)          +
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
```

### 9.2 Credential Storage

LLM tokens stored in `system_settings` table with `setting_type = 'llm_token'` and `value` encrypted. Never logged. Admin screen requires admin role. Test connection uses token but does not log it.

## 10. Change Log

- 2026-09-18: Added Sec.6 LLM Fundamental Analysis, Sec.7 RW Formula Integration, Sec.8 Timing-Aware Trading, Sec.9 LLM Admin Screen (FR-11, FR-12, FR-16, FR-13)
- 2026-07: Added Phase 5 (Paperclip Zero-Human Trading Firm: FR-7, FR-8, FR-9, FR-10)
