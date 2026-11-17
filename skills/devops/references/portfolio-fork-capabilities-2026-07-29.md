# Portfolio Fork Capabilities — ksfraser/portfolio

Fork cloned to /home/kevin/Documents/ksfraser_portfolio_fork/ on 2026-07-29.
Upstream: portfolio-performance/portfolio, 8,244 commits. Fork: 6,979 commits (~1,265 behind; user cited ~1,500).

## Packagist gap

No PHP Composer package implements portfolio cash-flow-adjusted performance metrics (TWR, IRR, drawdown) in the PP model. Closest candidate `academe/php-finance` requires PHP >= 8.3 and does not cover these metrics.

## Algorithms worth porting

### TWR (True Time-Weighted Return)
`name.abuchen.portfolio/src/.../snapshot/ClientIndex.java:96-100`
delta = (valuation + outflows) / (valuation + inflows) - 1 ; accumulated chains geometrically.

### Annualized TWR
`PerformanceIndex.java:200-205`
`Math.pow(1 + accumulatedPercentage, 365.0 / days) - 1`

### IRR (Money-Weighted Return / XIRR equivalent)
`math/IRR.java` — Newton-Raphson on NPV with bisection fallback.
Inputs: List<LocalDate> dates, List<Double> values.

### Volatility / Drawdown
`math/Risk.java` — log-returns std dev, semi-deviation, annualized via sqrt(252).
`math/Risk.Drawdown` — peak tracking, max decline %, recovery time interval.

## Recommended package

Package: `ksf/portfolio-performance` | Namespace: `KSF\Performance` | PHP >=7.4 | pure PHP, no deps.

Thin wrappers: stockmarket maps portfolio_transactions → TWR/IRR; ksfii_app maps FA ledger; ksf-fa hooks read GL → package → widget.

## Priority order
1. PDF importer (CIBC/Questrade)
2. TWR+IRR+volatility package
3. FX-aware cost basis
4. Asset allocation + drift alerts
