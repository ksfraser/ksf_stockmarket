# TA Storage Architecture & Signal Weight Correlation Design
# ============================================================

## Q1: How are ~340 TA values stored? 340 columns or name-value?

**Answer: Hybrid approach — "wide" for common, "narrow" for exotic.**

### Tier 1 (Trigger, per-INSERT): ~10 columns
Stored as WIDE columns in `daily_indicators`:
  daily_return, gap_pct, sma_20, sma_50, sma_200, volume_sma_20
  (+ symbol, price_date, updated_at)

### Tier 2 (Daily batch, window functions): ~15 columns
Stored as WIDE columns in `daily_tier2`:
  bb_middle, bb_upper, bb_lower, bb_width, bb_pct,
  atr_14, atr_pct, vol_ratio_20, vol_ratio_50,
  trend_50_200, signal_strength, signal_reasons
  (+ symbol, price_date, calc_method, updated_at)

### Tier 3 (Python/TA-Lib, full array processing): Name-Value pairs
Stored as NARROW rows in `ta_values`:

  CREATE TABLE ta_values (
      symbol      CHAR(16)    NOT NULL,
      price_date  DATE        NOT NULL,
      indicator   VARCHAR(64) NOT NULL,  -- e.g., 'RSI_14', 'MACD', 'CDL_DOJI'
      value       DECIMAL(15,8) NULL,
      signal      ENUM('BUY', 'SELL', 'NEUTRAL', 'N/A') NULL,
      PRIMARY KEY (symbol, price_date, indicator)
  ) PARTITION BY RANGE (YEAR(price_date)) (...);

This gives us:
- ~25 wide columns for the most common indicators (fast queries, no joins)
- ~315 name-value rows for the exotic indicators (flexible, extensible)
- Total per symbol per day: ~340 data points across both storage models

### Why not all wide?
- 340 columns per row is wide but manageable for InnoDB
- BUT: many indicators are NULL for most symbols (e.g., candlestick patterns only fire occasionally)
- Adding a new indicator = ALTER TABLE (wide) vs INSERT (narrow)
- Name-value is better for the long tail of ~315 indicators

### Why not all narrow?
- The ~25 most common indicators are queried together constantly
- JOIN or pivot on 25 name-value rows per day per symbol = slow
- Wide columns for common indicators = single row read

## Q2: TA calculation — piecemeal triggers vs full array?

**Answer: Full array processing by Python, NOT piecemeal triggers.**

### The Problem with Piecemeal
- RSI needs 14 days of data. A trigger on day 14 can calculate it, but
  recalculating on every INSERT means re-reading 14 rows per symbol per insert.
- MACD needs 26 days. Same problem.
- For 2000 symbols × 14 rows = 28,000 row reads per price update. Prohibitive.

### The Solution: Batch Processing
1. **Tier 1 (trigger)**: Only the cheap calculations — daily return, gap, SMA.
   These need at most 200 rows (for SMA-200) and are O(1) per row.
   
2. **Tier 2 (daily event)**: Window functions for BB, ATR. These scan
   20-50 rows per symbol but run ONCE per day, not per insert.

3. **Tier 3 (Python cron)**: Full TA-Lib calculation. Python reads the
   last N days of data for each symbol into a pandas DataFrame, calculates
   ALL ~340 indicators in vectorized operations, and writes results to
   `ta_values` in bulk.

### Python TA Processing Flow
```
For each symbol:
  1. Read last 250 days of OHLCV from stockprices (single query)
  2. pandas DataFrame with 250 rows
  3. ta-lib calculates RSI, MACD, Bollinger, candlestick patterns, etc.
     — all vectorized over the 250-row array
  4. Write today's values to ta_values (bulk INSERT)
  5. Update daily_tier2 with summary signals

This is O(n_symbols × 250) per day, not O(n_symbols × n_indicators × lookback).
```

### When does Tier 3 run?
- After market close (6 PM ET) via cron
- Reads from `stockprices` (partitioned, so recent data is in one partition)
- Writes to `ta_values` and `daily_tier2`
- Also populates `signal_weights` with correlation analysis

## Q3: Signal Weight Correlation — Pre-indicators vs Real-time

**Answer: Yes, signal_weights tracks correlation and lead/lag relationships.**

### The Problem
- RSI < 30 (oversold) might fire 5 days before the price bottoms
- MACD crossover might fire at the bottom
- Volume spike might fire 2 days after the bottom
- If we treat all signals equally, we get conflicting information

### The Solution: Correlation-Aware Signal Weights

The `signal_weights` table is enhanced:

  CREATE TABLE signal_weights (
      symbol          CHAR(16)    NOT NULL,
      signal_type     VARCHAR(64) NOT NULL,  -- e.g., 'RSI_OVERSOLD'
      weight          DECIMAL(8,4) NOT NULL DEFAULT 1.0,
      
      -- Correlation analysis
      win_rate        DECIMAL(5,4) NULL,  -- % of times signal led to profit
      avg_lead_days   DECIMAL(5,1) NULL,  -- How many days before price move
      correlation     DECIMAL(5,4) NULL,  -- Correlation with future return
      is_pre_indicator TINYINT(1) NULL,   -- 1 if signal leads, 0 if coincident
      
      -- Correlation with OTHER signals
      correlates_with VARCHAR(255) NULL,  -- JSON array of correlated signal types
      correlation_matrix JSON NULL,       -- Full correlation matrix for this symbol
      
      n_trades        INT UNSIGNED NULL,
      last_updated    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (symbol, signal_type)
  );

### How Correlation Strengthens Pre-indicators

Example: RSI_OVERSOLD has a lower raw win rate (say 55%) but consistently
fires 3-5 days before MACD_CROSS (win rate 65%). The correlation analysis:

1. Detects that RSI_OVERSOLD → MACD_CROSS sequence has 78% win rate
2. Increases RSI_OVERSOLD weight when MACD_CROSS hasn't fired yet
3. Decreases RSI_OVERSOLD weight after MACD_CROSS fires (already confirmed)
4. The pre-indicator gets "credit" for the full sequence

### Correlation Discovery Process

The Python backtest engine runs correlation analysis:

```
For each symbol:
  1. Get all signal fire dates from daily_tier2 + ta_values
  2. For each signal pair (A, B):
     a. Find dates when A fired
     b. Check if B fired within N days after A
     c. Calculate: P(profit | A→B) vs P(profit | A alone) vs P(profit | B alone)
     d. If P(profit | A→B) > P(profit | B alone), A is a pre-indicator for B
  3. Store correlation matrix in signal_weights
  4. Adjust weights: pre-indicators get boosted weight when their
     correlated follow-on signal hasn't fired yet
```

### Weight Adjustment Formula

```
effective_weight = base_weight × correlation_boost × recency_factor

where:
  correlation_boost = 1.0 + (correlation × 0.5)  -- up to 1.5x for strong correlation
  recency_factor = 1.0 if signal fired within 5 days, else 0.8
```

### Example: Strengthening a Pre-indicator

Signal: RSI_OVERSOLD (base weight: 1.0)
- Fires on day 0
- MACD_CROSS fires on day 3 (70% of the time)
- Win rate for RSI alone: 55%
- Win rate for RSI→MACD sequence: 78%
- Correlation: 0.72

Effective weight when RSI fires but MACD hasn't yet:
  = 1.0 × (1.0 + 0.72 × 0.5) × 1.0 = 1.36

Effective weight after MACD confirms:
  = 1.0 × 1.0 × 1.0 = 1.0 (back to base — confirmation already priced in)

This means the system learns that RSI_OVERSOLD is more valuable as a
pre-indicator than as a standalone signal.
