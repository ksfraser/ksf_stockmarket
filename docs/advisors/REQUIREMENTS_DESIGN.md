# Public-Facing AI Advisor Personas — Requirements and Design

## Use Cases

### 1. Public Reference Portfolios
Show independent model portfolios run by personas that mimic known styles (Buffett, Lynch) and systematic strategies (index regions/sectors, day/week/month/bi-annual trading). Regular users can view them without logging in.

### 2. Simulation Evidence
Each advisor runs with the same portfolio tables as regular users, so results are comparable. Advisors start from the same initial conditions and execute trades via the same mechanics (mid-price fills on daily bars).

### 3. Strategy Comparison
Index advisors isolate regional/sector exposures. Trader advisors isolate frequency/time-horizon effects. This produces actionable comparison data.

## Requirements

### Functional Requirements
- FR-1 Each advisor is a user-level account with a portfolio in the `portfolio` table.
- FR-2 Advisor portfolios are public; regular user portfolios private by default.
- FR-3 Start date is fixed to 2025-01-02 with an initial cash balance of 100,000 CAD.
- FR-4 Advisor trades are priced at the day's mid price (approximate from open/high/low/close).
- FR-5 Strategy modules map to advisor accounts:
  - warren-buffet
  - peter-lynch
  - index-canada
  - index-usa
  - index-euro
  - index-cad-us
  - index-energy
  - index-essentials
  - index-tech
  - index-bio
  - aggressive-day-trader
  - weekly-trader
  - monthly-trader
  - bi-annual-trader
- FR-6 Day trader executes daily; weekly once per week; monthly once per month; bi-annual twice per year.
- FR-7 Strategies may pull ideas from TradingView via MCP and news + LLM impact notes for volume/range anomalies.
- FR-8 Advisor run metadata is recorded for each trade date/run.

### Non-Functional Requirements
- NFR-1 Use existing schema where possible; avoid duplicate portfolio logic.
- NFR-2 Minimal UI changes; public flag implemented at data layer only.
- NFR-3 All new database objects are backward compatible with existing code.

## Database Design

### New Tables

```sql
CREATE TABLE IF NOT EXISTS advisor_accounts (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id INT UNSIGNED NOT NULL,
  slug VARCHAR(64) NOT NULL,
  display_name VARCHAR(128) NOT NULL,
  strategy VARCHAR(64) NOT NULL,
  profile_json JSON NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_slug (slug),
  UNIQUE KEY uk_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS portfolio_visibilities (
  user_id INT UNSIGNED NOT NULL,
  visibility ENUM('private','public','unlisted') NOT NULL DEFAULT 'private',
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS advisor_runs (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  advisor_slug VARCHAR(64) NOT NULL,
  user_id INT UNSIGNED NOT NULL,
  trade_date DATE NOT NULL,
  status ENUM('queued','running','complete','failed') NOT NULL DEFAULT 'queued',
  started_at TIMESTAMP NULL,
  completed_at TIMESTAMP NULL,
  result_json JSON NULL,
  error_message TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_advisor_date (advisor_slug, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS advisor_trades (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  advisor_slug VARCHAR(64) NOT NULL,
  user_id INT UNSIGNED NOT NULL,
  trade_date DATE NOT NULL,
  symbol VARCHAR(16) NOT NULL,
  action ENUM('BUY','SELL','HOLD') NOT NULL,
  shares DECIMAL(14,4) NOT NULL,
  price DECIMAL(10,2) NOT NULL,
  commission DECIMAL(10,2) NOT NULL DEFAULT 9.95,
  notes TEXT NULL,
  news_impact_json JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_advisor_symbol_date (advisor_slug, symbol, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Schema Changes to `portfolio`/`users`
No required schema changes if we keep advisor identity in `advisor_accounts` and visibility in `portfolio_visibilities`.

## Advisor Strategy Mapping

| Advisor | Strategy module | Frequency |
|---|---|---|
| warren-buffet | value_investor | monthly |
| peter-lynch | grow_at_reasonable_price | weekly |
| index-canada | cdn_index | bi_annual |
| index-usa | us_index | bi_annual |
| index-euro | euro_index | bi_annual |
| index-cad-us | cad_us_balanced_index | bi_annual |
| index-energy | sector_index_energy | monthly |
| index-essentials | sector_index_essentials | monthly |
| index-tech | sector_index_tech | monthly |
| index-bio | sector_index_bio | monthly |
| aggressive-day-trader | momentum_day | daily |
| weekly-trader | swing | weekly |
| monthly-trader | position | monthly |
| bi-annual-trader | long_hold | bi_annual |

## Execution Rules
- For any daily-bar strategy, execution price = mid price = (high + low + close) / 3 unless only close/open exist, then use day mid price approximation.
- All buys/sells reserve cash in portfolio `portfolio` table by updating cash position; sell first before buy.

## Public Exposure Rules
- Public route `/advisors/{slug}` or equivalent should expose:
  - Current holdings
  - Trade history
  - Run history
- Hidden fields for regular users should continue to remain private unless explicitly public.

## Implementation Approach
1. Add the SQL migration above.
2. Add bootstrap script to create advisor users and cash start position.
3. Add advisor strategy engine to run scheduled simulations.
