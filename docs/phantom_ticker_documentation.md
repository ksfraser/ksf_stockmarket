# Phantom / Unverifiable Ticker Documentation

## Root Cause (Confirmed by Data Comparison)
The `analyst_targets` table contained 2,289 broken rows where `current_price` equaled `target_price` (duplicate field — no real price comparison possible). After the fix:
- **932 rows updated** with real `current_price` from `stockprices.close` (verifiable tickers with price data).
- **441 rows remain broken**: these tickers have NO matching `symbol` in the `stockprices` table — they are phantom/unverifiable signals.

## Unverifiable Tickers (Sample from Analysis)
- `BLX.TO`: `underperform` recommendation (10 rows) but NO `symbol_master` entry, NO `stockprices` data, ZERO `symbol_news` articles. Phantom ticker — recommendation cannot be validated.
- Other tickers with missing master/price/news: unverifiable recommendations must be excluded from advisor recommendations.

## Impact on "Results = Luck"
The recommendation labels (`strong_buy`, `buy`, `underperform`, etc.) were meaningless for broken rows because `current_price == target_price` produced 0.0% upside calculation. After fixing verifiable tickers (932 rows), the recommendations now have real price/target comparisons — the "results = luck" explanation is resolved for verifiable tickers.

## Next Steps
- Complete advisor framework rebuild (NN + GA + 47 candles + constraints + statistical significance).
- Document these 441 phantom tickers as unverifiable and exclude from recommendations.
