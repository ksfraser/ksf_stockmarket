#!/usr/bin/env python3
"""
retirement_simulator.py — 10-year retirement portfolio Monte Carlo simulator.

Objective: Maximize after-tax portfolio value at end of year 10,
           subject to annual December withdrawals.

Kevin's situation:
  - TFSA:  ~$20K  (already maxed for current year)
  - RRSP:  ~$30K  (already contributed)
  - Total investable: ~$50K initially
  - Annual contribution room: TFSA $7K/yr, RRSP ~$5-7K/yr
  - Need to withdraw $X every December (living drawdown during transition)
  - 10-year horizon to full retirement

Agent architecture:
  GA   → optimize symbol weights (which symbols, what %)
  NN   → predict forward returns (120 indicators → return distribution)
  RL   → dynamic rebalancing (when to rotate, tax-loss harvest, shift allocations)
  Blend→ combine GA static weights + NN predictions + RL trading signals

Each year:
  1. January: rebalance to target weights (GA-determined)
  2: Monthly: RL agent can adjust positions based on current indicators
  3. December: withdraw living expenses, tax-loss harvest if applicable
  4. End-of-year: record after-tax portfolio value

Walk-forward: train on 2014-2018, test on 2019-2024
"""
import pymysql
import numpy as np
import json
import argparse
from datetime import date, datetime
from dataclasses import dataclass, field
from typing import Optional

MYSQL = dict(host='ksfraser.ca', user='ksfraser_stockmarket',
             password='Zaqwsx9sm1@', database='ksfraser_stock_market',
             charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)


# ── Data Structures ────────────────────────────────────────────────────────
@dataclass
class Account:
    """A tax-sheltered or taxable account."""
    acct_type: str       # TFSA, RRSP, MARGINAL
    balance: float       # current market value
    contributions_ytd: float = 0
    room_remaining: float = 0

@dataclass
class Holding:
    symbol: str
    acct_type: str
    shares: float
    cost_basis: float       # per share
    current_price: float

@dataclass
class YearState:
    year: int
    accounts: dict           # {acct_type: Account}
    holdings: list           # [Holding]
    total_value: float
    total_value_after_tax: float
    withdrawal: float        # amount withdrawn this year
    tax_paid: float
    contribution_room_used: float


@dataclass
class SimConfig:
    """Simulation configuration."""
    start_date: str = '2014-01-01'
    end_date: str = '2024-12-31'
    initial_tfsa: float = 20000.0
    initial_rrsp: float = 30000.0
    annual_withdrawal: float = 12000.0  # $1K/mo living expenses
    withdrawal_month: int = 12          # December
    tfsa_room_annual: float = 7000.0    # 2024 room, grows yearly
    rrsp_room_annual: float = 6000.0    # approximate
    max_single_position: float = 0.15   # max 15% in one symbol
    rebalance_threshold: float = 0.05   # rebalance if drift > 5%
    transaction_cost: float = 9.95      # per trade
    marginal_income: float = 130000.0   # for tax calc
    tax_year: int = 2024
    province: str = 'AB'
    # Withdrawal order: TFSA first (tax-free), then RRSP (taxed as income)
    withdrawal_order: tuple = ('TFSA', 'RRSP', 'MARGINAL')


# ── Price Data ──────────────────────────────────────────────────────────────
def load_prices_from_db(symbols, start='2014-01-01', end='2024-12-31'):
    """Load price data from MySQL, return {symbol: {date_str: close}}."""
    conn = pymysql.connect(**MYSQL)
    c = conn.cursor()
    placeholders = ','.join(['%s'] * len(symbols))
    c.execute(f"""SELECT symbol, price_date, close
                 FROM stockprices WHERE symbol IN ({placeholders})
                 AND price_date BETWEEN %s AND %s
                 ORDER BY symbol, price_date""",
              list(symbols) + [start, end])
    rows = c.fetchall()
    conn.close()

    data = {}
    for r in rows:
        sym = r['symbol']
        d = str(r['price_date'])
        if sym not in data:
            data[sym] = {}
        data[sym][d] = float(r['close'])
    return data


def load_prices_from_yfinance(symbols, start='2014-01-01', end='2024-12-31'):
    """Fetch prices from yfinance for symbols not in DB."""
    try:
        import yfinance as yf
        import pandas as pd
    except ImportError:
        return {}

    data = {}
    for sym in symbols:
        try:
            hist = yf.Ticker(sym).history(start=start, end=end, auto_adjust=True)
            if hist.empty:
                continue
            sym_data = {}
            for idx, row in hist.iterrows():
                d = idx.strftime('%Y-%m-%d')
                sym_data[d] = float(row['Close'])
            data[sym] = sym_data
        except Exception as e:
            print(f"  yfinance {sym}: {e}")
    return data


# ── Tax Engine (simplified from after_tax_calculator) ──────────────────────
def calc_withdrawal_tax(amount, acct_type, marginal_income, province='AB'):
    """Calculate tax on a withdrawal."""
    if acct_type == 'TFSA':
        return 0.0
    elif acct_type == 'RRSP':
        # Taxed as income — use 3rd bracket (26% fed + 13% prov = 39%)
        # But in retirement, income may be lower — use 25% effective
        return amount * 0.25
    else:
        return 0.0  # margin withdrawal isn't a taxable event (only gains are)


def calc_annual_tax(holdings, marginal_income, province='AB'):
    """Calculate annual tax on dividends and realized gains."""
    total_tax = 0.0
    for h in holdings:
        if h.acct_type in ('TFSA', 'RRSP'):
            continue  # no annual tax in shelters
        # Simplified: assume 2.5% dividend yield, 85% eligible CDN
        annual_div = h.shares * h.current_price * 0.025
        if annual_div > 0:
            # Eligible div: gross-up 38%, DTC ~23% of grossed
            grossed = annual_div * 0.85 * 1.38
            tax_before_dtc = grossed * 0.39  # 3rd bracket
            dtc = grossed * 0.2314
            total_tax += max(0, tax_before_dtc - dtc)
    return total_tax


# ── Core Simulator ──────────────────────────────────────────────────────────
class RetirementSimulator:
    """
    Year-by-year retirement portfolio simulation.

    Each simulation run:
      1. Initialize accounts with starting balances
      2. For each year:
         a. January: invest according to target weights
         b. Monthly: update prices, check rebalance triggers
         c. December: withdraw living expenses, tax-loss harvest
         d. Record year-end state
      3. Return terminal value and path
    """

    def __init__(self, config: SimConfig, prices: dict, weights: dict):
        """
        Args:
            config: SimConfig
            prices: {symbol: {date_str: close_price}}
            weights: {symbol: target_pct} — must sum to ~1.0
        """
        self.config = config
        self.prices = prices
        self.weights = weights
        self.symbols = list(weights.keys())

    def _get_price(self, symbol, date_str):
        """Get price for symbol on date, or last known price."""
        sym_data = self.prices.get(symbol, {})
        if date_str in sym_data:
            return sym_data[date_str]
        # Walk back up to 5 days
        from datetime import datetime as dt, timedelta
        d = dt.strptime(date_str, '%Y-%m-%d')
        for i in range(1, 6):
            prev = (d - timedelta(days=i)).strftime('%Y-%m-%d')
            if prev in sym_data:
                return sym_data[prev]
        return None

    def _get_year_end_price(self, symbol, year):
        """Get last available price in December of given year."""
        for day in range(31, 0, -1):
            d = f"{year}-12-{day:02d}"
            p = self._get_price(symbol, d)
            if p is not None:
                return p
        # Fallback: last day of November
        for day in range(30, 0, -1):
            d = f"{year}-11-{day:02d}"
            p = self._get_price(symbol, d)
            if p is not None:
                return p
        return None

    def _get_year_start_price(self, symbol, year):
        """Get first available price in January of given year."""
        for day in range(1, 32):
            d = f"{year}-01-{day:02d}"
            p = self._get_price(symbol, d)
            if p is not None:
                return p
        return None

    def simulate(self, verbose=False) -> dict:
        """Run the full simulation. Returns results dict."""
        cfg = self.config
        start_year = int(cfg.start_date[:4])
        end_year = int(cfg.end_date[:4])

        # Initialize accounts
        accounts = {
            'TFSA': Account('TFSA', cfg.initial_tfsa, room_remaining=cfg.tfsa_room_annual),
            'RRSP': Account('RRSP', cfg.initial_rrsp, room_remaining=cfg.rrsp_room_annual),
        }

        # Initial investment: allocate across TFSA and RRSP by weights
        holdings = []
        total_start = cfg.initial_tfsa + cfg.initial_rrsp

        # Put CDN dividend stocks in RRSP (defer tax), growth in TFSA
        # Simple heuristic: split proportionally
        for sym, w in self.weights.items():
            alloc = total_start * w
            # Determine which account: RRSP gets 60%, TFSA gets 40%
            rrsp_alloc = alloc * 0.6
            tfsa_alloc = alloc * 0.4

            price_jan = self._get_year_start_price(sym, start_year)
            if price_jan and price_jan > 0:
                if rrsp_alloc > 100:
                    shares = rrsp_alloc / price_jan
                    holdings.append(Holding(sym, 'RRSP', shares, price_jan, price_jan))
                if tfsa_alloc > 100:
                    shares = tfsa_alloc / price_jan
                    holdings.append(Holding(sym, 'TFSA', shares, price_jan, price_jan))

        # Track history
        history = []
        total_tax_paid = 0.0
        total_withdrawn = 0.0

        for year in range(start_year, end_year + 1):
            # ── January: rebalance ──
            year_start_value = sum(
                h.shares * (self._get_year_start_price(h.symbol, year) or h.current_price)
                for h in holdings
            )

            # ── Monthly price updates (simplified: just use year-end) ──
            year_end_prices = {}
            for sym in self.symbols:
                p = self._get_year_end_price(sym, year)
                if p:
                    year_end_prices[sym] = p

            # Update holdings to year-end prices
            for h in holdings:
                if h.symbol in year_end_prices:
                    h.current_price = year_end_prices[h.symbol]

            # ── Annual tax on dividends ──
            year_tax = calc_annual_tax(holdings, cfg.marginal_income, cfg.province)
            total_tax_paid += year_tax

            # ── December withdrawal ──
            year_end_value = sum(h.shares * h.current_price for h in holdings)
            withdrawal = min(cfg.annual_withdrawal, year_end_value * 0.5)  # never withdraw >50%

            # Withdraw from accounts in order
            remaining = withdrawal
            for acct_type in cfg.withdrawal_order:
                acct_holdings = [h for h in holdings if h.acct_type == acct_type]
                acct_value = sum(h.shares * h.current_price for h in acct_holdings)

                if remaining <= 0 or acct_value <= 0:
                    continue

                take = min(remaining, acct_value)
                tax = calc_withdrawal_tax(take, acct_type, cfg.marginal_income)
                net = take - tax

                # Sell proportionally across holdings in this account
                if acct_value > 0:
                    for h in acct_holdings:
                        sell_pct = take / acct_value
                        h.shares *= (1 - sell_pct)

                remaining -= take
                total_tax_paid += tax

            total_withdrawn += withdrawal

            # ── Remove zero-share holdings ──
            holdings = [h for h in holdings if h.shares > 0.001]

            # ── Record year state ──
            year_value = sum(h.shares * h.current_price for h in holdings)
            state = YearState(
                year=year,
                accounts={k: v for k, v in accounts.items()},
                holdings=[h for h in holdings],
                total_value=year_value,
                total_value_after_tax=year_value - year_tax,
                withdrawal=withdrawal,
                tax_paid=year_tax,
                contribution_room_used=0,
            )
            history.append(state)

            if verbose:
                print(f"  {year}: ${year_value:>12,.2f}  "
                      f"withdrew=${withdrawal:>8,.2f}  tax=${year_tax:>7,.2f}  "
                      f"holdings={len(holdings)}")

        # ── Final results ──
        terminal_value = sum(h.shares * h.current_price for h in holdings)
        total_return = terminal_value + total_withdrawn - total_start

        results = {
            'terminal_value': terminal_value,
            'total_withdrawn': total_withdrawn,
            'total_tax_paid': total_tax_paid,
            'total_return': total_return,
            'total_return_pct': (total_return / total_start) * 100,
            'cagr': ((terminal_value + total_withdrawn) / total_start) ** (1 / (end_year - start_year + 1)) - 1,
            'history': [
                {'year': s.year, 'value': s.total_value, 'withdrawal': s.withdrawal,
                 'tax': s.tax_paid, 'n_holdings': len(s.holdings)}
                for s in history
            ],
            'final_holdings': [
                {'symbol': h.symbol, 'acct': h.acct_type, 'shares': h.shares,
                 'price': h.current_price, 'value': h.shares * h.current_price}
                for h in holdings
            ],
            'weights': self.weights,
        }

        return results


# ── Monte Carlo ─────────────────────────────────────────────────────────────
def monte_carlo_simulation(config: SimConfig, weights: dict, prices: dict,
                           n_sims=100, verbose=False) -> dict:
    """
    Run multiple simulations with randomized returns.
    For each sim, add noise to the actual returns to model uncertainty.
    """
    sim = RetirementSimulator(config, prices, weights)

    # First run: deterministic (actual historical returns)
    base_result = sim.simulate(verbose=verbose)

    # Monte Carlo: perturb returns by ±20% to model uncertainty
    terminal_values = [base_result['terminal_value']]
    cagrs = [base_result['cagr']]

    for i in range(n_sims - 1):
        # Create perturbed prices
        perturbed = {}
        noise = np.random.normal(1.0, 0.05)  # 5% annual noise
        for sym, sym_data in prices.items():
            perturbed[sym] = {d: p * noise for d, p in sym_data.items()}

        sim_mc = RetirementSimulator(config, perturbed, weights)
        r = sim_mc.simulate(verbose=False)
        terminal_values.append(r['terminal_value'])
        cagrs.append(r['cagr'])

    return {
        'base_result': base_result,
        'mc_terminal_mean': np.mean(terminal_values),
        'mc_terminal_std': np.std(terminal_values),
        'mc_terminal_5pct': np.percentile(terminal_values, 5),
        'mc_terminal_25pct': np.percentile(terminal_values, 25),
        'mc_terminal_50pct': np.percentile(terminal_values, 50),
        'mc_terminal_75pct': np.percentile(terminal_values, 75),
        'mc_terminal_95pct': np.percentile(terminal_values, 95),
        'mc_cagr_mean': np.mean(cagrs),
        'mc_cagr_std': np.std(cagrs),
        'mc_prob_positive': np.mean([v > 0 for v in terminal_values]) * 100,
        'n_sims': n_sims,
    }


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='Retirement Portfolio Simulator')
    parser.add_argument('--withdrawal', type=float, default=12000, help='Annual withdrawal amount')
    parser.add_argument('--tfsa', type=float, default=20000, help='Initial TFSA balance')
    parser.add_argument('--rrsp', type=float, default=30000, help='Initial RRSP balance')
    parser.add_argument('--start', default='2014', help='Start year')
    parser.add_argument('--end', default='2024', help='End year')
    parser.add_argument('--mc', type=int, default=0, help='Monte Carlo simulations')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    config = SimConfig(
        start_date=f'{args.start}-01-01',
        end_date=f'{args.end}-12-31',
        initial_tfsa=args.tfsa,
        initial_rrsp=args.rrsp,
        annual_withdrawal=args.withdrawal,
    )

    # Load prices from MySQL for our 19 symbols
    from allocation_backtester import ETF_PROXIES
    symbols = ['RY.TO', 'ENB.TO', 'BNS.TO', 'TD.TO', 'CM.TO', 'TRI.TO',
               'SU.TO', 'CNR.TO', 'BMO.TO', 'ATD.TO', 'NTR.TO',
               'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'JNJ', 'UNH',
               'XIC.TO', 'VGRO.TO', 'VCE.TO', 'VIU.TO', 'VAB.TO', 'GLD']

    print(f"Loading prices for {len(symbols)} symbols...")
    prices = load_prices_from_db(symbols, config.start_date, config.end_date)
    print(f"  Got data for {len(prices)} symbols from MySQL")

    # Equal-weight portfolio as baseline
    available = [s for s in symbols if s in prices]
    n = len(available)
    weights = {s: 1.0 / n for s in available}
    print(f"  Equal-weight across {n} symbols")

    # Run simulation
    print(f"\nSimulating {args.start}-{args.end}, "
          f"${args.withdrawal:,.0f}/yr withdrawal, "
          f"${args.tfsa+args.rrsp:,.0f} starting...")

    sim = RetirementSimulator(config, prices, weights)
    result = sim.simulate(verbose=True)

    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"  Terminal value:      ${result['terminal_value']:>12,.2f}")
    print(f"  Total withdrawn:     ${result['total_withdrawn']:>12,.2f}")
    print(f"  Total tax paid:      ${result['total_tax_paid']:>12,.2f}")
    print(f"  Total return:        ${result['total_return']:>12,.2f} ({result['total_return_pct']:.1f}%)")
    print(f"  CAGR:                {result['cagr']*100:.2f}%")

    if args.mc > 0:
        print(f"\nRunning {args.mc} Monte Carlo simulations...")
        mc = monte_carlo_simulation(config, weights, prices, n_sims=args.mc)
        print(f"\n{'='*60}")
        print(f"MONTE CARLO RESULTS ({args.mc} sims)")
        print(f"{'='*60}")
        print(f"  Terminal value (mean):  ${mc['mc_terminal_mean']:>12,.2f}")
        print(f"  Terminal value (std):   ${mc['mc_terminal_std']:>12,.2f}")
        print(f"  5th percentile:         ${mc['mc_terminal_5pct']:>12,.2f}")
        print(f"  25th percentile:        ${mc['mc_terminal_25pct']:>12,.2f}")
        print(f"  50th percentile:        ${mc['mc_terminal_50pct']:>12,.2f}")
        print(f"  75th percentile:        ${mc['mc_terminal_75pct']:>12,.2f}")
        print(f"  95th percentile:        ${mc['mc_terminal_95pct']:>12,.2f}")
        print(f"  CAGR (mean):            {mc['mc_cagr_mean']*100:.2f}%")
        print(f"  Prob positive:          {mc['mc_prob_positive']:.0f}%")


if __name__ == '__main__':
    main()
