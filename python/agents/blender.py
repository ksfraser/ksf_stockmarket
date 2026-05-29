#!/usr/bin/env python3
"""
blender.py — Signal Blender & Portfolio Optimizer
===================================================
FIFTH and final agent in the pipeline. Consumes outputs from GA, NN, and RL
agents, produces a weighted consensus signal, applies position sizing with
user caps, and generates a rebalance plan.

Pipeline: GA (weights) → NN (direction+confidence) → RL (policy) → BLENDER (consensus+execution)

Responsibilities:
  1. Read latest ga_results (optimized weights per signal)
  2. Read latest nn_predictions (direction + confidence + capped weight)
  3. Read latest rl_signals (RL policy decisions)
  4. Weighted consensus: ga_weight*0.30 + nn_weight*0.35 + rl_weight*0.35
  5. Position sizing: min(agent_recommended, user_position_caps)
  6. Rebalance plan: what to buy/sell/trim/add
  7. Write portfolio_orders table
  8. Optional: execute approved orders via backtest engine

Usage:
  python3 blender.py                                    # Full blend + rebalance plan
  python3 blender.py --dry-run                          # Don't write orders
  python3 blender.py --consensus-threshold 70           # Require 70% agreement
  python3 blender.py --max-positions 15                 # Smaller portfolio
  python3 blender.py --account TFSA                     # Only TFSA orders
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from python.db_connector import get_connection, get_active_symbols
from python.agents.ga_agent import chromosome_to_dict, SCORING_WEIGHT_KEYS
from python.agents.nn_agent import PositionCapEnforcer, DEFAULT_CONFIG as NN_DEFAULTS

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ===========================================================================
# CONFIGURATION
# ===========================================================================

DEFAULT_CONFIG = {
    'ga_weight': 0.30,           # Weight for GA signal in consensus
    'nn_weight': 0.35,           # Weight for NN signal in consensus
    'rl_weight': 0.35,           # Weight for RL signal in consensus
    'consensus_threshold': 60.0,  # Minimum % agreement to generate trade
    'max_positions': 20,          # Max simultaneous positions
    'risk_per_trade_pct': 1.0,    # Max portfolio % risked per trade
    'review_frequency_days': 7,   # Days between full portfolio reviews
    'min_consensus_for_new': 2,   # Min agents agreeing to open new position
    'min_consensus_for_exit': 2,  # Min agents agreeing to close position
    'rebalance_tolerance': 0.02,  # Don't trade if within 2% of target
    'seed': 42,
}

# Signal → numeric score for consensus
SIGNAL_SCORES = {
    'STRONG_BUY':  2.0,
    'BUY':         1.0,
    'HOLD':        0.0,
    'SELL':       -1.0,
    'STRONG_SELL': -2.0,
}

# Direction from RL actions to our signal space
RL_ACTION_TO_SIGNAL = {
    'BUY':      'BUY',
    'SELL':     'SELL',
    'HOLD':     'HOLD',
    'INCREASE': 'STRONG_BUY',
    'DECREASE': 'SELL',
}


# ===========================================================================
# SIGNAL CONSENSUS ENGINE
# ===========================================================================

class SignalConsensus:
    """
    Combines GA, NN, RL signals into a weighted consensus.
    """

    def __init__(self, config: dict):
        self.config = config

    def compute_consensus(self, ga_signal: dict, nn_signal: dict,
                           rl_signal: dict) -> dict:
        """
        Compute weighted consensus from three agent signals.

        Returns dict with:
          - direction: consensus direction
          - consensus_score: numeric score (-2 to +2)
          - consensus_pct: % of agents in agreement
          - target_weight: recommended position weight
          - agent_agreement: which agents agree
        """
        # Extract signals
        ga_dir = ga_signal.get('direction', 'HOLD')
        ga_weight = SIGNAL_SCORES.get(ga_dir, 0) * ga_signal.get('strength', 0)

        nn_dir = nn_signal.get('direction', 'HOLD')
        nn_weight = SIGNAL_SCORES.get(nn_dir, 0) * nn_signal.get('confidence', 0.5)
        nn_capped_weight = nn_signal.get('user_cap_weight', 0.05)

        rl_dir = rl_signal.get('direction', 'HOLD')
        rl_weight = SIGNAL_SCORES.get(rl_dir, 0) * rl_signal.get('confidence', 0.5)
        rl_target = rl_signal.get('target_weight', 0.05)

        # Weighted consensus score
        ga_norm = max(min(ga_signal.get('strength', 0) / 50.0, 1.0), -1.0)
        nn_norm = nn_weight * 2  # Scale to roughly -1 to 1
        rl_norm = rl_weight * 2

        consensus_score = (
            self.config['ga_weight'] * ga_norm +
            self.config['nn_weight'] * nn_norm +
            self.config['rl_weight'] * rl_norm
        )

        # Map score back to direction
        if consensus_score > 0.8:
            consensus_dir = 'STRONG_BUY'
        elif consensus_score > 0.3:
            consensus_dir = 'BUY'
        elif consensus_score > -0.3:
            consensus_dir = 'HOLD'
        elif consensus_score > -0.8:
            consensus_dir = 'SELL'
        else:
            consensus_dir = 'STRONG_SELL'

        # Consensus %: how many agents agree on direction
        # Use "base" direction for agreement check (STRONG_BUY → BUY, STRONG_SELL → SELL)
        def _base_dir(d):
            if d in ('STRONG_BUY', 'BUY'):
                return 'BUY'
            if d in ('STRONG_SELL', 'SELL'):
                return 'SELL'
            return d

        base_consensus = _base_dir(consensus_dir)
        all_dirs = [ga_dir, nn_dir, rl_dir]
        agreement_count = sum(1 for d in all_dirs if _base_dir(d) == base_consensus)
        consensus_pct = (agreement_count / 3.0) * 100

        # Position sizing: average of NN capped weight and RL target
        target_weight = (
            self.config['nn_weight'] * nn_capped_weight +
            self.config['rl_weight'] * rl_target +
            self.config['ga_weight'] * min(abs(ga_norm) * 0.1, 0.10)
        )

        # Which agents agree (base direction match)
        agents_agree = []
        for name, d in [('GA', ga_dir), ('NN', nn_dir), ('RL', rl_dir)]:
            if _base_dir(d) == base_consensus:
                agents_agree.append(name)

        return {
            'direction': consensus_dir,
            'consensus_score': round(consensus_score, 4),
            'consensus_pct': round(consensus_pct, 2),
            'target_weight': round(target_weight, 4),
            'agents_agree': agents_agree,
            'ga_direction': ga_dir,
            'nn_direction': nn_dir,
            'rl_direction': rl_dir,
            'ga_strength': round(ga_signal.get('strength', 0), 2),
            'nn_confidence': round(nn_signal.get('confidence', 0), 4),
            'rl_confidence': round(rl_signal.get('confidence', 0), 4),
        }


# ===========================================================================
# REBALANCE PLAN GENERATOR
# ===========================================================================

class RebalancePlan:
    """
    Generates a rebalance plan: what to buy, sell, increase, decrease.
    Considers current holdings, consensus signals, position caps.
    """

    def __init__(self, conn, config: dict, cap_enforcer: PositionCapEnforcer):
        self.conn = conn
        self.config = config
        self.cap_enforcer = cap_enforcer

    def get_current_holdings(self) -> Dict[str, dict]:
        """Get current portfolio from database."""
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT symbol, SUM(shares) as shares, SUM(cost_total) as cost_total
            FROM portfolio
            WHERE is_active = 1
            GROUP BY symbol
        """)
        holdings = {}
        for row in cursor.fetchall():
            if row['shares'] > 0:
                holdings[row['symbol']] = {
                    'shares': float(row['shares']),
                    'cost_basis': float(row['cost_total']) / float(row['shares']) if row['shares'] > 0 else 0,
                    'cost_total': float(row['cost_total']),
                }
        cursor.close()
        return holdings

    def get_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get latest prices for symbols."""
        prices = {}
        cursor = self.conn.cursor(dictionary=True)
        for symbol in symbols:
            cursor.execute("""
                SELECT day_close FROM stockprices
                WHERE symbol = %s
                ORDER BY price_date DESC LIMIT 1
            """, (symbol,))
            row = cursor.fetchone()
            if row and row['day_close']:
                prices[symbol] = float(row['day_close'])
        cursor.close()
        return prices

    def generate_plan(self, consensus_signals: Dict[str, dict],
                      current_value: float = 100000.0) -> List[dict]:
        """
        Generate rebalance orders based on consensus signals and current holdings.
        Returns list of order dicts.
        """
        holdings = self.get_current_holdings()
        prices = self.get_current_prices(list(consensus_signals.keys()) + list(holdings.keys()))

        orders = []

        # --- Determine actions for each symbol ---
        all_symbols = set(consensus_signals.keys()) | set(holdings.keys())
        current_positions = len([s for s in holdings if holdings[s]['shares'] > 0])

        # First pass: identify sells and trims (free up capital)
        sells = []
        for symbol in holdings:
            if symbol not in consensus_signals:
                continue

            sig = consensus_signals[symbol]
            if 'SELL' in sig['direction']:
                sells.append((symbol, sig))

        # Second pass: identify buys (sorted by consensus score)
        buys = []
        for symbol in consensus_signals:
            sig = consensus_signals[symbol]
            if 'BUY' in sig['direction']:
                buys.append((symbol, sig))
        buys.sort(key=lambda x: x[1]['consensus_score'], reverse=True)

        # --- Generate SELL orders ---
        for symbol, sig in sells:
            pos = holdings.get(symbol)
            if not pos:
                continue

            price = prices.get(symbol, 0)
            if price <= 0:
                continue

            shares = pos['shares']

            order = {
                'symbol': symbol,
                'action': 'SELL',
                'reason': f"Consensus: {sig['direction']} "
                          f"(GA:{sig.get('ga_direction','?')} "
                          f"NN:{sig.get('nn_direction','?')} "
                          f"RL:{sig.get('rl_direction','?')})",
                'target_shares': 0,
                'trade_shares': -int(shares),
                'estimated_price': price,
                'estimated_cost': -(shares * price - 9.95),
                'ga_signal': sig.get('ga_direction'),
                'nn_signal': sig.get('nn_direction'),
                'rl_signal': sig.get('rl_direction'),
                'consensus_pct': sig['consensus_pct'],
                'priority': 1,  # Sells first
            }
            orders.append(order)

        # --- Generate BUY orders ---
        max_new_positions = self.config['max_positions'] - current_positions + len(sells)
        new_positions = 0

        for symbol, sig in buys:
            if new_positions >= max_new_positions:
                break

            if symbol in holdings and holdings[symbol]['shares'] > 0:
                # Already holding — check if we should increase
                if sig['direction'] == 'STRONG_BUY':
                    action = 'INCREASE'
                else:
                    continue  # Already holding, no increase needed
            else:
                action = 'BUY'

            price = prices.get(symbol, 0)
            if price <= 0:
                continue

            # Position sizing
            target_weight = sig['target_weight']
            target_value = current_value * target_weight
            raw_shares = int(target_value / price)

            if raw_shares <= 0:
                continue

            # Apply caps
            effective_weight, cap_reason = self.cap_enforcer.get_effective_weight(
                target_weight, symbol=symbol
            )
            capped_value = current_value * effective_weight
            capped_shares = int(capped_value / price)
            capped_shares = max(capped_shares, 1)  # At least 1 share

            if action == 'INCREASE':
                add_shares = min(capped_shares, holdings[symbol]['shares'])
                trade_shares = add_shares
                target_shares = holdings[symbol]['shares'] + add_shares
            else:
                trade_shares = capped_shares
                target_shares = capped_shares

            cost = trade_shares * price + 9.95

            order = {
                'symbol': symbol,
                'action': action,
                'reason': f"Consensus: {sig['direction']} "
                          f"score={sig['consensus_score']:.2f} "
                          f"({','.join(sig['agents_agree'])}) "
                          f"cap: {cap_reason}",
                'target_shares': target_shares,
                'trade_shares': trade_shares,
                'estimated_price': price,
                'estimated_cost': cost,
                'ga_signal': sig.get('ga_direction'),
                'nn_signal': sig.get('nn_direction'),
                'rl_signal': sig.get('rl_direction'),
                'consensus_pct': sig['consensus_pct'],
                'priority': 3 if action == 'INCREASE' else 2,
            }
            orders.append(order)
            if action == 'BUY':
                new_positions += 1

        # Sort: sells first, then buys by priority
        orders.sort(key=lambda x: x['priority'])

        return orders


# ===========================================================================
# BLENDER AGENT — Main class
# ===========================================================================

class BlenderAgent:
    """
    Signal Blender & Portfolio Optimizer.
    Fifth and final agent in the pipeline.
    """

    def __init__(self, conn, config: dict, run_id: int = None,
                 machine_id: str = None, priority: int = 3):
        self.conn = conn
        self.config = {**DEFAULT_CONFIG, **config}
        self.run_id = run_id
        self.machine_id = machine_id or os.uname().nodename
        self.priority = priority
        self.consensus_engine = SignalConsensus(self.config)
        self.cap_enforcer = PositionCapEnforcer(conn)

    def _create_agent_run(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO agent_runs
                (agent_type, run_name, priority, machine_id, status,
                 symbol_target, started_at)
            VALUES ('blender', %s, %s, %s, 'running', NULL, NOW())
        """, (
            f"BLEND_{self.config['ga_weight']}/{self.config['nn_weight']}/{self.config['rl_weight']}",
            self.priority,
            self.machine_id,
        ))
        self.conn.commit()
        run_id = cursor.lastrowid
        cursor.close()
        return run_id

    def _update_agent_run(self, status: str, result_json: dict = None,
                          error: str = None):
        cursor = self.conn.cursor()
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
            result_json.get('consensus_score_avg') if result_json else None,
            json.dumps(result_json) if result_json else None,
            error,
            self.run_id,
        ))
        self.conn.commit()
        cursor.close()

    def _fetch_ga_signals(self, symbols: List[str],
                           as_of_date: date) -> Dict[str, dict]:
        """Fetch latest GA-optimized weights and generate signals."""
        signals = {}
        cursor = self.conn.cursor(dictionary=True)
        for symbol in symbols:
            # Get latest GA result for this symbol
            cursor.execute("""
                SELECT weights_json, fitness_composite
                FROM ga_results
                WHERE symbol LIKE %s
                ORDER BY created_at DESC LIMIT 1
            """, (f'%{symbol}%',))
            row = cursor.fetchone()
            if not row:
                signals[symbol] = {'direction': 'HOLD', 'strength': 0}
                continue

            weights = json.loads(row['weights_json']) if row['weights_json'] else {}
            # Use weights to generate a signal score
            # Simple: if GA weights are positive → BUY bias, negative → SELL bias
            weight_avg = sum(weights.values()) / len(weights) if weights else 0
            strength = weight_avg * 10

            if strength > 10:
                direction = 'BUY'
            elif strength < -10:
                direction = 'SELL'
            else:
                direction = 'HOLD'

            signals[symbol] = {
                'direction': direction,
                'strength': strength,
                'weights': weights,
                'fitness': float(row['fitness_composite'] or 0),
            }
        cursor.close()
        return signals

    def _fetch_nn_signals(self, symbols: List[str],
                           as_of_date: date) -> Dict[str, dict]:
        """Fetch latest NN predictions."""
        signals = {}
        cursor = self.conn.cursor(dictionary=True)
        for symbol in symbols:
            cursor.execute("""
                SELECT direction, confidence, raw_weight, user_cap_weight
                FROM nn_predictions
                WHERE symbol = %s AND prediction_date <= %s
                ORDER BY prediction_date DESC, created_at DESC LIMIT 1
            """, (symbol, as_of_date))
            row = cursor.fetchone()
            if row:
                signals[symbol] = {
                    'direction': row['direction'],
                    'confidence': float(row['confidence'] or 0.5),
                    'raw_weight': float(row['raw_weight'] or 0.05),
                    'user_cap_weight': float(row['user_cap_weight'] or 0.05),
                }
            else:
                signals[symbol] = {
                    'direction': 'HOLD',
                    'confidence': 0.0,
                    'raw_weight': 0,
                    'user_cap_weight': 0,
                }
        cursor.close()
        return signals

    def _fetch_rl_signals(self, symbols: List[str],
                           as_of_date: date) -> Dict[str, dict]:
        """Fetch latest RL signals."""
        signals = {}
        cursor = self.conn.cursor(dictionary=True)
        for symbol in symbols:
            cursor.execute("""
                SELECT action, target_weight, confidence
                FROM rl_signals
                WHERE symbol = %s AND signal_date <= %s
                ORDER BY signal_date DESC, created_at DESC LIMIT 1
            """, (symbol, as_of_date))
            row = cursor.fetchone()
            if row:
                direction = RL_ACTION_TO_SIGNAL.get(row['action'], 'HOLD')
                signals[symbol] = {
                    'direction': direction,
                    'confidence': float(row['confidence'] or 0.5),
                    'target_weight': float(row['target_weight'] or 0.05),
                    'action': row['action'],
                }
            else:
                signals[symbol] = {
                    'direction': 'HOLD',
                    'confidence': 0.0,
                    'target_weight': 0,
                    'action': 'HOLD',
                }
        cursor.close()
        return signals

    def blend(self, symbols: List[str] = None,
              as_of_date: date = None) -> List[dict]:
        """
        Full blend: fetch all agent signals, compute consensus, generate plan.
        Returns list of order dicts.
        """
        if not self.run_id:
            self.run_id = self._create_agent_run()

        start_time = time.time()
        as_of_date = as_of_date or date.today()

        # Get symbols from DB if not provided
        if not symbols:
            cursor = self.conn.cursor()
            cursor.execute("SELECT symbol FROM portfolio WHERE is_active = 1 GROUP BY symbol")
            symbols = [row[0] for row in cursor.fetchall()]
            cursor.close()

        if not symbols:
            logger.warning("No symbols to blend")
            return []

        logger.info(f"Blender run #{self.run_id} | {len(symbols)} symbols")

        # --- Fetch signals from all agents ---
        logger.info("  Fetching GA signals...")
        ga_signals = self._fetch_ga_signals(symbols, as_of_date)

        logger.info("  Fetching NN signals...")
        nn_signals = self._fetch_nn_signals(symbols, as_of_date)

        logger.info("  Fetching RL signals...")
        rl_signals = self._fetch_rl_signals(symbols, as_of_date)

        # --- Consensus ---
        logger.info("  Computing consensus...")
        consensus_results = {}
        for symbol in symbols:
            ga = ga_signals.get(symbol, {'direction': 'HOLD', 'strength': 0})
            nn = nn_signals.get(symbol, {'direction': 'HOLD', 'confidence': 0, 'user_cap_weight': 0})
            rl = rl_signals.get(symbol, {'direction': 'HOLD', 'confidence': 0, 'target_weight': 0})

            consensus = self.consensus_engine.compute_consensus(ga, nn, rl)
            consensus_results[symbol] = consensus

        # --- Generate rebalance plan ---
        logger.info("  Generating rebalance plan...")
        planner = RebalancePlan(self.conn, self.config, self.cap_enforcer)
        orders = planner.generate_plan(consensus_results)

        # --- Filter by consensus threshold ---
        actionable_orders = [
            o for o in orders
            if o['consensus_pct'] >= self.config['consensus_threshold']
        ]

        logger.info(f"  {len(orders)} total signals, "
                     f"{len(actionable_orders)} above threshold "
                     f"({self.config['consensus_threshold']}%)")

        # --- Save to database ---
        self._save_orders(actionable_orders)

        elapsed = time.time() - start_time
        sells = [o for o in actionable_orders if o['action'] == 'SELL']
        buys = [o for o in actionable_orders if o['action'] in ('BUY', 'INCREASE')]

        result = {
            'total_symbols': len(symbols),
            'total_signals': len(orders),
            'actionable_signals': len(actionable_orders),
            'sells': len(sells),
            'buys': len(buys),
            'consensus_scores': {s: consensus_results[s]['consensus_score']
                                 for s in symbols if s in consensus_results},
            'elapsed_sec': elapsed,
        }
        self._update_agent_run('complete', result_json=result)

        return actionable_orders

    def _save_orders(self, orders: List[dict]):
        """Save orders to portfolio_orders table."""
        today = date.today()
        cursor = self.conn.cursor()

        for order in orders:
            try:
                cursor.execute("""
                    INSERT INTO portfolio_orders
                        (order_date, symbol, action, target_shares,
                         trade_shares, estimated_price, estimated_cost,
                         ga_signal, nn_signal, rl_signal, consensus_pct,
                         status, blender_run_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s)
                """, (
                    today,
                    order['symbol'],
                    order['action'],
                    order.get('target_shares'),
                    order.get('trade_shares'),
                    order.get('estimated_price'),
                    order.get('estimated_cost'),
                    order.get('ga_signal'),
                    order.get('nn_signal'),
                    order.get('rl_signal'),
                    order.get('consensus_pct'),
                    self.run_id,
                ))
            except Exception as e:
                logger.warning(f"Failed to save order for {order['symbol']}: {e}")

        self.conn.commit()
        cursor.close()
        logger.info(f"  Saved {len(orders)} orders to portfolio_orders")

    def approve_orders(self, order_ids: List[int], approved_by: str = 'auto'):
        """Approve pending orders for execution."""
        cursor = self.conn.cursor()
        for oid in order_ids:
            cursor.execute("""
                UPDATE portfolio_orders
                SET status = 'approved', approved_by = %s
                WHERE id = %s
            """, (approved_by, oid))
        self.conn.commit()
        cursor.close()
        logger.info(f"  Approved {len(order_ids)} orders")

    def print_report(self, orders: List[dict]):
        """Print a formatted rebalance report."""
        if not orders:
            print("\n📊 Blender Report: No actionable signals above threshold.")
            return

        sells = [o for o in orders if o['action'] == 'SELL']
        buys = [o for o in orders if 'BUY' in o['action']]
        increases = [o for o in orders if o['action'] == 'INCREASE']

        print(f"\n{'='*70}")
        print(f"📊 BLENDER REBALANCE REPORT — {date.today()}")
        print(f"{'='*70}")
        print(f"  Agent weights: GA={self.config['ga_weight']*100:.0f}% "
              f"NN={self.config['nn_weight']*100:.0f}% "
              f"RL={self.config['rl_weight']*100:.0f}%")
        print(f"  Consensus threshold: {self.config['consensus_threshold']:.0f}%")
        print(f"  Total orders: {len(orders)}")

        if sells:
            print(f"\n🔴 SELL ({len(sells)})")
            print(f"  {'Symbol':10s} {'Shares':>8s} {'Price':>10s} {'Cost':>12s} "
                  f"{'GA':>12s} {'NN':>12s} {'RL':>12s} {'Agree':>6s}")
            total_sell_cost = 0
            for o in sells:
                total_sell_cost += abs(o.get('estimated_cost', 0))
                print(f"  {o['symbol']:10s} {o['trade_shares']:>8,d} "
                      f"${o.get('estimated_price', 0):>9.2f} "
                      f"${o.get('estimated_cost', 0):>11,.2f} "
                      f"{(o.get('ga_signal') or '>'):>12s} "
                      f"{(o.get('nn_signal') or '>'):>12s} "
                      f"{(o.get('rl_signal') or '>'):>12s} "
                      f"{o['consensus_pct']:>5.0f}%")
            print(f"  {'':>10s} {'':>8s} {'':>10s} "
                  f"Total proceeds: ${total_sell_cost:>10,.2f}")

        if buys:
            print(f"\n🟢 BUY ({len(buys)})")
            print(f"  {'Symbol':10s} {'Shares':>8s} {'Price':>10s} {'Cost':>12s} "
                  f"{'GA':>12s} {'NN':>12s} {'RL':>12s} {'Agree':>6s}")
            total_buy_cost = 0
            for o in buys:
                total_buy_cost += o.get('estimated_cost', 0)
                print(f"  {o['symbol']:10s} {o['trade_shares']:>8,d} "
                      f"${o.get('estimated_price', 0):>9.2f} "
                      f"${o.get('estimated_cost', 0):>11,.2f} "
                      f"{(o.get('ga_direction') or o.get('ga_signal') or '>'):>12s} "
                      f"{(o.get('nn_direction') or o.get('nn_signal') or '>'):>12s} "
                      f"{(o.get('rl_direction') or o.get('rl_signal') or '>'):>12s} "
                      f"{o['consensus_pct']:>5.0f}%")
            print(f"  {'':>10s} {'':>8s} {'':>10s} "
                  f"Total cost: ${total_buy_cost:>10,.2f}")

        if increases:
            print(f"\n📈 INCREASE ({len(increases)})")
            for o in increases:
                print(f"  {o['symbol']:10s} +{o['trade_shares']:>7,d} "
                      f"${o.get('estimated_price', 0):>9.2f} "
                      f"${o.get('estimated_cost', 0):>11,.2f} "
                      f"{o['consensus_pct']:>5.0f}%")

        net_cash = sum(o.get('estimated_cost', 0) for o in sells) - \
                   sum(o.get('estimated_cost', 0) for o in buys + increases)
        print(f"\n💰 Net cash impact: ${net_cash:+,.2f}")
        print(f"{'='*70}")


# ===========================================================================
# CLI
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Blender Agent — Signal Consensus & Portfolio Optimizer'
    )
    parser.add_argument('--symbols', type=str, default='',
                        help='Comma-separated symbols (default: from portfolio)')
    parser.add_argument('--ga-weight', type=float, default=DEFAULT_CONFIG['ga_weight'])
    parser.add_argument('--nn-weight', type=float, default=DEFAULT_CONFIG['nn_weight'])
    parser.add_argument('--rl-weight', type=float, default=DEFAULT_CONFIG['rl_weight'])
    parser.add_argument('--consensus-threshold', type=float,
                        default=DEFAULT_CONFIG['consensus_threshold'])
    parser.add_argument('--max-positions', type=int,
                        default=DEFAULT_CONFIG['max_positions'])
    parser.add_argument('--dry-run', action='store_true',
                        help='Print report but do not write orders')
    parser.add_argument('--account', type=str, default=None,
                        help='Filter by account type (RRSP/TFSA/MARGIN)')
    parser.add_argument('--run-id', type=int, default=None)
    parser.add_argument('--machine-id', type=str, default=None)
    parser.add_argument('--priority', type=int, default=3)

    args = parser.parse_args()

    config = {
        'ga_weight': args.ga_weight,
        'nn_weight': args.nn_weight,
        'rl_weight': args.rl_weight,
        'consensus_threshold': args.consensus_threshold,
        'max_positions': args.max_positions,
    }

    conn = get_connection()

    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(',')]
    else:
        symbols = None  # Will fetch from portfolio

    agent = BlenderAgent(
        conn=conn,
        config=config,
        run_id=args.run_id,
        machine_id=args.machine_id,
        priority=args.priority,
    )

    try:
        orders = agent.blend(symbols=symbols)
        agent.print_report(orders)

        if args.dry_run:
            logger.info("DRY RUN — orders not written to database")
            # Rollback any saved orders
            cursor = conn.cursor()
            cursor.execute("DELETE FROM portfolio_orders WHERE blender_run_id = %s", (agent.run_id,))
            conn.commit()
            cursor.close()

    except KeyboardInterrupt:
        logger.info("Interrupted")
        if agent.run_id:
            agent._update_agent_run('cancelled', error='KeyboardInterrupt')
    except Exception as e:
        logger.error(f"Blender error: {e}")
        import traceback
        traceback.print_exc()
        if agent.run_id:
            agent._update_agent_run('failed', error=str(e))
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
