= Oscillators & Technical Indicators =

This page provides reference documentation for all technical indicators used by the Investment Agent platform, including their construction, interpretation, and known limitations based on our 372,000+ backtest results.

''Last updated: 2026-05-31''

== Important Caveat ==

'''From our backtests:''' Most individual technical indicators have near-zero predictive power at the daily timeframe. Only ATR/volatility measures show meaningful correlation to forward returns. Indicators are most useful as ensemble components and for position sizing.

== Tier 1: Always Computed (on every price import) ==

{| class="wikitable"
! Indicator | Description | Period
|-
| OHLCV | Open, High, Low, Close, Volume | Daily
|-
| Gap Up/Down | Open vs Previous Close | Daily
|-
| Body Size | |Close − Open| | Daily
|-
| Upper/Lower Shadow | Wick lengths | Daily
|-
| True Range | max(H−L, |H−prevC|, |L−prevC|) | Daily
|-
| ATR | Average True Range | 1, 7, 14, 20
|}

== Tier 2: Technical Indicators (refreshed weekly) ==

=== RSI — Relative Strength Index ===

'''Source:''' Welles Wilder (1978), Investopedia<br>
'''Period:''' 7 and 14 days

RSI = 100 − (100 / (1 + RS)) where RS = avg gain / avg loss

{| class="wikitable"
! RSI Level !! Interpretation !! Action
|-
| > 70 || Overbought || Consider selling / don't buy
|-
| 50-70 || Bullish momentum || Hold / add on pullbacks
|-
| 30-50 || Bearish momentum || Don't add / reduce
|-
| < 30 || Oversold || Watch for buying opportunity
|}

'''Swing Rejection refinement:''' Wait for RSI to drop below 30, then wait for FIRST crossover back above 30 as entry trigger. More precise than simple RSI < 30.

'''Backtest result:''' RSI 14 → 20-day forward return correlation: '''-0.002''' (zero predictive power standalone).<br>
Best used as confirmation within oscillator convergence ensemble.

=== MACD — Moving Average Convergence Divergence ===

'''Source:''' Gerald Appel, Investopedia<br>
'''Parameters:''' 12, 26, 9

* MACD Line = EMA(12) − EMA(26)
* Signal Line = EMA(9) of MACD Line
* Histogram = MACD Line − Signal Line

{| class="wikitable"
! Signal !! Interpretation
|-
| MACD crosses above signal || Bullish (buy)
|-
| MACD crosses below signal || Bearish (sell)
|-
| Histogram bars shrinking || Momentum fading — prepare for reversal
|-
| Histogram bars growing || Momentum building
|}

'''Backtest result:''' MACD hist → 20-day forward return correlation: '''0.011'''. Barely profitable standalone (PF 1.08). Use as ensemble member only.

=== Stochastic Oscillator ===

'''Source:''' George Lane, Investopedia<br>
'''Parameters:''' 14, 3, 3

%K = (Close − Lowest Low) / (Highest High − Lowest Low) × 100<br>
%D = SMA(3) of %K

{| class="wikitable"
! Level !! Interpretation
|-
| %K > 80 (overbought) || Potential sell
|-
| %K < 20 (oversold) || Potential buy
|-
| %K crosses above %D in <20 zone || Strongest buy signal
|-
| Price/Stochastic divergence || Reversal warning
|}

=== Bollinger Bands ===

'''Source:''' John Bollinger (2001), Investopedia<br>
'''Parameters:''' 20-day, 2σ

* Upper Band = SMA(20) + 2 × σ(20)
* Middle Band = SMA(20)
* Lower Band = SMA(20) − 2 × σ(20)
* %B = (Price − Lower) / (Upper − Lower)

{| class="wikitable"
! Condition !! Interpretation
|-
| Price touches upper band || Overbought / trending strong
|-
| Price touches lower band || Oversold / trending down
|-
| %B > 1 || Above upper band (breakout)
|-
| %B < 0 || Below lower band (breakdown)
|-
| Band width narrow (squeeze) || Low vol — expansion coming
|}

See also: [[Timing Strategies#Bollinger Band Strategies]]

=== ADX — Average Directional Index ===

'''Source:''' Welles Wilder (1978), Investopedia<br>
'''Period:''' 14-day

Measures ''trend strength'', NOT direction. The single most important filter.

{| class="wikitable"
! ADX Level !! Market Condition !! Strategy Type to Use
|-
| > 25 || Strong trending || Trend-following (SMA, Turtle)
|-
| 20-25 || Developing || Wait for confirmation
|-
| < 20 || Range-bound || Mean-reversion (Bollinger MR, Stochastic)
|}

* +DI > −DI = bullish trend bias
* −DI > +DI = bearish trend bias
* Rising ADX from <20 to >25 = trend beginning → prepare entries

=== ATR — Average True Range ===

'''The only consistently predictive indicator in our backtests.'''

'''Source:''' Welles Wilder (1978), Investopedia

Average True Range measures volatility. High ATR → higher expected returns (risk premium).

{| class="wikitable"
! Indicator | 20-day Correlation | Symbols Agree | Verdict
|-
| '''NATR_20''' | '''+0.162''' | 89% | ✓ Predictive
|-
| '''NATR_14''' | '''+0.159''' | 95% | ✓ Predictive
|-
| '''ATR%''' | '''+0.138''' | 89% | ✓ Predictive
|}

This is a '''stock selection''' signal, not a timing signal. High-volatility stocks earn ~1% more per 20-day period. Annualized: ~25% excess return from screening for high-NATR names.

=== OBV — On-Balance Volume ===

'''Source:''' Joe Granville (1963), Investopedia

Cumulative volume: adds on up days, subtracts on down days.

{| class="wikitable"
! Divergence !! Interpretation !! Signal
|-
| Price lower low + OBV higher low || Bullish (accumulation) || Strong buy
|-
| Price higher high + OBV lower high || Bearish (distribution) || Strong sell
|-
| OBV breakout before price || Leading indicator || Prepare entry
|}

Leading indicator — diverges 1-3 weeks before price reverses.

== What DOES NOT Work ==

From our 372,134 backtest runs on 19 symbols:

{| class="wikitable"
! Category !! Count !! Avg Correlation !! Verdict
|-
| All Candlestick Patterns | 59 | < 0.01 | ❌ IGNORE for daily trading
|-
| Moving Averages (various) | 28 | < 0.01 | ❌ Noise for direction
|-
| Bollinger Bands (all widths) | 36 | < 0.01 | ❌ Noise alone
|-
| Momentum (RSI/MACD/STOCH/CCI) | 48 | < 0.02 | ❌ Noise standalone
|-
| Volume (OBV/AD/ADOSC/BOP) | 4 | < 0.01 except OBV | ⚠ OBV divergence works
|-
| Cycle indicators | 6 | < 0.01 | ❌ Noise
|}

=== Candlestick Patterns ===

'''59 TA-Lib patterns tested: ~50% hit rate = coin flip.'''

May be useful for 1-day predictions but statistically insignificant at 3+ day horizons. Use only within ensemble at ≤20% weight. See [[Candlestick Patterns]].

== Indicator Correlation to 20-Day Forward Returns ==

Full results from our backtest:

{| class="wikitable sortable"
! Indicator !! 1-day !! 3-day !! 5-day !! 10-day !! 20-day !! Hit%
|-
| NATR_20 | 0.024 | 0.048 | 0.064 | 0.092 | **0.162** | 50.4%
|-
| NATR_14 | 0.023 | 0.045 | 0.061 | 0.089 | **0.159** | 50.5%
|-
| NATR_7 | 0.021 | 0.040 | 0.056 | 0.082 | **0.151** | 50.3%
|-
| ATR% | 0.029 | 0.051 | 0.067 | 0.097 | **0.138** | 50.4%
|-
| hvol_20 | 0.025 | 0.041 | 0.053 | 0.081 | **0.114** | 50.8%
|-
| macd_hist | 0.006 | 0.010 | 0.010 | 0.010 | 0.011 | 50.3%
|-
| roc_10 | 0.001 | 0.005 | 0.014 | 0.004 | 0.000 | 50.5%
|-
| signal_strength | 0.002 | −0.001 | 0.002 | −0.007 | −0.019 | 50.1%
|}

Only ATR/volatility family shows meaningful correlation. Everything else is for ensemble confirmation only.

== See Also ==

* [[Stock Selection Strategies]] — Universe filtering
* [[Timing Strategies]] — Using indicators for entry/exit
* [[Money Management]] — Using ATR for position sizing and stops
* [[Candlestick Patterns]] — Candlestick reference
* [[Risk Management]] — Portfolio-level risk controls
