# Sneaky Pivot Strategy
## Floor Pivot Points with Hidden Signal Enhancement

> **Status:** Proposed | **Category:** Mean Reversion/Trend Following Hybrid

---

## Overview

The Sneaky Pivot Strategy combines classic floor trader pivot points with hidden volatility signals to identify potential reversal points that conventional traders miss.

## Core Concept

Traditional pivot points are calculated from the previous period's high, low, and close:

```
Pivot Point (PP) = (High + Low + Close) / 3
Resistance 1 (R1) = (2 × PP) - Low
Support 1 (S1) = (2 × PP) - High
Resistance 2 (R2) = PP + (High - Low)
Support 2 (S2) = PP - (High - Low)
```

The "sneaky" twist: **Wait for price to close BEYOND the prior day's pivot range, then fade the move when it reverts toward the new pivot.**

## Strategy Rules

### Entry (Long)
1. Calculate daily pivots using prior day's HLC
2. Wait for price to CLOSE below S1 (below pivot range)
3. Look for reversal pattern:
   - Next bar closes above S1
   - Volume spike > 1.5× average (hidden confirmation)
   - RSI(14) < 30 (oversold)
4. Enter at market open or S1 retest

### Exit (Long)
1. Target: Pivot Point (PP) or R1
2. Stop: Below recent swing low or 2× ATR
3. Time-based: Exit after 3 days if neither hit

### Entry (Short) 
1. Price closes above R1
2. Next bar closes below R1
3. Volume spike + RSI(14) > 70
4. Enter short

### Exit (Short)
1. Target: PP or S1
2. Stop: Above recent swing high or 2× ATR

## Sneaky Enhancement

The key enhancement that makes this "sneaky":

### Volume-Absorption Threshold
Monitor volume on the breakout bar. If volume is **below 1.2× average** despite the breakout, the move lacks conviction — fade it with higher confidence.

### Time-of-Day Filter
Only trade during the snekiest hours:
- **Long entries:** 10:00-11:30 EST (institutional sellers exhausted)
- **Short entries:** 14:30-15:30 EST (institutional buyers exhausted)

### NATR Confirmation
Use the NATR(20) discovery from your correlation analysis:
- Higher NATR (> 2%) → Stronger move, wider stops needed
- Lower NATR (< 1%) → Mean reversion more likely, tighter stops

## Integration with Existing Pipeline

Add to `trading_pipeline_v3.py`:

```python
def sneaky_pivot_signal(df: pd.DataFrame) -> pd.DataFrame:
    """Sneaky pivot strategy with volume absorption."""
    
    # Calculate prior day pivots
    df['pivot'] = (df['high'].shift(1) + df['low'].shift(1) + df['close'].shift(1)) / 3
    df['r1'] = (2 * df['pivot']) - df['low'].shift(1)
    df['s1'] = (2 * df['pivot']) - df['high'].shift(1)
    df['r2'] = df['pivot'] + (df['high'].shift(1) - df['low'].shift(1))
    df['s2'] = df['pivot'] - (df['high'].shift(1) - df['low'].shift(1))
    
    # Volume absorption
    df['vol_avg_20'] = df['volume'].rolling(20).mean()
    df['vol_absorption'] = df['volume'] < 1.2 * df['vol_avg_20']
    
    # Hidden signal: Low volume breakout = sneaky entry
    df['close_below_s1'] = df['close'] < df['s1']
    df['sneaky_long'] = df['close_below_s1'] & df['vol_absorption'] & (df['rsi_14'] < 30)
    
    # Time filter (needs hourly data)
    df['entry_hour'] = df.index.hour
    df['sneaky_hours'] = df['entry_hour'].between(10, 11)
    
    df['signal'] = np.where(
        df['sneaky_long'] & df['sneaky_hours'], 'BUY',
        np.where(df['close'] > df['r1'] & df['vol_absorption'], 'SELL', 'HOLD')
    )
    
    return df
```

## Backtest Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Timeframe | Daily | Hourly for time filter |
| Lookback | 20 days | For volume average |
| Stop loss | 2× ATR(14) | Dynamic |
| Take profit | PP level | Conservative |
| Max hold | 3 days | Time decay |

## Expected Performance Characteristics

Based on your STRATEGY_REFERENCE findings:

- **Type:** Mean reversion hybrid with trend confirmation
- **Best for:** Range-bound, moderate-NATR stocks
- **Avoid:** High-NATR breakout stocks (like MTY per your analysis)
- **Correlation edge:** Pairs well with Bollinger MR (complementary timing)

## Risk Considerations

1. **Gap risk:** Overnight gaps can skip stops
2. **False breakdown:** High-volume breakouts may continue (not sneaky)
3. **End-of-day:** Avoid entries in last hour (slippage)

## Implementation Status

- [ ] Add pivot columns to `daily_indicators` table
- [ ] Add strategy function to `trading_pipeline_v3.py`
- [ ] Add to signal_weights correlation analysis
- [ ] Backtest against 19-symbol universe
- [ ] Add to combo strategies if Sharpe > 0.10