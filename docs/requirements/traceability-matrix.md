# Requirements Traceability Matrix
## KSF Stock Market Analysis System

| Business Req | Functional Req | User Story | DB Table(s) | PHP Class | Python Script | Status |
|---|---|---|---|---|---|---|
| BR-1: Portfolio Tracking | FR-7 User Mgmt | US-12 Manage Users | users, roles | UserController, UserModel | — | Phase 1 |
| BR-1 | FR-7 | US-2 Add Transaction | user_trades, portfolio | TransactionController | — | Phase 1 |
| BR-1 | FR-7 | US-1 View Dashboard | portfolio, portfolio_history | PortfolioController | — | Phase 1 |
| BR-1 | FR-7 | US-3 Track History | portfolio_history | PortfolioHistoryModel | — | Phase 1 |
| BR-2: Stock & ETF Analysis | FR-2 TA | US-4 View TA | stockprices, daily_indicators, daily_tier2, ta_values | TAController, PythonBridge | ta_calculator.py | Phase 1 |
| BR-2 | FR-2 | US-5 Run Screen | motleyfool, investorplace, tenets | ScreenController | screener.py | Phase 2 |
| BR-2: Stock & ETF Analysis | FR-3 Screening | US-5 Run Screen | tradingview_screener_results | StockController::screener() | — | Phase 1 |
| BR-2 | FR-3 | — | tradingview_screener_results | api_screener (AJAX) | — | Phase 1 |
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
| — | FR-7 | US-13 Watchlists | watchlists, watchlist_symbols | WatchlistController | — | Phase 2 |
| BR-1: Advisor Accounts | FR-9 Shared Access | US-14 Share Advisor Portfolio | portfolio, portfolio_visibilities, portfolio_share_users | SharedWithMeController | — | Phase 2 |
| BR-1 | FR-9 | US-15 View Shared Portfolio | portfolio | SharedWithMeController | — | Phase 2 |
| BR-1 | FR-9 | US-16 View Shared Transactions | portfolio_trades | SharedWithMeController | — | Phase 2 |
| BR-4: Advisor Backtests | FR-4 Backtesting | US-17 Advisor Leaderboard | backtest_runs | AdvisorBacktestController | advisor_backtest.py | Phase 2 |
| BR-2: Rating Screener | FR-3 Screening | US-18 Rating Presets | tradingview_screener_results | StockController::screener() | populate_ratings.py | Phase 2 |
| BR-2 | FR-Population | US-19 Analyst Ratings Population | analyst_ratings | — | populate_analyst_ratings.py | Phase 2 |
| BR-1: Broker Stops | FR-10 Stop Orders | US-20 Place Stop | broker_stop_orders | BrokerStopController | — | Phase 2 |
| BR-1 | FR-10 | US-21 Historical Stops | broker_stop_orders | BrokerStopController | — | Phase 2 |
| BR-1 | FR-11 Alerts | US-22 Review Alerts | alert_queue | AlertsController | — | Phase 2 |
| BR-5 | FR-1 | — | stockprices, price_intraday | — | sync_stock_prices.py (YFinanceFetcher → Repository) | Phase 1 |
| BR-5 | FR-1 | — | stockprices, price_intraday | — | detection_triggers.py (Repository read, --sqlite) | Phase 1 |
| BR-5 | NFR-4.1.3 | — | stockprices, price_intraday | StockPriceDTO | src/db/stock_price_dto.py | Phase 1 |
| BR-5 | NFR-4.1.2 | — | stockprices, price_intraday | StockPriceRepository | src/db/sqlite_price_repository.py, mariadb_price_repository.py | Phase 1 |
| BR-1 | FR-3 Screening | US-5 Run Screen | price_intraday | — | src/db/price_fetcher.py (YFinanceFetcher) | Phase 2 |
| BR-4: Custom Advisors | FR-4 Backtesting | US-23 Compose Advisor | strategy_rules | AdvisorComposerController | src/rules/composer.py | Phase 3 |
| BR-4: Custom Advisors | FR-4 Backtesting | US-24 Combo Test | backtest_runs, backtest_trades | AdvisorBacktestController | src/rules/pipeline_integration.py | Phase 3 |
| BR-4: Custom Advisors | FR-4 Backtesting | US-25 Param Sweep | backtest_runs | AdvisorBacktestController | src/rules/pipeline_integration.py | Phase 3 |
| BR-4: Custom Advisors | FR-4 Backtesting | US-26 Forward Walk | backtest_runs | AdvisorBacktestController | src/rules/pipeline_integration.py | Phase 3 |
| BR-4: Custom Advisors | FR-9 Shared Access | US-27 Publish Advisor | strategy_rules, portfolio_share_users | SharedWithMeController | src/rules/composer.py | Phase 3 |
| BR-4: Custom Advisors | — | — | strategy_rules | — | ga_optimizer.py ↔ rules | Phase 3 |
| BR-4: Custom Advisors | — | — | strategy_rules | — | nn_agent.py ↔ rules | Phase 3 |
| BR-7: Advisor Hiring | FR-6 | US-28 Hire Advisor | user_advisors, advisor_recommendations | AdvisorHiringController, AdvisorNotificationController | run_advisor_recommendations.py | Phase 3 |
| BR-7 | FR-6 | US-29 Notification Preferences | user_settings | AdvisorNotificationController | advisor_notifier.py | Phase 3 |
|| BR-7 | FR-6 | US-30 View Recommendations | advisor_recommendations | AdvisorNotificationController | advisor_notifier.py (deliver) | Phase 3 |
|| BR-7 | FR-6.9 | US-31 WhatsApp Delivery | advisor_recommendations | AdvisorNotificationController | advisor_notifier.py (WhatsApp gateway) | Phase 3 |
|| BR-7 | FR-6.10 | US-32 Private Discord | advisor_recommendations | AdvisorNotificationController | advisor_notifier.py (Discord) | Phase 3 |
|| BR-7 | FR-104 | US-33 Admin Optional Rules | strategy_rules | AdminSettingsController | seed_strategy_rules.py | Phase 3 |
|| BR-105 | FR-103 | Optional KB rules: min reward:risk, emergency buffer, blacklist | strategy_rules.risk_rules.optional_rules | rules/risk.py + rules_backtest.py | Done |
|| BR-105 | FR-104 | Admin edit optional_rules | strategy_rules.risk_rules.optional_rules | AdminSettingsController | seed_strategy_rules.py | Phase 3 |
|| BR-105 | FR-105 | Leverage + margin rules | strategy_rules.risk_rules.optional_rules | rules/risk.py + rules_backtest.py | Done |
