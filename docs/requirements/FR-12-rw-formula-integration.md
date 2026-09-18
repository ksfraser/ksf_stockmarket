# FR-12: Research Wizard Formula Integration

## Requirement

The system shall parse and execute Research Wizard (RW) pre-defined filter formulas as reusable advisor screening criteria. Each newsletter-style advisor adopts one RW formula as its stock-picking rule set.

## Business Context

BR-8 requires that Zacks-style Research Wizard pre-defined filters be usable as advisor screening criteria. RW filters use a simple declarative syntax (comparisons, logical operators, field references) that must be parsed into executable conditions against the system's database.

## Formula Syntax

RW pre-defined filters use the following syntax elements:

- **Comparisons**: GT (>), LT (<), GTE (>=), LTE (<=), EQ (=), NEQ (!=)
- **Logical operators**: AND, OR, NOT
- **Grouping**: Parentheses for precedence
- **Field references**: Named fields resolved to DB columns or computed values
- **Literals**: Numbers (10, 50.5), strings ("string"), booleans (TRUE, FALSE)

Example:
```
Stock Price > 10 AND Relative Volume > 1.5 AND Zacks Rank <= 2
```

## Parser Design

The RW formula parser follows a three-stage pipeline:

1. **Lexer**: Tokenizes the formula into tokens (FIELD, OP, LITERAL, LOGIC, PAREN)
2. **Parser**: Builds an AST from tokens using recursive descent
3. **Code generator**: Produces executable filter -- either a SQL WHERE clause or a Python filter lambda

The parser supports:
- Binary comparisons (field OP literal)
- Logical combinations (AND, OR, NOT)
- Nested parentheses
- Field name resolution against a registry

## Field Reference Resolution

| RW Field Name | DB Source / Computation |
|---------------|------------------------|
| price | stockprices.close (latest) |
| open, high, low | stockprices (latest bar) |
| volume | stockprices.volume (latest) |
| avg_volume | Computed: AVG(volume) over lookback period |
| market_cap | symbol_master.market_cap or computed |
| pe_ratio | Computed: close / eps or from fundamentals table |
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

## Advisor Integration

Each newsletter-style advisor (per FR-14) can adopt an RW formula as its screening criteria:

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
        # Advisor-specific pick logic
        ...
```

## Formula Caching

Parsed formula results are cached per screener run (FR-12.4):
- Cache key: SHA-256 hash of formula text
- Cache lifetime: duration of the screener run
- Cache stores: parsed AST + compiled filter function
- Cache miss: parse and compile (one-time cost per formula per run)

## Formula Editor UI

A formula editor UI (FR-12.5) allows users to:
- Paste an RW formula text
- Select from a library of pre-defined RW formulas
- Preview matching stocks before saving
- Save formulas to a user formulas table for reuse

## Acceptance Criteria

- [ ] Parser handles GT, LT, GTE, LTE, EQ, NEQ comparisons
- [ ] Parser handles AND, OR, NOT logical operators
- [ ] Parser handles nested parentheses
- [ ] Field references resolve to correct DB columns / computed values
- [ ] Formula parse time < 100ms per formula
- [ ] Formula evaluate (screen 2000 symbols) < 30 seconds
- [ ] Cached formula evaluate < 5 seconds for full screen
- [ ] Advisors can load RW formulas as screening criteria
- [ ] Formula editor UI allows preview of matching stocks

## Related

- BR-8: Zacks / Research Wizard Pre-Defined Filter Integration
- FR-14: Zacks RW Pipeline (existing)
- `docs/advisors/REQUIREMENTS_DESIGN.md` §Research Wizard Formula Integration
- `docs/architecture/architecture-document.md` §10.6
- `docs/architecture/stock-filter-engine.md` §11
