# ATR Multiplier Backtest Comparison

## warren-buffet (buffett_quality/default)
Period: 2024-01-01 → 2024-12-31 | Capital: $100,000 | Frequency: weekly

| Multiplier | Final Value | Total Return | Trades | Win Rate |
|---|---|---|---|---|
| 1.50 (baseline DB) | $100,928.74 | 0.93% | 119 | — |
| 2.00 | $109,250.76 | 9.25% | 105 | — |
| 2.25 | $109,251.91 | 9.25% | 103 | — |
| 2.50 | $109,467.86 | 9.47% | 99 | — |

## momentum (momentum/default)
Period: 2024-01-01 → 2024-12-31 | Capital: $100,000 | Frequency: quarterly (weekly is >10m per run)

| Multiplier | Final Value | Total Return | Trades | Win Rate |
|---|---|---|---|---|
| 2.00 (baseline DB) | $109,416.42 | 9.42% | 89 | — |
| 2.25 | $109,416.42 | 9.42% | 89 | — |
| 2.50 | $109,416.42 | 9.42% | 89 | — |

## Summary
- **buffett_quality**: 2.5× ATR is best (9.47%), 2.0× and 2.25× are effectively tied at 9.25%. The baseline 1.5× is significantly worse (0.93%). This suggests stops are too tight at 1.5× for this universe/period.
- **momentum**: No difference across 2.0/2.25/2.5 at quarterly cadence. With weekly rebalancing the per-run compute exceeds current capacity, so this result may understate differentiation.
