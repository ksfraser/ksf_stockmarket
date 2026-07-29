# UML — WealthSystem Port
BR-081 | WealthSystem Detail + Edit on Symbol Detail Page

## Class Diagram
```
StockController
 + detail(string): array
 + loadWealthSystemDetail(string): array
 + saveLlmAnalysis(string, string, string, string, string, string): bool
 + saveEvaluationScores(string, array, string): bool
 + saveMotleyFool(string, array, string): bool
 + saveTenets(string, array, string): bool
 + ensureTables(array): void
```

## Sequence Diagram — Save
```
User Browser
    | POST detail_enhanced.php (ws_subaction)
    ↓
index.php
    | instantiate StockController
    ↓
StockController::saveXxx(symbol, payload)
    | PDO upsert MySQL
    ↓
redirect ?action=detail&symbol=...&msg=Saved
    ↓
detail() → loadWealthSystemDetail() → renders WS partials
```

## Sequence Diagram — Load
```
detail_enhanced.php
    | $ctrl->detail(symbol)
    ↓
StockController::detail()
    | loads latest/history/indicators/fundamentals
    | calls loadWealthSystemDetail()
    ↓
loadWealthSystemDetail()
    | SELECT FROM tenets, motleyfool, evaluation_scores, llm_analysis, stock_technical_indicators, stock_fundamentals
    ↓
returns augmented payload
    ↓
render partials with fallback defaults
```
