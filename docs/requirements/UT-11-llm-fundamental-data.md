# Unit Test Outline: UT-11 — LLM Fundamental Data

## Requirement Coverage
- FR-11: LLM Fundamental Data Tables
- BR-9: LLM-Enhanced Fundamental Analysis

## Preconditions
- Test database with `llm_insider_trading`, `llm_news_events`, `llm_product_dev`, `llm_regulatory` tables created
- Test symbol data in `symbol_master`
- LLM service mock or stub (no real LLM API calls in unit tests)

## Test Cases

### TC-11-01: Create llm_insider_trading table
**Given** a fresh test database
**When** the migration creates the `llm_insider_trading` table
**Then** the table exists with all columns: id, symbol, event_date, as_of, source, headline, details, confidence, conviction_score, is_verified, created_at, updated_at
**And** indexes on (symbol, event_date) and (conviction_score) exist

### TC-11-02: Create llm_news_events table
**Given** a fresh test database
**When** the migration creates the `llm_news_events` table
**Then** the table exists with all columns including category ENUM
**And** indexes on (symbol, event_date) and (category) exist

### TC-11-03: Create llm_product_dev table
**Given** a fresh test database
**When** the migration creates the `llm_product_dev` table
**Then** the table exists with lifecycle_stage ENUM('concept','prototype','production_rollout','market_launch','modification','end_of_life')
**And** indexes on (symbol, lifecycle_stage) and (event_date) exist

### TC-11-04: Create llm_regulatory table
**Given** a fresh test database
**When** the migration creates the `llm_regulatory` table
**Then** the table exists with regulatory_type and status ENUMs
**And** indexes on (symbol, regulatory_type) and (event_date) exist

### TC-11-05: Insert and read llm_insider_trading row
**Given** the `llm_insider_trading` table exists
**When** a row is inserted for symbol 'AAPL' with event_date '2026-01-15'
**Then** the row can be read back by symbol
**And** conviction_score is stored as DECIMAL(5,2)
**And** is_verified defaults to 0

### TC-11-06: Insert and read llm_news_events row
**Given** the `llm_news_events` table exists
**When** a row is inserted with category 'earnings'
**Then** the row can be read back by symbol and category
**And** sentiment_score and conviction_score are stored correctly

### TC-11-07: Insert and read llm_product_dev row
**Given** the `llm_product_dev` table exists
**When** a row is inserted with lifecycle_stage 'market_launch'
**Then** the row can be read back by symbol and lifecycle_stage
**And** expected_impact is stored correctly

### TC-11-08: Insert and read llm_regulatory row
**Given** the `llm_regulatory` table exists
**When** a row is inserted with regulatory_type 'approval' and status 'approved'
**Then** the row can be read back by symbol and regulatory_type
**And** jurisdiction is stored correctly

### TC-11-09: LLM advisor reads all four tables by symbol
**Given** rows exist in all four llm_* tables for symbol 'MSFT'
**When** the LLM advisor queries by symbol='MSFT'
**Then** all rows across all four tables are returned
**And** the advisor can iterate over insider_trading, news_events, product_dev, and regulatory rows

### TC-11-10: LLM advisor updates conviction_score on existing row
**Given** an existing row in `llm_news_events` with conviction_score = 50.00
**When** the LLM advisor updates the conviction_score to 75.50
**Then** the row reflects the new conviction_score
**And** updated_at is set to the current timestamp
**And** created_at remains unchanged

### TC-11-11: Duplicate event prevention
**Given** a row exists in `llm_news_events` for symbol 'GOOG' with event_date '2026-03-01' and a specific headline
**When** the LLM advisor attempts to insert a row with the same symbol, date, and headline hash
**Then** the duplicate is not inserted (upsert or reject)
**And** no duplicate rows exist for the same symbol + date + headline

### TC-11-12: is_verified flag management
**Given** an unverified row (is_verified = 0) in `llm_insider_trading`
**When** a human analyst marks it as verified
**Then** is_verified is set to 1
**And** the row is included in verified-only queries

### TC-11-13: Old unverified low-confidence rows flagged
**Given** a row in `llm_news_events` with is_verified = 0, confidence = 30, and event_date > 90 days ago
**When** the flagging query runs
**Then** the row is included in the flagged-for-review set
**And** rows with confidence >= 50 or is_verified = 1 are not flagged

### TC-11-14: Investment thesis summary stored in evalsummary
**Given** an LLM analysis produces a thesis summary for symbol 'TSLA'
**When** the advisor completes analysis
**Then** the thesis summary is stored in `evalsummary.llm_recommendation` for symbol 'TSLA'
**And** the evalsummary row is linked to the latest llm_* events for that symbol

## Postconditions
- All four llm_* tables exist and are functional
- LLM advisor can read and write to all four tables
- Duplicate events are prevented
- Old low-confidence unverified rows are flaggable
- Investment thesis summaries are stored in evalsummary

## Related
- FR-11: LLM Fundamental Data Tables
- BR-9: LLM-Enhanced Fundamental Analysis
- `docs/advisors/REQUIREMENTS_DESIGN.md` §LLM Fundamental Data
- `docs/architecture/architecture-document.md` §10.5
