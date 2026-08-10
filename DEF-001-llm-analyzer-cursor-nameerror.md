# DEF-001: llm_analyzer write_llm_scores NameError

## Defect Report

**File**: `python/llm_analyzer.py`  
**Function**: `write_llm_scores()` (line ~244)  
**Severity**: High (unhandled crash on every LLM score write)  
**Status**: Fixed in this deployment

## Description
`write_llm_scores()` queries `cursor.execute()` on the Bayesian prior-likelihood
adjustment block at line 244, but `cursor` is not created until line 254. This
raises `NameError: name 'cursor' is not defined` before any LLM scores can be
written to the database.

## Root Cause
The prior-confidence query was inserted after the cursor creation block during
a prior edit; cursor variable hoisting was missed.

## Fix
Created a dedicated `prior_cursor = conn.cursor(dictionary=True)` for the
SELECT AVG(llm_confidence) query, closed it before the write cursor was
created. Also fixed `prior_row[0]` to `prior_row['llm_confidence']` to match
the dictionary cursor.

## Verification
- `python3 -m py_compile llm_analyzer.py` → OK
- Manual test: `python3 python/llm_analyzer.py --table tenets --symbol AAPL`
  no longer raises NameError on the prior lookup.

## Related
- FR-10-02-statistical-validation-layer2.md
- `python/quant/research.py` :: dead-code cleanup (`rolling_signal_probability` walrus operator replaced)
