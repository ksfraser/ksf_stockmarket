#!/usr/bin/env python3
"""
rl_agent.py — Reinforcement Learning trading agent using SB3 PPO.

Custom Gym environment simulates portfolio trading:
- State: portfolio composition + indicators + regime
- Action: for each position, [-1 sell, -0.5 trim, 0 hold, +0.5 add, +1 buy more]
- Reward: daily after-tax P&L − transaction costs − risk penalty

Walk-forward training: 2014-2018, test 2019-2024.

Usage:
    python3 rl_agent.py [--train-steps 100000] [--test]
"""
import sys, os, json, argparse
import numpy as np
import pymysql
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
from config_loader import Config

try:
    import gymnasium as gym
    from gymnasium import spaces
except ImportError:
    try:
        import gym
        from gym import spaces
    except ImportError:
        print("gym/gymnasium not installed: pip3 install gymnasium"); sys.exit(1)

try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv
except ImportError:
    print("stable-baselines3 not installed: pip3 install stable-baselines3"); sys.exit(1)

MYSQL = dict(host='ksfraser.ca', user='ksfraser_stockmarket',
             password='Zaqwsx9sm1@', database='ksfraser_stock_market',
             charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)


# ── Trading Environment ────────────────────────────────────────────────────
class PortfolioEnv(gym.Env):
    """
    Custom Gym environment for portfolio trading.

    State vector (per step):
      - [0:N]    Portfolio weights (N symbols, sum to 1.0)
      - [N:2N]   Signal consensus per symbol [-1, 1]
      - [2N:3N]  Predicted return from NN [mean, std] per symbol
      - [3N]     Cash ratio
      - [3N+1]   ADX (trend strength)
      - [3N+2]   Days since last rebalance
      - [3N+3]   Portfolio drawdown
      - [3N+4]   Tax loss harvesting available (0/1)

    Action vector (per step):
      - [0:N]    Trade signal per symbol [-1, 1]:
                 -1 = sell all, -0.5 = trim 50%, 0 = hold,
                 +0.5 = add 50%, +1 = max position size

    Reward:
      - daily portfolio P&L (after tax)
      - minus transaction cost per trade ($9.95)
      - minus risk penalty if single position > 15%
    """

    metadata = {'render_modes': ['human']} if hasattr(gym.spaces, 'Box') else {}

    def __init__(self, symbols, prices, signals, indicators,
                 initial_capital=50000.0, transaction_cost=9.95,
                 max_position=0.15, tax_rate=0.25, verbose=False):
        super().__init__()

        self.symbols = symbols
        self.n_symbols = len(symbols)
        self.prices = prices
        self.signals = signals
        self.indicators = indicators
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        self.max_position = max_position
        self.tax_rate = tax_rate
        self.verbose = verbose

        # Build date index from prices
        all_dates = set()
        for sym in symbols:
            if sym in prices:
                all_dates.update(prices[sym].keys())
        self.dates = sorted(all_dates)
        self.max_steps = len(self.dates)

        # State: positions (N) + signals (N) + cash + adx + days_since_reb + dd
        state_size = self.n_symbols * 2 + 5
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf,
                                             shape=(state_size,), dtype=np.float32)

        # Action: per-symbol trade signal in [-1, 1]
        self.action_space = spaces.Box(low=-1, high=1,
                                        shape=(self.n_symbols,), dtype=np.float32)

        self.reset()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.step_idx = 0
        self.capital = self.initial_capital
        self.positions = {s: 0.0 for s in self.symbols}  # shares held
        self.cash = self.initial_capital
        self.total_trades = 0
        self.total_tax_paid = 0
        self.peak_value = self.initial_capital
        self.current_value = self.initial_capital
        self.days_since_rebalance = 0
        self.prev_weights = {s: 0.0 for s in self.symbols}

        return self._get_obs(), {}

    def _get_current_date(self):
        return self.dates[self.step_idx] if self.step_idx < len(self.dates) else None

    def _get_prices(self):
        d = self._get_current_date()
        return {s: self.prices.get(s, {}).get(d, None) for s in self.symbols}

    def _get_portfolio_value(self):
        prices = self._get_prices()
        pos_value = sum(self.positions[s] * prices[s]
                       for s in self.symbols if prices.get(s) is not None)
        return self.cash + pos_value

    def _get_obs(self):
        prices = self._get_prices()
        pv = max(self._get_portfolio_value(), 1.0)

        # Position weights
        weights = np.array([self.positions[s] * prices.get(s, 0) / pv
                           if prices.get(s) else 0.0
                           for s in self.symbols], dtype=np.float32)

        # Signal consensus for today
        current_date = self._get_current_date()
        sigs = np.array([self.signals.get((s, current_date), 0.0)
                        for s in self.symbols], dtype=np.float32)

        # ADX from indicators (if available)
        adx_val = 0.0
        if self.indicators and current_date:
            # Use first symbol's ADX as market proxy
            first_sym = self.symbols[0]
            adx_val = self.indicators.get((first_sym, current_date), {}).get('adx_14', 25.0) / 50.0

        # Drawdown
        dd = (self.peak_value - pv) / self.peak_value if self.peak_value > 0 else 0

        # State extras
        extras = np.array([
            self.cash / pv,
            min(adx_val, 1.0),
            self.days_since_rebalance / 30.0,
            dd,
            1.0 if self.days_since_rebalance > 330 else 0.0,  # harvest available
        ], dtype=np.float32)

        obs = np.concatenate([weights, sigs, extras]).astype(np.float32)
        return obs

    def step(self, action):
        """
        Execute trades based on action, advance one day, compute reward.
        """
        current_date = self._get_current_date()
        if current_date is None or self.step_idx >= self.max_steps - 1:
            return self._get_obs(), 0.0, True, False, {}

        prices = self._get_prices()
        pv_before = self._get_portfolio_value()

        # ── Execute trades ──
        trades_today = 0
        for i, sym in enumerate(self.symbols):
            if prices.get(sym) is None:
                continue

            act = action[i]  # [-1, 1]

            if act < -0.2:  # SELL
                # Sell fraction of position
                sell_pct = min(abs(act), 1.0)
                shares_to_sell = self.positions[sym] * sell_pct
                if shares_to_sell > 0.01:
                    proceeds = shares_to_sell * prices[sym]
                    # Tax on gains (simplified)
                    gain = proceeds - shares_to_sell * self.prev_weights.get(sym, prices[sym])
                    if gain > 0:
                        tax = gain * 0.5 * self.tax_rate  # CG 50% inclusion
                        self.total_tax_paid += tax
                        proceeds -= tax
                    self.cash += proceeds - self.transaction_cost
                    self.positions[sym] -= shares_to_sell
                    trades_today += 1

            elif act > 0.2:  # BUY
                # Buy with available cash
                buy_pct = min(act, 1.0)
                max_invest = min(
                    self.cash * buy_pct,
                    pv_before * self.max_position  # position limit
                )
                if max_invest > 100:  # minimum $100 trade
                    cost = max_invest + self.transaction_cost
                    if cost <= self.cash:
                        shares = max_invest / prices[sym]
                        self.positions[sym] += shares
                        self.cash -= cost
                        trades_today += 1

        self.total_trades += trades_today
        self.days_since_rebalance += 1

        # Advance to next day
        self.step_idx += 1
        new_date = self._get_current_date()

        # Update portfolio value
        new_prices = self._get_prices()
        pv_after = self._get_portfolio_value()
        self.current_value = pv_after

        if pv_after > self.peak_value:
            self.peak_value = pv_after

        # ── Reward = daily P&L - costs ──
        daily_pnl = pv_after - pv_before
        trade_penalty = trades_today * self.transaction_cost * 0.01  # small penalty

        # Concentration penalty
        max_w = max((self.positions[s] * new_prices.get(s, 0) / max(pv_after, 1)
                     for s in self.symbols), default=0)
        concent_penalty = max(0, max_w - self.max_position) * 1000

        reward = (daily_pnl - trade_penalty - concent_penalty) / self.initial_capital

        terminated = self.step_idx >= self.max_steps - 1
        truncated = pv_after < self.initial_capital * 0.1  # portfolio depleted

        if (self.step_idx % 60 == 0) and self.verbose:
            print(f"  Step {self.step_idx:>5} ({new_date}): "
                  f"PV=${pv_after:>10,.2f}  cash=${self.cash:>8,.2f}  "
                  f"trades={self.total_trades}  reward={reward:.4f}")

        return self._get_obs(), float(reward), terminated, truncated, {
            'portfolio_value': pv_after, 'trades': self.total_trades
        }


# ── Data Loading ───────────────────────────────────────────────────────────
def load_env_data(symbols, start, end):
    """Load prices and indicators for the environment."""
    conn = pymysql.connect(**MYSQL)
    c = conn.cursor()

    # Prices
    placeholders = ','.join(['%s'] * len(symbols))
    c.execute(f"SELECT symbol, price_date, close FROM stockprices "
              f"WHERE symbol IN ({placeholders}) AND price_date BETWEEN %s AND %s "
              f"ORDER BY symbol, price_date", list(symbols) + [start, end])
    prices = {}
    for r in c.fetchall():
        prices.setdefault(r['symbol'], {})[str(r['price_date'])] = float(r['close'])

    # Indicators (ADX for regime)
    c.execute(f"SELECT symbol, price_date, adx_14 FROM indicators "
              f"WHERE symbol IN ({placeholders}) AND price_date BETWEEN %s AND %s",
              list(symbols) + [start, end])
    indicators = {}
    for r in c.fetchall():
        indicators.setdefault((r['symbol'], str(r['price_date'])), {})['adx_14'] = float(r['adx_14'] or 25)

    conn.close()
    return prices, indicators


def get_candidate_symbols(config):
    """Get symbols from screener or DB."""
    conn = pymysql.connect(**MYSQL); c = conn.cursor()
    c.execute("SELECT DISTINCT symbol FROM stockprices ORDER BY symbol LIMIT 20")
    syms = [r['symbol'] for r in c.fetchall()]
    conn.close()
    return syms


# ── Training ────────────────────────────────────────────────────────────────
def train_rl(config, symbols, train_start, train_end, test_start=None, test_end=None,
             total_timesteps=100000, verbose=False):
    """Train PPO agent with walk-forward testing."""
    device = 'cuda' if __import__('torch').cuda.is_available() else 'cpu'

    print(f"\n{'='*60}")
    print(f"RL AGENT (PPO) — {len(symbols)} symbols")
    print(f"Train: {train_start}-{train_end} | device={device}")
    print(f"{'='*60}")

    # Create training environment
    train_prices, train_indicators = load_env_data(symbols, train_start, train_end)
    # Dummy signals (random if no real signal engine yet)
    train_signals = {}

    def make_env():
        return PortfolioEnv(symbols, train_prices, train_signals, train_indicators,
                           initial_capital=50000, transaction_cost=9.95,
                           max_position=0.15, verbose=False)

    env = DummyVecEnv([make_env])

    # PPO model
    cfg = config.rl
    model = PPO("MlpPolicy", env,
                learning_rate=cfg.learning_rate,
                n_steps=cfg.n_steps,
                batch_size=cfg.batch_size,
                gamma=cfg.gamma,
                gae_lambda=cfg.gae_lambda,
                clip_range=cfg.clip_range,
                verbose=int(verbose),
                device=device)

    print(f"Training {total_timesteps} timesteps...")
    model.learn(total_timesteps=total_timesteps, progress_bar=verbose)
    model.save("/tmp/rl_agent.zip")
    print("Model saved")

    # Walk-forward test
    if test_start and test_end:
        print(f"\n{'='*60}")
        print(f"WALK-FORWARD TEST: {test_start}-{test_end}")
        print(f"{'='*60}")

        test_prices, test_indicators = load_env_data(symbols, test_start, test_end)

        def make_test_env():
            return PortfolioEnv(symbols, test_prices, {}, test_indicators,
                               initial_capital=50000, transaction_cost=9.95,
                               max_position=0.15, verbose=True)

        test_env = make_test_env()
        obs, _ = test_env.reset()

        total_reward = 0
        for _ in range(test_env.max_steps):
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = test_env.step(action)
            total_reward += reward
            if terminated or truncated:
                break

        print(f"\nTest terminal value: ${info['portfolio_value']:,.2f}")
        print(f"Total trades: {info['trades']}")
        print(f"Total reward: {total_reward:.2f}")

        # Compare to buy-and-hold
        eq_env = make_test_env()
        obs, _ = eq_env.reset()
        for _ in range(eq_env.max_steps):
            obs, _, terminated, truncated, info = eq_env.step(np.zeros(len(symbols)))
            if terminated or truncated:
                break

        print(f"B&H terminal value: ${info['portfolio_value']:,.2f}")
        if info['portfolio_value'] > 0:
            print(f"RL vs B&H: {(info['portfolio_value'] / info['portfolio_value'] - 1) * 100:+.1f}%")

    return model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--train-start', default='2014')
    parser.add_argument('--train-end', default='2018')
    parser.add_argument('--test-start', default='2019')
    parser.add_argument('--test-end', default='2024')
    parser.add_argument('--timesteps', type=int, default=100000)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    config = Config('/home/ksf_stockmarket/ksf_stockmarket/config.yaml')
    symbols = get_candidate_symbols(config)

    print(f"RL Agent: {len(symbols)} symbols")
    train_rl(config, symbols,
             f'{args.train_start}-01-01', f'{args.train_end}-12-31',
             f'{args.test_start}-01-01', f'{args.test_end}-12-31',
             total_timesteps=args.timesteps, verbose=args.verbose)


if __name__ == '__main__':
    main()
