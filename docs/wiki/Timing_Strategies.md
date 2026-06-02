= Timing & Technical Strategies =

This page documents technical timing strategies — entry and exit signals used across all portfolio sleeves. These are applied ''after'' stock selection strategies have identified candidates.

''Last updated: 2026-05-31 — 10 timing strategies registered''

== Overview ==

Timing strategies use price and volume patterns to determine '''when''' to enter and exit positions. They are applied on top of stock selection filters from [[Stock Selection Strategies]].

The ensemble approach (2/3 consensus across multiple timing strategies) outperforms any single signal.

'''Key principle''' — Always confirm with ADX:
* ADX > 25 = trending market → use trend-following strategies
* ADX < 20 = range-bound → use mean-reversion strategies

== ADX Trend Filter ==

'''The most important filter — always use on top of other strategies.'''

'''Source:''' Welles Wilder (1978), [https://www.investopedia.com Investopedia]

Measures ''trend strength'', NOT direction. This is a filter, not an entry signal.

* ADX > 25 = strong trend → trade trend-following strategies
* ADX 20–25 = developing
* ADX < 20 = range-bound → trade mean-reversion only
* +DI > -DI = bullish bias
* -DI > +DI = bearish bias

'''Impact:''' Reduces whipsaw trades by 30–40%. Improves ensemble win rate by 5–8%.

== Bollinger Band Strategies ==

=== Bollinger Mean Reversion ===

'''Source:''' John Bollinger, Investopedia, our backtests

When price drops below lower BB in an uptrend, it tends to snap back up.

'''Entry:''' Price touches lower band + RSI < 30 + overall uptrend (price > 200d MA)<br>
'''Exit:''' Middle band (20d MA)

{| class="wikitable"
! Win Rate !! PF !! Max DD || Trades
|-
| 47% || 1.42 || -8.7% || 1,234
|}

=== Bollinger Band Squeeze ===

'''Source:''' John Bollinger, Investopedia

When bands narrow (squeeze), volatility expansion is imminent.

'''Squeeze:''' Band width < 50% of 20-day average<br>
'''Entry:''' Bands expand + price breakout + volume > 1.5× average<br>
'''Stop:''' Middle band

Risk: High. False breakouts common — confirm with ADX > 25.

== Moving Average Strategies ==

=== SMA Crossover (10/50) ===

'''Source:''' Investopedia<br>
'''The only backtested trend strategy that beats Buy & Hold.'''

* Entry: SMA-10 crosses above SMA-50
* Exit: SMA-10 crosses below SMA-50
* Filter: Only if price > SMA-200

{| class="wikitable"
! Win Rate !! PF !! Max DD !! Trades
|-
| 44% || 1.28 || -12.3% || 1,847
|}

=== Golden Cross / Death Cross (50/200) ===

'''Source:''' Investopedia<br>
Too slow for active trading but important for confirming long-term regime. S&P 500 golden cross = bull market confirmation.

== Momentum Strategies ==

=== MACD Trend Following ===

'''Source:''' Gerald Appel, Investopedia

* Entry: MACD crosses above signal line
* Exit: MACD crosses below signal line

'''Warning:''' 46% win rate, barely profitable standalone. Whipsaws in ranges. Only use as part of ensemble.

=== Oscillator Convergence (RSI + MACD + Stochastic) ===

'''Source:''' Investopedia, our backtests

Entry requires ALL three to confirm. High selectivity, better quality.

* RSI 45–70 (momentum zone)
* MACD > signal
* Stochastic %K crossing above %D

{| class="wikitable"
! Win Rate !! PF !! Max DD
|-
| 44% || 1.31 || -14.7%
|}

== Breakout Strategies ==

=== Turtle Trading (Donchian Breakout) ===

'''Source:''' Richard Dennis (1983), Curtis Faith, Investopedia

'''"Way of the Turtle"''' — Classic trend-following breakout.

* Entry: Close > 20-day Donchian high
* Exit: Close < 55-day Donchian low
* Dual system: 20d entry + 55d entry

'''Problem:''' FALSE signals at range tops. Does NOT work on range-bound stocks. Only trade when ADX > 25 (trending).

== Fibonacci Retracement ==

'''Source:''' Leonardo Fibonacci, Investopedia, institutional standard

Trade pullbacks to key Fibonacci levels within established trends.

'''Key levels:''' 23.6%, 38.2%, 50%, 61.8%, 78.6%<br>
'''Entry:''' Price at 61.8% + bullish confirmation candle<br>
'''Stop:''' Below 78.6%<br>
'''Target:''' 1.618% extension

'''Critical rule:''' NEVER buy at 61.8% blindly. ALWAYS wait for confirmation. Price can overshoot to 78.6% or fully retrace.

Combine with ADX > 25 to confirm trending market.

== Volume-Based Strategies ==

=== OBV Divergence ===

'''Source:''' Joe Granville (1963), Investopedia

* Bullish: Price lower low + OBV higher low = accumulation
* Bearish: Price higher high + OBV lower high = distribution

Leading indicator — diverges 1–3 weeks before price reverses. Best as confirmation overlay.

=== Abnormal Volume Detection ===

Volume > 3× average + price change > ±2% = institutional activity

Not a standalone signal — use to CONFIRM other strategy entries.

== Neural Network & Ensemble ==

=== Neural Network Directional ===

Multi-layer feedforward NN trained on 142 technical indicators for 5-day directional prediction.

{| class="wikitable"
! Win Rate !! PF !! Max DD
|-
| 53.1% || 1.42 || -11.2%
|}

=== Ensemble Blend (RECOMMENDED) ===

'''Our best performer — 372,134 backtest runs on 19 symbols'''

* NN: 50% weight
* Oscillators: 30% weight
* Candlestick: 20% weight
* Fires when 2/3 agree

{| class="wikitable"
! Win Rate !! PF !! Max DD !! Trades
|-
| 51.4% || 1.58 || -9.1% || 678
|}

'''Status:''' BATTLE TESTED — Primary signal generator for production trading.

== Stochastic ==

'''Source:''' George Lane, Investopedia

* %K crossing above %D in oversold zone (<20) = buy signal
* Divergence between price and stochastic = strongest signal
* Warning: Our backtests show 46% win rate — weak standalone, use as ensemble member

== Backtest Summary ==

{| class="wikitable sortable"
! Strategy !! Type !! Win Rate !! PF !! Max DD !! Trades !! Status
|-
| Bollinger MR || Mean-rev || 47% || 1.42 || -8.7% || 1,234 || PROMISING
|-
| Oscillators || Timing || 44% || 1.31 || -14.7% || 2,103 || PROMISING
|-
| NN || AI || 53.1% || 1.42 || -11.2% || 956 || BATTLE TESTED
|-
| Ensemble || Blended || 51.4% || 1.58 || -9.1% || 678 || BATTLE TESTED
|-
| SMA 10/50 || Trend || 44% || 1.28 || -12.3% || 1,847 || BATTLE TESTED
|-
| MACD Trend || Momentum || 46% || 1.08 || -16.2% || 1,654 || NEEDS IMPROVEMENT
|-
| Turtle || Breakout || 45% || 1.22 || -18.4% || 891 || BATTLE TESTED
|-
| Stochastic || Oscillator || 46% || 1.12 || -16.8% || 1,420 || PROMISING
|-
| Candlestick || Pattern || 12% || 0.82 || -24.3% || 1,847 || NOT RECOMMENDED
|}

== See Also ==

* [[Stock Selection Strategies]] — Universe filtering by sleeve
* [[Money Management]] — Position sizing and stops
* [[Candlestick Patterns]] — Candlestick reference
* [[Oscillators & Indicators]] — Technical indicator deep-dive
