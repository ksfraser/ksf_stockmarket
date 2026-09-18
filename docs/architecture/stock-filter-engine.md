## 11. RW Formula Integration (NEW — 2026-09-18)

### 11.1 Overview

BR-8 and FR-12 require that Research Wizard (RW) pre-defined filter formulas be parsed and executed as reusable advisor screening criteria. This section captures the architecture and design for the RW formula engine.

### 11.2 Formula Syntax

RW pre-defined filters use a simple declarative syntax:

- **Comparison operators**: GT (>), LT (<), GTE (>=), LTE (<=), EQ (=), NEQ (!=)
- **Logical operators**: AND, OR, NOT
- **Grouping**: Parentheses for precedence
- **Field references**: Named fields resolved to DB columns or computed values
- **Literals**: Numbers, strings, booleans

Example formula:
```
Stock Price > 10 AND Relative Volume > 1.5 AND Zacks Rank <= 2
```

### 11.3 Parser Architecture

The RW formula parser follows a three-stage pipeline:

1. **Lexer**: Tokenizes the formula into tokens (FIELD, OP, LITERAL, LOGIC, PAREN)
2. **Parser**: Builds an AST from tokens using recursive descent parsing
3. **Code generator**: Produces executable filter — either a SQL WHERE clause or a Python filter lambda

The parser supports binary comparisons, logical combinations (AND, OR, NOT), and nested parentheses.

### 11.4 Field Reference Resolution

Field references in RW formulas are resolved to DB columns or computed values:

|| RW Field Name | DB Source / Computation |
|---|---|---|
| price | stockprices.close (latest) |
| open, high, low | stockprices (latest bar) |
| volume | stockprices.volume (latest) |
| avg_volume | Computed: AVG(volume) over lookback period |
| market_cap | symbol_master.market_cap or computed |
| pe_ratio | Computed: close / eps or from fundamentals |
| eps | fundamentals.eps or zacks_eps |
| dividend_yield | Computed: annual_dividend / price |
| beta | symbol_master.beta or computed |
| sma_50, sma_200 | daily_indicators or ta_values |
| rsi_14 | ta_values |
| macd | ta_values |
| bollinger_upper, bollinger_lower | daily_tier2 |
| zacks_rank | zacks_broker_recommendations or zacks_rank table |
| zacks_consensus | zacks_broker_recommendations |
| zacks_eps_change | fundamentals.zacks_eps_change_f1_4w |

### 11.5 Advisor Picking Flow

Each newsletter-style advisor (FR-14) can adopt an RW formula as its screening criteria:

```
1. Advisor loads RW formula text (from config or user selection)
2. Formula parser validates syntax and builds AST
3. Field resolver maps RW field names to DB columns / computed values
4. Code generator produces executable filter (SQL WHERE or Python lambda)
5. On screener run: filter executes against symbol universe
6. Results cached per run (FR-12.4) — cache key = SHA-256 of formula text
7. Advisor pick() method selects from screened results using advisor-specific logic
```

### 11.6 Performance Targets

- Formula parse: < 100ms per formula (one-time cost, cached)
- Formula evaluate (screen 2000 symbols): < 30 seconds
- Formula cache hit: < 5 seconds for full screen
- Formula editor preview (UI): < 5 seconds for preview

### 11.7 Formula Editor UI

A formula editor UI allows users to:
- Paste an RW formula text
- Select from a library of pre-defined RW formulas
- Preview matching stocks before saving
- Save formulas to a user formulas table for reuse

### 11.8 Related

- FR-12: Research Wizard Formula Integration
- BR-8: Zacks / Research Wizard Pre-Defined Filter Integration
- `docs/requirements/FR-12-rw-formula-integration.md`
- `docs/advisors/REQUIREMENTS_DESIGN.md` §Research Wizard Formula Integration
- `docs/architecture/architecture-document.md` §10.6
