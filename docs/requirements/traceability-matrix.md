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
|| BR-6: External Strategy Research | FR-7 Research Agent | — | research_briefs | AdvisorController | research_agent.py | Phase 3 |
|| BR-6 | FR-8 External Auth | — | external_auth_tokens, system_settings | ExternalAuthController | — | Phase 3 |
|| BR-6 | FR-9 Risk Gate | — | risk_thresholds.json, strategy_registry | AdvisorController (preTradeGate) | — | Phase 3 |
|| BR-6 | FR-10 Automation | — | research_briefs | AdvisorController | research_agent.py + cron | Phase 3 |
|| BR-14: Zacks RW Screen Pipeline | FR-14: Data pipeline, schema, field contract, backtest/stat computation | UC-14a Import and run screens · UC-14b Backtest & Advisor portfolio · UC-14c Nightly pipeline | user_screens, zacks_broker_recommendations, zacks_ratios_history, stock_performance_windows, fundamentals (zacks_*), alert_queue | ZacksScreenController, ZacksScreenImporter, ZacksScreenRunner, ZacksUniverse, ZacksRankPopulator, ZacksFieldResolver, ZacksRwConfig | zacks_scraper.py, refresh_perf_windows.php, zacks_signal_dispatcher.py, import_zacks_screens.php | Phase 3 (in progress) |
|| BR-14 | FR-14 | UC-14c Nightly EPS-revision signal dispatch | fundamentals (zacks_eps_change_f1_4w, forward_eps), alert_queue, system_settings | — | zacks_signal_dispatcher.py | Phase 3 (in progress) |
|| BR-14 | FR-14 | UC-14b Backtest & Advisor portfolio | stockprices, stock_performance_windows, user_screens, portfolio + portfolio_history (Advisor portfolio running totals) | ZacksScreenRunner, ZacksUniverse | refresh_perf_windows.php (window pre-compute for backtest pricing) | Phase 3 (in progress) |
|| BR-15: Stock Price Storage Refactor — Per-Symbol Tables in Per-Exchange DBs | FR-15: Per-symbol history tables × per-exchange DBs; recent cross-symbol table per exchange; quarterly/post-earnings window cadence; centralized schema management; formulaic routing from symbol_master.exchange | UC-15a Migrate existing prices into per-symbol/per-exchange storage · UC-15b Nightly dual-write (history + recent) · UC-15c Routing validation (formulaic from symbol_master) · UC-15d Performance-window recalculation (quarterly/post-earnings) · UC-15e Backtest cross-symbol audit | stockprices (being split out), stockprices_<symbol> (per-symbol history), stockprices_recent_<exchange> (per-exchange recent), stock_performance_windows, symbol_master (+ split_factor_current), ksfraser_sm_* exchange DBs | SymbolTableRouter, StockPriceRepository, PriceIngestionService, PerformanceWindowService, SchemaManager, migrate_prices_to_exchange_dbs.php | nightly ingestion (dual-write), migrate_prices_to_exchange_dbs.php, performance-window recalc jobs | Phase 3 (in progress) |
|| BR-15 | FR-15 | UC-15a Migration | stockprices (source), stockprices_<symbol> (dest), stockprices_recent_<exchange> (dest), symbol_master.split_factor_current | SchemaManager, migrate_prices_to_exchange_dbs.php | migrate_prices_to_exchange_dbs.php | Phase 3 (in progress) |
|| BR-15 | FR-15 | UC-15b Nightly dual-write | stockprices_<symbol>, stockprices_recent_<exchange>, symbol_master.split_factor_current, stock_performance_windows (short windows) | PriceIngestionService, SymbolTableRouter, StockPriceRepository | nightly price ingestion (dual-write path) | Phase 3 (in progress) |
|| BR-15 | FR-15 | UC-15c Routing validation | symbol_master, ksfraser_sm_* exchange DBs | SymbolTableRouter | — | Phase 3 (in progress) |
|| BR-15 | FR-15 | UC-15d Window recalculation (quarterly/post-earnings) | stock_performance_windows, stockprices_<symbol> (history source), stockprices_recent_<exchange> (short-window source) | PerformanceWindowService | quarterly + post-earnings recalc jobs, nightly short-window rollup | Phase 3 (in progress) |
|| BR-15 | FR-15 | UC-15e Backtest cross-symbol audit | stockprices_<symbol>, stockprices_recent_<exchange>, backtest_runs, backtest_trades, portfolio, portfolio_history | StockPriceRepository, BacktestEngine (read path) | backtest_engine.py, backtest.py (audit) | Phase 3 (follow-up) |
