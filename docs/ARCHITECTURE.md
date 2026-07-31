# Investment Agent — Architecture & Specification

> **Version:** 5.0 | **Date:** 2026-06-01 | **Repo:** `ksfraser/ksf_stockmarket`
> **Status:** Web dashboard complete. Auth, portfolio, transactions, strategies pages live. GA/NN/RL agents in development.

---

## 1. Problem Statement

**Objective:** Maximize after-tax portfolio value over a 10-year horizon, subject to annual December withdrawals for living expenses, to reach a retirement target of $250,000.

**Context:**
- Kevin Fraser, Airdrie Alberta, 3rd tax bracket ($111K-$173K taxable income)
- Accounts: TFSA ~$20K, RRSP ~$30K initial
- CIBC Investor's Edge brokerage (TSX free trades, US at $9.95/trade)
- Annual withdrawal: $12K in December
- TFSA room: $7K/yr, RRSP room: ~$6K/yr
- Transition income may decline (part-time) — creates RRSP deregistration opportunity
- 23 portfolio holdings across RRSP, TFSA, MARGIN accounts (~$137K book, ~$384K market)
- 404 symbols tracked in `symbol_master`, 49 with price data (May 2025)

---

## 2. Design Principles

### 2.1 Sleeves Not Consensus
Strategies are **competing allocation buckets**, not voting signals. Each sleeve has:
- Its own entry/exit rules
- Its own time horizon
- Its own signal set
- Its own position sizing model

The Blender optimizes how much capital goes to each sleeve, not how signals are averaged.

### 2.2 Everything Is Configurable
Every numeric parameter lives in `config.yaml`. Defaults are research-backed but overridable. The GA/NN/RL agents optimize subsets of these parameters during walk-forward training.

### 2.3 Walk-Forward Only — No Future Peeking
All analysis uses strict `data[:current_date]` cut-off. Training window rolls forward annually.

### 2.4 Tax-Aware at Every Layer
Tax impact is computed at every decision point — entry, rebalance, exit, harvest. Account placement (which sleeve goes in which account) is part of the optimization.

### 2.5 Forex Matters
USD/CAD trends affect US vs CDN allocation. The GA includes forex as a feature signal. Forex shift is bounded ±5% per signal to avoid overreacting to noise.

### 2.6 Per-Indicator Horizon Selection
From the 222-indicator correlation study:
- **Short (1-5d):** Bollinger position, MA deviation → entry timing
- **Medium (10-20d):** RSI, MACD, ADX, NATR → direction, regime, sizing
- **Quarterly (90d):** Dividend calendar, FCF seasonality → cash flow planning
- Candlestick patterns: uniformly noise at all horizons → **dropped entirely**

### 2.7 SOLID PHP, Typed Python
- PHP: PSR-4 autoloading, `declare(strict_types=1)`, DI via constructors, SRP controllers
- Python: Type hints, abstract base classes, config-driven factory pattern
- Both: Comprehensive test coverage (pytest for Python, PHPUnit for PHP)

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR (weekly)                        │
│  Runs Layer 0, triggers Layer 1 daily, feeds GA/NN/RL          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
     ┌─────────────────────┼─────────────────────┐
     ▼                     ▼                     ▼
┌─────────┐         ┌──────────┐         ┌──────────┐
│ Layer 0  │         │ Layer 1  │         │ Layer 2  │
│ Screener │────────▶│ Signals  │────────▶│ Money    │
│ (weekly) │         │ (daily)  │         │ Mgt      │
└─────────┘         └──────────┘         └──────────┘
     │                     │                     │
     ▼                     ▼                     ▼
┌─────────┐         ┌──────────┐         ┌──────────┐
│ Layer 3  │         │ Layer 4  │         │Agents    │
│ Portfolio│         │ Risk     │         │GA/NN/RL │
│ Construct│         │ Mgt      │         │(weekly)  │
└─────────┘         └──────────┘         └──────────┘
     │                     │                     │
     ▼                     ▼                     ▼
┌──────────────────────────────────────────────────────────┐
│              BLENDER (quarterly rebalance)                │
│  GA weight × static allocation                            │
│  NN weight × tactical timing                              │
│  RL weight × dynamic rebalancing                          │
│  → Final positions per sleeve                             │
└──────────────────────────────────────────────────────────┘
```

### 3.0 Web Dashboard (PHP 8.1 + Apache)

**URL:** `http://192.168.1.102/stockmarket/` and `http://192.168.1.102/dashboard/`

**Stack:** PHP 8.1, Apache, PHP-FPM, PDO MySQL, inline CSS/JS (canvas charts), sessions

**Directory Layout:**
```
/var/www/stockmarket-app/          ← Workspace (authoritative)
  index.php                        ← Front controller
  src/Controller/                  ← PSR-4 controllers
    DashboardController.php        ← App-level overview
    StockController.php            ← Symbol list, detail, portfolio
    TransactionController.php      ← Transaction history
    StrategyController.php         ← Backtested strategy results
    UserController.php             ← My Dashboard + Settings
    AuthController.php             ← Login/logout/session
    SymbolAdminController.php      ← Symbol activation/deactivation
    FundamentalsController.php     ← Fundamental data fetcher
  src/Model/Database.php           ← PDO singleton
  src/View/helpers.php             ← Template helpers
  templates/                       ← PHP templates
  config/database.php              ← DB credentials

/var/www/html/stockmarket/         ← Apache web root (rsync copy)
/var/www/html/dashboard-owl/       ← /dashboard/ alias (copy)
```

**Web Routes:**

| Action | Controller | Description |
|---|---|---|
| `overview` (default) | DashboardController | App-level dashboard: all-symbol gainers/losers, portfolio summary, full data coverage |
| `my_dashboard` | UserController | Personal dashboard: buy/sell recs, earnings, dividends, portfolio movers |
| `portfolio` | StockController | Holdings with annualized P&L, cost-basis div yield, stop prices, strategy details |
| `transactions` | TransactionController | Filterable transaction history (account/symbol/type/date) |
| `detail&symbol=X` | StockController | Single symbol with Buffett score, oscillators, analyst targets, options, news |
| `list` | StockController | All 404 tracked symbols with prices |
| `strategy_stock` | StrategyController | Stock selection strategies with backtested results |
| `strategy_money` | StrategyController | Money/risk management with Kelly criterion, stops, sleeves |
| `admin_symbols` | SymbolAdminController | Symbol activate/deactivate, exchange mapping |
|| `settings` | UserController | Per-user settings (color scheme, font size, password) |
|| `advisor` | AdvisorController | Research briefs, risk thresholds, pre-trade gate |
|| `external_auth` | ExternalAuthController | OAuth/API key auth for Reddit, TradingView, arXiv |
|| `admin_settings` | AdminSettingsController | System config (Discord, LLM, external auth credentials) |
|| `login` / `logout` | AuthController | Session-based auth with remember-me cookies |

**Authentication:**
- Session-based PHP auth with `user_sessions` table for remember-me (30-day cookies)
- Default admin: `admin` / `admin123` (change immediately)
- Per-user settings: color scheme, font size, compact tables, decimal places, date format, landing page

**Portfolio Page Columns:**

| Column | Description |
|---|---|
| Symbol | Link to detail page |
| Account | RRSP / TFSA / MARGIN |
| Shares | Quantity |
| Cost Basis | Average cost per share |
| Current | Latest close price |
| Market Value | Shares × current price |
| P&L $ | Dollar gain/loss |
| P&L % | Percentage gain/loss |
| **Annualized P&L %** | CAGR since entry date |
| **Cost Basis Allocation %** | Cost basis as % of total portfolio cost |
| Div Yield | Current dividend yield |
| **Cost-Basis Div Yield** | Yield relative to what was paid |
| **Safety** | Dividend safety score with tooltip explanation |
| **Stop $** | Effective stop price in green/yellow/red |
| **Strategy** | Trailing stop % + ATR multiplier details |

**CSS Theme:** Grey background (#4a5568), blue-ish data boxes (#5a7a9e), white text, accent blue (#63b3ed)

### 3.1 Layer 0 — Universe Screener (weekly, Sundays)
**Input:** 404 symbols from CurrentData/ + portfolio holdings
**Output:** Per-sleeve candidate list in MySQL `layer0_candidates`

```
For each symbol:
  1. Fetch price, volume, market cap
  2. Global hard filter: price > $5, volume > 100K/day, cap > $500M
  3. CIBC Investor's Edge eligibility check
  4. For each active sleeve:
     a. Fetch fundamentals from yfinance (ROE, D/E, FCF, margins, div)
     b. Buffett score (0-100)
     c. Apply sleeve-specific filters
     d. Tag symbol with sleeve(s) it qualifies for
  5. Save top N per sleeve to DB
```

**Sleeve-specific screening criteria:**
| Criteria | Core (Buffett) | Tactical (Swing) | Income (Div) | Satellite (Spec) |
|---|---|---|---|---|
| ROE min | 15% | 10% | 10% | 5% |
| D/E max | 0.3 | 0.8 | 0.6 | — |
| FCF streak | 5yr | 2yr | — | — |
| Gross margin | 40% | 25% | — | — |
| Volatility | < 1.2 beta | 20-50% | — | > 30% |
| Div yield | — | — | > 2.5% | < 2% |
| Market cap | > $5B | > $1B | > $2B | > $500M |

### 3.2 Layer 1 — Signal Generation (daily, market close)
**Input:** Layer 0 candidates + indicators from `indicators_json` table (142 per symbol/day)
**Output:** Per-symbol signals per sleeve

```
For each candidate in each sleeve:
  a. Short-horizon: BB position (3d), MA deviation, RSI
  b. Medium-horizon: RSI(14), MACD, ADX, NATR(14)
  c. Regime: ADX > 20 required for trend trades
  d. Volume: OBV > 50d average
  e. Conviction: count agreeing signals / total signals
  f. Output: signal_strength [-1, 1], conviction [0, 1]
```

### 3.3 Layer 2 — Money Management
- ATR risk model: shares = (portfolio × risk_pct) / (ATR × stop_mult)
- Kelly Criterion: f* = (bp - q) / b, quarter-Kelly for satellite
- Trailing stop activation: triggered at +3× ATR profit
- Stop methodology: max(trailing_stop, fixed_stop) — trailing overrides when higher

### 3.4 Layer 3 — Portfolio Construction
- Tax-loss harvest: Dec only if unrealized loss > 5% and saves > $50 tax
- Sleeve allocation: Core 40%, Tactical 30%, Income 20%, Satellite 10%
- Cash buffer: maintain 5%

### 3.5 Layer 4 — Risk Management
- Portfolio drawdown > 15% → reduce position sizes 50%
- Portfolio drawdown > 25% → shift 30% to cash
- VIX > 30 → halve new position sizes
- VIX > 40 → emergency cash shift

### 3.6 Paperclip Zero-Human Trading Firm Components

Mapped to existing stack to minimize re-architecture:

**Research Agent** (`python/research_agent.py` + `AdvisorController.php`)
- **Internal brief** (daily 02:00): Aggregates ATR stop optimization leaders, evaluation signals, fundamental scores into `research_briefs` DB table
- **External brief**: Scans Reddit (`r/algotrading`, `r/quant`, `r/options`, `r/investing`), arXiv quant finance, TradingView ideas
- **LLM scoring**: Novelty/feasibility/edge 1-10 (heuristic until LLM endpoint wired)
- **Outputs**: Markdown + JSON in `memory/institutional/`, DB rows in `research_briefs`
- **Hermes skill**: `stockmarket-research-agent` for on-demand execution
- **Nightly cron**: `a0fa8b782742` at 02:00 daily

**Risk Gate** (`AdvisorController::preTradeGate()` + `config/risk_thresholds.json`)
- Pre-trade checks: Sharpe minimum 1.5, max drawdown 15%, strategy gates
- Verdicts: APPROVED, REVIEW, BLOCKED
- Paper trading default; live trading requires board approval
- Thresholds stored in `config/risk_thresholds.json` (editable only by board)

**External Provider Auth** (`ExternalAuthController.php` + `external_auth_tokens` table)
- OAuth 2.0 authorization code flow for Reddit
- API key storage for TradingView, arXiv (extensible)
- Redirect URI: `http://192.168.1.102/stockmarket/?action=external_auth&view=callback&provider=reddit`
- Tokens stored as [REDACTED] in `external_auth_tokens` (unique per user/provider)
- Admin configures app credentials in `AdminSettingsController` → stored in `system_settings`

**Execution**
- Reuses `advisor_backtest.php` for paper-only execution
- No live broker credentials in system

---

## 4. Agent Ensemble

### 4.1 GA (DEAP) — Strategic Allocation Optimizer
**Purpose:** Find the optimal static allocation across sleeves and symbols within each sleeve.
**Fitness:** after_tax_terminal_value − λ_dd × max_drawdown − λ_cash_depletion × I(portfolio_hits_0)
**Training:** Walk-forward 2014-2018, test 2019-2024. Population 200, generations 100.

### 4.2 NN (PyTorch LSTM) — Tactical Return Predictor
**Purpose:** Predict 20-day forward return distribution for each candidate symbol.
**Architecture:** 2-layer LSTM (128 hidden, dropout 0.2), linear output head with uncertainty.
**Training:** Walk-forward on Layer 0 candidate symbols. Train on 5 years, validate on 1 year.
**Backtest result:** 53.1% directional accuracy

### 4.3 RL (SB3 PPO) — Dynamic Rebalancing Agent
**Purpose:** Learn when to deviate from GA static allocation based on market conditions.
**State:** Portfolio composition + signal consensus + market regime (ADX, VIX) + time since last rebalance
**Action:** For each position: [-1 sell half, -0.5 trim, 0 hold, +0.5 add, +1 double]
**Training:** 100K timesteps per walk-forward step, rolling annually.

### 4.4 Blender
```
final_weight(symbol) = 
  GA_weight × GA_static_weight(symbol) +
  NN_weight × NN_tactical_adjustment(symbol) +
  RL_weight × RL_dynamic_adjustment(symbol)
```
**Rebalancing:** Every 90 days, re-blend based on trailing 90-day Sharpe ratio of each agent.

---

## 5. Backtested Strategy Results (as of 2026-02-01)

| Strategy | Win Rate | Profit Factor | Max Drawdown | Status |
|---|---|---|---|---|
| Candlestick Patterns | 12% | 0.82 | -24.3% | Needs Improvement |
| Oscillators (RSI/MACD/Stoch) | 44% | 1.31 | -14.7% | Promising |
| Neural Network Directional | 53.1% | 1.42 | -11.2% | Battle Tested |
| Buffett Quality Score | N/A (screening) | N/A | N/A | Screening Tool |
| Ensemble Blend (NN+Osc+Cdl) | 51.4% | 1.58 | -9.1% | Battle Tested |
| Kelly + Win Rate Inversion | Varies | 1.72 | -6.8% | Recommended |
| Sleeve-Based Allocation | N/A | N/A | -8.2% | Active |

---

## 6. Database (MySQL at ksfraser.ca)

| Table | Purpose | Key Columns |
|---|---|---|
| `stockprices` | OHLCV daily prices | symbol, price_date, close, volume |
| `indicators_json` | 142 TA indicators per row | symbol, price_date, data (JSON) |
| `symbol_master` | 404-symbol universe | symbol, name, exchange, sector, is_active |
| `portfolio` | 23 current positions | symbol, account_type, shares, cost_basis, trailing_stop_pct, atr_multiplier |
|| `users` | Authentication | username, password_hash, role, is_active |
|| `user_settings` | Per-user preferences | user_id, setting_key, setting_value |
|| `user_sessions` | Remember-me tokens | id, user_id, expires_at |
|| `fundamentals` | Fundamental data | symbol, fetch_date, pe, div_yield, roe, ... |
|| `analyst_ratings` | Analyst predictions | symbol, date, firm, rating, price_target |
|| `symbol_news` | News articles | symbol, date, title, url, source |
|| `options_snapshot` | Options data | symbol, fetch_date, put_call_ratio, iv |
|| `exchange_mapping` | Symbol→exchange map | symbol, exchange, yahoo_suffix |
|| `transactions` | Transaction history | symbol, trade_date, type, quantity, price, total |
|| `research_briefs` | Strategy research briefs | brief_date, mode, category, title, summary, scores, source_url |
|| `external_auth_tokens` | OAuth/API tokens for external providers | provider, access_token, refresh_token, expires_at, is_active |
|| `system_settings` | System-wide config (LLM, Discord, external auth) | setting_key, setting_value, setting_type |
|| `advisor_recommendations` | Advisor trade recommendations | symbol, account_type, direction, entry_price, stop_price |
|| `advisor_trades` | Executed paper trades | symbol, trade_date, type, quantity, price, pnl |
|| `strategy_registry` | Strategy catalog for risk gate | strategy_key, name, category, sleeve, is_active, board_approved_for_live, params |

---

## 7. Python DB Adapter Layer

**Abstract interface** (`python/db/adapter.py`):
```python
class DBConnection(ABC):
    @abstractmethod
    def execute(self, query, params=None): ...
    @abstractmethod
    def fetchall(self): ...
    @abstractmethod
    def fetchone(self): ...
```

**Implementations:**
- `MySQLAdapter` — pymysql, connects to ksfraser.ca (PRIMARY)
- `SQLiteAdapter` — sqlite3, DEPRECATED (kept for testing only; all production data uses MariaDB)

**Factory:** `Database.from_config('config.yaml')` uses MariaDB by default.

**Tests:** Tests use MariaDB connection to ksfraser_stock_market.

---

## 8. Key Research Findings

### Indicator Horizons
| Horizon | Avg |corr| | Max |corr| | Best For |
|---|---|---|---|---|
| 1d | 0.016 | 0.047 | NATR only |
| 3d | 0.027 | 0.096 | Bollinger, MA deviation |
| 5d | 0.035 | 0.096 | Entry timing |
| 10d | 0.052 | 0.127 | Direction, regime |
| 20d | 0.066 | **0.162** | NATR, position sizing |

### Indicator Groups by Use
| Use | Indicators | Horizon |
|---|---|---|
| **Stock selection** | NATR_7/14/20, STDDEV_14, VAR_14 | 20d |
| **Entry timing** | BB position, MA deviation, short NATR | 3-5d |
| **Direction** | RSI, MACD(12,26,9), ADX | 20d |
| **Position sizing** | NATR (inverse relationship) | 20d |
| **Confirmation** | OBV rising, volume > 50d avg | 20d |
| **Candlestick patterns** | ALL 59: noise | ALL: ignore |

---

## 9. File Locations

| Component | Path |
|---|---|
| PHP workspace | `/var/www/stockmarket-app/` |
| Apache web root | `/var/www/html/stockmarket/` |
| Dashboard alias | `/var/www/html/dashboard-owl/` |
| Python project | `/home/ksf_stockmarket/ksf_stockmarket/` |
| Python DB adapter | `python/db/` |
| Python pipeline | `python/daily_pipeline.py` |
| Python research agent | `python/research_agent.py` |
| Python tests | `tests/unit/test_db_adapter.py` |
| Config | `config.yaml` (Python), `config/database.php` (PHP) |
| Risk thresholds | `config/risk_thresholds.json` |
| External auth config | `config/external_auth.json` |
| MySQL host | `ksfraser.ca` |
| DB name | `ksfraser_stock_market` |
