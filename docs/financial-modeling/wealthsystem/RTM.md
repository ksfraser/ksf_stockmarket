# Requirements Traceability Matrix — WealthSystem Port
BR-081 | WealthSystem Detail + Edit on Symbol Detail Page

| Req | Source | Controller Method | Template / Partial | Table(s) | Test / Verify |
|---|---|---|---|---|---|
| Load Buffett 12 tenets | Business_Requirements §1 | loadWealthSystemDetail() | partials/ws/buffett.php | tenets | detail page shows tenets count + list |
| Edit + Save Buffett | Business_Requirements §6 | saveTenets() | detail_enhanced.php form | tenets | POST → reload → checkboxes persist |
| Load Motley 10 criteria | Business_Requirements §2 | loadWealthSystemDetail() | partials/ws/motley_fool.php | motleyfool | detail page shows criteria rows |
| Edit + Save Motley | Business_Requirements §6 | saveMotleyFool() | detail_enhanced.php form | motleyfool | POST → reload → checkboxes persist |
| Load TA narrative | Business_Requirements §3 | loadWealthSystemDetail() | partials/ws/technical_analysis.php | stock_technical_indicators | narrative renders latest indicators |
| Load 4-domain eval | Business_Requirements §4 | loadWealthSystemDetail() | partials/ws/evaluations.php | evaluation_scores | domains render with grades |
| Edit + Save evals | Business_Requirements §6 | saveEvaluationScores() | detail_enhanced.php form | evaluation_scores | POST → reload → scores persist |
| Load LLM notes | Business_Requirements §5 | loadWealthSystemDetail() | partials/ws/llm_analysis.php | llm_analysis | summary + model render |
| Edit + Save LLM | Business_Requirements §6 | saveLlmAnalysis() | detail_enhanced.php form | llm_analysis | POST → reload → summary persists |
| Load IPlace | Business_Requirements §4 | detail() | partials/ws/iplace.php | iplace_scoring | composite + recommendation render |
| Load VectorVest | Business_Requirements §3 | detail() | partials/ws/vectorvest.php | — | checklist points + details render |
| Graceful missing-data | Business_Requirements §7,8 | try/catch in loaders | fallbacks | all | remove table → page loads with empty states |
