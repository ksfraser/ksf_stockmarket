# Unit Test Outline — Research Wizard Formula Advisors (UT-12)

Test the RwFormulaParser integration and formula-based advisor picking.

## UT-12-001: RwFormulaParser parses field ref with time-lag offset

**Given** formula string `i95 > i95[Recent-4Q]`

**When** `RwFormulaParser::parse()` is called

**Then** the AST contains a BinaryNode with operator '>', left FieldNode code=95, right FieldNode code=95 with timeframe Recent-4Q

## UT-12-002: RwFormulaParser parses MovingMean call

**Given** formula string `MovingMean2(i5) > MovingMean4(i5)`

**When** `RwFormulaParser::parse()` is called

**Then** the AST contains CallNodes for MovingMean2 and MovingMean4 with argument FieldNode code=5

## UT-12-003: RwFormulaParser parses scoped reference

**Given** formula string `i13[,qqq] > 0`

**When** `RwFormulaParser::parse()` is called

**Then** the AST contains FieldNode code=13 with scope='qqq'

## UT-12-004: RwFormulaParser parses AND/OR grouping

**Given** formula string `i22 >= i22[Recent-1W] And i22[Recent-1W] >= i22[Recent-2W]`

**When** `RwFormulaParser::parse()` is called

**Then** the AST is a BoolNode with op='and' and two BinaryNode children

## UT-12-005: RwFormulaParser parses coalesce fallback

**Given** formula string `(1/(i192=1)) | (3/(i192=2))`

**When** `RwFormulaParser::parse()` is called

**Then** the AST contains BinaryNodes with operator '|' for the coalesce chain

## UT-12-006: ZacksFieldResolver binds known field codes

**Given** field codes 5 (close), 19 (beta), 192 (zacks_rank)

**When** `ZacksFieldResolver::spec()` is called for each

**Then** each returns a non-null spec with source, key, and approx flag

## UT-12-007: ZacksFieldResolver returns null for unknown field codes

**Given** a field code not in SPECS (e.g. 9999)

**When** `ZacksFieldResolver::spec()` is called

**Then** the method returns null (caller should skip this field)

## UT-12-008: Formula engine evaluates simple field comparison

**Given** formula `i5 > 100` (close > 100), symbol data with close=150

**When** the formula engine evaluates against the symbol

**Then** the result is true (symbol passes the filter)

## UT-12-009: Formula engine evaluates field comparison fails

**Given** formula `i5 > 100`, symbol data with close=50

**When** the formula engine evaluates against the symbol

**Then** the result is false (symbol fails the filter)

## UT-12-010: Formula engine skips unknown field codes

**Given** formula `i9999 > 0` (unknown field code)

**When** the formula engine evaluates against any symbol

**Then** the field is skipped with a report entry; the symbol is not filtered out (neutral), and fully_executed=false

## UT-12-011: Formula engine evaluates AND group

**Given** formula `i5 > 50 And i19 < 2.0`, symbol data with close=100, beta=1.5

**When** the formula engine evaluates against the symbol

**Then** the result is true (both conditions pass)

## UT-12-012: Formula engine evaluates OR group

**Given** formula `i5 > 200 Or i19 < 1.0`, symbol data with close=100, beta=0.8

**When** the formula engine evaluates against the symbol

**Then** the result is true (second condition passes, OR is satisfied)

## UT-12-013: Formula engine with time-lag offset evaluates correctly

**Given** formula `i5 > i5[Recent-4Q]`, symbol data with current close=150 and 4-quarters-ago close=100

**When** the formula engine evaluates against the symbol

**Then** the result is true (150 > 100)

## UT-12-014: Advisor stores formula in profile_json

**Given** an advisor with formula-based picking

**When** the advisor account is saved

**Then** profile_json contains picking.formula (the formula string) and picking.method='rw_formula'

## UT-12-015: Advisor picking runs formula against universe

**Given** an advisor with a valid formula and a universe of 100 symbols

**When** the advisor picking runs

**Then** the formula is parsed once, field codes are bound via ZacksFieldResolver, the AST is evaluated per symbol, and matching symbols are returned with a skipped report if any fields were unavailable

---

*Prerequisite test infrastructure:* `tests/Unit/RwFormulaAdvisorTest.php` — new file. Reuses the existing `RwFormulaParser` and `ZacksFieldResolver` from `ksfraser/research-wizard-reader`. Formula evaluation tests need a small hand-built symbol data array (mimicking the data sources the resolver returns). The advisor profile_json tests need the advisor_accounts table or a mock.
