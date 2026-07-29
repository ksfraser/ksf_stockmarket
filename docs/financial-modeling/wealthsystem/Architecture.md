# Architecture — WealthSystem Port
BR-081 | WealthSystem Detail + Edit on Symbol Detail Page

## System Context
```
Browser → detail_enhanced.php
   ↓
StockController::detail() + loadWealthSystemDetail()
   ↓
MySQL (016 tables)
   ↓
WS partials render
POST detail_enhanced.php → StockController::save*()
   ↓
MySQL upsert
```

## Data Flow
- **Load path**
  - `detail()` builds base payload (`latest`, `history`, `indicators`, `fundamentals`, etc.)
  - `loadWealthSystemDetail()` augments with `ws_fundamentals`, `ws_indicators`, `ws_llm_analysis`, `ws_evaluations`, `buffett_score`, `motley`
  - Template maps payload into partial variables

- **Save path**
  - `index.php` intercepts `POST` to `action=detail`
  - Subactions: `save_tenets`, `save_motley`, `save_evals`, `save_llm`
  - Each calls a typed `StockController` save method
  - Redirect back to GET with `?msg=...` flash

## Tables Used
- `tenets`
- `motleyfool`
- `evaluation_scores`
- `llm_analysis`
- `stock_technical_indicators`
- `stock_fundamentals`

## Files Changed
- `php/src/Controller/StockController.php`
- `php/index.php`
- `php/templates/detail_enhanced.php`
- `php/templates/partials/ws/*.php` (new)

## Error Handling
- All DB reads wrapped in try/catch with silent fallback to empty arrays
- `ensureTables()` placeholder for pre-flight schema creation
- Save methods use transactions where multi-row; PDO exceptions return `false`
