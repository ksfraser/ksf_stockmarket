# Changelog

All notable changes to the OWL Investment Dashboard project.

## [5.0.0] — 2026-06-01

### Added — Web Dashboard (Complete)

#### Authentication & User Management
- `users`, `user_settings`, `user_sessions` MySQL tables
- `AuthController` — login, logout, session management, remember-me cookies (30-day)
- `UserController` — per-user settings page (color scheme, font size, compact tables, decimal places, date format, default landing page, password change)
- Login page at `?action=login` (default: admin / admin123)
- Nav bar shows username + logout link when authenticated

#### My Dashboard (`?action=my_dashboard`)
- Buy/sell recommendations based on RSI, MACD, SMA crossovers, trailing stop proximity
- Upcoming earnings dates for portfolio symbols
- Upcoming ex-dividend dates with rate and yield
- Top gainers/losers **within portfolio** (not all symbols)
- Data coverage stats for portfolio symbols only

#### App Dashboard (`?action=overview`)
- Renamed from "Dashboard" to "App Dashboard" with clear header
- All-symbol top 10 gainers and losers
- Full data coverage stats (total symbols, with indicators, active fetching, price/indicator rows, freshness)
- Link to switch to My Dashboard

#### Enhanced Portfolio Page (`?action=portfolio`)
- **Annualized P&L %** column (CAGR since entry date)
- **Cost-Basis Dividend Yield** column (yield vs what was paid)
- **Cost-Basis Allocation %** column (cost as % of total portfolio cost)
- **Stop $** column with color coding: green (safe), yellow (within 2%), red (breach)
- **Enhanced Safety** column with tooltip explaining dividend safety score
- **Strategy** column expanded: trailing stop % + ATR multiplier
- Account type filter dropdown (All / RRSP / TFSA / MARGIN)
- Total row with aggregate annualized P&L

#### Transactions Page (`?action=transactions`)
- Filterable by account, symbol, type (BUY/SELL/DIVIDEND/SPLIT), date range
- Summary stats: total trades, buys, sells, dividends
- Color-coded rows: green for buys, red for sells

#### Strategy Pages
- **Stock Selection Strategies** (`?action=strategy_stock`):
  - Candlestick Patterns (12% WR, needs improvement)
  - Oscillators RSI/MACD/Stochastic (44% WR, promising)
  - Neural Network Directional (53.1% WR, battle tested)
  - Buffett Quality Score (screening tool)
  - Ensemble Blend (51.4% WR, battle tested)
  - Each with win rate, profit factor, max drawdown, avg win/loss, implications, last-tested timestamp

- **Money & Risk Management** (`?action=strategy_money`):
  - Kelly Criterion quick reference with formula and worked example
  - Win Rate Inversion + Kelly Multiplier
  - Trailing Supertrend Stop (ATR-based, tightening rules)
  - Sleeve-Based Position Sizing (Core 40%, Tactical 30%, Income 20%, Satellite 10%)
  - Fixed Fractional Position Sizing (1-2% risk per trade)
  - Stop methodology explainer (when trailing stop overrides fixed stop)

#### Detail Page Charts
- `enhanced_charts.js` loads for detail/indicators pages
- Price chart with entry, stop, analyst targets, news markers
- RSI, MACD, Stochastic oscillator charts
- ATR and Bollinger Band charts

### Added — Python DB Adapter Layer
- Abstract `DBConnection` interface (`python/db/adapter.py`)
- `MySQLAdapter` — pymysql, connects to ksfraser.ca
- `SQLiteAdapter` — sqlite3, for local unit testing
- `Database.from_config()` factory — picks adapter from `config.yaml` `db.engine` key
- 18 passing unit tests (`tests/unit/test_db_adapter.py`)
- `pyproject.toml` — Python project metadata + dependencies

### Changed
- `DashboardController` — now provides app-level stats (all symbols, all gainers/losers)
- `StockController::portfolio()` — enhanced with annualized P&L, cost-basis div yield, stop calculations, strategy details
- `layout.php` — updated nav with My Dashboard, Transactions, Strategies links; user auth menu
- `index.php` — added auth routes, my_dashboard, settings, transactions, strategy_stock, strategy_money
- CSS: grey background (#4a5568), blue-ish data boxes (#5a7a9e), white text theme
- `symbol_master.is_active` — Python fetcher respects flag; PHP shows all symbols (historical data preserved)

### Database Changes
- New tables: `users`, `user_settings`, `user_sessions`
- `portfolio` table added: `trailing_stop_pct`, `stop_loss_pct`, `atr_multiplier`, `strategy`
- `symbol_master` table added: `is_active`, `deactivated_at`, `deactivated_reason`
- `exchange_mapping` table for symbol-to-exchange lookup

### Architecture
- PHP: PSR-4 autoloading, `declare(strict_types=1)`, DI via constructors, SRP controllers
- Python: Type hints, abstract base classes, config-driven factory pattern
- Hybrid: PHP web UI + Python analysis, shared MySQL at ksfraser.ca
- Apache serves `/stockmarket/` and `/dashboard/` from `/var/www/stockmarket-app/`

---

## [4.0.0] — 2026-05-31

### Added
- Walk-forward analysis framework (no future data peeking)
- 222-indicator correlation study with horizon analysis
- Candlestick pattern backtest (12% win rate — dropped as standalone)
- Oscillator backtest (44% win rate — promising with filters)
- Neural Network directional predictor (53.1% accuracy)
- Ensemble blender (51.4% win rate, 1.58 profit factor)
- Kelly Criterion position sizing simulator
- Sleeve-based allocation model (Core/Tactical/Income/Satellite)

---

## [3.0.0] — 2026-05-30

### Added
- PHP web dashboard with portfolio overview
- Symbol detail page with fundamentals
- MySQL schema v2 with partitioned tables
- Tax-aware return calculation engine
- Forex-aware allocation (±5% bounded shift)

---

## [2.0.0] — 2026-05-27

### Added
- Python price fetcher pipeline (`daily_pipeline.py`)
- Technical analysis with TA-Lib (142 indicators per symbol)
- Backtesting engine framework
- SQLite → MySQL migration tools

---

## [1.0.0] — 2026-05-15

### Added
- Initial project structure
- MySQL database with stockprices, symbol_master tables
- Basic PHP front controller
- CSV portfolio import (23 holdings from AccountHoldings files)
