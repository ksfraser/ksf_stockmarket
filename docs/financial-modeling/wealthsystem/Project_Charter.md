# Project Charter — WealthSystem Port
**Module:** ksf_stockmarket WealthSystem Detail Integration  
**Owner:** Kevin Fraser  
**Date:** 2026-07-29

## Goal
Deliver a persistent, editable WealthSystem-grade detail experience in `ksf_stockmarket`:
- 12-tenet Buffett checklist
- 10-criteria Motley Fool checklist
- Detailed technical-analysis narrative
- 4-domain evaluation breakdown (Business, Financial, Management, Market)
- LLM qualitative analysis notes

## Scope
**In scope**
- `php/templates/partials/ws/` (5 partials)
- `StockController` loaders + save handlers
- Detail page save forms (`detail_enhanced.php`)
- MySQL persistence via `016_wealthsystem_schemas.sql` tables

**Out of scope**
- Backfilling historical AI analysis
- Auto-generation of Buffett/MF scores from fundamentals
- User permissions beyond existing admin/auth roles

## Success Criteria
- Detail page renders 5 WS sections with or without persisted data
- Save forms update MySQL and reload without error
- All partials are syntactically valid PHP
- Controller methods are covered by end-to-end manual verification
