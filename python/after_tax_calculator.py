#!/usr/bin/env python3
"""
after_tax_calculator.py — CDN after-tax return engine for Alberta investors.

Models three account types:
  TFSA:      0% tax on everything (growth + dividends + withdrawals)
  RRSP:      0% tax on contributions/growth, taxed as income on withdrawal
  MARGINAL:  Taxed annually on dividends (gross-up + DTC) and capital gains (50% inclusion)

Uses 2024 Alberta tax brackets seeded in tax_parameters table.

Research basis:
  - Eligible dividends: 38% gross-up, 15.0198% federal DTC, 8.12% Alberta DTC
  - Non-eligible: 15% gross-up, 9.0301% federal DTC, ~4-8% provincial (varies by province)
  - Capital gains: 50% inclusion rate (federal + provincial)
  - US dividends: 15% withholding tax under treaty (no DTC in taxable)
  - Foreign dividends: no gross-up, no DTC, withholding tax varies
  - TFSA: no tax but no deduction on contributions
  - RRSP: deduction at marginal rate, withdrawal taxed as income
"""
import pymysql
import json
from datetime import date, datetime
from dataclasses import dataclass, field
from typing import Optional

# ── Config ──────────────────────────────────────────────────────────────────
MYSQL = dict(host='ksfraser.ca', user='ksfraser_stockmarket',
             password='Zaqwsx9sm1@', database='ksfraser_stock_market',
             charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)


# ── Data Classes ────────────────────────────────────────────────────────────
@dataclass
class TaxBracket:
    name: str
    income_min: float
    income_max: float
    federal_rate: float
    provincial_rate: float
    combined_rate: float
    gross_up: float = 1.38
    fed_dtc: float = 0.150198
    prov_dtc: float = 0.0812
    us_withholding: float = 0.15


@dataclass
class Position:
    symbol: str
    account_type: str  # TFSA, RRSP, MARGINAL
    shares: float
    cost_basis: float
    current_price: float
    eligible_dividend_yield: float = 0.0  # annual $ per share
    non_eligible_dividend_yield: float = 0.0
    is_canadian: bool = True
    is_us: bool = False
    is_foreign: bool = False


@dataclass
class TaxResult:
    position: str
    account_type: str
    market_value: float
    cost_basis_total: float
    unrealized_gain: float
    # Pre-tax returns
    annual_dividend: float
    annual_capital_appreciation: float
    total_pretax_return: float
    # Tax breakdown
    grossed_up_dividend: float
    federal_tax: float
    provincial_tax: float
    div_tax_credit: float
    withholding_tax: float
    cg_tax: float
    total_tax: float
    # After-tax
    after_tax_return: float
    tax_drag_pct: float
    effective_div_rate: float
    after_tax_yield_pct: float


@dataclass
class PortfolioTaxSummary:
    total_market_value: float
    total_cost_basis: float
    total_unrealized_gain: float
    total_annual_dividend: float
    total_pretax_return: float
    total_tax: float
    total_after_tax: float
    blended_tax_drag: float
    positions: list = field(default_factory=list)
    by_account: dict = field(default_factory=dict)


# ── Core Calculator ─────────────────────────────────────────────────────────
class AfterTaxCalculator:
    """Calculate after-tax returns for CDN (Alberta) investors."""

    def __init__(self, tax_year=2024, province='AB', db_config=None):
        self.db_config = db_config or MYSQL
        self.tax_year = tax_year
        self.province = province
        self.brackets = self._load_brackets()

    def _load_brackets(self):
        """Load tax brackets from MySQL."""
        conn = pymysql.connect(**self.db_config)
        c = conn.cursor()
        c.execute("""SELECT * FROM tax_parameters WHERE year=%s AND province=%s ORDER BY taxable_income_min""",
                  (self.tax_year, self.province))
        rows = c.fetchall()
        conn.close()
        brackets = []
        for r in rows:
            brackets.append(TaxBracket(
                name=r['bracket_name'],
                income_min=float(r['taxable_income_min']),
                income_max=float(r['taxable_income_max']),
                federal_rate=float(r['federal_rate']),
                provincial_rate=float(r['provincial_rate']),
                combined_rate=float(r['combined_rate']),
                gross_up=float(r['eligible_gross_up_rate']),
                fed_dtc=float(r['eligible_fed_dtc_rate']),
                prov_dtc=float(r['eligible_prov_dtc_rate']),
                us_withholding=float(r['us_withholding']),
            ))
        return brackets

    def get_bracket(self, taxable_income: float) -> TaxBracket:
        """Find the tax bracket for a given taxable income."""
        for b in self.brackets:
            if float(b.income_min) <= taxable_income <= float(b.income_max):
                return b
        return self.brackets[-1]  # top bracket

    def calculate_position(self, pos: Position, annual_price_change_pct: float = 0.0,
                           marginal_income: float = 130000) -> TaxResult:
        """Calculate after-tax return for a single position."""
        mv = pos.shares * pos.current_price
        cost = pos.shares * pos.cost_basis
        unrealized = mv - cost

        # Annual income from this position
        annual_elig_div = pos.shares * pos.eligible_dividend_yield
        annual_nonelig_div = pos.shares * pos.non_eligible_dividend_yield
        annual_total_div = annual_elig_div + annual_nonelig_div

        # Capital appreciation (annualized)
        annual_cg = mv * (annual_price_change_pct / 100)
        total_pretax = annual_total_div + annual_cg

        bracket = self.get_bracket(marginal_income)
        result = TaxResult(
            position=pos.symbol, account_type=pos.account_type,
            market_value=mv, cost_basis_total=cost, unrealized_gain=unrealized,
            annual_dividend=annual_total_div, annual_capital_appreciation=annual_cg,
            total_pretax_return=total_pretax,
            grossed_up_dividend=0, federal_tax=0, provincial_tax=0,
            div_tax_credit=0, withholding_tax=0, cg_tax=0, total_tax=0,
            after_tax_return=0, tax_drag_pct=0, effective_div_rate=0,
            after_tax_yield_pct=0
        )

        if pos.account_type == 'TFSA':
            # TFSA: zero tax on everything
            result.after_tax_return = total_pretax
            result.tax_drag_pct = 0
            result.after_tax_yield_pct = (annual_total_div / mv * 100) if mv > 0 else 0
            return result

        if pos.account_type == 'RRSP':
            # RRSP: no annual tax, but withdrawal taxed as income
            # For annual reporting: show pre-tax, note future liability
            result.after_tax_return = total_pretax
            result.federal_tax = 0  # deferred
            result.provincial_tax = 0  # deferred
            # But track the "phantom" tax that will be due on withdrawal
            phantom_tax = total_pretax * bracket.combined_rate
            result.total_tax = phantom_tax  # future liability
            result.tax_drag_pct = phantom_tax / total_pretax if total_pretax > 0 else 0
            result.after_tax_yield_pct = (annual_total_div / mv * 100) if mv > 0 else 0
            return result

        # ── MARGINAL account — actual annual tax ──
        tax = 0.0

        # 1. Eligible dividends (Canadian)
        if annual_elig_div > 0 and pos.is_canadian:
            grossed = annual_elig_div * bracket.gross_up
            result.grossed_up_divided = grossed  # typo handled below
            result.grossed_up_dividend = grossed

            fed_tax = grossed * bracket.federal_rate
            prov_tax = grossed * bracket.provincial_rate
            fed_credit = grossed * bracket.fed_dtc
            prov_credit = grossed * bracket.prov_dtc
            div_tc = fed_credit + prov_credit

            net_div_tax = max(0, fed_tax + prov_tax - div_tc)
            result.federal_tax += fed_tax - fed_credit
            result.provincial_tax += prov_tax - prov_credit
            result.div_tax_credit = div_tc
            tax += net_div_tax

        # 2. US dividends — 15% withholding, no DTC in taxable
        if annual_total_div > 0 and pos.is_us:
            wht = annual_total_div * bracket.us_withholding
            result.withholding_tax += wht
            # Also taxed as income grossed up (but US already withheld)
            grossed = annual_total_div * 1.15  # 15% gross-up for foreign
            fed_tax = grossed * bracket.federal_rate
            prov_tax = grossed * bracket.provincial_rate
            # Foreign tax credit = withholding (can't double-deduct)
            net = max(0, fed_tax + prov_tax - wht)
            result.federal_tax += max(0, fed_tax - wht)
            result.provincial_tax += prov_tax
            tax += net

        # 3. Foreign (non-US, non-CA) dividends — withholding only
        if annual_total_div > 0 and pos.is_foreign and not pos.is_us:
            # 15% withholding (typical treaty rate)
            wht = annual_total_div * 0.15
            result.withholding_tax += wht
            tax += wht  # no DTC for most foreign
            result.federal_tax += annual_total_div * bracket.federal_rate * 0.5
            result.provincial_tax += annual_total_div * bracket.provincial_rate * 0.5

        # 4. Capital gains (only unrealized when realized)
        if annual_cg > 0:
            included = annual_cg * 0.5  # 50% inclusion rate
            cg_fed = included * bracket.federal_rate
            cg_prov = included * bracket.provincial_rate
            result.cg_tax = cg_fed + cg_prov
            tax += result.cg_tax

        result.total_tax = tax
        result.after_tax_return = total_pretax - tax
        result.tax_drag_pct = tax / total_pretax if total_pretax > 0 else 0
        result.effective_div_rate = bracket.combined_rate - (
            bracket.fed_dtc + bracket.prov_dtc) * bracket.gross_up if pos.is_canadian else bracket.us_withholding
        result.after_tax_yield_pct = (result.after_tax_return / mv * 100) if mv > 0 else 0

        return result

    def calculate_portfolio(self, positions: list, annual_return_pct: float = 8.0,
                            marginal_income: float = 130000) -> PortfolioTaxSummary:
        """Calculate after-tax returns for an entire portfolio."""
        summary = PortfolioTaxSummary(
            total_market_value=0, total_cost_basis=0, total_unrealized_gain=0,
            total_annual_dividend=0, total_pretax_return=0,
            total_tax=0, total_after_tax=0, blended_tax_drag=0,
            positions=[], by_account={'TFSA': [], 'RRSP': [], 'MARGINAL': []}
        )

        for pos in positions:
            # Estimate annual price change from portfolio target
            result = self.calculate_position(pos, annual_return_pct, marginal_income)
            summary.positions.append(result)
            summary.by_account[pos.account_type].append(result)

            summary.total_market_value += result.market_value
            summary.total_cost_basis += result.cost_basis_total
            summary.total_unrealized_gain += result.unrealized_gain
            summary.total_annual_dividend += result.annual_dividend
            summary.total_pretax_return += result.total_pretax_return
            summary.total_tax += result.total_tax
            summary.total_after_tax += result.after_tax_return

        summary.blended_tax_drag = (
            summary.total_tax / summary.total_pretax_return
            if summary.total_pretax_return > 0 else 0
        )

        return summary

    def compare_accounts(self, pos: Position, annual_return_pct: float = 8.0,
                         marginal_income: float = 130000,
                         rrsp_withdrawal_years: int = 20) -> dict:
        """Compare the same position across TFSA vs RRSP vs MARGINAL."""
        results = {}
        for acct in ['TFSA', 'RRSP', 'MARGINAL']:
            p = Position(
                symbol=pos.symbol, account_type=acct,
                shares=pos.shares, cost_basis=pos.cost_basis,
                current_price=pos.current_price,
                eligible_dividend_yield=pos.eligible_dividend_yield,
                is_canadian=pos.is_canadian, is_us=pos.is_us
            )
            r = self.calculate_position(p, annual_return_pct, marginal_income)
            results[acct] = {
                'after_tax_annual': r.after_tax_return,
                'tax_drag_pct': r.tax_drag_pct,
                'effective_yield': r.after_tax_yield_pct,
                'total_tax_paid': r.total_tax,
            }

        # RRSP: adjust for withdrawal tax penalty
        rrsp_results = results['RRSP']
        rrsp_phantom = rrsp_results['total_tax_paid']
        # If withdrawn over N years, average tax rate on withdrawal
        bracket = self.get_bracket(marginal_income)
        rrsp_withdrawal_rate = bracket.combined_rate * 0.7  # assume lower bracket in retirement
        real_rrsp_tax = rrsp_results['after_tax_annual'] * rrsp_withdrawal_rate
        results['RRSP']['after_tax_annual_real'] = rrsp_results['after_tax_annual'] - real_rrsp_tax
        results['RRSP']['withdrawal_tax_estimate'] = real_rrsp_tax

        return results

    def store_results(self, results: PortfolioTaxSummary, strategy_name: str = 'default'):
        """Store after-tax results in MySQL for reporting."""
        conn = pymysql.connect(**self.db_config)
        c = conn.cursor()

        for r in results.positions:
            c.execute("""INSERT INTO after_tax_returns 
                (date,strategy_name,account_type,total_return,capital_gain,
                 eligible_div,foreign_div,fed_tax,prov_tax,div_tax_credit,
                 withholding_tax,after_tax_return,tax_drag_pct)
                VALUES (CURDATE(),%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (strategy_name, r.account_type, r.total_pretax_return,
                 r.annual_capital_appreciation, r.annual_dividend if 'CDN' in r.position else 0,
                 r.annual_dividend if 'US' in r.position else 0,
                 r.federal_tax, r.provincial_tax, r.div_tax_credit,
                 r.withholding_tax, r.after_tax_return, r.tax_drag_pct))

        conn.commit()
        conn.close()


# ── CLI / Report ────────────────────────────────────────────────────────────
def format_report(summary: PortfolioTaxSummary, marginal_income: float = 130000) -> str:
    """Format a human-readable tax report."""
    lines = []
    lines.append("=" * 70)
    lines.append(f"AFTER-TAX RETURN REPORT — 2024 Alberta, ${marginal_income:,.0f} income")
    lines.append(f"Total Portfolio: ${summary.total_market_value:,.2f}")
    lines.append("=" * 70)

    lines.append(f"\n{'Position':<12} {'Acct':<8} {'MarketVal':>12} {'PreTax':>10} "
                 f"{'Tax':>10} {'AfterTax':>10} {'Drag':>8}")
    lines.append("-" * 70)

    for r in summary.positions:
        lines.append(
            f"{r.position:<12} {r.account_type:<8} ${r.market_value:>11,.2f} "
            f"${r.total_pretax_return:>9,.2f} ${r.total_tax:>9,.2f} "
            f"${r.after_tax_return:>9,.2f} {r.tax_drag_pct*100:>6.1f}%"
        )

    lines.append("-" * 70)
    lines.append(
        f"{'TOTAL':<12} {'':8} ${summary.total_market_value:>11,.2f} "
        f"${summary.total_pretax_return:>9,.2f} ${summary.total_tax:>9,.2f} "
        f"${summary.total_after_tax:>9,.2f} {summary.blended_tax_drag*100:>6.1f}%"
    )

    lines.append("\n── By Account Type ──")
    for acct, positions in summary.by_account.items():
        if not positions:
            continue
        acct_mv = sum(p.market_value for p in positions)
        acct_pretax = sum(p.total_pretax_return for p in positions)
        acct_tax = sum(p.total_tax for p in positions)
        acct_after = sum(p.after_tax_return for p in positions)
        acct_drag = (acct_tax / acct_pretax * 100) if acct_pretax > 0 else 0
        lines.append(f"  {acct:<10} ${acct_mv:>12,.2f}  pre-tax=${acct_pretax:>10,.2f}  "
                     f"tax=${acct_tax:>10,.2f}  after=${acct_after:>10,.2f}  drag={acct_drag:.1f}%")

    return "\n".join(lines)


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    calc = AfterTaxCalculator(tax_year=2024, province='AB')

    # Load portfolio from MySQL
    conn = pymysql.connect(**MYSQL)
    c = conn.cursor()
    c.execute("SELECT * FROM portfolio WHERE shares > 0")
    holdings = c.fetchall()
    conn.close()

    if not holdings:
        # Demo with sample positions
        print("No portfolio positions with shares > 0. Running demo...")
        positions = [
            Position('RY.TO', 'MARGINAL', 100, 95.0, 130.0,
                     eligible_dividend_yield=3.20, is_canadian=True),
            Position('ENB.TO', 'MARGINAL', 200, 42.0, 48.0,
                     eligible_dividend_yield=3.80, is_canadian=True),
            Position('VGS', 'TFSA', 150, 85.0, 105.0,
                     eligible_dividend_yield=2.10, is_foreign=True),
            Position('AAPL', 'TFSA', 50, 140.0, 185.0,
                     eligible_dividend_yield=0.50, is_us=True),
            Position('VNQ', 'RRSP', 80, 75.0, 88.0,
                     eligible_dividend_yield=3.50, is_us=True),
            Position('XIC.TO', 'MARGINAL', 20, 45.0, 55.12,
                     eligible_dividend_yield=1.80, is_canadian=True),
        ]
    else:
        positions = []
        for h in holdings:
            is_ca = h['symbol'].endswith('.TO') or h['symbol'].endswith('.VN')
            positions.append(Position(
                symbol=h['symbol'], account_type=h['account_type'],
                shares=float(h['shares']), cost_basis=float(h['cost_basis']),
                current_price=float(h['cost_basis']) * 1.1,  # estimate
                is_canadian=is_ca,
                eligible_dividend_yield=2.5 if is_ca else 1.5,
            ))

    # Calculate
    summary = calc.calculate_portfolio(positions, annual_return_pct=8.0, marginal_income=130000)

    # Print report
    report = format_report(summary, marginal_income=130000)
    print(report)

    # Store in MySQL
    calc.store_results(summary, 'demo_strategy')
    print("\nResults stored in after_tax_returns table")

    # Compare accounts for one position
    if positions:
        print("\n" + "=" * 70)
        print("ACCOUNT COMPARISON — RY.TO")
        print("=" * 70)
        comp = calc.compare_accounts(positions[0])
        for acct, data in comp.items():
            print(f"\n  {acct}:")
            for k, v in data.items():
                if isinstance(v, float):
                    print(f"    {k}: ${v:,.2f}" if v > 1 else f"    {k}: {v:.4f}")
                else:
                    print(f"    {k}: {v}")


if __name__ == '__main__':
    main()
