= Money & Risk Management =

This page documents money management and risk strategies — the most important part of the investment platform. A mediocre strategy with excellent money management outperforms a great strategy with poor risk management.

''Last updated: 2026-05-31 — 3 money management strategies + framework''

== Overview ==

Money management controls:
* '''Position sizing''' — How much to risk per trade
* '''Stop losses''' — When to exit losing trades
* '''Portfolio construction''' — How to allocate across strategies and sleeves

'''Key principle:''' Always use the ''more conservative'' of two position sizing methods. If Kelly says 15% but fixed fractional says 2%, use 2%.

== Kelly Criterion ==

'''Source:''' John Kelly (1956), Investopedia, Ralph Vince

The Kelly Criterion determines optimal position size for long-term growth:

<div style="background:#f5f5f5;padding:15px;font-family:monospace;text-align:center;margin:15px 0;">
f* = (b × p − q) / b
</div>

Where:
* f* = fraction of bankroll to bet
* b = average win / average loss (the odds)
* p = probability of winning (win rate)
* q = probability of losing (1 − p)

=== Example ===
55% win rate, avg win 1.5× avg loss: b=1.5, p=0.55, q=0.45
f* = (1.5 × 0.55 − 0.45) / 1.5 = 0.25
→ Use '''25% of account''' (or '''12.5% for half-Kelly''' — recommended)

'''USE HALF-KELLY.''' Full Kelly is too aggressive for real markets with estimation error.

=== Win Rate Inversion ===
As win rate drops, required position size drops ''non-linearly''. A 40% win rate strategy needs much smaller positions than 55%.

== Sleeve-Based Allocation ==

'''Source:''' Institutional best practice (pension funds, endowments)

Four-sleeve model prevents any single strategy from destroying the portfolio:

{| class="wikitable"
! Sleeve !! Allocation !! Strategy !! Hold Period
|-
| '''Core''' || 40% || Buffett Quality, Everlasting, Aristocrats || 5+ years
|-
| '''Tactical''' || 30% || Ensemble, CANSLIM, Momentum || 1-6 months
|-
| '''Income''' || 20% || Dividend Aristocrats, Safety Screen || 1-3 years
|-
| '''Satellite''' || 10% || Rule Breakers, Deep Value, Options || 3-12 months
|}

* Each sleeve has independent strategy and risk parameters
* Quarterly rebalance to maintain target weights
* Max single position: 10% of sleeve value
* Portfolio max drawdown: ~8.2%

== ATR Trailing Stop ==

'''Source:''' Welles Wilder (1978), Investopedia

Every position gets '''two stops''':
# '''Fixed Stop:''' Maximum acceptable loss from cost basis (e.g., 15%). Worst-case exit.
# '''Trailing Stop:''' Dynamic, follows price up (e.g., 10% below recent high). Locks in profits.

'''Critical rule:''' Once the trailing stop exceeds the fixed stop, the fixed stop becomes irrelevant. The trailing stop will always trigger first.

=== ATR Calculation ===
<div style="background:#f5f5f5;padding:15px;font-family:monospace;">
Dynamic Stop = Price − (ATR(14) × Multiplier)<br>
Apply: 2× ATR initially → tighten to 1× after 3× ATR profit
</div>

ATR (Average True Range) self-adjusts: widens in high-volatility stocks, tightens in low-volatility stocks. This is superior to fixed-percentage stops.

== Stop Methodology ==

=== When Fixed Stop Meets Trailing Stop ===
# Bought at $100, fixed stop at $85 (15% loss)
# Price rises to $130 → trailing stop (10%) = $117
# Price rises to $150 → trailing stop (10%) = $135
# At $150, the trailing stop ($135) is well above your fixed stop ($85)
# → The trailing stop WILL trigger first → fixed stop is now irrelevant

=== Risk Per Trade ===
{| class="wikitable"
! Method || Max Risk || Notes
|-
| Fixed Fractional || 1-2% of portfolio || Baseline — never exceed
|-
| Half-Kelly || Variable || Use if MORE conservative than 1-2%
|-
| Maximum || 2% of portfolio || Hard cap regardless of calculation
|}

== Position Sizing Formula ==

<div style="background:#f5f5f5;padding:15px;font-family:monospace;">
Position Size = (Portfolio × Risk%) / (Entry − Stop)<br><br>
Example:<br>
Portfolio: $384,000<br>
Risk: 1% = $3,840<br>
Entry: $50.00<br>
Stop: $46.00 (ATR-based, below support)<br><br>
Position Size = $3,840 / ($50 − $46) = 960 shares<br>
Dollar amount: 960 × $50 = $48,000 (12.5% of portfolio)
</div>

== See Also ==

* [[Stock Selection Strategies]] — Universe filtering by sleeve
* [[Timing Strategies]] — Entry/exit signals
* [[Risk Management]] — Portfolio-level risk controls
* [[Oscillators & Indicators]] — ATR, ADX, and other indicators for stops
