# Unit Test Outline — LLM Fundamental Data (UT-11)

Test the LLM fundamental data tables and analyzer.

## UT-11-001: llm_news insert and query

**Given** `llm_news` table exists

**When** a row is inserted with symbol, headline, event_date, source

**Then** the row is queryable by symbol and event_date; is_analyzed defaults to 0

## UT-11-002: llm_guidance sentiment values

**Given** `llm_guidance` table exists

**When** rows are inserted with sentiment='positive', 'negative', 'neutral'

**Then** all three sentiment values are accepted; invalid values are rejected

## UT-11-003: llm_regulatory status values

**Given** `llm_regulatory` table exists

**When** rows are inserted with status='pending', 'approved', 'denied', 'withdrawn'

**Then** all four status values are accepted; invalid values are rejected

## UT-11-004: llm_analysis_sessions tracks provider

**Given** `llm_analysis_sessions` table exists

**When** a session row is inserted with provider_used and model_used

**Then** the row stores which LLM provider and model performed the analysis

## UT-11-005: LLM analyzer reads unanalyzed news

**Given** `llm_news` has 5 rows with is_analyzed=0 and 3 rows with is_analyzed=1

**When** the LLM analyzer queries for unanalyzed items

**Then** only the 5 unanalyzed rows are returned

## UT-11-006: LLM analyzer writes new findings

**Given** the LLM analyzer discovers a new regulatory event not in llm_regulatory

**When** the analyzer writes the finding

**Then** a new row is inserted into llm_regulatory with status='pending', llm_model set, created_at populated

## UT-11-007: Advisor reads LLM fundamental data

**Given** an advisor strategy is scoring candidates

**When** the strategy queries llm_news for material_impact='high' events in the last 30 days

**Then** the strategy receives the relevant news items and can adjust scores

---

*Prerequisite test infrastructure:* `tests/Unit/LlmFundamentalTest.php` — new file. Database tests use a test fixture SQLite DB (same pattern as existing unit tests). Integration tests require a test MariaDB with the llm_* tables created via migration.
