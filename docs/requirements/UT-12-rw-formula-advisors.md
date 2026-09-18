# Unit Test Outline: UT-12 — RW Formula Advisors

## Requirement Coverage
- FR-12: Research Wizard Formula Integration
- BR-8: Zacks / Research Wizard Pre-Defined Filter Integration

## Preconditions
- Test database with `symbol_master` and `stockprices` tables populated with test symbols
- RW formula parser module available
- Formula cache mechanism available

## Test Cases

### TC-12-01: Parse simple comparison formula
**Given** the RW formula parser
**When** parsing "price GT 10"
**Then** the parser produces an AST representing: field='price', op='GT', literal=10
**And** parse time is < 100ms

### TC-12-02: Parse compound AND formula
**Given** the RW formula parser
**When** parsing "price GT 10 AND volume GT 1000000"
**Then** the parser produces an AST with AND node having two comparison children
**And** field references are preserved for resolution

### TC-12-03: Parse compound OR formula
**Given** the RW formula parser
**When** parsing "pe_ratio LT 15 OR dividend_yield GT 3"
**Then** the parser produces an AST with OR node having two comparison children

### TC-12-04: Parse nested parentheses
**Given** the RW formula parser
**When** parsing "(price GT 10 AND volume GT 1000000) OR zacks_rank LTE 2"
**Then** the parser produces an AST respecting parentheses precedence
**And** the AND group is a child of the OR node

### TC-12-05: Parse NOT operator
**Given** the RW formula parser
**When** parsing "NOT (zacks_rank GT 3)"
**Then** the parser produces an AST with NOT node wrapping the comparison

### TC-12-06: Field resolution - price
**Given** the field resolver
**When** resolving field name 'price'
**Then** it maps to stockprices.close (latest bar close price)

### TC-12-07: Field resolution - zacks_rank
**Given** the field resolver
**When** resolving field name 'zacks_rank'
**Then** it maps to zacks_broker_recommendations.zacks_rank or equivalent table

### TC-12-08: Field resolution - rsi_14
**Given** the field resolver
**When** resolving field name 'rsi_14'
**Then** it maps to ta_values where indicator = 'rsi_14' for the symbol

### TC-12-09: Execute formula against test universe
**Given** a test universe of 20 symbols with known price, volume, pe_ratio, zacks_rank values
**And** a parsed formula "price GT 50 AND zacks_rank LTE 2"
**When** the formula is executed against the universe
**Then** only symbols with price > 50 AND zacks_rank <= 2 are returned
**And** the evaluate time for 2000 symbols is < 30 seconds

### TC-12-10: Formula caching
**Given** the same formula parsed twice
**When** the cache is queried with the formula text hash
**Then** the second parse returns the cached AST
**And** cache hit time is < 10ms

### TC-12-11: Advisor loads RW formula as screening criteria
**Given** an RWFormulaAdvisor configured with formula "price GT 10 AND volume GT 1000000"
**When** the advisor's screen() method is called with a universe
**Then** the advisor returns only symbols matching the formula
**And** the advisor's pick() method selects from the screened results

### TC-12-12: Multiple advisors with different formulas
**Given** advisor A with formula "pe_ratio LT 15"
**And** advisor B with formula "price GT 100 AND zacks_rank LTE 2"
**When** both advisors screen the same universe
**Then** advisor A returns different results than advisor B
**And** each advisor's results match its own formula

### TC-12-13: Invalid formula rejection
**Given** the RW formula parser
**When** parsing an invalid formula (unmatched parentheses, unknown operator)
**Then** the parser raises a parse error
**And** the error message indicates the issue (without leaking sensitive data)

### TC-12-14: Formula editor preview
**Given** a user pastes formula "price GT 10" into the formula editor UI
**When** the user clicks Preview
**Then** the UI shows a list of symbols matching the formula
**And** the preview loads in < 5 seconds

## Postconditions
- Parser handles all required syntax elements
- Field resolver maps all required RW field names
- Formula evaluate is performant (< 30s for 2000 symbols)
- Caching works correctly
- Multiple advisors with different formulas produce different results

## Related
- FR-12: Research Wizard Formula Integration
- BR-8: Zacks / Research Wizard Pre-Defined Filter Integration
- `docs/advisors/REQUIREMENTS_DESIGN.md` §Research Wizard Formula Integration
- `docs/architecture/architecture-document.md` §10.6
- `docs/architecture/stock-filter-engine.md` §11
