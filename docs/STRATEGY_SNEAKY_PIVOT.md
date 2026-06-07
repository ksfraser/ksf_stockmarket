# Sneaky Pivot Strategy
## The Rumbers Intraday Scalping Method

> **Source:** The Rumbers YouTube Channel | **Timeframe:** 15-minute | **Style:** Scalping/Mean Reversion

---

## Core Concept

Based on The Rumbers' approach: Price trades between **Range High/Low** (previous day) and **Swing High/Low** (extended levels). The "sneaky" candle pattern signals reversals within these zones.

---

## Strategy Components

### Key Levels
| Level | Definition |
|-------|------------|
| **Range High** | Previous day's high |
| **Range Low** | Previous day's low |
| **Swing High** | Previous price extreme higher than Range High (any timeframe) |
| **Swing Low** | Previous price extreme lower than Range Low (any timeframe) |

### Price Zones
- **Sell Zone:** Between Range High and Swing High
- **Buy Zone:** Between Range Low and Swing Low

---

## Entry Patterns (First Hour)

The strategy uses **3 consecutive 15-minute candles**:

### Bullish Setup (Buy Signal)
| Candle | Pattern | Meaning |
|--------|---------|---------|
| **1st (Signal)** | Green Hammer | Reversal signal at Swing Low |
| **2nd (Sneaky)** | Red Hammer | Confirms support holding |
| **3rd** | Red upside-down hammer | Trigger for entry |

### Bearish Setup (Sell Signal)
| Candle | Pattern | Meaning |
|--------|---------|---------|
| **1st (Signal)** | Red shooting star/upside-down hammer | Reversal signal at Swing High |
| **2nd (Sneaky)** | Green shooting star | Confirms resistance holding |
| **3rd** | Green shooting star | Trigger for entry |

---

## Rules

### Entry
1. **Wait for 9:30-10:30 EST** (first hour after open)
2. **Identify Swing High/Low levels** from prior data
3. **Mark Range High/Low** (previous day's levels)
4. **Only trade if price enters one of the zones:**
   - Price in Sell Zone → Look for BEARISH 3-candle pattern
   - Price in Buy Zone → Look for BULLISH 3-candle pattern
5. **Entry:** After completing the 3-candle sequence

### Exit
1. **Target:** Opposite zone boundary (e.g., buy zone target = Range Low)
2. **Stop:** Beyond Swing level
3. **Time:** End of day (scalping strategy)

---

## Candlestick Definitions

### Green Hammer
- Small body near top of range
- Long lower wick (2× body length)
- Indicates buying pressure

### Red Hammer (Sneaky)
- Small red body near middle of range
- Long lower wick
- Shows sellers couldn't push lower

### Red Upside-Down Hammer
- Small red body
- Long upper wick
- Sellers still in control but weakening

### Green Shooting Star
- Small green body near top
- Long upper wick
- Indicates rejection of higher prices

---

## Implementation for Backtesting

```python
def sneaky_pivot_intraday(df_15min, prev_day_high, prev_day_low):
    """
    df_15min: DataFrame with 15-min OHLCV data
    prev_day_high/low: Previous day's range levels
    Returns: Entry signals at zone reversals
    """
    # Calculate Swing levels from extended history
    swing_high = df_15min['high'].max() if df_15min['high'].iloc[0] < prev_day_high else prev_day_high
    swing_low = df_15min['low'].min() if df_15min['low'].iloc[0] > prev_day_low else prev_day_low
    
    # Zone detection
    in_sell_zone = (df_15min['high'] > prev_day_high) & (df_15min['low'] < swing_high)
    in_buy_zone = (df_15min['high'] > swing_low) & (df_15min['low'] < prev_day_low)
    
    # Candlestick pattern detection
    signal = detect_3_candle_pattern(df_15min)
    
    return signal
```

---

## Backtest Requirements

1. **15-minute OHLCV data** (not daily)
2. **Previous day's HLC** for Range levels
3. **Extended history** for Swing High/Low detection
4. **Market hours filter:** 9:30 AM - 4:00 PM EST

---

## Next Steps

- [ ] Create 15-minute data pipeline
- [ ] Implement candle pattern detection
- [ ] Add to backtesting engine
- [ ] Test on your 19 symbols
- [ ] Calculate win rate for 3-candle pattern