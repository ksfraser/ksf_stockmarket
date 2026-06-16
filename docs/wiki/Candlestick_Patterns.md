[[Category: ksf_stockmarket]]
= Candlestick Patterns =

[[ Candlestick patterns]] have ~50% hit rate on daily timeframes — no better than coin flip. They may be useful for 1-day predictions but are statistically insignificant at 3+ day horizons. Our backtests (372K runs) confirm: CDL patterns are essentially noise. Use only as one input within an ensemble, never standalone.

''Source: Our backtest results; academic Efficient Market Hypothesis''

== Overview ==

Candlestick charting originated in Japan in the 1700s (Munehisa Homma, rice trading). Steve Nison introduced them to Western markets in 1991.

A candlestick shows OHLC (Open, High, Low, Close) for a period:
* '''Body''' = Close – Open (filled if down, hollow if up)
* '''Wicks/Shadows''' = High to body top, body bottom to low
* '''Size''' = volatility; '''Body ratio''' = conviction

== Single-Candle Patterns ==

{| class="wikitable"
! Pattern !! Description !! Signal
|-
| Doji || Open ≈ Cross (tiny body) || Indecision — potential reversal, NOT entry signal
|-
| Hammer || Small body at top, long lower wick || Bullish at support — needs confirmation
|-
| Hanging Man || Same shape as Hammer AT TOP || Bearish — distribution pattern
|-
| Shooting Star || Small body at bottom, long upper wick || Bearish at resistance
|-
| Marubozu || Full body, no wicks || Strong conviction in direction
|-
| Spinning Top || Small body, equal wicks || Indecision
|}

== Dual-Candle Patterns ==

{| class="wikitable"
! Pattern !! Description !! Signal
|-
| Bullish Engulfing || Green candle fully engulfs previous red || Bullish reversal at support
|-
| Bearish Engulfing || Red candle fully engulfs previous green || Bearish reversal at resistance
|-
| Piercing || Green opens below, closes above midpoint of prior red || Bullish reversal
|-
| Dark Cloud Cover || Red opens above, closes below midpoint of prior green || Bearish reversal
|-
| Tweezer Bottom || Two lows at same level || Support test
|-
| Harami || Small candle inside prior large body || Reduced momentum (not reversal)
|}

== Triple-Candle Patterns ==

{| class="wikitable"
! Pattern !! Description !! Signal
|-
| Morning Star || Red → Doji/Spinning Top → Green || Bullish reversal (strong)
|-
| Evening Star || Green → Doji → Red || Bearish reversal (strong)
|-
| Three White Soldiers || 3 consecutive green, each closing higher || Strong bullish
|-
| Three Black Crows || 3 consecutive red, each closing lower || Strong bearish
|-
| Abandoned Baby || Star + gap + reversal candle || Very strong reversal
|-
| Kicker || Gap reversal opposite prior direction || Strongest reversal signal
|}

== Our Backtest Results ==

We tested all 59 TA-Lib candlestick patterns across 19 symbols:

* '''Average correlation to forward returns:'''< 0.01 (noise)
* '''Hit rate:''' ~50% (coin flip)
* '''Best day-1 accuracy:''' 52% (not meaningful)
* '''Day-3 accuracy:''' 50% (no predictive power)

'''Recommendation:''' Drop all standalone candlestick calculations. Use only within ensemble with weight ≤ 20%. Focus on volume confirmation instead.

== When Candlesticks Work ==

* '''Weekly timeframe''' — Higher signal-to-noise than daily
* '''Combined with support/resistance''' — At key Fibonacci levels
* '''With volume spike''' — Engulfing on 3× volume = meaningful
* '''As ensemble member only''' — Never as the only entry signal

== See Also ==

* [[Timing Strategies]] — Entry/exit signals
* [[Oscillators & Indicators]] — RSI, MACD, Stochastic, Bollinger
* [[Fibonacci Retracement]] — Combining Fib levels with candles
* [[Volume Analysis]] — Volume confirmation of candle signals
