# Business Requirements — WealthSystem Port
BR-081 | WealthSystem Detail + Edit on Symbol Detail Page

## Background
The current symbol detail page shows price, chart, indicators, and fundamentals, but lacks deep WealthSystem-style qualitative/quantitative breakdowns and in-page editing.

## Requirements
1. Load and display Buffett 12-tenet checklist with per-tenet pass/fail and notes.
2. Load and display Motley Fool 10 criteria with pass/fail state.
3. Load and display detailed technical-analysis narrative derived from `stock_technical_indicators`.
4. Load and display 4-domain evaluation breakdown with score, max, grade, and note.
5. Load and display LLM qualitative analysis summary and model metadata.
6. Persist user edits for Buffett, Motley, evaluations, and LLM from the detail page via POST.
7. Always render WealthSystem sections; show empty/not-yet-evaluated state when no DB rows exist.
8. Do not block page load if any WealthSystem table is missing; degrade gracefully.
