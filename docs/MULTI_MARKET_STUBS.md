# Multi-Market Expansion Plan for ksf_stockmarket

## Comparison: Jackson vs Our Architecture

| Aspect | Jackson (claude-code-stocks-futures) | ksf_stockmarket |
|--------|-------------------------------------|-----------------|
| Data | yfinance (Alpaca for live) | MariaDB partitioned stockprices |
| Process Mgmt | PM2 ecosystem | Cron jobs + PHP controller |
| Markets | Forex (EUR/USD), Futures (NQ1!) | Stocks (TSX/USD), Stablecoins |
| DB | PostgreSQL | MariaDB |
| Architecture | Single-file Python strategy | 3-layer PHP/Python hybrid |

## Key Differences / Gaps

1. **No Forex/Futures support** - We only have stock symbols
2. **No PM2 process management** - We use cron jobs instead
3. **No Alpaca integration** - We use different data sources
4. **No multi-instrument scaling** - Need to extend `run_walkforward()` to accept tickers list

## Integration Points for ksf_stockmarket

### Forex Stub (PHP + MariaDB)
- Symbols like `EUR.CAD`, `USD.CAD` in symbol_master
- Same SIGNAL_STRATEGIES apply (EMA cross, RSI, etc.)
- Different session hours (24/5)

### Futures Stub (PHP + MariaDB)
- Symbols like `ES`, `NQ`, `CL` in symbol_master
- 24/5 trading hours
- Larger tick values, different contract specs

### Hedge Fund (Multi-Regime) Stub
- Multiple strategy portfolios simultaneously
- Cross-asset correlation filters
- Heat limits across sectors/asset classes
- Regime-aware strategy selection (already partially done)

---

## Stub Files Created

`php/src/Service/ForexTracker.php` - Forex position tracking
`php/src/Service/FuturesTracker.php` - Futures contract tracking  
`python/src/portfolio/multi_asset_portfolio.py` - Cross-asset portfolio construction

---

## Next Actions (NOT executed)

- Add Forex/Futures symbols to symbol_master table
- Extend trading_pipeline_v3.py to iterate over instrument list
- Create separate backtest tables for forex/futures
- Add instrument_type enum to data model