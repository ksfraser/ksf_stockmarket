# FR-11: LLM Fundamental Data Tables

## Requirement

The system shall maintain four LLM-powered fundamental analysis tables that track forward guidance, news events, product development, and regulatory actions per symbol. LLM-enabled advisors read these tables at session start and update them when new information is discovered during scanning.

## Business Context

BR-9 (LLM-Enhanced Fundamental Analysis) requires structured storage for the qualitative insights that LLM advisors produce. Rather than relying on ephemeral LLM output, the system persists findings to four dedicated tables so that:
- Multiple advisors can reference the same underlying data
- Backtests can evaluate how early access to guidance/news/regulatory info would have affected returns
- Human analysts can verify and override LLM findings
- Conviction scores accumulate over time as new events arrive

## Data Model

### llm_insider_trading

| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT AUTO_INCREMENT PK | |
| symbol | VARCHAR(20) NOT NULL | Ticker symbol |
| event_date | DATE NOT NULL | Date of the insider event |
| as_of | DATE NOT NULL | Data freshness date |
| source | VARCHAR(255) | Source URL or feed name |
| headline | VARCHAR(500) | Brief title |
| details | TEXT | Full description |
| confidence | TINYINT UNSIGNED | LLM confidence 0-100 |
| conviction_score | DECIMAL(5,2) | -100 to +100 sentiment |
| is_verified | TINYINT UNSIGNED DEFAULT 0 | Human-verified flag |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

Indexes: `(symbol, event_date)`, `(conviction_score)`

### llm_news_events

| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT AUTO_INCREMENT PK | |
| symbol | VARCHAR(20) NOT NULL | |
| event_date | DATE NOT NULL | |
| as_of | DATE NOT NULL | |
| source | VARCHAR(255) | |
| headline | VARCHAR(500) | |
| details | TEXT | |
| category | ENUM('earnings','product_launch','regulatory','executive','financial','market','other') | |
| confidence | TINYINT UNSIGNED | 0-100 |
| sentiment_score | DECIMAL(5,2) | -100 to +100 |
| conviction_score | DECIMAL(5,2) | -100 to +100 |
| is_verified | TINYINT UNSIGNED DEFAULT 0 | |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

Indexes: `(symbol, event_date)`, `(category)`

### llm_product_dev

| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT AUTO_INCREMENT PK | |
| symbol | VARCHAR(20) NOT NULL | |
| product_name | VARCHAR(255) | |
| lifecycle_stage | ENUM('concept','prototype','production_rollout','market_launch','modification','end_of_life') NOT NULL | |
| event_date | DATE NOT NULL | |
| as_of | DATE NOT NULL | |
| source | VARCHAR(255) | |
| headline | VARCHAR(500) | |
| details | TEXT | |
| expected_impact | ENUM('positive','neutral','negative') | |
| confidence | TINYINT UNSIGNED | 0-100 |
| conviction_score | DECIMAL(5,2) | -100 to +100 |
| is_verified | TINYINT UNSIGNED DEFAULT 0 | |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

Indexes: `(symbol, lifecycle_stage)`, `(event_date)`

### llm_regulatory

| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT AUTO_INCREMENT PK | |
| symbol | VARCHAR(20) NOT NULL | |
| event_date | DATE NOT NULL | |
| as_of | DATE NOT NULL | |
| source | VARCHAR(255) | |
| headline | VARCHAR(500) | |
| details | TEXT | |
| regulatory_type | ENUM('approval','pending_review','industry_change','compliance_action','investigation','other') | |
| jurisdiction | VARCHAR(100) | |
| status | ENUM('approved','pending','rejected','withdrawn','ongoing') | |
| confidence | TINYINT UNSIGNED | 0-100 |
| conviction_score | DECIMAL(5,2) | -100 to +100 |
| is_verified | TINYINT UNSIGNED DEFAULT 0 | |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

Indexes: `(symbol, regulatory_type)`, `(event_date)`

## LLM Read/Write Flow

1. LLM-enabled advisor starts analysis session for target symbols
2. Reads from `llm_insider_trading`, `llm_news_events`, `llm_product_dev`, `llm_regulatory` for those symbols
3. Fetches current data from external sources (news APIs, SEC EDGAR, regulatory databases)
4. Sends context to LLM (primary -> secondary -> fallback chain per FR-13)
5. LLM produces: new events to insert, conviction score updates, investment thesis summary
6. System upserts rows into the four tables (new rows inserted, existing rows updated with fresh conviction scores)
7. `is_verified` remains 0 until a human analyst reviews the finding
8. Investment thesis summary feeds into `evalsummary.llm_recommendation`

## Acceptance Criteria

- [ ] All four tables exist in the database with the schema above
- [ ] LLM advisor can read rows from all four tables by symbol
- [ ] LLM advisor can insert new rows into all four tables
- [ ] LLM advisor can update `conviction_score` and `details` on existing rows
- [ ] `is_verified` defaults to 0 and can be set to 1 by human analyst
- [ ] Duplicate events (same symbol + date + headline hash) are not inserted
- [ ] Rows older than 90 days with `is_verified = 0` and `confidence < 50` are flagged for review
- [ ] Investment thesis summary from LLM is stored in `evalsummary.llm_recommendation`

## Related

- BR-9: LLM-Enhanced Fundamental Analysis
- FR-13: LLM Advisor Admin Screen (fallback chain configuration)
- `docs/advisors/REQUIREMENTS_DESIGN.md` §LLM Fundamental Data
- `docs/architecture/architecture-document.md` §10.5
