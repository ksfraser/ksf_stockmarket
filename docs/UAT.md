# Investment Agent — UAT (User Acceptance Testing)

> **Standard:** Each test must pass _before_ the system is considered usable.
> **Environment:** MySQL at ksfraser.ca, walk-forward 2014-2018 train / 2019-2024 test.
> **Baseline:** Buy-and-hold equal-weight across 19 migrated symbols = benchmark to beat.

---

## UAT-1: Data Pipeline

| ID | Test | Expected | How to Verify |
|---|---|---|---|
| UAT-1.1 | Schema v4 creates 9 tables | `SHOW TABLES` returns 9 rows | `python3 -c "import pymysql; ..."` |
| UAT-1.2 | All 61,336 SQLite prices migrated | `SELECT COUNT(*) FROM stockprices` = 61,336 | COUNT query |
| UAT-1.3 | 404 symbols in symbol_master | `SELECT COUNT(*) FROM symbol_master` = 404 | COUNT query |
| UAT-1.4 | Correlation results migrated | `SELECT COUNT(*) FROM indicator_correlation` = 1,080 | COUNT query |
| UAT-1.5 | Partition pruning works | `EXPLAIN SELECT * FROM stockprices WHERE price_date='2020-06-01'` shows `p2020` only | EXPLAIN |
| UAT-1.6 | Tax parameters correct | 3rd bracket = 39% combined rate, gross-up = 1.38 | SELECT query |

## UAT-2: After-Tax Calculator

| ID | Test | Expected | How to Verify |
|---|---|---|---|
| UAT-2.1 | TFSA withdrawal tax = 0 | `calc_withdrawal_tax(5000, 'TFSA', 130000)` = 0 | Unit test |
| UAT-2.2 | RRSP withdrawal at bracket 3 | Tax on $10K from RRSP ≈ $2,500-$3,900 | Calculate |
| UAT-2.3 | Eligible div DTC | $1,000 CDN eligible div → grossed $1,380, DTC ≈ $320, net tax ≈ $217 | vs CRA calculator |
| UAT-2.4 | Capital gains 50% inclusion | $1,000 CG → $500 included → tax ≈ $195 at 39% bracket | Calculate |
| UAT-2.5 | Portfolio summary | 5-position portfolio → sum matches across all accounts | Cross-check |
| UAT-2.6 | Account comparison | RY.TO in TFSA > same in MARGINAL for total return | Asymmetric benefit |

## UAT-3: Allocation Backtester

| ID | Test | Expected | How to Verify |
|---|---|---|---|
| UAT-3.1 | US_Only > CDN_Only after-tax | US return 9.39% > CDN 6.06% | Backtest output |
| UAT-3.2 | Balanced 60/40 lowest tax drag | < 20% tax drag | Backtest output |
| UAT-3.3 | Results stored in DB | `after_tax_returns` table populated | COUNT query |
| UAT-3.4 | At least 3 strategies beat 0% after-tax | 3+ strategies have positive after-tax CAGR | Backtest |

## UAT-4: Retirement Simulator

| ID | Test | Expected | How to Verify |
|---|---|---|---|
| UAT-4.1 | Without withdrawal, portfolio grows | $50K → $86K+ (5%+ CAGR) on 19 symbols verbose sim | Output shows growth |
| UAT-4.2 | With $12K/yr withdrawal, portfolio depletes | Depletes within 4-5 years on conservative allocation | Output shows depletion |
| UAT-4.3 | December withdrawal order correct | TFSA drawn first, then RRSP | History shows TFSA→0 before RRSP drops |
| UAT-4.4 | Annual tax computed | Annual tax > 0 for marginal positions with dividends | Year state shows tax > 0 |
| UAT-4.5 | No share count goes negative | All holdings.shares >= 0 at all times | Assert in sim loop |
| UAT-4.6 | Monte Carlo distribution | Mean > 0, std > 0, 5th pctile < mean < 95th pctile | MC output |

## UAT-5: Universe Screener (Layer 0)

| ID | Test | Expected | How to Verify |
|---|---|---|---|
| UAT-5.1 | Fetches yfinance fundamentals | Fundamentals returned for a known symbol (e.g. AAPL) | Layer 0 output |
| UAT-5.2 | Buffett score for quality stock | AAPL score > 50 (good ROE, margins, FCF) | Layer 0 output |
| UAT-5.3 | CIBC eligibility check | TSX symbols → cost=0, OTC → rejected | Layer 0 output |
| UAT-5.4 | Per-sleeve filtering | Core sleeve has fewer candidates than tactical | Different counts per sleeve |
| UAT-5.5 | Candidates saved to DB | `layer0_candidates` table has rows with sleeve column | SELECT query |
| UAT-5.6 | Screener completes in < 30 min | 404 symbols × yfinance with rate limiting | Timing |

## UAT-6: GA Optimizer

| ID | Test | Expected | How to Verify |
|---|---|---|---|
| UAT-6.1 | Population initializes | 200 individuals, each valid (weights sum to 1.0, within constraints) | Assertion |
| UAT-6.2 | Fitness function runs | Each individual gets a single fitness value (no crash) | 200 fitness values |
| UAT-6.3 | Selection picks best | Top 5% survive (elitism), randomness in tournament | Generation 10 != Gen 1 |
| UAT-6.4 | Fitness improves over generations | Best fitness at Gen 100 >= Best fitness at Gen 0 | Log file |
| UAT-6.5 | Walk-forward doesn't peek | Training fitness uses 2014-2018 data only, test uses 2019-2024 | Data trace |
| UAT-6.6 | Output is actionable | Best individual maps to real portfolio decisions (which symbols, how much) | Decoded output |
| UAT-6.7 | Outperforms buy-and-hold | GA-optimized fitness > equal-weight B&H on test period | Compare terminal |
| UAT-6.8 | Runs in < 2 hours | Population 200 × Generations 100 × evaluation completes | Wall clock |

## UAT-7: NN (LSTM)

| ID | Test | Expected | How to Verify |
|---|---|---|---|
| UAT-7.1 | Model loads | LSTM with 120 input features, 2 layers, 120 hidden | print(model) |
| UAT-7.2 | Training runs | Loss decreases over 50 epochs (on training set) | Loss curve |
| UAT-7.3 | Validation doesn't overfit | Val loss within 2× train loss (no massive divergence) | Loss curve |
| UAT-7.4 | Predictions are reasonable | Mean prediction in range [-0.02, +0.02] for 20d return | Stats |
| UAT-7.5 | Walk-forward trains correctly | Train on 2014-2018, validate on 2019-2020, test on 2021-2024 | No data leak |
| UAT-7.6 | Outputs feed into GA | Predicted returns correlate (r > 0.05) with actual returns | Correlation |
| UAT-7.7 | Runs on GPU if available | Uses CUDA if nvidia-smi shows GPU, else CPU gracefully | Runtime check |

## UAT-8: RL (SB3 PPO)

| ID | Test | Expected | How to Verify |
|---|---|---|---|
| UAT-8.1 | Environment initializes | Gym env with correct observation/action spaces | env.observation_space |
| UAT-8.2 | Agent learns | Reward increases over 100K timesteps (on training set) | Reward curve |
| UAT-8.3 | Actions are valid | No sell more than owned, no buy beyond portfolio value | Assertion |
| UAT-8.4 | Walk-forward testing | Trained on 2014-2018, tested on 2019-2024 | Performance report |
| UAT-8.5 | Outperforms random | RL Sharpe > Random agent Sharpe on test period | Sharpe comparison |

## UAT-9: Blender

| ID | Test | Expected | How to Verify |
|---|---|---|---|
| UAT-9.1 | Weights sum to 1.0 | GA_weight + NN_weight + RL_weight = 1.0 always | Assertion |
| UAT-9.2 | Adaptive reweighting | Changes sleeve weights quarterly based on trailing Sharpe | Weight history |
| UAT-9.3 | Final decisions are coherent | No conflicting buy/sell for same symbol | Cross-check |
| UAT-9.4 | Outperforms any single agent | Blender Sharpe > GA-only, NN-only, RL-only Sharpe | Comparison |

## UAT-10: End-to-End Integration

| ID | Test | Expected | How to Verify |
|---|---|---|---|
| UAT-10.1 | Full pipeline runs | L0 → L1 → L2 → GA → NN → RL → Blender without crash | Script output |
| UAT-10.2 | Results stored in DB | `after_tax_returns` has walk-forward results | SELECT COUNT |
| UAT-10.3 | Walk-forward no peeking | Each training fold only sees past data | Timestamp audit |
| UAT-10.4 | Outperforms buy-and-hold | Agent terminal value > equal-weight B&H terminal value | Comparison |
| UAT-10.5 | Runs under disk budget | Total MySQL size < 500MB | `SELECT table_schema, SUM(index_length+data_length)` |
| UAT-10.6 | Generates human-readable report | Terminal report shows: start, end, CAGR, Sharpe, agents compared | Print output |

---

## Non-Functional Requirements

| ID | Requirement | Target |
|---|---|---|
| NF-1 | Screener run time (weekly) | < 30 minutes |
| NF-2 | GA optimization | < 2 hours |
| NF-3 | NN training | < 1 hour |
| NF-4 | RL training | < 4 hours |
| NF-5 | DB size | < 500 MB |
| NF-6 | Code coverage | > 80% |
| NF-7 | All parameters configurable | 100% in config.yaml |
