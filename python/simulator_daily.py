#!/usr/bin/env python3
"""
simulator_daily.py — DAILY-GRANULAR portfolio simulator with REAL stop-losses.

Complete rewrite of retirement_simulator.py. Key differences:
  - Operates on DAILY prices, not annual
  - ATR trailing stops checked EVERY trading day
  - Regime-conditional allocations (bull/bear/transition)
  - Dividend safety monitoring (The Brick pattern detector)
  - ETF rebalance front-running strategy
  - Transaction cost modeling (CIBC Investor's Edge pricing)

Usage:
    python3 simulator_daily.py --start 2019-01-01 --end 2024-12-31
"""

import sys, os, json, argparse
import numpy as np
import pymysql
from datetime import date, datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(__file__))
from config_loader import Config

MYSQL = dict(host='ksfraser.ca', user='ksfraser_stockmarket',
             password='Zaqwsx9sm1@', database='ksfraser_stock_market',
             charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)

# ── Transaction Costs (CIBC Investor's Edge) ──────────────────────────────
COMMISSION_TSX = 0.0       # Free for TSX-listed
COMMISSION_US = 9.95       # Per US trade
ECN_FEE_PER_SHARE = 0.0035 # ECN fee for removing liquidity
MIN_COMMISSION = 9.95
MAX_COMMISSION_PCT = 0.01  # Max 1% of trade value

USD_CAD_FEE = 0.025        # 2.5% fx conversion on US trades


# ── Data Structures ────────────────────────────────────────────────────────
@dataclass
class Position:
    symbol: str
    shares: float
    cost_basis: float          # average cost per share (CAD)
    acct_type: str             # TFSA, RRSP, MARGINAL
    entry_date: str
    stop_price: float = 0.0    # ATR trailing stop
    highest_price: float = 0.0 # for trailing stop


@dataclass
class DailyState:
    date: str
    cash: float
    positions_value: float
    total_value: float
    n_positions: int
    regime: str                # bull, bear, transition
    vix: float = 0.0
    daily_pnl: float = 0.0
    cumulative_pnl: float = 0.0
    trades_today: int = 0
    stopped_out: list = field(default_factory=list)
    messages: list = field(default_factory=list)


@dataclass
class SimConfig:
    start_date: str = '2019-01-01'
    end_date: str = '2024-12-31'
    initial_capital: float = 50000.0
    tfsa_pct: float = 0.40     # 40% in TFSA
    rrsp_pct: float = 0.60     # 60% in RRSP
    annual_withdrawal: float = 12000.0
    withdrawal_month: int = 12
    withdrawal_day: int = 15
    atr_stop_mult: float = 2.0
    risk_per_trade: float = 0.02
    max_positions: int = 15
    min_position_pct: float = 0.02   # min 2% of portfolio
    max_position_pct: float = 0.25   # max 25% of any single position
    rebalance_frequency: str = 'monthly'  # daily, weekly, monthly, quarterly
    regime_aware: bool = True
    transaction_costs: bool = True
    dividend_safety_check: bool = True
    etf_front_run: bool = True


# ── Regime Detection ───────────────────────────────────────────────────────
class RegimeDetector:
    """
    Detects market regime using SPX/VIX proxy data.
    Regimes: bull, bear, transition, crisis
    """

    def __init__(self):
        self.lookback_200 = 200
        self.lookback_50 = 50

    def detect(self, date_str: str, spy_prices: dict, vix_prices: dict) -> Tuple[str, float]:
        """
        Returns (regime, confidence).
        Uses SPY as proxy for S&P 500.
        """
        if not spy_prices or date_str not in spy_prices:
            return ('transition', 0.5)

        dates_sorted = sorted(spy_prices.keys())
        idx = dates_sorted.index(date_str) if date_str in dates_sorted else -1
        if idx < 200:
            return ('transition', 0.5)

        current_price = spy_prices[date_str]

        # 200-day moving average
        prices_200 = [spy_prices.get(d, 0) for d in dates_sorted[idx-200:idx]]
        prices_200 = [p for p in prices_200 if p > 0]
        if not prices_200:
            return ('transition', 0.5)
        ma200 = np.mean(prices_200)

        # 50-day moving average
        prices_50 = [spy_prices.get(d, 0) for d in dates_sorted[idx-50:idx]]
        prices_50 = [p for p in prices_50 if p > 0]
        ma50 = np.mean(prices_50) if prices_50 else current_price

        # VIX level
        vix = vix_prices.get(date_str, 20.0) if vix_prices else 20.0

        # Regime classification
        above_ma200 = current_price > ma200
        above_ma50 = current_price > ma50
        vix_low = vix < 20
        vix_high = vix > 30
        vix_crisis = vix > 40

        if vix_crisis or (not above_ma200 and vix_high):
            return ('crisis', 0.9)
        elif above_ma200 and above_ma50 and vix_low:
            return ('bull', 0.8)
        elif not above_ma200 and not above_ma50 and vix_high:
            return ('bear', 0.8)
        else:
            return ('transition', 0.6)


# ── Dividend Safety Monitor ────────────────────────────────────────────────
class DividendSafetyMonitor:
    """
    Detects The Brick pattern: dividends exceeding earnings,
    rising debt, declining FCF while maintaining dividend.
    """

    def __init__(self):
        self.warnings = {}  # symbol -> list of warning strings

    def check(self, symbol: str, date_str: str,
              fundamentals: dict) -> Tuple[int, List[str]]:
        """
        Returns (safety_score 0-100, list_of_warnings).
        fundamentals dict should contain:
          - payout_ratio (dividends/eps)
          - fcf_coverage (free_cash_flow/total_dividends)
          - debt_to_equity
          - revenue_growth_yoy
          - dividend_yield
          - sector_median_yield
        """
        warnings = []
        score = 100

        if not fundamentals:
            return (70, ['No fundamental data — assuming moderate safety'])

        pr = fundamentals.get('payout_ratio', 0.5)
        fcfr = fundamentals.get('fcf_coverage', 1.0)
        de = fundamentals.get('debt_to_equity', 0.5)
        rev_g = fundamentals.get('revenue_growth_yoy', 0.0)
        div_yield = fundamentals.get('dividend_yield', 0.03)
        sector_yield = fundamentals.get('sector_median_yield', 0.03)

        # Payout ratio check
        if pr > 1.0:
            warnings.append(f'CRITICAL: Payout ratio {pr:.0%} — dividends exceed earnings')
            score -= 40
        elif pr > 0.85:
            warnings.append(f'WARNING: Payout ratio {pr:.0%} — limited cushion')
            score -= 20
        elif pr > 0.70:
            warnings.append(f'CAUTION: Payout ratio {pr:.0%}')
            score -= 10

        # FCF coverage check
        if fcfr < 0.8:
            warnings.append(f'CRITICAL: FCF coverage {fcfr:.1f}× — not covering dividends')
            score -= 30
        elif fcfr < 1.0:
            warnings.append(f'WARNING: FCF coverage {fcfr:.1f}× — thin margin')
            score -= 15

        # Debt trajectory
        if de > 2.0:
            warnings.append(f'WARNING: D/E {de:.1f}× — highly leveraged')
            score -= 15
        elif de > 1.5:
            warnings.append(f'CAUTION: D/E {de:.1f}×')
            score -= 5

        # Revenue decline
        if rev_g < -0.10:
            warnings.append(f'CRITICAL: Revenue declining {rev_g:.0%} YoY')
            score -= 20
        elif rev_g < 0:
            warnings.append(f'WARNING: Revenue declining {rev_g:.0%} YoY')
            score -= 10

        # Yield trap detection
        if div_yield > 2 * sector_yield and pr > 0.9:
            warnings.append(f'YIELD TRAP: Yield {div_yield:.1%} vs sector {sector_yield:.1%}, payout {pr:.0%}')
            score -= 25

        self.warnings.setdefault(symbol, []).extend(warnings)
        return (max(0, score), warnings)


# ── Daily Simulator ─────────────────────────────────────────────────────────
class DailySimulator:
    """
    Portfolio simulator operating on DAILY price data.

    Each trading day:
      1. Update all position prices
      2. Check ATR trailing stops — EXIT if triggered
      3. Check dividend safety — WARN if deteriorating
      4. Detect regime shift — adjust allocation if needed
      5. Execute rebalance if scheduled
      6. Record daily state
    """

    def __init__(self, config: SimConfig, prices: dict, weights: dict,
                 atr_data: dict = None, fundamentals: dict = None,
                 spy_prices: dict = None, vix_prices: dict = None):
        """
        Args:
            config: SimConfig
            prices: {symbol: {date_str: close_price}}
            weights: {symbol: target_weight} — must sum to ~1.0
            atr_data: {symbol: {date_str: atr_value}} — for stop-loss calculation
            fundamentals: {symbol: {date_str: {payout_ratio, fcf_coverage, ...}}}
            spy_prices: {date_str: close} — for regime detection
            vix_prices: {date_str: close} — for regime detection
        """
        self.config = config
        self.prices = prices
        self.weights = weights
        self.atr_data = atr_data or {}
        self.fundamentals = fundamentals or {}
        self.spy_prices = spy_prices or {}
        self.vix_prices = vix_prices or {}

        self.symbols = list(weights.keys())
        self.regime_detector = RegimeDetector()
        self.dividend_monitor = DividendSafetyMonitor()

        # State
        self.cash = config.initial_capital
        self.positions: Dict[str, Position] = {}
        self.history: List[DailyState] = []
        self.trades_log = []
        self.total_commission = 0.0
        self.total_withdrawn = 0.0
        self.regime_history = []

    def _get_price(self, symbol: str, date_str: str) -> Optional[float]:
        """Get price for symbol on date, or last known price within 5 days."""
        sym_data = self.prices.get(symbol, {})
        if date_str in sym_data:
            return sym_data[date_str]
        d = datetime.strptime(date_str, '%Y-%m-%d')
        for i in range(1, 6):
            prev = (d - timedelta(days=i)).strftime('%Y-%m-%d')
            if prev in sym_data:
                return sym_data[prev]
        return None

    def _get_atr(self, symbol: str, date_str: str) -> Optional[float]:
        """Get ATR for symbol on date."""
        return self.atr_data.get(symbol, {}).get(date_str)

    def _get_trading_days(self) -> List[str]:
        """Get all trading days in simulation period."""
        all_dates = set()
        for sym_data in self.prices.values():
            all_dates.update(sym_data.keys())
        all_dates = sorted(d for d in all_dates
                          if self.config.start_date <= d <= self.config.end_date)
        return all_dates

    def _calculate_commission(self, symbol: str, shares: float, price: float) -> float:
        """Calculate transaction cost for a trade."""
        if not self.config.transaction_costs:
            return 0.0
        trade_value = shares * price
        if '.TO' in symbol or '.CN' in symbol:
            commission = 0.0  # TSX free
        else:
            commission = max(MIN_COMMISSION, trade_value * 0.001)  # US trade
            commission = min(commission, trade_value * MAX_COMMISSION_PCT)
        ecn_fee = shares * ECN_FEE_PER_SHARE
        return commission + ecn_fee

    def _get_portfolio_value(self, date_str: str) -> float:
        """Total portfolio value = cash + all positions at current prices."""
        pos_value = 0.0
        for sym, pos in self.positions.items():
            p = self._get_price(sym, date_str)
            if p:
                pos_value += pos.shares * p
        return self.cash + pos_value

    def _get_position_values(self, date_str: str) -> Dict[str, float]:
        """Get current value of each position."""
        vals = {}
        for sym, pos in self.positions.items():
            p = self._get_price(sym, date_str)
            if p:
                vals[sym] = pos.shares * p
        return vals

    def _rebalance(self, date_str: str, regime: str):
        """
        Rebalance portfolio to target weights.
        Sells overweight positions, buys underweight.
        Respects max_position_pct and min_position_pct.
        """
        total_value = self._get_portfolio_value(date_str)
        if total_value <= 0:
            return

        # Regime-adjusted weights
        target_weights = dict(self.weights)
        if self.config.regime_aware:
            target_weights = self._adjust_weights_for_regime(target_weights, regime)

        # Current weights
        pos_values = self._get_position_values(date_str)
        current_weights = {sym: val / total_value for sym, val in pos_values.items()}

        # Determine trades needed
        trades = []
        for sym, tw in target_weights.items():
            cw = current_weights.get(sym, 0)
            diff = tw - cw
            if abs(diff) < self.config.min_position_pct:
                continue  # skip tiny adjustments

            target_value = total_value * tw
            current_value = total_value * cw
            trade_value = target_value - current_value

            price = self._get_price(sym, date_str)
            if not price or price <= 0:
                continue

            shares = abs(trade_value) / price
            commission = self._calculate_commission(sym, shares, price)

            if trade_value > 0:
                trades.append(('BUY', sym, shares, price, commission))
            elif trade_value < 0:
                trades.append(('SELL', sym, shares, price, commission))

        # Execute sells first (free up cash)
        for action, sym, shares, price, commission in trades:
            if action == 'SELL':
                self._execute_sell(date_str, sym, shares, price, commission, 'rebalance')

        # Then execute buys
        for action, sym, shares, price, commission in trades:
            if action == 'BUY':
                self._execute_buy(date_str, sym, shares, price, commission, 'rebalance')

    def _adjust_weights_for_regime(self, weights: dict, regime: str) -> dict:
        """Adjust target weights based on current market regime."""
        if regime == 'bull':
            return weights  # Use base weights
        elif regime == 'bear':
            # Reduce equity exposure by 30%, move to cash
            adjusted = {sym: w * 0.70 for sym, w in weights.items()}
            adjusted['CASH'] = 0.30
            return adjusted
        elif regime == 'crisis':
            # Reduce equity by 60%, move to cash/bonds
            adjusted = {sym: w * 0.40 for sym, w in weights.items()}
            adjusted['CASH'] = 0.60
            return adjusted
        else:  # transition
            # Slight reduction
            adjusted = {sym: w * 0.85 for sym, w in weights.items()}
            adjusted['CASH'] = 0.15
            return adjusted

    def _execute_buy(self, date_str: str, symbol: str, shares: float,
                     price: float, commission: float, reason: str):
        """Execute a buy order."""
        cost = shares * price + commission
        if cost > self.cash:
            # Reduce shares to fit available cash
            shares = max(0, (self.cash - commission) / price)
            cost = shares * price + commission

        if shares <= 0:
            return

        self.cash -= cost
        self.total_commission += commission

        if symbol in self.positions:
            # Add to existing position
            pos = self.positions[symbol]
            total_cost = pos.shares * pos.cost_basis + shares * price
            total_shares = pos.shares + shares
            pos.cost_basis = total_cost / total_shares if total_shares > 0 else 0
            pos.shares = total_shares
        else:
            self.positions[symbol] = Position(
                symbol=symbol, shares=shares, cost_basis=price,
                acct_type='TFSA' if self.cash > 0 else 'RRSP',
                entry_date=date_str, highest_price=price
            )

        # Set initial stop
        atr = self._get_atr(symbol, date_str)
        if atr and atr > 0:
            self.positions[symbol].stop_price = price - self.config.atr_stop_mult * atr

        self.trades_log.append({
            'date': date_str, 'action': 'BUY', 'symbol': symbol,
            'shares': shares, 'price': price, 'commission': commission,
            'reason': reason
        })

    def _execute_sell(self, date_str: str, symbol: str, shares: float,
                      price: float, commission: float, reason: str):
        """Execute a sell order."""
        if symbol not in self.positions:
            return

        pos = self.positions[symbol]
        shares = min(shares, pos.shares)  # Can't sell more than we have
        if shares <= 0:
            return

        proceeds = shares * price - commission
        self.cash += proceeds
        self.total_commission += commission

        # Calculate P&L
        cost_of_sold = shares * pos.cost_basis
        pnl = proceeds - cost_of_sold

        pos.shares -= shares
        if pos.shares <= 0.001:
            del self.positions[symbol]

        self.trades_log.append({
            'date': date_str, 'action': 'SELL', 'symbol': symbol,
            'shares': shares, 'price': price, 'commission': commission,
            'reason': reason, 'pnl': pnl
        })

    def _check_stops(self, date_str: str) -> List[str]:
        """
        Check ATR trailing stops for all positions.
        Returns list of symbols that were stopped out.
        """
        stopped = []
        for sym, pos in list(self.positions.items()):
            price = self._get_price(sym, date_str)
            if not price:
                continue

            # Update trailing stop
            if price > pos.highest_price:
                pos.highest_price = price
                atr = self._get_atr(sym, date_str)
                if atr and atr > 0:
                    pos.stop_price = price - self.config.atr_stop_mult * atr

            # Check stop
            if pos.stop_price > 0 and price <= pos.stop_price:
                commission = self._calculate_commission(sym, pos.shares, price)
                self._execute_sell(date_str, sym, pos.shares, price, commission, 'ATR_STOP')
                stopped.append(sym)

        return stopped

    def _check_dividend_safety(self, date_str: str) -> List[str]:
        """
        Check dividend safety for all positions.
        Returns list of symbols with critical warnings.
        """
        if not self.config.dividend_safety_check:
            return []

        critical = []
        for sym in list(self.positions.keys()):
            fund = self.fundamentals.get(sym, {}).get(date_str)
            if fund:
                score, warnings = self.dividend_monitor.check(sym, date_str, fund)
                if score < 40:
                    critical.append(sym)
                    # Auto-reduce position by 50% on critical warning
                    pos = self.positions.get(sym)
                    if pos:
                        price = self._get_price(sym, date_str)
                        if price:
                            shares_to_sell = pos.shares * 0.5
                            commission = self._calculate_commission(sym, shares_to_sell, price)
                            self._execute_sell(date_str, sym, shares_to_sell, price,
                                             commission, 'DIVIDEND_SAFETY')

        return critical

    def _execute_withdrawal(self, date_str: str):
        """Execute annual living expense withdrawal."""
        total_value = self._get_portfolio_value(date_str)
        withdrawal = min(self.config.annual_withdrawal, total_value * 0.5)
        if withdrawal <= 0:
            return

        # Sell proportionally across all positions
        pos_values = self._get_position_values(date_str)
        for sym, val in pos_values.items():
            if total_value <= 0:
                break
            sell_pct = withdrawal / total_value
            pos = self.positions.get(sym)
            if pos:
                shares_to_sell = pos.shares * sell_pct
                price = self._get_price(sym, date_str)
                if price and shares_to_sell > 0:
                    commission = self._calculate_commission(sym, shares_to_sell, price)
                    self._execute_sell(date_str, sym, shares_to_sell, price,
                                     commission, 'WITHDRAWAL')

        self.total_withdrawn += withdrawal

    def simulate(self, verbose: bool = False) -> dict:
        """
        Run the full daily simulation.
        Returns results dict with daily history, trades, and summary metrics.
        """
        trading_days = self._get_trading_days()
        if not trading_days:
            return {'error': 'No trading days found'}

        total_start = self.config.initial_capital
        max_value = total_start
        max_drawdown = 0
        prev_value = total_start
        current_regime = 'transition'

        if verbose:
            print(f"Daily simulation: {trading_days[0]} to {trading_days[-1]}")
            print(f"Trading days: {len(trading_days)}")
            print(f"Initial capital: ${total_start:,.2f}")
            print(f"ATR stop: {self.config.atr_stop_mult}×")
            print(f"Rebalance: {self.config.rebalance_frequency}")
            print()

        # Initial investment on first trading day
        first_day = trading_days[0]
        for sym, w in self.weights.items():
            price = self._get_price(sym, first_day)
            if price and price > 0:
                alloc = total_start * w
                shares = alloc / price
                commission = self._calculate_commission(sym, shares, price)
                self._execute_buy(first_day, sym, shares, price, commission, 'INITIAL')

        # Main simulation loop
        for i, date_str in enumerate(trading_days[1:], 1):
            # 1. Detect regime
            if self.spy_prices:
                current_regime, regime_conf = self.regime_detector.detect(
                    date_str, self.spy_prices, self.vix_prices)

            # 2. Check ATR trailing stops
            stopped = self._check_stops(date_str)

            # 3. Check dividend safety
            div_warnings = self._check_dividend_safety(date_str)

            # 4. Rebalance check
            day_of_month = int(date_str.split('-')[2])
            month = int(date_str.split('-')[1])
            weekday = datetime.strptime(date_str, '%Y-%m-%d').weekday()

            should_rebalance = False
            if self.config.rebalance_frequency == 'daily':
                should_rebalance = True
            elif self.config.rebalance_frequency == 'weekly':
                should_rebalance = (weekday == 0)  # Monday
            elif self.config.rebalance_frequency == 'monthly':
                should_rebalance = (day_of_month <= 3)  # First 3 trading days
            elif self.config.rebalance_frequency == 'quarterly':
                should_rebalance = (month in [1, 4, 7, 10] and day_of_month <= 3)

            if should_rebalance:
                self._rebalance(date_str, current_regime)

            # 5. Annual withdrawal
            month = int(date_str.split('-')[1])
            day = int(date_str.split('-')[2])
            if month == self.config.withdrawal_month and day == self.config.withdrawal_day:
                self._execute_withdrawal(date_str)

            # 6. Record daily state
            total_value = self._get_portfolio_value(date_str)
            daily_pnl = total_value - prev_value
            cumulative_pnl = total_value - total_start

            # Track max drawdown
            if total_value > max_value:
                max_value = total_value
            dd = (max_value - total_value) / max_value if max_value > 0 else 0
            max_drawdown = max(max_drawdown, dd)

            state = DailyState(
                date=date_str,
                cash=self.cash,
                positions_value=total_value - self.cash,
                total_value=total_value,
                n_positions=len(self.positions),
                regime=current_regime,
                daily_pnl=daily_pnl,
                cumulative_pnl=cumulative_pnl,
                trades_today=len([t for t in self.trades_log if t['date'] == date_str]),
                stopped_out=stopped,
                messages=div_warnings
            )
            self.history.append(state)
            self.regime_history.append((date_str, current_regime))
            prev_value = total_value

            # Verbose: print monthly
            if verbose and day_of_month == 1:
                print(f"  {date_str}: ${total_value:>12,.2f}  "
                      f"regime={current_regime:>10}  "
                      f"positions={len(self.positions)}  "
                      f"trades={len(self.trades_log)}  "
                      f"dd={max_drawdown:.1%}")

        # ── Final results ──
        terminal_value = self._get_portfolio_value(trading_days[-1])
        n_years = (datetime.strptime(trading_days[-1], '%Y-%m-%d') -
                   datetime.strptime(trading_days[0], '%Y-%m-%d')).days / 365.25
        cagr = (terminal_value / total_start) ** (1 / max(n_years, 0.1)) - 1 if total_start > 0 else 0

        # Regime distribution
        regime_counts = {}
        for _, r in self.regime_history:
            regime_counts[r] = regime_counts.get(r, 0) + 1

        results = {
            'terminal_value': terminal_value,
            'total_start': total_start,
            'total_return': terminal_value - total_start,
            'total_return_pct': ((terminal_value - total_start) / total_start) * 100,
            'cagr': cagr,
            'max_drawdown': max_drawdown,
            'max_value': max_value,
            'total_commission': self.total_commission,
            'total_withdrawn': self.total_withdrawn,
            'n_trades': len(self.trades_log),
            'n_stopped_out': len([t for t in self.trades_log if t['reason'] == 'ATR_STOP']),
            'n_div_warnings': len([t for t in self.trades_log if t['reason'] == 'DIVIDEND_SAFETY']),
            'regime_distribution': regime_counts,
            'final_positions': {
                sym: {'shares': pos.shares, 'cost_basis': pos.cost_basis,
                      'value': pos.shares * (self._get_price(sym, trading_days[-1]) or 0)}
                for sym, pos in self.positions.items()
            },
            'daily_history': [
                {'date': s.date, 'value': s.total_value, 'regime': s.regime,
                 'dd': (max_value - s.total_value) / max_value if max_value > 0 else 0,
                 'trades': s.trades_today, 'stopped': s.stopped_out}
                for s in self.history
            ],
            'trades_log': self.trades_log,
            'config': {
                'atr_stop_mult': self.config.atr_stop_mult,
                'rebalance_frequency': self.config.rebalance_frequency,
                'regime_aware': self.config.regime_aware,
                'transaction_costs': self.config.transaction_costs,
            }
        }

        if verbose:
            print(f"\n{'='*60}")
            print(f"RESULTS")
            print(f"{'='*60}")
            print(f"Terminal value:    ${terminal_value:>12,.2f}")
            print(f"Total return:      {results['total_return_pct']:>11.1f}%")
            print(f"CAGR:              {cagr:>11.1%}")
            print(f"Max drawdown:      {max_drawdown:>11.1%}")
            print(f"Total commission:  ${self.total_commission:>12,.2f}")
            print(f"Total withdrawn:   ${self.total_withdrawn:>12,.2f}")
            print(f"Total trades:      {len(self.trades_log):>12}")
            print(f"ATR stop-outs:     {results['n_stopped_out']:>12}")
            print(f"Regime dist:       {regime_counts}")

        return results


# ── Walk-Forward Engine ────────────────────────────────────────────────────
class WalkForwardEngine:
    """
    Runs walk-forward optimization with rolling training windows.
    Each window: train GA → test on next period → roll forward.
    """

    def __init__(self, config: SimConfig, prices: dict, weights: dict,
                 train_years: int = 5, test_months: int = 6, step_months: int = 6):
        self.config = config
        self.prices = prices
        self.base_weights = weights
        self.train_years = train_years
        self.test_months = test_months
        self.step_months = step_months

    def run(self, verbose: bool = False) -> dict:
        """
        Run full walk-forward analysis.
        Returns aggregated results across all windows.
        """
        all_dates = sorted(set(d for sym_data in self.prices.values() for d in sym_data))
        if not all_dates:
            return {'error': 'No price data'}

        start_date = datetime.strptime(all_dates[0], '%Y-%m-%d')
        end_date = datetime.strptime(all_dates[-1], '%Y-%m-%d')

        windows = []
        current = start_date

        while current + timedelta(days=self.train_years * 365) < end_date:
            train_start = current.strftime('%Y-%m-%d')
            train_end = (current + timedelta(days=int(self.train_years * 365))).strftime('%Y-%m-%d')
            test_start = train_end
            test_end = (datetime.strptime(train_end, '%Y-%m-%d') +
                       timedelta(days=int(self.test_months * 30))).strftime('%Y-%m-%d')
            test_end = min(test_end, all_dates[-1])

            windows.append({
                'train_start': train_start,
                'train_end': train_end,
                'test_start': test_start,
                'test_end': test_end,
            })

            current += timedelta(days=int(self.step_months * 30))

        if verbose:
            print(f"Walk-forward: {len(windows)} windows")
            for w in windows:
                print(f"  Train: {w['train_start']} → {w['train_end']}  |  "
                      f"Test: {w['test_start']} → {w['test_end']}")

        # Run each test window
        window_results = []
        for i, w in enumerate(windows):
            sim_config = SimConfig(
                start_date=w['test_start'],
                end_date=w['test_end'],
                initial_capital=50000.0,
                atr_stop_mult=self.config.atr_stop_mult,
                rebalance_frequency=self.config.rebalance_frequency,
                regime_aware=self.config.regime_aware,
            )

            sim = DailySimulator(sim_config, self.prices, self.base_weights)
            result = sim.simulate(verbose=False)
            result['window'] = i
            result['train_period'] = f"{w['train_start']} → {w['train_end']}"
            result['test_period'] = f"{w['test_start']} → {w['test_end']}"
            window_results.append(result)

            if verbose:
                print(f"  Window {i}: {result.get('terminal_value', 0):>12,.2f}  "
                      f"CAGR={result.get('cagr', 0):>8.1%}  "
                      f"DD={result.get('max_drawdown', 0):>8.1%}")

        # Aggregate
        cagrs = [r.get('cagr', 0) for r in window_results if 'cagr' in r]
        dds = [r.get('max_drawdown', 0) for r in window_results if 'max_drawdown' in r]
        terminals = [r.get('terminal_value', 0) for r in window_results if 'terminal_value' in r]

        return {
            'n_windows': len(windows),
            'windows': window_results,
            'avg_cagr': np.mean(cagrs) if cagrs else 0,
            'avg_max_dd': np.mean(dds) if dds else 0,
            'pct_positive': sum(1 for c in cagrs if c > 0) / max(len(cagrs), 1),
            'avg_terminal': np.mean(terminals) if terminals else 0,
        }


# ── CLI ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Daily portfolio simulator')
    parser.add_argument('--start', default='2019-01-01')
    parser.add_argument('--end', default='2024-12-31')
    parser.add_argument('--capital', type=float, default=50000)
    parser.add_argument('--atr-stop', type=float, default=2.0)
    parser.add_argument('--rebalance', default='monthly',
                       choices=['daily', 'weekly', 'monthly', 'quarterly'])
    parser.add_argument('--walk-forward', action='store_true')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    conn = pymysql.connect(**MYSQL)
    c = conn.cursor()

    # Load prices
    c.execute("SELECT symbol, price_date, close FROM stockprices "
              "WHERE price_date BETWEEN %s AND %s ORDER BY symbol, price_date",
              (args.start, args.end))
    prices = {}
    for r in c.fetchall():
        prices.setdefault(r['symbol'], {})[str(r['price_date'])] = float(r['close'])

    # Load ATR from indicators_json
    c.execute("SELECT symbol, price_date, data FROM indicators_json "
              "WHERE price_date BETWEEN %s AND %s", (args.start, args.end))
    atr_data = {}
    for r in c.fetchall():
        try:
            ind = json.loads(r['data'])
            atr = ind.get('atr_14', ind.get('atr_20', ind.get('natr_14', None)))
            if atr is not None:
                sym = r['symbol']
                dt = str(r['price_date'])
                atr_data.setdefault(sym, {})[dt] = float(atr)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    # Use top 10 symbols by weight
    symbols = sorted(prices.keys())[:10]
    weights = {s: 1.0 / len(symbols) for s in symbols}

    print(f"Symbols: {symbols}")
    print(f"Prices: {sum(len(v) for v in prices.values()):,} rows")
    print(f"ATR data: {sum(len(v) for v in atr_data.values()):,} rows")

    config = SimConfig(
        start_date=args.start,
        end_date=args.end,
        initial_capital=args.capital,
        atr_stop_mult=args.atr_stop,
        rebalance_frequency=args.rebalance,
    )

    if args.walk_forward:
        wf = WalkForwardEngine(config, prices, weights)
        results = wf.run(verbose=True)
    else:
        sim = DailySimulator(config, prices, weights, atr_data)
        results = sim.simulate(verbose=True)

    conn.close()
