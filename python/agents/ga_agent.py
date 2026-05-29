#!/usr/bin/env python3
"""
ga_agent.py — Genetic Algorithm Agent for Signal Weight Optimization
=====================================================================
Uses DEAP (Distributed Evolutionary Algorithms in Python) to evolve
optimal signal weights for the 10 scoring tables. Each chromosome encodes
a full set of weights; fitness is evaluated by running the backtest engine
and measuring Sharpe ratio, return, and max drawdown.

Pipeline position: FIRST — runs nightly on priority symbols.
Results feed into NN Agent (as weighted features) and Blender (as signals).

Architecture:
  1. Chromosome = flattened dict of all scoring weights + TA signal weights
  2. Fitness = backtest(engine with these weights) → composite(Sharpe, return, maxdd)
  3. Selection = tournament (size 5)
  4. Crossover = simulated binary crossover (SBX)
  5. Mutation = polynomial bounded mutation
  6. Elitism = top 10% survive unchanged

Usage:
  python3 ga_agent.py                              # All holdings, default config
  python3 ga_agent.py --symbols RY.TO,TD.TO        # Specific symbols
  python3 ga_agent.py --generations 100 --pop 200  # More generations
  python3 ga_agent.py --fitness-objective sharpe   # Optimize for Sharpe only
  python3 ga_agent.py --run-id 42                  # Resume from agent_runs #42
"""

import argparse
import json
import logging
import os
import random
import sys
import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# DEAP for evolutionary computation
try:
    from deap import base, creator, tools, algorithms
    HAS_DEAP = True
except ImportError:
    HAS_DEAP = False
    print("WARNING: DEAP not available. Install with: pip install deap")

# Project imports
from python.db_connector import get_connection, get_active_symbols, fetch_price_data
from python.backtest_engine import BacktestEngine, DEFAULT_INITIAL_CAPITAL, DEFAULT_COMMISSION, DEFAULT_MAX_POSITION_PCT

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ===========================================================================
# CONFIGURATION
# ===========================================================================

DEFAULT_CONFIG = {
    'population_size': 100,
    'num_generations': 50,
    'mutation_rate': 0.15,
    'crossover_rate': 0.8,
    'elitism_pct': 0.1,
    'tournament_size': 5,
    'weight_min': -5.0,
    'weight_max': 5.0,
    'fitness_objective': 'sharpe_return_combo',  # sharpe, return, maxdd, sharpe_return_combo
    'backtest_years': 3,
    'initial_capital': DEFAULT_INITIAL_CAPITAL,
    'commission': DEFAULT_COMMISSION,
    'max_position_pct': DEFAULT_MAX_POSITION_PCT,
    'rebalance_frequency': 'monthly',
    'max_positions': 20,
    'seed': 42,
}

# Scoring table weight keys — each represents a multiplier for that signal group
# These are the "genes" in our chromosome
SCORING_WEIGHT_KEYS = [
    # 10 scoring table composite scores (from evalsummary)
    'w_totalscore',        # Overall composite score weight
    'w_marginsafety',      # Margin of safety weight
    'w_ratioscore',        # Financial ratios score weight
    'w_iplacecalcscore',   # InvestorPlace score weight
    'w_managementscore',   # Management tenets weight
    'w_financialscore',    # Financial tenets weight
    'w_businessscore',     # Business tenets weight
    'w_mf_score',          # Motley Fool score weight
    'w_ip_score',          # InvestorPlace score weight
    'w_tenet_score',       # Buffett tenets weight
    # TA signal weights (from daily_indicators / daily_tier2)
    'w_rsi_signal',        # RSI-based signal weight
    'w_macd_signal',       # MACD crossover weight
    'w_bollinger_signal',  # Bollinger Band breakout weight
    'w_volume_signal',     # Volume anomaly weight
    'w_sma_cross_signal',  # SMA crossover weight
    'w_gap_signal',        # Gap up/down weight
    'w_atr_signal',        # ATR volatility breakout weight
    # Correlation multiplier
    'w_correlation_boost', # How much to boost pre-indicators
]

NUM_GENES = len(SCORING_WEIGHT_KEYS)

# Signal-to-numeric mapping for fitness evaluation
SIGNAL_MAP = {
    'STRONG_BUY': 2.0,
    'BUY': 1.0,
    'HOLD': 0.0,
    'SELL': -1.0,
    'STRONG_SELL': -2.0,
}

BACKTEST_START_YEARS = 3  # Years of history for backtest fitness


# ===========================================================================
# CHROMOSOME / INDIVIDUAL
# ===========================================================================

def create_chromosome(config: dict) -> list:
    """Create a random chromosome (list of float weights)."""
    wmin = config.get('weight_min', -5.0)
    wmax = config.get('weight_max', 5.0)
    return [random.uniform(wmin, wmax) for _ in range(NUM_GENES)]


def chromosome_to_dict(chromosome: list) -> dict:
    """Convert chromosome list to named dict."""
    return {SCORING_WEIGHT_KEYS[i]: chromosome[i] for i in range(NUM_GENES)}


def dict_to_chromosome(weights_dict: dict) -> list:
    """Convert named dict back to chromosome list."""
    return [weights_dict.get(k, 1.0) for k in SCORING_WEIGHT_KEYS]


# ===========================================================================
# FITNESS EVALUATION
# ===========================================================================

class WeightedSignalGenerator:
    """
    Generates trading signals using weighted combination of all scoring tables
    and TA indicators. Used by the GA fitness function to evaluate a chromosome.
    """

    def __init__(self, conn, chromosome: list, config: dict):
        self.conn = conn
        self.weights = chromosome_to_dict(chromosome)
        self.config = config

    def get_weighted_signal(self, symbol: str, as_of_date: date) -> dict:
        """
        Generate a weighted signal for a symbol on a given date.
        Returns dict with 'direction' (BUY/SELL/HOLD), 'strength', 'score'.
        """
        signal_score = 0.0
        reasons = []

        # --- Fundamental signals from scoring tables ---
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT totalscore, marginsafety, ratioscore, iplacecalcscore,
                   managementscore, financialscore, businessscore,
                   mf_score, ip_score, tenet_score
            FROM evalsummary WHERE symbol = %s
        """, (symbol,))
        evalsum = cursor.fetchone()
        cursor.close()

        if evalsum:
            # Convert sqlite3.Row to dict if needed
            if hasattr(evalsum, 'keys'):
                evalsum = {k: evalsum[k] for k in evalsum.keys()}
            # Weight each scoring component
            if evalsum.get('totalscore') is not None:
                signal_score += self.weights['w_totalscore'] * (evalsum['totalscore'] / 36.0) * 100
            if evalsum.get('marginsafety') is not None:
                signal_score += self.weights['w_marginsafety'] * float(evalsum['marginsafety']) * 50
            if evalsum.get('ratioscore') is not None:
                signal_score += self.weights['w_ratioscore'] * (evalsum['ratioscore'] / 8.0) * 100
            if evalsum.get('iplacecalcscore') is not None:
                signal_score += self.weights['w_iplacecalcscore'] * (evalsum['iplacecalcscore'] / 10.0) * 100
            if evalsum.get('managementscore') is not None:
                signal_score += self.weights['w_managementscore'] * (evalsum['managementscore'] / 9.0) * 100
            if evalsum.get('financialscore') is not None:
                signal_score += self.weights['w_financialscore'] * (evalsum['financialscore'] / 4.0) * 100
            if evalsum.get('businessscore') is not None:
                signal_score += self.weights['w_businessscore'] * (evalsum['businessscore'] / 5.0) * 100
            if evalsum.get('mf_score') is not None:
                signal_score += self.weights['w_mf_score'] * (evalsum['mf_score'] / 7.0) * 100
            if evalsum.get('ip_score') is not None:
                signal_score += self.weights['w_ip_score'] * (evalsum['ip_score'] / 15.0) * 100
            if evalsum.get('tenet_score') is not None:
                signal_score += self.weights['w_tenet_score'] * (evalsum['tenet_score'] / 120.0) * 100

        # --- TA signals from daily indicators ---
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT rsi_14, macd, macd_signal, macd_hist,
                   sma_5, sma_20, sma_50, sma_200,
                   day_return, gap_pct, volume_ratio,
                   boll_upper, boll_middle, boll_lower, atr_14
            FROM v_with_indicators
            WHERE symbol = %s AND price_date = %s
        """, (symbol, as_of_date))
        ta = cursor.fetchone()
        cursor.close()

        if ta:
            # RSI signal (oversold < 30, overbought > 70)
            rsi = ta.get('rsi_14')
            if rsi is not None:
                rsi_val = float(rsi)
                if rsi_val < 30:
                    signal_score += self.weights['w_rsi_signal'] * (30 - rsi_val)
                    reasons.append(f'RSI_oversold={rsi_val:.1f}')
                elif rsi_val > 70:
                    signal_score += self.weights['w_rsi_signal'] * -(rsi_val - 70)
                    reasons.append(f'RSI_overbought={rsi_val:.1f}')

            # MACD crossover
            macd_hist = ta.get('macd_hist')
            if macd_hist is not None:
                signal_score += self.weights['w_macd_signal'] * np.sign(float(macd_hist)) * min(abs(float(macd_hist)) * 100, 5)
                if float(macd_hist) > 0:
                    reasons.append(f'MACD_bullish')
                else:
                    reasons.append(f'MACD_bearish')

            # Bollinger Band position
            close = ta.get('day_close')  # Added in view
            boll_upper = ta.get('boll_upper')
            boll_lower = ta.get('boll_lower')
            if close and boll_upper and boll_lower:
                close_f = float(close)
                if close_f > float(boll_upper):
                    signal_score += self.weights['w_bollinger_signal'] * -3  # Overbought
                elif close_f < float(boll_lower):
                    signal_score += self.weights['w_bollinger_signal'] * 3   # Oversold

            # SMA cross (golden cross / death cross)
            sma_50 = ta.get('sma_50')
            sma_200 = ta.get('sma_200')
            if sma_50 and sma_200:
                if float(sma_50) > float(sma_200):
                    signal_score += self.weights['w_sma_cross_signal'] * 5  # Golden cross
                else:
                    signal_score += self.weights['w_sma_cross_signal'] * -5  # Death cross

            # Volume spike
            vol_ratio = ta.get('volume_ratio')
            if vol_ratio is not None and float(vol_ratio) > 2.0:
                signal_score += self.weights['w_volume_signal'] * min(float(vol_ratio), 5)

            # Gap
            gap = ta.get('gap_pct')
            if gap is not None and abs(float(gap)) > 0.02:  # > 2% gap
                signal_score += self.weights['w_gap_signal'] * np.sign(float(gap)) * min(abs(float(gap)) * 100, 10)

        # Determine direction
        if signal_score > 15:
            direction = 'BUY'
        elif signal_score < -15:
            direction = 'SELL'
        else:
            direction = 'HOLD'

        return {
            'direction': direction,
            'strength': signal_score,
            'score': signal_score,
            'reasons': '; '.join(reasons) if reasons else 'weighted_combo',
        }


class GAFitnessEvaluator:
    """
    Evaluates a chromosome by running a simplified backtest.
    Uses the existing BacktestEngine infrastructure but overrides signal
    generation with weighted signals.
    """

    def __init__(self, conn, symbols: list, config: dict):
        self.conn = conn
        self.symbols = symbols
        self.config = config

    def evaluate(self, chromosome: list) -> tuple:
        """
        Evaluate a chromosome's fitness.
        Returns tuple of (composite_fitness,) for DEAP.

        Fitness = weighted combination of:
          - Sharpe ratio (40%)
          - Total return (35%)
          - Negative max drawdown (25% — lower DD is better)
        """
        try:
            weights = chromosome_to_dict(chromosome)
            sig_gen = WeightedSignalGenerator(self.conn, chromosome, self.config)

            # Run a simplified backtest using weighted signals
            start_date = date.today() - timedelta(days=365 * self.config['backtest_years'])
            end_date = date.today()

            # Get trading dates
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT DISTINCT price_date FROM stockprices
                WHERE price_date BETWEEN %s AND %s
                AND symbol IN ({})
                ORDER BY price_date ASC
            """.format(','.join(['%s'] * len(self.symbols))),
                [start_date, end_date] + self.symbols)
            trading_dates = [row[0] for row in cursor.fetchall()]
            cursor.close()

            if len(trading_dates) < 50:
                logger.warning(f"Insufficient trading dates: {len(trading_dates)}")
                return (-999.0,)  # Punish — not enough data

            # Simplified backtest simulation
            initial_capital = self.config['initial_capital']
            cash = initial_capital
            positions = {}  # symbol -> {shares, cost_basis, entry_date}
            portfolio_values = []
            num_trades = 0

            rebalance_interval = 30  # Monthly
            last_rebalance = trading_dates[0] - timedelta(days=rebalance_interval + 1)

            min_price_data_points = 20

            for i, current_date in enumerate(trading_dates):
                # Monthly rebalance
                if (current_date - last_rebalance).days >= rebalance_interval:
                    last_rebalance = current_date

                    # Generate weighted symbols for all symbols
                    buy_candidates = []
                    sell_candidates = []

                    for symbol in self.symbols:
                        # Check if we have a position
                        has_position = symbol in positions

                        # Only generate signals periodically to save compute
                        signal = sig_gen.get_weighted_signal(symbol, current_date)

                        if signal['direction'] == 'BUY' and signal['strength'] > 20:
                            buy_candidates.append((symbol, signal['strength'], signal['reasons']))
                        elif signal['direction'] == 'SELL' and has_position:
                            sell_candidates.append((symbol, signal['strength'], signal['reasons']))

                    # Sort by strength
                    buy_candidates.sort(key=lambda x: x[1], reverse=True)
                    sell_candidates.sort(key=lambda x: x[1])

                    # Execute sells first
                    for symbol, strength, reasons in sell_candidates:
                        pos = positions[symbol]
                        cursor = self.conn.cursor(dictionary=True)
                        cursor.execute("""
                            SELECT day_close FROM stockprices
                            WHERE symbol = %s AND price_date = %s
                        """, (symbol, current_date))
                        row = cursor.fetchone()
                        cursor.close()
                        if row:
                            price = float(row['day_close'])
                            proceeds = pos['shares'] * price - self.config['commission']
                            cash += proceeds
                            num_trades += 1
                            del positions[symbol]

                    # Execute buys (top N by signal strength)
                    max_positions = self.config['max_positions']
                    for symbol, strength, reasons in buy_candidates:
                        if len(positions) >= max_positions:
                            break
                        if symbol in positions:
                            continue

                        cursor = self.conn.cursor(dictionary=True)
                        cursor.execute("""
                            SELECT day_close FROM stockprices
                            WHERE symbol = %s AND price_date = %s
                        """, (symbol, current_date))
                        row = cursor.fetchone()
                        cursor.close()
                        if not row:
                            continue

                        price = float(row['day_close'])
                        max_investment = cash * self.config['max_position_pct']
                        shares = int(max_investment / price)
                        if shares <= 0:
                            continue
                        cost = shares * price + self.config['commission']
                        if cost > cash:
                            shares = int((cash - self.config['commission']) / price)
                            if shares <= 0:
                                continue
                            cost = shares * price + self.config['commission']

                        cash -= cost
                        positions[symbol] = {
                            'shares': shares,
                            'cost_basis': price,
                            'entry_date': current_date,
                        }
                        num_trades += 1

                # Record weekly portfolio value
                if i % 5 == 0:
                    total_value = cash
                    for symbol, pos in positions.items():
                        cursor = self.conn.cursor(dictionary=True)
                        cursor.execute("""
                            SELECT day_close FROM stockprices
                            WHERE symbol = %s AND price_date <= %s
                            ORDER BY price_date DESC LIMIT 1
                        """, (symbol, current_date))
                        row = cursor.fetchone()
                        cursor.close()
                        if row:
                            total_value += pos['shares'] * float(row['day_close'])

                    portfolio_values.append(total_value)

            # Final valuation
            final_value = cash
            for symbol, pos in positions.items():
                cursor = self.conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT day_close FROM stockprices
                    WHERE symbol = %s AND price_date <= %s
                    ORDER BY price_date DESC LIMIT 1
                """, (symbol, trading_dates[-1]))
                row = cursor.fetchone()
                cursor.close()
                if row:
                    final_value += pos['shares'] * float(row['day_close'])

            # Compute metrics
            total_return = (final_value - initial_capital) / initial_capital

            # Max drawdown
            peak = initial_capital
            max_drawdown = 0
            for val in portfolio_values:
                if val > peak:
                    peak = val
                dd = (peak - val) / peak if peak > 0 else 0
                if dd > max_drawdown:
                    max_drawdown = dd

            # Sharpe ratio (simplified)
            sharpe = 0.0
            if len(portfolio_values) > 1:
                returns = []
                for j in range(1, len(portfolio_values)):
                    prev = portfolio_values[j - 1]
                    curr = portfolio_values[j]
                    if prev > 0:
                        returns.append((curr - prev) / prev)
                if returns:
                    returns_arr = np.array(returns)
                    if returns_arr.std() > 0:
                        sharpe = float((returns_arr.mean() / returns_arr.std()) * (252 ** 0.5))

            # Composite fitness based on objective
            objective = self.config['fitness_objective']
            if objective == 'sharpe':
                fitness = sharpe
            elif objective == 'return':
                fitness = total_return * 100  # Percentage
            elif objective == 'maxdd':
                fitness = -max_drawdown * 100  # Negative so lower DD = higher fitness
            else:  # sharpe_return_combo
                # Normalize: Sharpe × 0.4 + return% × 0.35 + (-maxdd%) × 0.25
                fitness = (
                    sharpe * 0.4
                    + total_return * 100 * 0.35
                    + (-max_drawdown * 100) * 0.25
                )

            # Penalize too few trades (overfitting) or too many (overtrading)
            if num_trades < 5:
                fitness *= 0.5
            elif num_trades > 200:
                fitness *= 0.8

            logger.debug(
                f"  Fitness={fitness:.4f} | Sharpe={sharpe:.3f} | "
                f"Return={total_return*100:.1f}% | MaxDD={max_drawdown*100:.1f}% | "
                f"Trades={num_trades} | Final=${final_value:,.0f}"
            )

            return (fitness,)

        except Exception as e:
            logger.error(f"Fitness evaluation error: {e}")
            import traceback
            traceback.print_exc()
            return (-999.0,)  # Punish errors


# ===========================================================================
# DEAP SETUP
# ===========================================================================

def setup_deap(config: dict):
    """Initialize DEAP framework with fitness and individual types."""
    # Clear any previous DEAP state (important for repeated runs)
    if hasattr(creator, 'FitnessMax'):
        del creator.FitnessMax
    if hasattr(creator, 'Individual'):
        del creator.Individual

    creator.create("FitnessMax", base.Fitness, weights=(1.0,))
    creator.create("Individual", list, fitness=creator.FitnessMax)

    toolbox = base.Toolbox()

    # Attribute generator
    toolbox.register("attr_float", random.uniform,
                     config['weight_min'], config['weight_max'])

    # Structure initializers
    toolbox.register("individual", tools.initRepeat, creator.Individual,
                     toolbox.attr_float, n=NUM_GENES)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    # Genetic operators
    toolbox.register("mate", tools.cxSimulatedBinaryBounded,
                     low=config['weight_min'], up=config['weight_max'], eta=20.0)
    toolbox.register("mutate", tools.mutPolynomialBounded,
                     low=config['weight_min'], up=config['weight_max'],
                     eta=20.0, indpb=config['mutation_rate'])
    toolbox.register("select", tools.selTournament,
                     tournsize=config['tournament_size'])

    return toolbox


# ===========================================================================
# GA AGENT — Main class
# ===========================================================================

class GAAgent:
    """
    Genetic Algorithm Agent — Evolves optimal signal weights.
    Writes results to ga_results table and agent_runs table.
    """

    def __init__(self, conn, symbols: list, config: dict, run_id: int = None,
                 machine_id: str = None, priority: int = 5):
        self.conn = conn
        self.symbols = symbols
        self.config = {**DEFAULT_CONFIG, **config}
        self.run_id = run_id
        self.machine_id = machine_id or os.uname().nodename
        self.priority = priority
        self.start_time = None
        self.best_chromosome = None
        self.best_fitness = None
        self.generation_stats = []

    def _create_agent_run(self) -> int:
        """Create an agent_runs record and return the run_id."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO agent_runs
                (agent_type, run_name, priority, machine_id, status,
                 symbol_target, started_at)
            VALUES ('ga', %s, %s, %s, 'running', NULL, NOW())
        """, (
            f"GA_{self.config['num_generations']}gen_{len(self.symbols)}sym",
            self.priority,
            self.machine_id,
        ))
        self.conn.commit()
        run_id = cursor.lastrowid
        cursor.close()
        return run_id

    def _update_agent_run(self, status: str, result_json: dict = None,
                          error: str = None):
        """Update the agent_runs record."""
        cursor = self.conn.cursor()
        fitness_val = float(self.best_fitness) if self.best_fitness else None
        cursor.execute("""
            UPDATE agent_runs
            SET status = %s,
                completed_at = NOW(),
                duration_sec = TIMESTAMPDIFF(SECOND, started_at, NOW()),
                reward_score = %s,
                result_json = %s,
                error_message = %s
            WHERE id = %s
        """, (
            status,
            fitness_val,
            json.dumps(result_json) if result_json else None,
            error,
            self.run_id,
        ))
        self.conn.commit()
        cursor.close()

    def _save_ga_results(self, generation: int, population: list,
                          fitnesses: list, halloffame):
        """Save GA generation results to database."""
        best_idx = np.argmax(fitnesses)
        best_ind = population[best_idx]
        best_fit = fitnesses[best_idx]

        # Save best of this generation
        weights_dict = chromosome_to_dict(best_ind)
        cursor = self.conn.cursor()

        # Get fitness components from hall of fame
        is_best = 0
        if halloffame and len(halloffame) > 0:
            if best_ind == halloffame[0]:
                is_best = 1

        cursor.execute("""
            INSERT INTO ga_results
                (agent_run_id, symbol, generation, weights_json,
                 fitness_sharpe, fitness_return, fitness_maxdd,
                 fitness_composite, is_best)
            VALUES (%s, %s, %s, %s, NULL, NULL, NULL, %s, %s)
        """, (
            self.run_id,
            ','.join(self.symbols[:5]) + ('...' if len(self.symbols) > 5 else ''),
            generation,
            json.dumps(weights_dict),
            float(best_fit),
            is_best,
        ))
        self.conn.commit()
        cursor.close()

        # Update signal_weights with the best chromosome
        if is_best or generation == 0:
            self._update_signal_weights(weights_dict)

    def _update_signal_weights(self, weights_dict: dict):
        """Write best weights to signal_weights table for use by other agents."""
        cursor = self.conn.cursor()
        for i, key in enumerate(SCORING_WEIGHT_KEYS):
            weight_val = weights_dict.get(key, 1.0)
            cursor.execute("""
                INSERT INTO signal_weights
                    (signal_name, base_weight, source, updated_at)
                VALUES (%s, %s, 'ga_agent', NOW())
                ON DUPLICATE KEY UPDATE
                    base_weight = VALUES(base_weight),
                    source = VALUES(source),
                    updated_at = VALUES(updated_at)
            """, (key, float(weight_val)))
        self.conn.commit()
        cursor.close()
        logger.info(f"Updated signal_weights with {len(weights_dict)} GA-optimized weights")

    def run(self) -> dict:
        """
        Run the genetic algorithm optimization.
        Returns dict with best_fitness, best_weights, generations, etc.
        """
        if not HAS_DEAP:
            raise RuntimeError("DEAP not installed. Run: pip install deap")

        self.start_time = time.time()

        # Create agent run record
        if not self.run_id:
            self.run_id = self._create_agent_run()
        logger.info(f"GA Agent run #{self.run_id} | {self.config['num_generations']} generations | "
                    f"{self.config['population_size']} population | {len(self.symbols)} symbols")

        # Set random seed
        random.seed(self.config['seed'])
        np.random.seed(self.config['seed'])

        # Setup DEAP
        toolbox = setup_deap(self.config)

        # Create fitness evaluator
        evaluator = GAFitnessEvaluator(self.conn, self.symbols, self.config)

        # Register fitness evaluation function
        def evaluate_individual(individual):
            return evaluator.evaluate(individual)

        toolbox.register("evaluate", evaluate_individual)

        # Create initial population
        pop = toolbox.population(n=self.config['population_size'])

        # Hall of fame to track best individual
        hof = tools.HallOfFame(1)

        # Statistics
        stats = tools.Statistics(lambda ind: ind.fitness.values)
        stats.register("avg", np.mean)
        stats.register("std", np.std)
        stats.register("min", np.min)
        stats.register("max", np.max)

        # Logbook
        logbook = tools.Logbook()
        logbook.header = ["gen", "nevals", "avg", "std", "min", "max"]

        # Evaluate initial population
        logger.info("Evaluating initial population...")
        fitnesses = list(map(toolbox.evaluate, pop))
        for ind, fit in zip(pop, fitnesses):
            ind.fitness.values = fit

        hof.update(pop)
        record = stats.compile(pop)
        logbook.record(gen=0, nevals=len(pop), **record)
        logger.info(f"  Gen 0: avg={record['avg']:.3f} max={record['max']:.3f} min={record['min']:.3f}")

        self._save_ga_results(0, pop, [ind.fitness.values[0] for ind in pop], hof)

        # Evolution loop
        num_gens = self.config['num_generations']
        cx_rate = self.config['crossover_rate']
        mut_rate = self.config['mutation_rate']
        elitism_count = max(1, int(self.config['elitism_pct'] * self.config['population_size']))

        for gen in range(1, num_gens + 1):
            gen_start = time.time()

            # Selection + cloning
            offspring = toolbox.select(pop, len(pop) - elitism_count)
            offspring = list(map(toolbox.clone, offspring))

            # Crossover
            for child1, child2 in zip(offspring[::2], offspring[1::2]):
                if random.random() < cx_rate:
                    toolbox.mate(child1, child2)
                    del child1.fitness.values
                    del child2.fitness.values

            # Mutation
            for mutant in offspring:
                if random.random() < mut_rate:
                    toolbox.mutate(mutant)
                    del mutant.fitness.values

            # Elitism: carry over best individuals
            if hof and len(hof) > 0:
                elites = list(map(toolbox.clone, hof[:elitism_count]))
                for e in elites:
                    e.fitness.values = hof[0].fitness.values
                offspring.extend(elites)

            # Evaluate new individuals
            invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
            if invalid_ind:
                fitnesses = map(toolbox.evaluate, invalid_ind)
                for ind, fit in zip(invalid_ind, fitnesses):
                    ind.fitness.values = fit

            # Replace population
            pop[:] = offspring
            hof.update(pop)

            # Record stats
            record = stats.compile(pop)
            gen_time = time.time() - gen_start
            logbook.record(gen=gen, nevals=len(invalid_ind), **record)

            self.generation_stats.append({
                'generation': gen,
                'avg_fitness': float(record['avg']),
                'max_fitness': float(record['max']),
                'min_fitness': float(record['min']),
                'std_fitness': float(record['std']),
                'time_sec': gen_time,
            })

            if gen % 5 == 0 or gen == num_gens:
                logger.info(
                    f"  Gen {gen}/{num_gens}: avg={record['avg']:.3f} "
                    f"max={record['max']:.3f} min={record['min']:.3f} "
                    f"std={record['std']:.3f} ({gen_time:.1f}s)"
                )

            # Save to DB every 10 generations
            if gen % 10 == 0:
                self._save_ga_results(gen, pop,
                                      [ind.fitness.values[0] for ind in pop], hof)

        # Final save
        self._save_ga_results(num_gens, pop,
                              [ind.fitness.values[0] for ind in pop], hof)

        # Best individual
        best = hof[0]
        self.best_chromosome = list(best)
        self.best_fitness = best.fitness.values[0]
        best_weights = chromosome_to_dict(self.best_chromosome)

        # Final signal_weights update
        self._update_signal_weights(best_weights)

        elapsed = time.time() - self.start_time
        logger.info(f"{'='*60}")
        logger.info(f"GA Agent Complete — Run #{self.run_id}")
        logger.info(f"  Best Fitness:    {self.best_fitness:.4f}")
        logger.info(f"  Best Weights:    {json.dumps(best_weights, indent=4)}")
        logger.info(f"  Generations:     {num_gens}")
        logger.info(f"  Elapsed:         {elapsed:.1f}s")
        logger.info(f"{'='*60}")

        # Update agent run
        result = {
            'best_fitness': float(self.best_fitness),
            'best_weights': best_weights,
            'num_generations': num_gens,
            'num_symbols': len(self.symbols),
            'population_size': self.config['population_size'],
            'fitness_objective': self.config['fitness_objective'],
            'generation_stats': self.generation_stats,
            'elapsed_sec': elapsed,
        }
        self._update_agent_run('complete', result_json=result)

        return result


# ===========================================================================
# CLI
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(
        description='GA Agent — Genetic Algorithm for Signal Weight Optimization'
    )
    parser.add_argument('--symbols', type=str, default='',
                        help='Comma-separated symbols (default: all active)')
    parser.add_argument('--generations', type=int,
                        default=DEFAULT_CONFIG['num_generations'])
    parser.add_argument('--population', type=int,
                        default=DEFAULT_CONFIG['population_size'])
    parser.add_argument('--mutation-rate', type=float,
                        default=DEFAULT_CONFIG['mutation_rate'])
    parser.add_argument('--crossover-rate', type=float,
                        default=DEFAULT_CONFIG['crossover_rate'])
    parser.add_argument('--fitness-objective', type=str,
                        default=DEFAULT_CONFIG['fitness_objective'],
                        choices=['sharpe', 'return', 'maxdd', 'sharpe_return_combo'])
    parser.add_argument('--backtest-years', type=int,
                        default=DEFAULT_CONFIG['backtest_years'])
    parser.add_argument('--seed', type=int, default=DEFAULT_CONFIG['seed'])
    parser.add_argument('--run-id', type=int, default=None,
                        help='Resume from existing agent_runs ID')
    parser.add_argument('--machine-id', type=str, default=None)
    parser.add_argument('--priority', type=int, default=5)
    parser.add_argument('--weight-min', type=float, default=DEFAULT_CONFIG['weight_min'])
    parser.add_argument('--weight-max', type=float, default=DEFAULT_CONFIG['weight_max'])

    args = parser.parse_args()

    # Build config from args
    config = {
        'num_generations': args.generations,
        'population_size': args.population,
        'mutation_rate': args.mutation_rate,
        'crossover_rate': args.crossover_rate,
        'fitness_objective': args.fitness_objective,
        'backtest_years': args.backtest_years,
        'seed': args.seed,
        'weight_min': args.weight_min,
        'weight_max': args.weight_max,
    }

    # Connect to database
    conn = get_connection()

    # Get symbols
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(',')]
        logger.info(f"Using specified symbols: {symbols}")
    else:
        # Default: all active symbols with recent data
        symbols = get_active_symbols(conn)
        # Limit to top 50 for initial runs
        symbols = symbols[:50]
        logger.info(f"Using {len(symbols)} active symbols (limited to 50)")

    if not symbols:
        logger.error("No symbols found. Load data first.")
        sys.exit(1)

    # Create and run GA agent
    agent = GAAgent(
        conn=conn,
        symbols=symbols,
        config=config,
        run_id=args.run_id,
        machine_id=args.machine_id,
        priority=args.priority,
    )

    try:
        result = agent.run()
        print(json.dumps(result, indent=2, default=str))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        if agent.run_id:
            agent._update_agent_run('cancelled', error='KeyboardInterrupt')
    except Exception as e:
        logger.error(f"GA Agent failed: {e}")
        import traceback
        traceback.print_exc()
        if agent.run_id:
            agent._update_agent_run('failed', error=str(e))
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
