# Database Schema Comparison: Legacy vs. Modernized

## Source Systems

| Property | `stock_market` (old) | `back_finance` (new) | `ksf_stockmarket` (modern) |
|---|---|---|---|
| Origin | Original web app | Finance/trading module | Hybrid PHP+Python app |
| Tables | ~130 (FA + legacy SQL) | 21 tables | ~30 focused tables |
| Engine | MyISAM / InnoDB mix | MyISAM mostly | InnoDB |
| Charset | latin1 | latin1 | utf8mb4 |
| Partitioned | No | No | **Yes** (prices, indicators) |
| LLM-populated | No | No | **Yes** (scoring tables) |

## Scoring & Strategy Tables — KEEP + ENHANCE

These tables represent years of investment thesis work. They should be **preserved and enhanced**,
not discarded. The Python/LLM layer populates them by analyzing press releases, annual filings,
and financial data. They become the structured "memory" of the analysis system.

### `evalsummary` — Composite investment score per symbol
| Column | Type | Purpose |
|---|---|---|
| idstockinfo | varchar(6) | Stock symbol (PK) |
| totalscore | int | Total of all scores (out of 36) |
| marginsafety | float | Margin of safety (%) |
| ratioscore | int | Score from financial ratios (out of 8) |
| iplacecalcscore | int | InvestorPlace score (out of 10) |
| managementscore | int | Management tenets score (out of 9) |
| financialscore | int | Financial tenets score (out of 4) |
| businessscore | int | Business tenets score (out of 5) |
| reviseddate | timestamp | Last revision date |
| reviseduser | varchar(45) | Who last revised |

**LLM role**: Populate by analyzing annual reports, press releases, earnings calls.
Scores reflect qualitative judgment that the LLM can assist with but humans can override.

### `motleyfool` — Motley Fool Rule Breakers / Stock Advisor criteria
| Column | Type | Purpose |
|---|---|---|
| doubledigitrisingsales | int | Sales growth >= 10% |
| risingfreecashflow | int | Free cash flow rising |
| risingbookvalue | int | Book value rising |
| improvingmargin | int | Margins improving |
| risingreturnonequity | int | ROE rising |
| insiderownership | int | Executive ownership significant |
| regulardividends | int | Consistent dividend payments |

**LLM role**: Analyze earnings releases and 10-K/10-Q filings to determine if criteria are met.

### `investorplace` — InvestorPlace screening criteria
| Column | Type | Purpose |
|---|---|---|
| idstockinfo | int | Company (FK to stockinfo) |
| seventyfivepercent | bool | Domestic sales >= 75% |
| earningsgrowth | bool | Earnings growing |
| earningsaccel | bool | Earnings growth accelerating |
| pe | float | P/E ratio |
| tradingvolume | int | Trading volume |
| institutioninterest | int | Institutional ownership % |
| orderimbalance | bool | Buy/sell order balance |
| shortinterest | bool | High short interest |
| volatility | float | Share volatility |
| dividendearningratio | float | Dividend/earnings ratio |
| newproductline | bool | Innovations / new products |
| restructuring | bool | Cost-cutting restructuring |
| reengineering | bool | Business reengineering |
| sharebuyback | bool | Share buyback program |
| headcountcuts | bool | Announced staff reductions |
| spinoffs | bool | Business spin-offs |
| reducedrd | bool | Reducing R&D |
| extracash | bool | Cash on hand |
| shareholderprofitgoal | bool | Management focused on shareholder profit |
| dividendincreases | bool | Track record of dividend increases |
| score | int | Composite score |

**LLM role**: Parse press releases, 8-K filings, earnings call transcripts for restructuring,
buyback, spinoff, R&D changes, etc.

### `evalbusiness` — Business quality assessment
| Column | Type | Purpose |
|---|---|---|
| idstockinfo | int | Company (FK) |
| summary | int | Summary score (out of 5) |
| simple | bool | Simple business model |
| cosnsistanthistory | bool | Consistent performance history |
| neededproduct | bool | Product is needed |
| noclosesubstitute | bool | No close substitute |
| regulated | bool | Regulated industry (moat) |

**LLM role**: Analyze business descriptions, competitive landscape in 10-K filings.

### `tenets` — Management & business tenets (Buffett-style)
| Column | Type | Purpose |
|---|---|---|
| stocksymbol | char(7) | Company |
| simple | int | Simple business |
| consistent | int | Consistent performance |
| longterm | int | Long-term prospects |
| rationalmanager | int | Rational management |
| candid | int | Candid with shareholders |
| resistinstitution | int | Resists institutional pressures |
| focusroe | int | Focuses on ROE, not EPS |
| ownerearnings | int | Calculates owner earnings |
| highprofitmargin | int | High profit margins |
| retainedtomarket | int | Retained earnings → market value |
| valueofbusiness | int | Intrinsic value calculation |
| discounted | int | Purchased at discount to value |

**LLM role**: Analyze management discussion in annual letters, proxy statements, earnings calls.
These are qualitative assessments that benefit from LLM document analysis.

### `ratios` — Financial ratio analysis with attractiveness scoring
| Column | Type | Purpose |
|---|---|---|
| idstockinfo | int | Stock (FK) |
| ratioscore (`attractivesum`) | int | Sum of attractive scores |
| roe / roeattractive | float / int | ROE and whether it's attractive (>15%) |
| roa / attractiveroa | float / int | ROA and whether attractive |
| roce / attractiveroce | float / int | ROCE and whether attractive |
| grossprofitmargin / attractivegross | float / int | Gross margin and attractiveness |
| pretaxmargin / attractivepretax | float / int | Pre-tax margin and attractiveness |
| netmargin / attractivenet | float / int | Net margin and attractiveness |
| operatingmargin / lowcost | float / int | Operating margin, low-cost ops |
| debtratio / acceptabledebtratio | float / int | Debt ratios |
| peratio | float | P/E ratio |
| sustaindebtratio | int | Debt covered by income long-term |
| createduser / updateduser | int | Who created/updated |
| createddate / updateddate | datetime / timestamp | When |

**LLM role**: Calculate from financial data (Python), then LLM assesses qualitative factors
around sustainability, quality of earnings, etc.

### `quarter_statement` — Quarterly financial statements (60 columns)
Quarterly income statement and balance sheet data. LLM extracts from 10-Q filings.

### `evalmanagement` — Management evaluation (9 columns, from stock_market_2.sql)
Management quality assessment scores. LLM analyzes proxy statements and annual letters.

### `evalmarket` — Market evaluation (~5 columns)
Market condition assessment for the stock.

### `evalvalue` — Value assessment (~5 columns)
Intrinsic value calculation inputs and scores.

### `evalmarket` + `evalmaket` — Market evaluation (from stock_market.sql)

### `fin_statement` — Financial statements (~8 columns, from stock_market_2.sql)

## Scoring Philosophy

The scoring tables fall into three categories:

1. **Purely quantitative** (`ratios`): Python calculates from financial data
2. **Rule-based qualitative** (`motleyfool`, `investorplace`): LLM checks criteria against filings data
3. **Subjective qualitative** (`tenets`, `evalbusiness`, `evalsummary`): LLM assists with document analysis, human has final say

All scoring tables link back to `stockinfo` via symbol and include:
- `createduser` / `updateduser` — who populated the score
- `createddate` / `updateddate` — when
- `source` — what data source was used (10-K, press release, earnings call, etc.)

## Legacy `stock_market` Tables (full list)

All tables from the `stock_market.sql` dump and their migration status:

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
| **`evalsummary`** | **10** | **Composite investment score** | **✅ KEEP — evalsummary** |
| **`ratios`** | **28** | **Financial ratio scoring** | **✅ KEEP — ratios** |
| **`tenets`** | **14** | **Management/business tenets** | **✅ KEEP — tenets** |
| **`motleyfool`** | **8** | **MF screening criteria** | **✅ KEEP — motleyfool** |
| **`investorplace`** | **24** | **IP screening criteria** | **✅ KEEP — investorplace** |
| **`evalbusiness`** | **12** | **Business quality assessment** | **✅ KEEP — evalbusiness** |
| **`evalmanagement`** | **9** | **Management evaluation** | **✅ KEEP — evalmanagement** |
| **`evalmarket`** | **~5** | **Market evaluation** | **✅ KEEP — evalmarket** |
| **`evalvalue`** | **~5** | **Value assessment** | **✅ KEEP — evalvalue** |
| **`quarter_statement`** | **60** | **Quarterly financials** | **✅ KEEP — quarter_statement** |
| **`fin_statement`** | **8** | **Financial statements** | **✅ KEEP — fin_statement** |
| `technicalanalysis` | ~20 | Precomputed TA | Replaced by tier tables |
| `candlestickactions` | ~8 | Candlestick patterns | Replaced by Python/TA-Lib |
| `heikanashi` | ~8 | Candlestick data | Replaced by Python/TA-Lib |
| `fxprices` | ~5 | Forex prices | Separate module |
| `bondrate` | ~3 | Bond rates | Not migrated |
| `indices` | ~5 | Market indices | Not migrated |
| `taxstatus` | 76 | Tax lot tracking | `taxstatus` (simplified) |
| `hedgefolios` | ~8 | Hedge portfolio data | Not migrated |
| `turtledata` | ~8 | Turtle trading system | Replaced by Python |
| `beancounter` | ~9 | Trading system state | Replaced by backtest tables |

## Migration Plan

### Phase 1: Schema + Import (current)
1. Deploy `schema_v2_partitioned.sql`
2. Import CSV data into partitioned `stockprices`
3. Run Tier 2 event to populate `daily_tier2`
4. Verify trigger works
5. Benchmark query performance

### Phase 2: Scoring Engine (NEW)
1. Create Python scripts to populate scoring tables from filings data
2. LLM analyzes press releases, 10-K, 10-Q for qualitative criteria
3. Python calculates quantitative ratios from financial data
4. Store results in scoring tables with source attribution
5. Build comparison views: score trends over time, peer comparison

### Phase 3: PHP Integration
1. Update models to use modern schema
2. Add scoring dashboard UI
3. Show LLM-generated analysis alongside scores
4. Human override capability for subjective scores

### Phase 4: Python Bridge
1. CSV/yfinance import → partitioned prices
2. Tier 2 refresh cron
3. Backtesting reads from `v_stock_analysis`
4. Signal weights optimization
5. Scoring table population from document analysis
