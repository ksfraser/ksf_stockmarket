# FR-10-02: Statistical Validation — LLM Hypothesis Routing

## Requirement
When the LLM analyzer runs qualitative scoring on a symbol, it shall
automatically attach a quantitative hypothesis test result by routing the
analysis question through `route_hypothesis()`.

## Rationale (BR-3)
The LLM generates qualitative scores (Buffett tenets, Motley Fool criteria).
Without an evidence check, those scores float free of the price data. Layer 2
anchors every LLM score to a statistically-grounded quant result.

## Mechanism
`route_hypothesis()` auto-detects test type from hypothesis keywords:

| Keyword trigger | Test invoked |
|-----------------|--------------|
| "trend", "stationary", "adf" | ADF stationarity |
| "normal", "distribution" | Jarque-Bera |
| "vs sp500", "beta", "alpha" | OLS regression vs benchmark |
| "beat", "outperform", "mean" | One-sample t-test |
| "expect", "kelly", "position" | Half-Kelly sizing |
| default | Rolling hit rate |

## Persistence
Results are merged into the score dict as:
`scores['quant_test']`, `scores['quant_significant']`,
`scores['quant_p_value']`, `scores['quant_metric']`,
`scores['quant_detail']`, `scores['quant_recommendation']`

These are written to the scoring table alongside the LLM qualitative scores.

## Priority
Must Have

## Acceptance Criteria
- [ ] `run_llm_research()` called from `run_llm_analysis()` before `write_llm_scores()`
- [ ] Fallback graceful: if returns unavailable, skip quant test without failing LLM score write
- [ ] Pre-existing NameError in `write_llm_scores()` fixed (`cursor` used before creation)

## Implementation
- `python/llm_analyzer.py` :: `run_llm_research()`, `_fetch_recent_returns()`
- `python/quant/research.py` :: `route_hypothesis()`

## Regression Risk
Low — additive only; does not change existing LLM score format.
