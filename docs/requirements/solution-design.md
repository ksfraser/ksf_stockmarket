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

### 2.2 Three-Tier Indicator Architecture

| Tier | When | How | Storage | Indicators |
|---|---|---|---|---|
| 1 | Per INSERT | MySQL trigger | Wide columns in `daily_indicators` | daily_return, gap, SMA-20/50/200, vol_sma_20 |
| 2 | Daily batch | MySQL event (window functions) | Wide columns in `daily_tier2` | Bollinger, ATR-14, vol ratios, trend |
| 3 | Daily batch | Python cron (TA-Lib vectorized) | Name-value in `ta_values` | RSI, MACD, candlestick patterns, custom |

**Rationale**: 
- Tier 1 is O(1) per row — cheap enough for trigger
- Tier 2 needs 14-20 row window — expensive per insert, cheap once daily
- Tier 3 needs full array (250+ rows) — only efficient as batch vectorized operation

### 2.3 Scoring System Design

10 scoring tables preserved from legacy, enhanced with LLM integration:

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

### 2.4 Signal Weight Correlation Design

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

```
Daily Processing Flow:
1. Market closes (4 PM ET)
2. yfinance fetches latest prices → stockprices (trigger fires Tier 1)
3. MySQL event runs Tier 2 (window functions)
4. Python cron runs Tier 3 (TA-Lib vectorized batch)
5. Python cron runs scoring analysis (LLM + fundamental)
6. Python cron updates signal_weights (correlation analysis)
7. Results available for UI and monitoring
```

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
