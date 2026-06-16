[[Category: ksf_stockmarket]]
= Stock Selection Strategies =

This page documents all stock selection strategies used by the Investment Agent platform. For technical timing strategies, see [[Timing Strategies]]. For money and risk management, see [[Money Management]].

''Last updated: 2026-05-31 — 20 strategies registered''

== Overview ==

Stock selection strategies filter the universe of 400+ symbols to identify candidates. They are organized by the '''portfolio sleeve''' they are designed for:

* '''Core (40%)''' — Buy & hold 5+ years. Wide moat, quality compounders. Low turnover.
* '''Tactical (30%)''' — Hold 1-6 months. Momentum, earnings, breakouts.
* '''Income (20%)''' — Hold 1-3 years. Dividends, aristocrats, REITs.
* '''Satellite (10%)''' — Hold 3-12 months. Deep value, moonshots, options.

Each strategy is implemented as a PHP class implementing <code>IStrategy</code> and registered via ''Dependency Injection'' through <code>StrategyFactory</code>. To add a new strategy, create a class and register it — no hardcoded data needed.

Sources include: Investopedia, academic research (Jegadeesh & Titman, Piotroski, Bernard & Thomas), Motley Fool, and our own 372,000+ backtest results.

== Core Sleeve Strategies (40%) ==

=== Warren Buffett Quality Score ===

'''Source:''' Berkshire Hathaway letters, Motley Fool Stock Advisor "Wide Moat"<br>
'''Philosophy:''' Buy wonderful companies at fair prices and hold forever. Not a timing strategy — use as first-pass universe filter.

'''Screening Criteria:'''
* ROE > 15% (5-year average)
* Debt/Equity < 0.5
* Gross Margin > 40%
* Operating Margin > 15%
* Free Cash Flow positive 5+ years
* Revenue growth > 10% (5-year CAGR)
* PEG Ratio < 1.5
* Management ownership > 1%
* No earnings decline in last 5 years

'''Results:''' Stock Advisor returned +978% vs S&P +212% (2002-2026)<br>
'''Status:''' SCREENING TOOL<br>
'''Best For:''' Universe filter before applying technical entry signals. Holdings scoring >60/100 show significantly lower volatility.

=== GARP — Growth at Reasonable Price (Peter Lynch) ===

'''Source:''' Peter Lynch "One Up on Wall Street" (1989), Investopedia<br>
'''Results:''' Fidelity Magellan Fund returned 29.2% annually (1977-1990)

'''Screening Criteria:'''
* PEG Ratio < 1.0 (ideal), < 1.5 (acceptable)
* EPS growth 15-25% (too fast is unsustainable)
* Institutional ownership < 50%
* Insider buying in last 6 months
* Debt/Equity < industry average

'''Status:''' BATTLE TESTED<br>
'''Best For:''' Core quality compounders at reasonable valuations.

== Tactical Sleeve Strategies (30%) ==

=== CANSLIM (William O'Neil) ===

'''Source:''' William O'Neil, IBD, [https://www.investopedia.com Investopedia]<br>
'''Philosophy:''' Buy leading stocks in strong sectors just before breakouts from sound bases.

Each letter:
* '''C''' — Current quarterly EPS up ≥ 25% vs same quarter last year
* '''A''' — Annual EPS growth ≥ 20% for 5 years
* '''N''' — New products/services, new highs, new management
* '''S''' — Supply/demand, small float, high relative strength
* '''L''' — Leader — #1 in sector, RS Rating ≥ 80
* '''I''' — Institutional sponsorship — 3-10 mutual funds
* '''M''' — Market direction — ONLY buy in confirmed uptrend (S&P > 200d MA)

'''Backtest Results:'''
{| class="wikitable"
! Win Rate !! Profit Factor !! Max Drawdown !! Trades
|-
| 46% || 1.31 || -14.7% || 2,103
|}

'''Status:''' BATTLE TESTED<br>
'''Warning:''' Whipsaws in choppy markets. Stop losses essential (-7% rule). Underperforms in bear markets without market direction filter.

=== Momentum + Relative Strength ===

'''Source:''' Jegadeesh & Titman (1993), AQR, [https://www.investopedia.com Investopedia]<br>
'''Academic:''' Momentum generates 1% monthly alpha. AQR outperformed S&P by 3-5% annually since 1980.

'''Screening:''' 6-month return > 80th percentile, 12-month > 70th, RS ≥ 80, Price > 200d MA

'''DANGER:''' Momentum crashes (2009, 2020) — combine with VIX fear gauge and market direction filter.

=== Earnings Momentum (PEAD) ===

'''Source:''' Bernard & Thomas (1989), Investopedia<br>
'''Academic:''' Post-Earnings Announcement Drift generates 6-9% annualized excess return.

Stocks that beat earnings expectations continue to drift upward for 60-90 days after announcement.

'''Screening:''' Earnings surprise > 5%, revenue surprise > 3%, guidance raised, gap up > 3%.

== Income Sleeve Strategies (20%) ==

=== Dividend Aristocrats & Kings ===

'''Source:''' S&P Dividend Aristocrats Index, Investopedia<br>
'''Results:''' S&P Aristocrats returned 10.5% annually (2008-2023) with lower volatility.

'''Screening:''' 25+ consecutive years of dividend increases (Aristocrats), 50+ years (Kings), payout ratio < 60%.

=== Piotroski F-Score ===

'''Source:''' Piotroski (2000), Investopedia<br>
'''Academic:''' F-Score 8-9 stocks outperformed by 7.5% annually among cheap stocks.

Among low P/B stocks, pick financially healthy ones using 9 binary criteria. Score 8-9 = strong.

== Status Legend ==

{| class="wikitable"
! Status !! Meaning
|-
| style="color:green" | BATTLE TESTED || Validated through walk-forward backtesting, production-ready
|-
| style="color:green" | RECOMMENDED || Theoretical/strong evidence, recommended for use
|-
| style="color:orange" | PROMISING || Backed by some data, needs further validation
|-
| style="color:blue" | SCREENING TOOL || Universe filter, not a standalone timing strategy
|}

== See Also ==

* [[Timing Strategies]] — Technical entry/exit signals for all sleeves
* [[Money Management]] — Position sizing, stops, portfolio construction
* [[Candlestick Patterns]] — Candlestick pattern reference (largely noise for daily trading)
* [[Oscillators & Indicators]] — RSI, MACD, Stochastic, ADX, OBV, Bollinger reference
* [[Risk Management]] — Portfolio-level risk controls
* [[Habits of Successful Investors]] — Behavioural finance principles
