= Risk Management =

This page documents portfolio-level risk management — the framework that prevents catastrophic losses and ensures the portfolio survives to Compound.

''Last updated: 2026-05-31''

== The Core Principle ==

'''Max drawdown determines recovery difficulty:'''

{| class="wikitable"
! Loss !! Required Gain to Recover
|-
| −10% || +11%
|-
| −20% || +25%
|-
| −30% || +43%
|-
| −40% || +67%
|-
| −50% || +100% (doubling!)
|}

A 50% loss requires a 100% gain just to break even. '''Preventing large drawdowns is more important than maximizing returns.'''

== Portfolio-Level Risk Controls ==

=== Maximum Drawdown Limits ===

{| class="wikitable"
! Limit !! Action !! Authority
|-
| Portfolio −10% || Review all positions, tighten stops | Auto
|-
| Portfolio −15% || Reduce tactical & satellite by 50% | Auto + Alert
|-
| Portfolio −20% || Move to 80% cash (defensive) | Auto + Alert
|-
| Single position −15% || Hard stop — exit completely | Auto
|}

=== Correlation Filter ===

No two positions in the same sleeve may have 60-day correlation > 0.80. This prevents concentration disguised as diversification.

=== Sector Exposure Limits ===

{| class="wikitable"
! Category || Max Exposure
|-
| Single sector || 25% of total portfolio
|-
| Single position || 10% of sleeve / 4% of total
|-
| Single stock across sleeves || 15% of total portfolio
|}

=== Liquidity Requirements ===

* Min average daily volume: 100,000 shares
* Max position size must be < 5% of average daily volume
* Can exit full position within 2 trading days without market impact

=== Rebalancing Rules ===

{| class="wikitable"
! Event || Action
|-
| Quarterly (Jan/Apr/Jul/Oct) || Rebalance to target sleeve weights
|-
| Any sleeve drifts >5% from target || Rebalance that sleeve
|-
| Any position exceeds 15% of sleeve || Trim to 10%
|-
| ADX drops below 20 (range-bound) || Shift tactical → Bollinger MR
|-
| VIX exceeds 30 (fear) || Buy tactical opportunities / hedge
|}

== Regime Detection ==

=== VIX-Based Regime Classification ===

{| class="wikitable"
! VIX Level || Regime || Strategy Emphasis
|-
| < 15 | Complacency / Bull | Normal tactical, watch for reversal
|-
| 15-25 | Normal | All strategies active
|-
| 25-35 | Fear | Increase tactical, buy dips
|-
| > 35 | Panic | Maximum opportunity, add heavily
|}

=== Market Direction Filter (S&P 500) ===

{| class="wikitable"
! S&P 500 vs 200d MA || Interpretation || Action
|-
| Above rising MA || Confirmed bull | All strategies active
|-
| Above flat MA || Cautious bull | Reduce tactical size
|-
| Below MA || Bear market | Defensive: 80% cash, buy puts
|-
| Death cross (50d < 200d) || Major warning | Maximum defensive posture
|}

== Hedging Strategies ===

=== When to Hedge ===

* S&P 500 below 200-day MA (confirmed bear market)
* VIX term structure in backwardation
* All timing strategies showing majority sell signals
* Portfolio approaching −10% drawdown

=== Hedge Instruments ===

* SPY puts (protective) — max 2% of portfolio
* VIX calls (tail hedge) — max 1% of portfolio
* Inverse ETFs (SH, SDS) — temporary only
* Increase cash to 40-80%

=== Hedge Ratio ===

In confirmed bear market:
* Core sleeve: Full hedge (100% protection)
* Tactical sleeve: 50% hedge or exit
* Income sleeve: Dividend aristocrats naturally defensive
* Satellite sleeve: 100% exit or hedge

== Stress Testing ==

Monthly stress test scenarios:

{| class="wikitable"
! Scenario || Assessed Impact || Mitigation
|-
| 2008 repeat (−57%) | Projected: −25% with hedges | Reduce equity, add puts
|-
| COVID crash (−34%) | Projected: −15% with hedges | Cash reserve, buy dip
|-
| Rate shock (+200bps) | REITs −20%, growth −15% | Diversify sectors
|-
| Sector rotation | Tech −30%, energy +20% | Sector limits prevent damage
|}

== Recovery Protocol ==

When portfolio is at −15% or worse:
# Identify the cause (systematic vs individual positions)
# If systematic: move to defensive posture (reduce equity 50%, add hedges)
# If individual: exit losing positions, review entry criteria
# Document the lesson — update strategy criteria
# Gradually re-enter when regime improves (ADX rising, VIX declining)

== See Also ==

* [[Money Management]] — Position sizing and stops
* [[Stock Selection Strategies]] — Universe filtering
* [[Timing Strategies]] — ADX and VIX filters for timing
* [[Oscillators & Indicators]] — ATR, VIX, OBV for risk signals
* [[Habits of Successful Investors]] — Behavioural discipline
