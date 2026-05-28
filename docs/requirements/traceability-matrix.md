# Requirements Traceability Matrix
## KSF Stock Market Analysis System

| Business Req | Functional Req | User Story | DB Table(s) | PHP Class | Python Script | Status |
|---|---|---|---|---|---|---|
| BR-1: Portfolio Tracking | FR-5 User Mgmt | US-12 Manage Users | users, roles | UserController, UserModel | — | Phase 1 |
| BR-1 | FR-5 | US-2 Add Transaction | user_trades, portfolio | TransactionController | — | Phase 1 |
| BR-1 | FR-5 | US-1 View Dashboard | portfolio, portfolio_history | PortfolioController | — | Phase 1 |
| BR-1 | FR-5 | US-3 Track History | portfolio_history | PortfolioHistoryModel | — | Phase 1 |
| BR-2: Stock & ETF Analysis | FR-2 TA | US-4 View TA | stockprices, daily_indicators, daily_tier2, ta_values | TAController, PythonBridge | ta_calculator.py | Phase 1 |
| BR-2 | FR-2 | US-5 Run Screen | motleyfool, investorplace, tenets | ScreenController | screener.py | Phase 2 |
| BR-2 | FR-3 Screening | US-6 ETF Screener | etf_metadata, etf_scores | ETFScreenerController | etf_screener.py | Phase 2 |
| BR-2 | FR-1 Data Import | — | stockprices, data_import_log | — | migrate_legacy_prices.py | Phase 1 |
| BR-3: Scoring Preservation | FR-2 | — | evalsummary, motleyfool, investorplace, tenets, evalbusiness, ratios, quarter_statement, evalmanagement, evalmarket, evalvalue, scoring_history | ScoringController | scoring_engine.py, llm_analyzer.py | Phase 2 |
| BR-3 | — | — | signal_weights | — | correlation_analysis.py | Phase 3 |
| BR-4: Backtesting | FR-4 | US-7 Configure | backtest_runs | BacktestController | backtest_engine.py | Phase 1 |
| BR-4 | FR-4 | US-8 View Results | backtest_runs, backtest_trades | BacktestResultsController | — | Phase 1 |
| BR-5: Data Reliability | FR-1 | — | stockprices (partitioned) | — | migrate_legacy_prices.py | Phase 1 |
| BR-5 | — | — | All tier tables | — | backup_cron.py | Phase 1 |
| — | FR-6 FA Integration | US-10 Record Transfer | fa_transfers | FAController | — | Phase 2 |
| — | FR-6 | US-11 Revalue Assets | portfolio, fa_transfers | FARevaluationController | revalue.py | Phase 2 |
| — | FR-5 | US-13 Watchlists | watchlists, watchlist_symbols | WatchlistController | — | Phase 2 |
