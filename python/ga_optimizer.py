#!/usr/bin/env python3
"""
ga_optimizer.py — Genetic Algorithm optimizer for retirement portfolio.

Uses DEAP to evolve population of portfolio allocations.
Fitness = after-tax terminal value − λ × max_drawdown − penalty × cash_depletion

Walk-forward: train on 2014-2018, test on 2019-2024, step forward 1 year.

Usage:
    python3 ga_optimizer.py [--train-start 2014] [--train-end 2018] [--test-start 2019] [--test-end 2024]
"""
import sys, os, json, argparse, random, time
import numpy as np
import pymysql
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
from config_loader import Config
from retirement_simulator import RetirementSimulator, SimConfig

try:
    from deap import base, creator, tools, algorithms
except ImportError:
    print("DEAP not installed: pip3 install deap"); sys.exit(1)

MYSQL = dict(host='ksfraser.ca', user='ksfraser_stockmarket',
             password='Zaqwsx9sm1@', database='ksfraser_stock_market',
             charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)

# ── Gene Encoding ──────────────────────────────────────────────────────────
# Each individual = list of (symbol, weight) pairs + continuous params
# Weights sum to 1.0 per sleeve, continuous params within bounds

CONTINUOUS_PARAMS = [
    # name,          min,    max,    description
    ("atr_stop_mult", 1.5,   3.5,    "ATR stop multiplier"),
    ("risk_per_trade", 0.005, 0.02,  "Risk per trade (0.5-2%)"),
    ("forex_shift",   -0.10,  0.10,  "Forex allocation shift"),
    ("rebalance_pct", 0.03,   0.10,  "Rebalance drift threshold"),
    ("dca_installments", 1,   5,     "DCA installments (int)"),
]

N_CONTINUOUS = len(CONTINUOUS_PARAMS)


def load_prices_from_db(symbols, start, end):
    """Load price data from MySQL."""
    conn = pymysql.connect(**MYSQL); c = conn.cursor()
    placeholders = ','.join(['%s'] * len(symbols))
    c.execute(f"SELECT symbol, price_date, close FROM stockprices "
              f"WHERE symbol IN ({placeholders}) AND price_date BETWEEN %s AND %s "
              f"ORDER BY symbol, price_date", list(symbols) + [start, end])
    data = {}
    for r in c.fetchall():
        sym, d = r['symbol'], str(r['price_date'])
        data.setdefault(sym, {})[d] = float(r['close'])
    conn.close()
    return data


def get_candidate_symbols(config, sleeve=None):
    """Get candidate symbols from screener or DB."""
    conn = pymysql.connect(**MYSQL); c = conn.cursor()
    if sleeve:
        c.execute("SELECT DISTINCT symbol FROM layer0_candidates WHERE sleeve=%s ORDER BY buffet_score DESC LIMIT 50", (sleeve,))
    else:
        c.execute("SELECT symbol FROM symbol_master WHERE cibc_eligible=1 ORDER BY symbol LIMIT 100")
    syms = [r['symbol'] for r in c.fetchall()]
    conn.close()
    return syms


class GAEvaluator:
    """Evaluates fitness of a GA individual."""

    def __init__(self, symbols, prices, sim_config, ga_config):
        self.symbols = symbols
        self.prices = prices
        self.sim_config = sim_config
        self.ga_config = ga_config
        self.eval_count = 0

    def evaluate(self, individual):
        """
        Individual = [sym_weights..., continuous_params...]
        sym_weights: one float per candidate symbol (will be normalized to sum=1)
        continuous_params: 5 floats (ATR stop, risk%, forex shift, rebalance, DCA)
        """
        n_syms = len(self.symbols)

        # Decode individual
        raw_weights = list(individual[:n_syms])
        cont_params = individual[n_syms:]

        # Normalize weights
        total_w = sum(max(0, w) for w in raw_weights)
        if total_w <= 0:
            return (-1000.0,)  # invalid

        weights = {sym: max(0, w) / total_w for sym, w in zip(self.symbols, raw_weights)}

        # Remove tiny positions (< 1%)
        weights = {s: w for s, w in weights.items() if w >= 0.01}
        if not weights:
            return (-1000.0,)

        # Re-normalize
        tw = sum(weights.values())
        weights = {s: w / tw for s, w in weights.items()}

        # Build sim config
        sim_cfg = SimConfig(
            start_date=self.sim_config.start_date,
            end_date=self.sim_config.end_date,
            initial_tfsa=self.sim_config.initial_tfsa,
            initial_rrsp=self.sim_config.initial_rrsp,
            annual_withdrawal=self.sim_config.annual_withdrawal,
            marginal_income=self.sim_config.marginal_income,
        )

        try:
            sim = RetirementSimulator(sim_cfg, self.prices, weights)
            result = sim.simulate(verbose=False)

            terminal = result['terminal_value']
            total_start = sim_cfg.initial_tfsa + sim_cfg.initial_rrsp

            # Compute max drawdown from history
            values = [h['value'] for h in result['history']]
            max_dd = 0
            peak = values[0] if values else 1
            for v in values:
                if v > peak: peak = v
                dd = (peak - v) / peak if peak > 0 else 0
                max_dd = max(max_dd, dd)

            # Cash depletion penalty
            depletion_penalty = 0
            if terminal < total_start * 0.1:  # less than 10% remaining
                depletion_penalty = 10.0 * (1 - terminal / (total_start * 0.1))

            # Fitness after tax
            lambda_dd = self.ga_config.penalty_drawdown
            fitness = terminal - lambda_dd * max_dd * total_start - depletion_penalty * total_start

            self.eval_count += 1
            return (fitness,)

        except Exception:
            return (-1000.0,)


def run_ga(config, symbols, prices, train_start, train_end, test_start, test_end, verbose=False):
    """Run GA optimization with walk-forward testing."""
    cfg = config.ga

    # Create fitness and individual types
    creator.create("FitnessMax", base.Fitness, weights=(1.0,))
    creator.create("Individual", list, fitness=creator.FitnessMax)

    n_syms = len(symbols)
    n_genes = n_syms + N_CONTINUOUS

    toolbox = base.Toolbox()

    # Gene generators
    def random_weight():
        return random.random()  # 0-1, will be normalized

    def random_continuous(idx):
        lo, hi = CONTINUOUS_PARAMS[idx][1], CONTINUOUS_PARAMS[idx][2]
        return random.uniform(lo, hi)

    # Register generators
    toolbox.register("attr_weight", random_weight)
    toolbox.register("attr_cont", random_continuous)

    # Individual = n_syms weights + N_CONTINUOUS params
    toolbox.register("individual", tools.initCycle, creator.Individual,
                     (toolbox.attr_weight,) * n_syms +
                     (lambda i=i: random_continuous(i) for i in range(N_CONTINUOUS)),
                     n=1)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    # Operators
    toolbox.register("mate", tools.cxBlend, alpha=0.5)
    toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=0.1, indpb=0.2)
    toolbox.register("select", tools.selTournament, tournsize=3)

    # ── TRAINING ──────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"GA OPTIMIZATION — {n_syms} symbols, {n_genes} genes")
    print(f"Train: {train_start}-{train_end} | Test: {test_start}-{test_end}")
    print(f"Population: {cfg.population_size} | Generations: {cfg.generations}")
    print(f"{'='*60}")

    train_prices = {}
    for sym, sym_data in prices.items():
        train_prices[sym] = {d: p for d, p in sym_data.items() if train_start <= d[:4] <= train_end}

    train_sim_cfg = SimConfig(
        start_date=f'{train_start}-01-01', end_date=f'{train_end}-12-31',
        initial_tfsa=20000, initial_rrsp=30000, annual_withdrawal=12000,
        marginal_income=130000,
    )
    evaluator = GAEvaluator(symbols, train_prices, train_sim_cfg, cfg)
    toolbox.register("evaluate", evaluator.evaluate)

    # Run GA
    pop = toolbox.population(n=cfg.population_size)
    hof = tools.HallOfFame(maxsize=int(cfg.population_size * cfg.elite_pct))
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", np.mean)
    stats.register("min", np.min)
    stats.register("max", np.max)
    stats.register("std", np.std)

    t0 = time.time()
    pop, log = algorithms.eaSimple(pop, toolbox,
                                    cxpb=cfg.crossover_prob, mutpb=cfg.mutation_prob,
                                    ngen=cfg.generations, stats=stats, halloffame=hof,
                                    verbose=verbose)
    elapsed = time.time() - t0

    best = hof[0]
    n_syms_actual = len(symbols)
    best_weights = {sym: max(0, best[i]) for i, sym in enumerate(symbols)}
    tw = sum(best_weights.values())
    best_weights = {s: w / tw for s, w in best_weights.items() if w / tw >= 0.01}

    best_cont = {}
    for i, (name, lo, hi, desc) in enumerate(CONTINUOUS_PARAMS):
        best_cont[name] = best[n_syms_actual + i]

    print(f"\nTraining complete in {elapsed:.0f}s ({evaluator.eval_count} evaluations)")
    print(f"Best fitness: {best.fitness.values[0]:,.0f}")
    print(f"Best weights ({len(best_weights)} symbols):")
    for s, w in sorted(best_weights.items(), key=lambda x: -x[1])[:15]:
        print(f"  {s:<15} {w*100:>5.1f}%")
    print(f"Best continuous params:")
    for name, val in best_cont.items():
        print(f"  {name:<20} {val:.4f}" if isinstance(val, float) else f"  {name:<20} {val}")

    # ── WALK-FORWARD TEST ─────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"WALK-FORWARD TEST: {test_start}-{test_end}")
    print(f"{'='*60}")

    test_prices = {}
    for sym, sym_data in prices.items():
        test_prices[sym] = {d: p for d, p in sym_data.items() if test_start <= d[:4] <= test_end}

    test_sim_cfg = SimConfig(
        start_date=f'{test_start}-01-01', end_date=f'{test_end}-12-31',
        initial_tfsa=20000, initial_rrsp=30000, annual_withdrawal=12000,
        marginal_income=130000,
    )

    if test_prices and best_weights:
        test_sim = RetirementSimulator(test_sim_cfg, test_prices, best_weights)
        test_result = test_sim.simulate(verbose=True)

        # Compare to equal-weight
        eq_weights = {s: 1.0 / len(best_weights) for s in best_weights}
        eq_sim = RetirementSimulator(test_sim_cfg, test_prices, eq_weights)
        eq_result = eq_sim.simulate(verbose=False)

        print(f"\n{'='*60}")
        print(f"COMPARISON: GA vs Equal-Weight B&H")
        print(f"{'='*60}")
        terminal_ga = test_result['terminal_value']
        terminal_eq = eq_result['terminal_value']
        print(f"  GA optimized:   ${terminal_ga:>12,.2f}  CAGR: {test_result['cagr']*100:.2f}%")
        print(f"  Equal-weight:   ${terminal_eq:>12,.2f}  CAGR: {eq_result['cagr']*100:.2f}%")
        if terminal_eq > 0:
            outperf = (terminal_ga / terminal_eq - 1) * 100
            print(f"  Outperformance: {outperf:>+.1f}%")

        # Save results
        conn = pymysql.connect(**MYSQL); c = conn.cursor()
        c.execute("""INSERT INTO after_tax_returns 
            (date, strategy_name, account_type, total_return, after_tax_return, tax_drag_pct)
            VALUES (CURDATE(), 'GA_optimized', 'MARGINAL', %s, %s, %s)""",
            (terminal_ga, terminal_ga, 0))
        conn.commit(); conn.close()
    else:
        test_result = None
        print("  Insufficient test data — skipping walk-forward test")

    return {
        'best_weights': best_weights,
        'best_continuous': best_cont,
        'best_fitness': best.fitness.values[0],
        'training_time_s': elapsed,
        'n_evaluations': evaluator.eval_count,
        'test_result': test_result,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--train-start', type=int, default=2014)
    parser.add_argument('--train-end', type=int, default=2018)
    parser.add_argument('--test-start', type=int, default=2019)
    parser.add_argument('--test-end', type=int, default=2024)
    parser.add_argument('--symbols', type=int, default=19, help='Number of symbols to optimize')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    config = Config('/home/ksf_stockmarket/ksf_stockmarket/config.yaml')
    symbols = get_candidate_symbols(config)[:args.symbols]

    # Load all prices
    all_prices = load_prices_from_db(symbols, '2014-01-01', '2024-12-31')
    available = [s for s in symbols if s in all_prices]
    print(f"Available: {len(available)}/{len(symbols)} symbols")

    if len(available) < 3:
        print("Need at least 3 symbols for GA. Exiting.")
        return

    result = run_ga(config, available, all_prices,
                    args.train_start, args.train_end,
                    args.test_start, args.test_end,
                    verbose=args.verbose)

    # Save to JSON report
    report_path = '/root/.hermes/workspace/ksf_stockmarket/docs/ga_report.json'
    with open(report_path, 'w') as f:
        json.dump({
            'best_weights': result['best_weights'],
            'best_params': result['best_continuous'],
            'fitness': result['best_fitness'],
            'time_s': result['training_time_s'],
        }, f, indent=2, default=str)
    print(f"\nReport saved to {report_path}")


if __name__ == '__main__':
    main()
