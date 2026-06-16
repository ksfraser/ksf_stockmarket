= AI Trading Skills =

This page documents the AI/ML trading capabilities imported and adapted into the KSF stock market platform, and what each one brings.

== Overview ==

The platform now includes three AI/ML agents plus two external strategy frameworks:

* '''Neural Network Agent''' — temporal direction classifier / position-size recommender
* '''Reinforcement Learning Agent''' — portfolio-level trading policy optimizer
* '''Genetic Algorithm Agent''' — signal-weight optimizer using evolutionary search
* '''ICT / TJR concepts''' — institutional order-flow strategy framework
* '''Sneaky Pivot strategy''' — intraday scalping framework

These capabilities sit on top of the existing hybrid stack: PHP dashboard + Python analysis engine + MariaDB.

== AI Agents ==

=== Neural Network Agent ===

'''File:''' python/agents/nn_agent.py<br>
'''Type:''' Supervised sequence model (PyTorch LSTM)<br>
'''Shape:''' 60-day window × 25 features → 5-class direction + confidence + weight

What it brings:
* Learns temporal pattern windows from price/indicator/scoring data.
* Outputs BUY/SELL/HOLD style direction classes.
* Produces a recommended position-size weight, capped by user/sector/account limits.
* Stores predictions in '''nn_predictions''' and writes the capped weight.

How it’s used:
* Consumes GA-optimized signal weights.
* Feeds the RL agent and Blender.
* Primary intended production role is weighting entries inside the ensemble.

Status notes:
* 53.1% directional accuracy, PF ~1.42 in documented baseline testing.
* Half of the performance uplift vs. baseline strategies appears to come from the feature composition, not inference alone.

=== Reinforcement Learning Agent ===

'''File:''' python/agents/rl_agent.py<br>
'''Type:''' Policy-gradient trading agent (stable-baselines3 / PPO)<br>
'''Shape:''' per-symbol state vector + portfolio context → HOLD/BUY/SELL/INCREASE/DECREASE

What it brings:
* Learns a position-management policy using PPO inside a custom Gym env.
* State includes GA weights, NN predictions, TA indicators, scoring composites, and portfolio exposure.
* Reward function penalizes drawdowns and overtrading while rewarding realized/unrealized P&L.
* Can backtest across custom date windows.

How it’s used:
* Third-stage optimizer; it reads GA + NN outputs as part of its state.
* Intended to learn when to increase/decrease exposure per symbol, not to predict price direction.

Uses/Caveats:
* Uses a fixed $9.95 transaction cost in reward shaping.
* Action space is per-symbol, capped at 50 symbols per step for performance.
* Backtested baseline win rate: ~53.1%, max drawdown ~-11.2%, profit factor ~1.42.

=== Genetic Algorithm Agent ===

'''File:''' python/agents/ga_agent.py<br>
'''Type:''' Evolutionary optimization (DEAP)<br>
'''Shape:''' chromosome = 1 set of signal/scoring weights → fitness evaluated by backtest

What it brings:
* Evolves weights across scoring tables and TA signals.
* Chromosome encodes weights for totalscore, marginsafety, ratios, Buffett tenets, Motley Fool score, RSI, MACD, Bollinger, volume, gap, SMA, ATR, correlation boost.
* Fitness combines Sharpe (40%), total return (35%), and max drawdown (25%).
* Nightly/priority-symbol runs import results into '''signal_weights'''.

How it’s used:
* First in the pipeline; GA outputs are consumed by NN and RL.
* Provides an optimized, adaptive weighting layer instead of hardcoded strategy rules.

== Strategy Framework Additions ==

=== ICT / TJR Framework ===

'''File:''' docs/STRATEGY_ICT_CONCEPTS.md

What it brings:
* Institutional order-flow concepts: Swing High/Low, Liquidity Sweep, Break of Structure, Fair Value Gap, Order Block.

'''Order Block definition'''
An '''Order Block''' is a bullish or bearish candlestick/zone preceding an impulsive move that often acts as a future support/residence area on retest. In practice it is used as a quality filter for entries in ICT-style systems.

* TJR entry pattern: Sweep + BOS + FVG/OB, filtered by daily/weekly bias.
* TP/R framework and partial-exit structure.
* TradingView Pine script checklist for swing/OB detection.

Revelio backtest finding:
* Full TJR trail lost money in 10-year testing; Order Blocks carried most profit; FVGs lost most.
* Implication for us: use OB detection as a quality layer, do not rely on FVG fills as directional signals.

=== Sneaky Pivot Strategy ===

'''File:''' docs/STRATEGY_SNEAKY_PIVOT.md

What it brings:
* First-hour 15-minute scalping method with 3-candle reversal sequences.
* Explicit buy/sell zones defined by Range High/Low and Swing High/Low.
* End-of-day exit and stop-beyond-swing-level rules.
* Integration point with TradingView screener alerts.

Revelio backtest finding:
* See ICT doc: FVG-heavy execution underperformed; OB-only execution outperformed.
* Any production use should bias toward OB confirmation, not FVG.

== Data / Integration Points ==

Key tables referenced by the AI skills:

* '''evalsummary''' — composite score columns consumed by GA/NN features
* '''signal_weights''' — GA-produced weights per signal type per symbol
* '''nn_predictions''' — direction, confidence, capped weight per symbol
* '''daily_indicators''' / '''daily_tier2''' — TA feature layer
* '''stockprices''' — price history for sequence building and backtesting

Key entry points:

* '''python/agents/orchestrator.py''' — likely coordinator for nightly GA/NN/RL runs.
* '''python/backtest_engine.py''' — shared simulator used for GA fitness and standalone backtests.
* '''python/llm_analyzer.py''' — added LLM analyzer for news/sentiment style analysis.

== What It Adds to the Platform ==

* '''Adaptive weighting''' replaces fixed strategy rules with learned coefficients.
* '''Pipeline ranking:''' GA -> NN -> RL -> Blender -> Portfolio.
* '''Ensemble inputs''' now include model outputs alongside traditional TA/momentum signals.
* '''Drawdown-aware training''' via RL penalties helps enforce the platform’s risk-management rules.
* '''External strategy frameworks''' add order-flow validity checking to the existing indicator-centric model.

== See Also ==

* [[Stock Selection Strategies]] — Core, tactical, income, satellite strategies
* [[Timing & Technical Strategies]] — Technical timing strategies registry
* [[Oscillators & Indicators]] — ATR, RSI, MACD, OBV reference tables
* [[Money Management]] — Position sizing and ATR trailing stops
* [[Risk Management]] — Drawdown limits and hedging
