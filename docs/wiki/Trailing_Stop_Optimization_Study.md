[[Category: ksf_stockmarket]]
= Trailing Stop Optimization Study — June 2026 =

Purpose: answer whether our current trailing stops are too tight for long-hold, Buffett-style holdings, and what stop design is optimal by stock type.

== What We Tested ==

* '''Stop modes:''' fixed trailing percentage; ATR (Average True Range) multiple trailing stop
* '''Fixed % series:''' 5%, 8%, 10%, 12%, 15%, 20%, 25%
* '''ATR multiples:''' 1.0×, 1.5×, 2.0×, 2.5×, 3.0× (14-period ATR)
* '''Re-entry filters tested:''' none, [[Timing_Strategies#SMA]]-50 (Simple Moving Average), Bollinger lower band (not enabled in baseline results below)
* '''Regime filter tested:''' ADX (Average Directional Index) ≥ 25 (not enabled in baseline results below)
* '''Benchmarks:''' CA primary = [[Market_Reference#TSX_ETFs|XSP.TO / XI.TO]]; US primary = [[Market_Reference#US_ETFs|QQQ / SPY]]; CA supplemental = [[Market_Reference#TSX_ETFs|XIC.TO / XIU.TO]]

== Universe & Data Coverage ==

* Current distinct symbols with historical prices in MariaDB <code>stockprices</code>: '''258''' (mixed TSX (Toronto Stock Exchange), US, ETFs, and some older/tiny-cap issues)
* Symbols missing recent/robust data used in this run: '''MSFT, META, SHOP.TO, CVX, JPM, BAC, WFC, BRK-B, COST, TD.TO, BNS.TO''' sourced via <code>.TO</code> — some legacy symbols like <code>BNS</code> and <code>SU</code> had no data without the <code>.TO</code> suffix, which caused early-run skips
* Warnings we saw: repeated pandas SQLAlchemy DBAPI2 warning from <code>pd.read_sql(conn)</code>; non-fatal and worth replacing with an engine in follow-up work

== Methodology ==

* '''In/out flip equity model:''' one position at a time; fixed 5% of cash per entry; commission = $9.95/trade
* '''Trend filter:''' price > prior-day [[Timing_Strategies#Simple_Moving_Average]]-200 was required for entries
* '''Run window:''' 2018-01-01 → today
* '''Outputs produced (in repo):''' <code>atr_trailing_stop_analysis/summary.csv</code>, <code>leaderboard.csv</code>, <code>top_per_symbol.csv</code>, <code>raw_runs.csv</code>

== Results by Category ==

=== Growth / Quality Compounders (AAPL, AMZN, GOOG, HD, etc.) ===

* '''Buy-and-hold is decisively best.'''
* Fixed 20–25% trailing stops still underperformed buy-and-hold by ~250–620 percentage points over the full period.
* ATR stops made the gap worse because of extra churn.

Interpretation: these holdings spent most of the sample in established uptrends with ever-higher highs. Tight trailing stops captured noise and forced participation loss. See also [[Risk_Management#Drawdown_Control]].

=== Dividend / Slower-Growth Names (CA banks, utilities, energy, telecom) ===

* Mixed, leaning toward buy-hold advantage, but with thinner margins.
* Example: '''BNS.TO''' showed modest outperformance under fixed 25% trailing stop over buy-hold in our sample. That should be validated against the complete TSX income sleeve before generalizing.
* Energy names ([[Market_Reference#TSX_Energy|ENB.TO]], [[Market_Reference#TSX_Energy|TRP.TO]], [[Market_Reference#TSX_Energy|CNQ.TO]]) generally still favored buy-hold, but some ATR-3× modes reduced drawdown materially.

=== Speculative / Volatile Names ===

* Wider stops materially reduced stop-outs without materially improving net PnL.
* No tested stop mode reliably beat buy-and-hold over the full period for these names either.

=== What the 25% Stop-Out Rate Tells Us ===

* A 1-in-4 stop-out rate in the current environment is consistent with '''whipsaw / range conditions''', not necessarily a clean bear market. Related: [[Oscillators_and_Indicators#ADX]].
* The signal to watch: are stopouts occurring on ~1–3% pullbacks in quality names, or are they aligned with 10%+ corrections? If the former, stops are too tight; if the latter, the regime may be turning. See [[Timing_Strategies#Regime]].

== Conclusions ==

# '''Default for core holdings:''' do not use tight fixed % stops.
# '''For dividend/slower-growth names:''' test '''fixed 25%''' and '''3× ATR(14)''', with a long-trend filter (e.g., >200-day [[Timing_Strategies#Simple_Moving_Average]] or ADX ≥ 25) to avoid trading sideways chop.
# '''For growth/compounders:''' accept drawdowns in exchange for participation; use trend filter only, not active trailing stops.
# '''For speculative names:''' the evidence is mixed; prefer [[Money_Management#ATR-Based_Position_Sizing|ATR-based stops]] over fixed % if you must have an exit.

== Recommended Rule Set ==

{| class="wikitable"
! Segment !! Entry filter !! Stop !! Re-enter when
|-
|| Growth / compound || price > SMA-200 || none (use trend filter) || trend filter restored
|-
|| Dividend / income || price > SMA-200 || '''25% trailing''' or '''3× ATR(14)''' || new high / MA50 reclaim
|-
|| Speculative || trend filter + volume confirmation || '''3× ATR(14)''' || [[Oscillators_and_Indicators#Bollinger_Bands|Bollinger lower]] reclaim + SMA-50 reclaim
|}

== Next Steps ==

* Validate on the '''complete holdings list''', not just the defaults in the script.
* Add a regime-aware mode: use active stops only when ADX ≤ 25 (range), otherwise revert to buy-hold.
* Replace <code>pd.read_sql(conn)</code> with SQLAlchemy engine to eliminate the persistent warning in long-running runs.

== References ==

* [[Money_Management#Position_Sizing]]
* [[Risk_Management#Stop_Loss_Policy]]
* [[Timing_Strategies#SMA]]
* [[AI_Trading_Skills#Backtesting_Framework]]
* [https://www.investopedia.com/terms/t/trailingstop.asp Investopedia: Trailing Stop]
* [https://www.investopedia.com/terms/a/atr.asp Investopedia: Average True Range (ATR)]
