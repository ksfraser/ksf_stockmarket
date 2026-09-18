# Public-Facing AI Advisor Personas -- Requirements and Design

## Use Cases

### 1. Public Reference Portfolios
Show independent model portfolios run by personas that mimic known styles (Buffett, Lynch) and systematic strategies (index regions/sectors, day/week/month/bi-annual trading). Regular users can view them without logging in.

### 2. Simulation Evidence
Each advisor runs with the same portfolio tables as regular users, so results are comparable. Advisors start from the same initial conditions and execute trades via the same mechanics (mid-price fills on daily bars).

### 3. Strategy Comparison
Index advisors isolate regional/sector exposures. Trader advisors isolate frequency/time-horizon effects. This produces actionable comparison data.

### 4. LLM-Enhanced Fundamental Analysis (NEW -- 2026-09-18)
LLM-enabled advisors read forward guidance, news events, product development, and regulatory approval tracking tables to produce conviction scores and investment thesis summaries. Users can compare LLM-enhanced advisor performance against mechanical advisors.

### 5. Zacks / Research Wizard Formula-Based Advisors (NEW -- 2026-09-18)
Newsletter-style advisors each adopt a Research Wizard pre-defined filter formula as their stock-picking criteria. Users can compare different RW formula-based advisors against each other and against mechanical advisors.

### 6. Timing-Optimized Advisors (NEW -- 2026-09-18)
Advisors with day-of-week, day-of-month, market-cap-aware, and sector-rotation timing configurations. Users can compare timing-optimized advisors against default-timing advisors to find optimal entry/exit timing.

## Requirements

### Functional Requirements

#### FR-1 through FR-5 (Existing)
- FR-1 Each advisor is a user-level account with a portfolio in the `portfolio` table.
- FR-2 Advisor portfolios are public; regular user portfolios private by default.
- FR-3 Start date is fixed to 2025-01-02 with an initial cash balance of 100,000 CAD.
- FR-4 Advisor trades are priced at the day's mid price (approximate from open/high/low/close).
- FR-5 Strategy modules map to advisor accounts:
  - warren-buffet
  - peter-lynch
  - index-canada
  - index-usa
  - index-euro
  - index-cad-us
  - index-energy
  - index-essentials
  - index-tech

#### FR-6: LLM-Enhanced Fundamental Advisors (NEW -- 2026-09-18)
- FR-6.1 LLM-enabled advisors shall read `llm_insider_trading`, `llm_news_events`, `llm_product_dev`, `llm_regulatory` tables at session start.
- FR-6.2 LLM-enabled advisors shall produce conviction scores (-100 to +100) and investment thesis summaries (1-3 paragraphs).
- FR-6.3 LLM-enabled advisors shall update llm_* tables when new information is found during scanning.
- FR-6.4 LLM-enabled advisors shall operate within the LLM fallback chain (primary -> secondary -> fallback).
- FR-6.5 LLM-enabled advisors shall coordinate with scoring tables (evalsummary, evalbusiness, evalmanagement, evalvalue).

#### FR-7: Zacks / Research Wizard Formula Advisors (NEW -- 2026-09-18)
- FR-7.1 Newsletter-style advisors shall adopt RW pre-defined filter formulas as their stock-picking criteria.
- FR-7.2 RW formula parser shall interpret common RW syntax (GT, LT, GTE, LTE, EQ, NEQ, AND, OR, parentheses, field refs, literals).
- FR-7.3 Formula results shall be cached per screener run for performance.
- FR-7.4 Formula editor UI shall allow users to paste or select RW formulas and preview matching stocks.
- FR-7.5 Each advisor may use a different RW formula for stock screening.

#### FR-8: Timing-Aware Advisors (NEW -- 2026-09-18)
- FR-8.1 Advisors shall expose day-of-week timing preference (entry day, exit day).
- FR-8.2 Advisors shall expose day-of-month timing preference (week-of-month bias for entry and exit).
- FR-8.3 Backtest engine shall report win rate / Sharpe / drawdown by timing scenario.
- FR-8.4 Market-cap-aware position sizing limits shall be supported (larger caps = larger positions, capped at advisor max).
- FR-8.5 Sector rotation timing signals shall be supported (buy sector when momentum confirmed, reduce when momentum fades).

#### FR-9: LLM Admin Screen (NEW -- 2026-09-18)
- FR-9.1 Admin screen shall configure LLM provider URLs (primary, secondary, fallback), model names, and API tokens.
- FR-9.2 Admin screen shall support per-advisor LLM profile assignment.
- FR-9.3 Admin screen shall display connection health status for each endpoint.
- FR-9.4 Fallback chain shall automatically route to secondary -> fallback when primary is unavailable.
- FR-9.5 All LLM credentials shall be stored securely (never logged in plaintext).

### Non-Functional Requirements

#### NFR-1: Performance
- LLM fundamental analysis per symbol: < 5 seconds (LLM call + DB update)
- RW formula screen (2000 symbols): < 30 seconds
- RW formula parse: < 100ms (one-time, cached)
- Timing backtest scan (all day-of-week combos): < 10 minutes
- Admin screen load: < 2 seconds

#### NFR-2: Reliability
- LLM fallback chain: automatic failover to secondary -> fallback
- RW formula cache: persistent across runs
- LLM table writes: idempotent (re-running analysis doesn't duplicate events)

#### NFR-3: Security
- LLM tokens never logged in plaintext
- Admin screen role-restricted (admin only)
- All LLM API calls over HTTPS

## Implementation Approach

### 1. Existing Infrastructure (Already in Place)
1. SQL migration for advisor accounts and portfolios.
2. Bootstrap script to create advisor users and cash start position.
3. Advisor strategy engine to run scheduled simulations.

### 2. LLM Fundamental Analysis (NEW)
1. Create 4 llm_* tables (llm_insider_trading, llm_news_events, llm_product_dev, llm_regulatory).
2. Implement LLM Fundamental Analyzer Python service (reads llm_* tables, fetches external data, analyzes via LLM, updates tables, produces conviction scores + thesis).
3. Wire LLM fallback chain (primary -> secondary -> fallback).
4. Integrate with scoring tables (evalsummary, evalbusiness, evalmanagement, evalvalue).
5. Write tests (UT-11-llm-fundamental-data.md).

### 3. Research Wizard Formula Integration (NEW)
1. Implement RW formula parser (lexer -> parser -> AST -> code generator).
2. Implement field reference resolver (map RW field names to DB columns / computed values).
3. Implement formula cache per screener run.
4. Implement formula editor UI (paste/select formula, preview matching stocks).
5. Wire newsletter-style advisors to adopt RW formulas.
6. Write tests (UT-12-rw-formula-advisors.md).

### 4. Timing-Aware Backtesting (NEW)
1. Extend backtest engine to accept timing configurations (entry/exit day-of-week, week-of-month, market-cap position limits, sector rotation).
2. Implement timing filter in trade execution (only allow entries/exits on preferred days/weeks).
3. Implement market-cap-aware position sizing.
4. Implement sector rotation timing signals.
5. Backtest engine reports per-scenario metrics (win rate, Sharpe, drawdown, total return).
6. Write tests (UT-16-timing-backtesting.md).

### 5. LLM Admin Screen (NEW)
1. Create admin screen UI (/?action=admin&view=llm-config).
2. Implement LLM config CRUD (primary/secondary/fallback URL, model, token).
3. Implement per-advisor LLM profile assignment.
4. Implement connection health dashboard (ping each endpoint, report latency/success).
5. Secure credential storage (encrypted in system_settings, never logged).
6. Write tests (UT-11-06-llm-admin-console.md).

## Source Material
- `docs/requirements/FR-11-llm-fundamental-data.md` -- LLM fundamental data tables requirement
- `docs/requirements/FR-12-rw-formula-integration.md` -- RW formula integration requirement
- `docs/requirements/FR-13-llm-admin-screen.md` -- LLM admin screen requirement
- `docs/requirements/FR-16-timing-variables.md` -- Timing variables requirement
- `docs/requirements/UT-11-llm-fundamental-data.md` -- LLM fundamental data test outline
- `docs/requirements/UT-12-rw-formula-advisors.md` -- RW formula advisors test outline
- `docs/requirements/UT-16-timing-backtesting.md` -- Timing backtesting test outline
- `docs/requirements/UT-11-06-llm-admin-console.md` -- LLM admin console test outline
- `docs/architecture/architecture-document.md` Sec.10.5-Sec.10.8 -- Architecture sections for LLM, RW, timing, admin
- `docs/requirements/solution-design.md` Sec.6-Sec.9 -- Solution design sections
- `docs/architecture/stock-filter-engine.md` Sec.11 -- RW formula integration details
