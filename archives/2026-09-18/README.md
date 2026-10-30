# AI Advisor & Fundamental Analysis — Extension Docs
## Written 2026-09-18
## Context
This directory archives the documentation sections added to the KSF Stock Market Analysis System on 2026-09-18, covering AI-advisor personas, Zacks/Research Wizard formula integration, LLM-enhanced fundamental analysis, timing-aware backtesting, LLM admin configuration, and associated test outlines.

These sections were appended to the following files in the repository:
- `docs/requirements/requirements-specification.md` — BR-7..BR-11, FR-11..FR-13, FR-16, Change Log
- `docs/requirements/solution-design.md` — §6 LLM Fundamental Analysis, §7 RW Formula Integration, §8 Timing-Aware Trading, §9 LLM Admin & Configuration
- `docs/architecture/architecture-document.md` — §10.5 LLM Fundamental Data Tables, §10.6 RW Formula Service, §10.7 Timing Service, §10.8 LLM Admin Screen
- `docs/architecture/stock-filter-engine.md` — §11 RW Formula Integration (parser, field binding, advisor picking, performance targets)
- `docs/advisors/REQUIREMENTS_DESIGN.md` — rewritten with LLM Admin Screen, LLM Fundamental Data, Timing-Aware Trading, RW Formula Integration sections
- `docs/requirements/traceability-matrix.md` — BR-7..BR-11, FR-11..FR-13, FR-16 rows added

New test outline files created:
- `docs/requirements/UT-11-06-llm-admin-console.md`
- `docs/requirements/UT-11-llm-fundamental-data.md`
- `docs/requirements/UT-12-rw-formula-advisors.md`
- `docs/requirements/UT-16-timing-backtesting.md`

## References
- `docs/requirements/BR-14-zacks-rw-pipeline.md` — Zacks RW pipeline (existing)
- `docs/requirements/FR-10-01-statistical-validation-layer1.md` through `FR-10-04-half-kelly-position-sizing.md` — statistical validation layers (existing)
- `docs/requirements/BR-15-stock-price-storage-refactor.md` — price storage refactor (existing, ongoing)
