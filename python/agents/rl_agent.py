#!/usr/bin/env python3
"""
rl_agent.py — Reinforcement Learning Agent for Trading Policy
==============================================================
Uses PPO (Proximal Policy Optimization) via stable-baselines3 to learn
a trading policy. The agent operates in a custom Gym environment that
wraps MariaDB portfolio data.

Pipeline position: THIRD — reads GA weights + NN predictions as state.
Portfolio optimizer position — directly manages position sizing.

State Space (per symbol, per step):
  - Current position weight (0 if no position)
  - GA-optimized signal weight (from signal_weights table)
  - NN prediction (direction class + confidence, from nn_predictions)
  - TA indicators (RSI, MACD, BB position, ATR, volume ratio)
  - Scoring composite (totalscore, mf_score, ip_score)
  - Portfolio context (num positions, total exposure, available cash)
  - Price features (day return, gap, price vs SMAs)

Action Space (per symbol):
  0: HOLD (do nothing)
  1: BUY (add to position)
  2: SELL (close position)
  3: INCREASE (double down — only if already holding)
  4: DECREASE (trim position — only if already holding)

Reward Function:
  + Realized/unrealized P&L from price movement
  - Transaction cost ($9.95 per trade)
  - Holding penalty (small, to avoid idle portfolios)
  - Drawdown penalty (scaled by max drawdown magnitude)

Usage:
  python3 rl_agent.py                                    # Train on all symbols
  python3 rl_agent.py --episodes 500 --symbols RY.TO,TD.TO
  python3 rl_agent.py --backtest 2020-01-01 2024-12-31  # Backtest mode
  python3 rl_agent.py --predict                          # Use trained policy
"""

import argparse
import json
import logging
import math
import os
import random
import sys
import time
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import gymnasium as gym
import numpy as np
from gymnasium import spaces

# RL libraries
try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv
    from stable_baselines3.common.callbacks import BaseCallback
    HAS_SB3 = True
except ImportError:
    HAS_SB3 = False
    print("WARNING: stable-baselines3 not installed. Run: pip install stable-baselines3")

# Project imports
from python.db_connector import get_connection, get_active_symbols, fetch_price_data

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ===========================================================================
# CONFIGURATION
# ===========================================================================

DEFAULT_CONFIG = {
    'algorithm': 'PPO',
    'lookback_days': 120,
    'max_episodes': 200,
    'gamma': 0.99,
    'lambda_gae': 0.95,
    'clip_epsilon': 0.2,
    'learning_rate': 3e-4,
    'n_steps': 2048,
    'batch_size': 64,
    'n_epochs': 10,
    'initial_position_pct': 0.05,
    'max_position_pct': 0.15,
    'transaction_cost': 9.95,  # Fixed dollar cost per trade
    'holding_penalty': -0.0001,  # Small daily penalty for idle cash
    'drawdown_penalty_factor': 2.0,  # Multiplier for drawdown penalty
    'reward_scaling': 1000.0,  # Scale rewards for numerical stability
    'seed': 42,
}

# State space dimensions
STATE_FEATURES_PER_SYMBOL = 18  # TA + scoring + GA + NN features
PORTFOLIO_STATE_FEATURES = 5     # Global portfolio context
MAX_SYMBOLS_PER_STEP = 50       # Max symbols to include in state vector

# Action space
NUM_ACTIONS = 5  # HOLD, BUY, SELL, INCREASE, DECREASE
ACTION_NAMES = ['HOLD', 'BUY', 'SELL', 'INCREASE', 'DECREASE']


# ===========================================================================
# TRADING ENVIRONMENT
# ===========================================================================

class StockTradingEnv(gym.Env):
    """
    Custom Gym environment for stock trading.
    
    Each step represents one trading day. For each symbol, the agent
    observes the current state (TA indicators, GA weights, NN predictions,
    portfolio context) and takes an action (HOLD/BUY/SELL/INC/DEC).
    
    The environment tracks:
    - Cash balance
    - Positions (shares held per symbol)
    - Transaction costs
    - Portfolio value
    - Reward from P&L
    """

    metadata = {'render_modes': ['human', 'ansi']}

    def __init__(self, conn, symbols: List[str], config: dict,
                 start_date: date = None, end_date: date = None,
                 initial_capital: float = 100000.0):
        super().__init__()

        self.conn = conn
        self.symbols = symbols
        self.config = config
        self.initial_capital = initial_capital
        self.transaction_cost = config['transaction_cost']
        self.initial_position_pct = config['initial_position_pct']
        self.max_position_pct = config['max_position_pct']
        self.holding_penalty = config['holding_penalty']
        self.drawdown_penalty_factor = config['drawdown_penalty_factor']
        self.reward_scaling = config['reward_scaling']

        # Date range
        self.end_date = end_date or date.today()
        self.start_date = start_date or (self.end_date - timedelta(days=365 * 3))

        # Action/observation space
        # For each symbol: one of 5 actions
        self.action_space = spaces.MultiDiscrete([NUM_ACTIONS] * len(symbols))

        # Observation: per-symbol features + portfolio features
        obs_dim = MAX_SYMBOLS_PER_STEP * STATE_FEATURES_PER_SYMBOL + PORTFOLIO_STATE_FEATURES
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32
        )

        # State (set in reset)
        self.current_date = None
        self.cash = None
        self.positions = {}  # symbol -> {shares, cost_basis, entry_date}
        self.trading_dates = None
        self.current_step = None
        self.portfolio_history = []
        self.trades_today = []
        self.peak_value = 0
        self.max_drawdown = 0
        self.total_reward = 0
        self.episode_length = 0
        self.feature_cache = {}  # symbol -> precomputed features

        # Pre-load trading dates
        self._load_trading_dates()

    def _load_trading_dates(self):
        """Get all trading dates in the date range."""
        if self.conn is None:
            self.trading_dates = []
            return
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT price_date FROM stockprices
            WHERE price_date BETWEEN %s AND %s
            AND symbol IN ({})
            ORDER BY price_date ASC
        """.format(','.join(['%s'] * len(self.symbols))),
            [self.start_date, self.end_date] + self.symbols)
        self.trading_dates = [row[0] for row in cursor.fetchall()]
        cursor.close()
        logger.info(f"Loaded {len(self.trading_dates)} trading dates "
                    f"from {self.start_date} to {self.end_date}")

    def _compute_symbol_features(self, symbol: str, as_of_date: date) -> np.ndarray:
        """Compute the feature vector for a single symbol on a given date."""
        if (symbol, as_of_date) in self.feature_cache:
            return self.feature_cache[(symbol, as_of_date)]

        features = np.zeros(STATE_FEATURES_PER_SYMBOL, dtype=np.float32)

        cursor = self.conn.cursor(dictionary=True)

        # Current price
        cursor.execute("""
            SELECT day_open, day_high, day_low, day_close, volume
            FROM stockprices
            WHERE symbol = %s AND price_date = %s
        """, (symbol, as_of_date))
        price_row = cursor.fetchone()

        if not price_row or price_row['day_close'] is None:
            cursor.close()
            self.feature_cache[(symbol, as_of_date)] = features
            return features

        close = float(price_row['day_close'])
        volume = float(price_row['volume'] or 0)

        # Current position
        pos = self.positions.get(symbol)
        has_position = 1.0 if pos else 0.0
        current_weight = 0.0
        if pos and close > 0:
            current_weight = (pos['shares'] * close) / max(self._get_total_value(), 1.0)

        # TA features
        cursor.execute("""
            SELECT daily_return, gap_pct, sma_20, sma_50, sma_200
            FROM daily_indicators
            WHERE symbol = %s AND price_date = %s
        """, (symbol, as_of_date))
        di = cursor.fetchone()

        cursor.execute("""
            SELECT bb_width, bb_pct, atr_14, atr_pct, vol_ratio_20, vol_ratio_50
            FROM daily_tier2
            WHERE symbol = %s AND price_date = %s
        """, (symbol, as_of_date))
        dt = cursor.fetchone()

        cursor.execute("""
            SELECT totalscore, mf_score, ip_score
            FROM evalsummary WHERE symbol = %s
        """, (symbol, as_of_date))
        es = cursor.fetchone()

        # GA weight
        cursor.execute("""
            SELECT base_weight FROM signal_weights
            WHERE symbol = %s AND signal_type = 'w_totalscore'
            ORDER BY updated_at DESC LIMIT 1
        """, (symbol,))
        sw = cursor.fetchone()

        # NN prediction
        cursor.execute("""
            SELECT direction, confidence
            FROM nn_predictions
            WHERE symbol = %s AND prediction_date = %s
            ORDER BY created_at DESC LIMIT 1
        """, (symbol, as_of_date))
        nn = cursor.fetchone()

        cursor.close()

        # Build feature vector [0..17]
        idx = 0
        features[idx] = has_position; idx += 1
        features[idx] = current_weight; idx += 1
        # Price features
        features[idx] = float(di['daily_return'] or 0) * 10 if di else 0; idx += 1
        features[idx] = float(di['gap_pct'] or 0) * 10 if di else 0; idx += 1
        features[idx] = (close / float(di['sma_20']) - 1) * 5 if di and di['sma_20'] else 0; idx += 1
        features[idx] = (close / float(di['sma_50']) - 1) * 5 if di and di['sma_50'] else 0; idx += 1
        # TA features
        features[idx] = float(dt['bb_pct'] or 0.5) if dt else 0.5; idx += 1
        features[idx] = min(float(dt['atr_pct'] or 0.02) * 10, 1.0) if dt else 0.5; idx += 1
        features[idx] = min(float(dt['vol_ratio_20'] or 1.0), 5.0) / 5.0 if dt else 0.2; idx += 1
        # Scoring
        features[idx] = (float(es['totalscore'] or 18) / 36.0) if es else 0.5; idx += 1
        features[idx] = (float(es['mf_score'] or 3) / 7.0) if es else 0.5; idx += 1
        features[idx] = (float(es['ip_score'] or 7) / 15.0) if es else 0.5; idx += 1
        # GA weight
        features[idx] = float(sw['base_weight'] or 1.0) / 5.0 if sw else 0.2; idx += 1
        # NN prediction
        if nn:
            direction_map = {'STRONG_BUY': 1.0, 'BUY': 0.5, 'HOLD': 0, 'SELL': -0.5, 'STRONG_SELL': -1.0}
            features[idx] = direction_map.get(nn['direction'], 0); idx += 1
            features[idx] = float(nn['confidence'] or 0.5); idx += 1
        else:
            features[idx] = 0; idx += 1
            features[idx] = 0.5; idx += 1
        # Volume
        features[idx] = min(math.log10(volume + 1) / 10.0, 1.0) if volume > 0 else 0; idx += 1

        self.feature_cache[(symbol, as_of_date)] = features
        return features

    def _compute_portfolio_features(self) -> np.ndarray:
        """Compute global portfolio context features."""
        features = np.zeros(PORTFOLIO_STATE_FEATURES, dtype=np.float32)
        total_value = self._get_total_value()
        if total_value <= 0:
            return features

        # Cash ratio
        features[0] = min(self.cash / total_value, 1.0)

        # Exposure ratio (total non-cash)
        invested = total_value - self.cash
        features[1] = min(invested / total_value, 1.0) if total_value > 0 else 0

        # Number of positions (normalized)
        features[2] = min(len(self.positions) / self.config.get('max_positions', 20), 1.0)

        # Max drawdown (current)
        features[3] = self.max_drawdown

        # Daily return
        if self.portfolio_history:
            prev_value = self.portfolio_history[-1]
            if prev_value > 0:
                features[4] = (total_value - prev_value) / prev_value * 10

        return features

    def _get_total_value(self) -> float:
        """Get total portfolio value (cash + positions at current prices)."""
        total = self.cash
        for symbol, pos in self.positions.items():
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT day_close FROM stockprices
                WHERE symbol = %s AND price_date = %s
            """, (symbol, self.current_date))
            row = cursor.fetchone()
            cursor.close()
            if row and row['day_close']:
                total += pos['shares'] * float(row['day_close'])
        return total

    def _execute_action(self, symbol: str, action: int) -> float:
        """
        Execute an action for a symbol. Returns immediate reward.
        Actions: 0=HOLD, 1=BUY, 2=SELL, 3=INCREASE, 4=DECREASE
        """
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT day_close FROM stockprices
            WHERE symbol = %s AND price_date = %s
        """, (symbol, self.current_date))
        row = cursor.fetchone()
        cursor.close()

        if not row or not row['day_close']:
            return 0.0

        price = float(row['day_close'])
        reward = 0.0

        if action == 0:  # HOLD
            return 0.0

        elif action == 1:  # BUY
            if symbol in self.positions:
                return 0.0  # Already holding

            max_investment = self.cash * self.initial_position_pct
            shares = int(max_investment / price)
            if shares <= 0:
                return 0.0

            cost = shares * price + self.transaction_cost
            if cost > self.cash:
                shares = int((self.cash - self.transaction_cost) / price)
                if shares <= 0:
                    return 0.0
                cost = shares * price + self.transaction_cost

            self.cash -= cost
            self.positions[symbol] = {
                'shares': shares,
                'cost_basis': price,
                'entry_date': self.current_date,
            }
            reward = -self.transaction_cost / self.reward_scaling

        elif action == 2:  # SELL
            if symbol not in self.positions:
                return 0.0

            pos = self.positions[symbol]
            proceeds = pos['shares'] * price - self.transaction_cost
            pnl = proceeds - (pos['shares'] * pos['cost_basis'])

            self.cash += proceeds
            del self.positions[symbol]

            reward = (pnl - self.transaction_cost) / self.reward_scaling

        elif action == 3:  # INCREASE (double down)
            if symbol not in self.positions:
                return 0.0

            pos = self.positions[symbol]
            add_shares = pos['shares']  # Double: buy same amount again
            cost = add_shares * price + self.transaction_cost

            if cost > self.cash:
                add_shares = int((self.cash - self.transaction_cost) / price)
                if add_shares <= 0:
                    return 0.0
                cost = add_shares * price + self.transaction_cost

            # Update average cost basis
            old_value = pos['shares'] * pos['cost_basis']
            new_shares = pos['shares'] + add_shares
            pos['shares'] = new_shares
            pos['cost_basis'] = (old_value + add_shares * price) / new_shares

            self.cash -= cost
            reward = -self.transaction_cost / self.reward_scaling

        elif action == 4:  # DECREASE (trim 50%)
            if symbol not in self.positions:
                return 0.0

            pos = self.positions[symbol]
            sell_shares = max(1, pos['shares'] // 2)
            proceeds = sell_shares * price - self.transaction_cost
            pnl = proceeds - (sell_shares * pos['cost_basis'])

            pos['shares'] -= sell_shares
            if pos['shares'] <= 0:
                del self.positions[symbol]

            self.cash += proceeds
            reward = (pnl - self.transaction_cost) / self.reward_scaling

        return reward

    def reset(self, seed=None, options=None):
        """Reset environment to initial state."""
        super().reset(seed=seed)

        self.cash = self.initial_capital
        self.positions = {}
        self.current_step = 0
        self.portfolio_history = []
        self.trades_today = []
        self.peak_value = self.initial_capital
        self.max_drawdown = 0
        self.total_reward = 0
        self.episode_length = 0
        self.feature_cache = {}

        if self.trading_dates:
            self.current_date = self.trading_dates[0]

        obs = self._get_observation()
        info = {}
        return obs, info

    def _get_observation(self) -> np.ndarray:
        """Build the full observation vector."""
        obs_dim = MAX_SYMBOLS_PER_STEP * STATE_FEATURES_PER_SYMBOL + PORTFOLIO_STATE_FEATURES
        obs = np.zeros(obs_dim, dtype=np.float32)

        # Per-symbol features
        for i, symbol in enumerate(self.symbols[:MAX_SYMBOLS_PER_STEP]):
            if self.current_date:
                sym_features = self._compute_symbol_features(symbol, self.current_date)
                start_idx = i * STATE_FEATURES_PER_SYMBOL
                end_idx = start_idx + STATE_FEATURES_PER_SYMBOL
                obs[start_idx:end_idx] = sym_features

        # Portfolio features (append at end)
        port_start = MAX_SYMBOLS_PER_STEP * STATE_FEATURES_PER_SYMBOL
        obs[port_start:port_start + PORTFOLIO_STATE_FEATURES] = self._compute_portfolio_features()

        return obs

    def step(self, action):
        """
        Execute one step. Action is an array of per-symbol actions.
        Returns: (obs, reward, terminated, truncated, info)
        """
        if self.current_step >= len(self.trading_dates) - 1:
            obs = self._get_observation()
            return obs, 0.0, True, False, {}

        self.current_date = self.trading_dates[self.current_step]
        total_reward = 0.0

        # Execute actions for each symbol
        for i, symbol in enumerate(self.symbols):
            if i < len(action):
                sym_reward = self._execute_action(symbol, action[i])
                total_reward += sym_reward

        # Record portfolio value before next step
        total_value = self._get_total_value()
        self.portfolio_history.append(total_value)

        # Update peak and drawdown
        if total_value > self.peak_value:
            self.peak_value = total_value
        current_dd = (self.peak_value - total_value) / self.peak_value if self.peak_value > 0 else 0
        if current_dd > self.max_drawdown:
            self.max_drawdown = current_dd

        # Holding penalty (encourage being invested)
        if self.cash > self.initial_capital * 0.9:  # >90% cash
            total_reward += self.holding_penalty

        # Drawdown penalty
        if current_dd > 0.10:  # >10% drawdown
            total_reward -= current_dd * self.drawdown_penalty_factor / self.reward_scaling

        self.total_reward += total_reward
        self.episode_length += 1

        # Advance to next trading day
        self.current_step += 1
        done = self.current_step >= len(self.trading_dates) - 1

        obs = self._get_observation()
        info = {
            'portfolio_value': total_value,
            'cash': self.cash,
            'num_positions': len(self.positions),
            'max_drawdown': self.max_drawdown,
            'total_reward': self.total_reward,
        }

        return obs, total_reward, done, False, info

    def render(self, mode='human'):
        """Render current state."""
        total_value = self._get_total_value()
        pnl = total_value - self.initial_capital
        pnl_pct = (pnl / self.initial_capital) * 100 if self.initial_capital > 0 else 0
        return (
            f"Date: {self.current_date} | Value: ${total_value:,.0f} | "
            f"P&L: ${pnl:+,.0f} ({pnl_pct:+.1f}%) | "
            f"Cash: ${self.cash:,.0f} | "
            f"Positions: {len(self.positions)} | "
            f"MaxDD: {self.max_drawdown:.1%}"
        )

    def close(self):
        self.conn = None


class TrainingCallback(BaseCallback):
    """Callback to log training progress."""

    def __init__(self, verbose=0):
        super().__init__(verbose)

    def _on_step(self) -> bool:
        if self.n_calls % 1000 == 0:
            if self.locals and 'infos' in self.locals:
                for info in self.locals['infos']:
                    if 'episode' in info:
                        ep_reward = info['episode'].get('r', 0)
                        ep_length = info['episode'].get('l', 0)
                        logger.info(f"  Training step {self.n_calls}: "
                                    f"ep_reward={ep_reward:.2f} ep_len={ep_length}")
        return True


# ===========================================================================
# RL AGENT — Main class
# ===========================================================================

class RLAgent:
    """Reinforcement Learning Agent using PPO."""

    def __init__(self, conn, symbols: List[str], config: dict,
                 run_id: int = None, machine_id: str = None,
                 priority: int = 5, model_path: str = None):
        self.conn = conn
        self.symbols = symbols
        self.config = {**DEFAULT_CONFIG, **config}
        self.run_id = run_id
        self.machine_id = machine_id or os.uname().nodename
        self.priority = priority
        self.model_path = model_path or 'models/rl_ppo_latest.zip'
        self.env = None
        self.model = None

    def _create_agent_run(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO agent_runs
                (agent_type, run_name, priority, machine_id, status,
                 symbol_target, started_at)
            VALUES ('rl', %s, %s, %s, 'running', NULL, NOW())
        """, (
            f"RL_{self.config['max_episodes']}ep_{len(self.symbols)}sym",
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
            result_json.get('total_reward_norm') if result_json else None,
            json.dumps(result_json) if result_json else None,
            error,
            self.run_id,
        ))
        self.conn.commit()
        cursor.close()

    def train(self, total_timesteps: int = None) -> dict:
        """Train the RL agent."""
        if not HAS_SB3:
            raise RuntimeError("stable-baselines3 not installed")

        if not self.run_id:
            self.run_id = self._create_agent_run()

        start_time = time.time()
        logger.info(f"RL Agent training run #{self.run_id} | "
                    f"PPO | {self.config['max_episodes']} episodes | "
                    f"{len(self.symbols)} symbols")

        # Create environment
        env = StockTradingEnv(
            conn=self.conn,
            symbols=self.symbols,
            config=self.config,
            initial_capital=self.config.get('initial_capital', 100000.0),
        )

        # Wrap in DummyVecEnv for stable-baselines3
        vec_env = DummyVecEnv([lambda: env])

        # Create PPO model
        self.model = PPO(
            'MlpPolicy',
            vec_env,
            learning_rate=self.config['learning_rate'],
            n_steps=self.config['n_steps'],
            batch_size=self.config['batch_size'],
            n_epochs=self.config['n_epochs'],
            gamma=self.config['gamma'],
            gae_lambda=self.config['lambda_gae'],
            clip_range=self.config['clip_epsilon'],
            verbose=1,
            seed=self.config['seed'],
            tensorboard_log='./tensorboard_logs/',
        )

        # Train
        timesteps = total_timesteps or (self.config['max_episodes'] * 250)
        self.model.learn(
            total_timesteps=timesteps,
            callback=TrainingCallback(),
        )

        # Save model
        os.makedirs(os.path.dirname(self.model_path) or '.', exist_ok=True)
        self.model.save(self.model_path)
        logger.info(f"Model saved to {self.model_path}")

        # Collect results
        portfolio_value = env.portfolio_history[-1] if env.portfolio_history else self.config.get('initial_capital', 100000)
        total_return = (portfolio_value - 100000) / 100000

        elapsed = time.time() - start_time
        result = {
            'total_timesteps': timesteps,
            'final_portfolio_value': portfolio_value,
            'total_return': total_return,
            'max_drawdown': env.max_drawdown,
            'total_reward': env.total_reward,
            'total_reward_norm': env.total_reward / max(env.episode_length, 1),
            'episode_length': env.episode_length,
            'model_path': self.model_path,
            'elapsed_sec': elapsed,
        }

        vec_env.close()
        self._update_agent_run('complete', result_json=result)
        return result

    def backtest(self, start_date: date, end_date: date) -> dict:
        """Run a backtest with the trained policy."""
        if self.model is None:
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"No model at {self.model_path}")
            self.model = PPO.load(self.model_path)

        env = StockTradingEnv(
            conn=self.conn,
            symbols=self.symbols,
            config=self.config,
            start_date=start_date,
            end_date=end_date,
        )

        obs, info = env.reset()
        done = False
        step_count = 0

        logger.info(f"Backtest: {start_date} to {end_date}")

        while not done:
            action, _states = self.model.predict(obs, deterministic=True)
            obs, reward, done, truncated, info = env.step(action)
            step_count += 1

            if step_count % 50 == 0:
                logger.info(f"  Step {step_count}: {env.render()}")

        # Final results
        final_value = env.portfolio_history[-1] if env.portfolio_history else self.config.get('initial_capital', 100000)
        initial_value = self.config.get('initial_capital', 100000)
        total_return = (final_value - initial_value) / initial_value

        # Save trades to rl_signals table
        self._save_backtest_results(env)

        env.close()

        return {
            'start_date': str(start_date),
            'end_date': str(end_date),
            'initial_value': initial_value,
            'final_value': final_value,
            'total_return': total_return,
            'max_drawdown': env.max_drawdown,
            'num_trades': env.episode_length,
            'num_positions_final': len(env.positions),
        }

    def _save_backtest_results(self, env: StockTradingEnv):
        """Save backtest trade decisions to rl_signals table."""
        cursor = self.conn.cursor()
        try:
            for symbol, pos in env.positions.items():
                cursor.execute("""
                    INSERT INTO rl_signals
                        (symbol, signal_date, model_version, action,
                         target_weight, confidence, agent_run_id)
                    VALUES (%s, %s, 'ppo_v1', 'BUY',
                            %s, 0.8, %s)
                    ON DUPLICATE KEY UPDATE
                        action = VALUES(action),
                        target_weight = VALUES(target_weight)
                """, (
                    symbol,
                    env.current_date,
                    pos['shares'] * pos['cost_basis'] / max(env._get_total_value(), 1),
                    self.run_id,
                ))
            self.conn.commit()
        except Exception as e:
            logger.warning(f"Could not save backtest results: {e}")
        finally:
            cursor.close()

    def run(self, predict_only: bool = False) -> dict:
        """Full agent run."""
        if predict_only:
            return self.backtest(
                date.today() - timedelta(days=365),
                date.today(),
            )
        else:
            return self.train()

    def generate_signals(self, as_of_date: date = None) -> List[dict]:
        """Generate trading signals for today using the trained policy."""
        if self.model is None:
            if not os.path.exists(self.model_path):
                raise FileNotFoundError("No trained model available")
            self.model = PPO.load(self.model_path)

        as_of_date = as_of_date or date.today()
        signals = []

        for symbol in self.symbols:
            obs = np.zeros(
                MAX_SYMBOLS_PER_STEP * STATE_FEATURES_PER_SYMBOL + PORTFOLIO_STATE_FEATURES,
                dtype=np.float32
            )
            features = self._compute_symbol_features_for_signal(symbol, as_of_date)
            obs[:STATE_FEATURES_PER_SYMBOL] = features

            action, _ = self.model.predict(obs, deterministic=True)
            action_name = ACTION_NAMES[action[0]] if len(action) > 0 else 'HOLD'

            confidence = 0.7  # PPO doesn't give direct confidence, use value estimate

            signal = {
                'symbol': symbol,
                'action': action_name,
                'confidence': confidence,
                'date': as_of_date,
            }
            signals.append(signal)

        return signals

    def _compute_symbol_features_for_signal(self, symbol: str,
                                             as_of_date: date) -> np.ndarray:
        """Simplified feature computation for signal generation."""
        features = np.zeros(STATE_FEATURES_PER_SYMBOL, dtype=np.float32)

        if self.conn is None:
            return features

        cursor = self.conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT day_close FROM stockprices
            WHERE symbol = %s AND price_date <= %s
            ORDER BY price_date DESC LIMIT 1
        """, (symbol, as_of_date))
        row = cursor.fetchone()
        cursor.close()

        if not row:
            return features

        close = float(row['day_close'])

        # Get TA features from latest data
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT daily_return, gap_pct, sma_20, sma_50
            FROM daily_indicators
            WHERE symbol = %s AND price_date <= %s
            ORDER BY price_date DESC LIMIT 1
        """, (symbol, as_of_date))
        di = cursor.fetchone()
        cursor.close()

        idx = 0
        features[idx] = 0; idx += 1  # has_position
        features[idx] = 0; idx += 1  # current_weight
        if di:
            features[idx] = float(di['daily_return'] or 0) * 10; idx += 1
            features[idx] = float(di['gap_pct'] or 0) * 10; idx += 1
            features[idx] = (close / float(di['sma_20']) - 1) * 5 if di['sma_20'] else 0; idx += 1
            features[idx] = (close / float(di['sma_50']) - 1) * 5 if di['sma_50'] else 0; idx += 1

        return features


# ===========================================================================
# CLI
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(
        description='RL Agent — PPO for Trading Policy Optimization'
    )
    parser.add_argument('--symbols', type=str, default='',
                        help='Comma-separated symbols')
    parser.add_argument('--episodes', type=int, default=DEFAULT_CONFIG['max_episodes'])
    parser.add_argument('--timesteps', type=int, default=None,
                        help='Total training timesteps (overrides episodes)')
    parser.add_argument('--lr', type=float, default=DEFAULT_CONFIG['learning_rate'])
    parser.add_argument('--gamma', type=float, default=DEFAULT_CONFIG['gamma'])
    parser.add_argument('--clip', type=float, default=DEFAULT_CONFIG['clip_epsilon'])
    parser.add_argument('--seed', type=int, default=DEFAULT_CONFIG['seed'])
    parser.add_argument('--model-path', type=str, default='models/rl_ppo_latest.zip')
    parser.add_argument('--backtest-start', type=str, default=None,
                        help='Backtest start date (YYYY-MM-DD)')
    parser.add_argument('--backtest-end', type=str, default=None,
                        help='Backtest end date (YYYY-MM-DD)')
    parser.add_argument('--predict', action='store_true',
                        help='Generate signals (requires trained model)')
    parser.add_argument('--run-id', type=int, default=None)
    parser.add_argument('--machine-id', type=str, default=None)
    parser.add_argument('--priority', type=int, default=5)

    args = parser.parse_args()

    config = {
        'max_episodes': args.episodes,
        'learning_rate': args.lr,
        'gamma': args.gamma,
        'clip_epsilon': args.clip,
        'seed': args.seed,
    }

    conn = get_connection()

    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(',')]
    else:
        symbols = [s for s in get_active_symbols(conn) if s][:75]

    if not symbols:
        logger.error("No symbols available")
        sys.exit(1)

    agent = RLAgent(
        conn=conn,
        symbols=symbols,
        config=config,
        run_id=args.run_id,
        machine_id=args.machine_id,
        priority=args.priority,
        model_path=args.model_path,
    )

    try:
        if args.backtest_start and args.backtest_end:
            result = agent.backtest(
                datetime.strptime(args.backtest_start, '%Y-%m-%d').date(),
                datetime.strptime(args.backtest_end, '%Y-%m-%d').date(),
            )
        elif args.predict:
            signals = agent.generate_signals()
            result = {'signals': signals, 'count': len(signals)}
        else:
            result = agent.run(total_timesteps=args.timesteps)

        print(json.dumps(result, indent=2, default=str))

    except KeyboardInterrupt:
        logger.info("Interrupted")
        if agent.run_id:
            agent._update_agent_run('cancelled', error='KeyboardInterrupt')
    except Exception as e:
        logger.error(f"RL Agent error: {e}")
        import traceback
        traceback.print_exc()
        if agent.run_id:
            agent._update_agent_run('failed', error=str(e))
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
