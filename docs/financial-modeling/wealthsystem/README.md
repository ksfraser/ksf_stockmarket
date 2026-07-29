# README — WealthSystem Port
BR-081 | WealthSystem Detail + Edit on Symbol Detail Page

## Overview
Persistent WealthSystem detail integration for `ksf_stockmarket` symbol detail page.

## Capabilities
- **Buffett 12 tenets** — load/save checklist + notes
- **Motley Fool 10** — load/save pass/fail criteria
- **Technical Analysis narrative** — derived from `stock_technical_indicators`
- **Evaluations 4 domains** — Business, Financial, Management, Market scores/grades
- **LLM qualitative** — summary + model metadata
- **IPlace score** — composite score, recommendation, criteria breakdown
- **VectorVest checklist** — 5-point composite

## File Inventory
- `php/src/Controller/StockController.php` — loaders + 4 save handlers
- `php/index.php` — POST interception for detail page saves
- `php/templates/detail_enhanced.php` — WS variable mapping + save forms + flash message
- `php/templates/partials/ws/*.php` — render partials

## Database
Requires migration `016_wealthsystem_schemas.sql` executed.

## Docs
- `docs/financial-modeling/wealthsystem/Project_Charter.md`
- `docs/financial-modeling/wealthsystem/Business_Requirements.md`
- `docs/financial-modeling/wealthsystem/Architecture.md`
- `docs/financial-modeling/wealthsystem/UML_Class_and_Sequence.md`
- `docs/financial-modeling/wealthsystem/RTM.md`
- `docs/financial-modeling/wealthsystem/Test_Plan.md`
