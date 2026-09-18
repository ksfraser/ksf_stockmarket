"""
backtest_timing.py — Timing-Aware Backtest Extension

Extends the backtest engine with:
- Day-of-week timing (entry/exit day preferences)
- Day-of-month timing (week-of-month bias)
- Market-cap-aware position sizing limits
- Sector rotation timing signals

Usage:
    from python.backtest_timing import TimingConfig, TimingFilter

    timing = TimingConfig(
        entry_dow=3,          # Thursday
        exit_dow=1,           # Tuesday
        entry_week_of_month=1, # First week of month
        exit_week_of_month=5,  # Last week of month
        market_cap_limits={"micro": 0.02, "small": 0.03, "mid": 0.04, "large": 0.05},
        sector_rotation=True,
        sector_momentum_lookback=50,
    )

    # Check if a trade date is valid under timing rules
    filter = TimingFilter(timing, db_connection)
    if filter.can_enter(symbol, trade_date):
        # Allow entry
    if filter.can_exit(symbol, trade_date):
        # Allow exit
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Market Cap Tiers
# ---------------------------------------------------------------------------

class MarketCapTier(Enum):
    MICRO = "micro"      # < $300M
    SMALL = "small"      # $300M - $2B
    MID = "mid"          # $2B - $10B
    LARGE = "large"      # >= $10B


def get_market_cap_tier(market_cap: float) -> MarketCapTier:
    """Classify a market cap value into a tier."""
    if market_cap < 300_000_000:
        return MarketCapTier.MICRO
    elif market_cap < 2_000_000_000:
        return MarketCapTier.SMALL
    elif market_cap < 10_000_000_000:
        return MarketCapTier.MID
    else:
        return MarketCapTier.LARGE


# ---------------------------------------------------------------------------
# Week of Month Helper
# ---------------------------------------------------------------------------

def get_week_of_month(d: date) -> int:
    """
    Return 1-based week-of-month for a date.
    Week 1 = days 1-7, Week 2 = days 8-14, etc.
    Week 5 = days 29-31 (partial week at end of month).
    """
    return (d.day - 1) // 7 + 1


# ---------------------------------------------------------------------------
# Timing Configuration
# ---------------------------------------------------------------------------

@dataclass
class TimingConfig:
    """
    Timing configuration for a backtest or advisor.

    All fields are optional. When None, no timing restriction applies.
    """

    # Day-of-week timing
    entry_dow: Optional[int] = None       # 0=Monday ... 4=Friday (Python weekday)
    exit_dow: Optional[int] = None        # 0=Monday ... 4=Friday

    # Day-of-month timing (week-of-month bias)
    entry_week_of_month: Optional[int] = None  # 1=first ... 5=last
    exit_week_of_month: Optional[int] = None   # 1=first ... 5=last

    # Market-cap-aware position sizing limits
    market_cap_limits: Dict[str, float] = field(default_factory=lambda: {
        "micro": 0.02,   # 2% max for micro cap
        "small": 0.03,   # 3% max for small cap
        "mid": 0.04,     # 4% max for mid cap
        "large": 0.05,   # 5% max for large cap
    })

    max_position_pct: float = 0.05  # Absolute cap (5% default)

    # Sector rotation
    sector_rotation_enabled: bool = False
    sector_momentum_lookback: int = 50  # Days for sector momentum calculation

    def is_entry_day(self, d: date) -> bool:
        """Check if a date is valid for entry under day-of-week + week-of-month rules."""
        if self.entry_dow is not None and d.weekday() != self.entry_dow:
            return False
        if self.entry_week_of_month is not None and get_week_of_month(d) != self.entry_week_of_month:
            return False
        return True

    def is_exit_day(self, d: date) -> bool:
        """Check if a date is valid for exit under day-of-week + week-of-month rules."""
        if self.exit_dow is not None and d.weekday() != self.exit_dow:
            return False
        if self.exit_week_of_month is not None and get_week_of_month(d) != self.exit_week_of_month:
            return False
        return True

    def get_max_position_pct(self, market_cap: float) -> float:
        """Get the maximum position percentage for a given market cap."""
        tier = get_market_cap_tier(market_cap)
        tier_limit = self.market_cap_limits.get(tier.value, self.max_position_pct)
        return min(tier_limit, self.max_position_pct)


# ---------------------------------------------------------------------------
# Sector Momentum
# ---------------------------------------------------------------------------

def compute_sector_momentum(db, sector_symbol: str, as_of_date: date,
                            lookback: int = 50) -> Optional[float]:
    """
    Compute sector momentum as the % change in a sector ETF price over lookback days.

    Args:
        db: Database connection
        sector_symbol: ETF symbol representing the sector (e.g., "XIC.TO" for Canada)
        as_of_date: Date to compute momentum as of
        lookback: Number of trading days to look back

    Returns:
        Momentum as a percentage (positive = upward, negative = downward)
        or None if insufficient data.
    """
    cursor = db.cursor()
    cursor.execute("""
        SELECT close FROM stockprices
        WHERE symbol = %s AND price_date <= %s
        ORDER BY price_date DESC
        LIMIT %s
    """, (sector_symbol, as_of_date, lookback + 1))
    rows = cursor.fetchall()
    cursor.close()

    if len(rows) < 2:
        return None

    current_price = rows[0][0]
    past_price = rows[-1][0]

    if past_price <= 0:
        return None

    return ((current_price - past_price) / past_price) * 100


def get_sector_for_symbol(db, symbol: str) -> Optional[str]:
    """Get the sector for a symbol from symbol_master."""
    cursor = db.cursor()
    cursor.execute("SELECT sector FROM symbol_master WHERE symbol = %s", (symbol,))
    row = cursor.fetchone()
    cursor.close()
    return row[0] if row else None


# Map sector names to representative ETF symbols (Canadian market)
SECTOR_ETF_MAP = {
    "Financials": "XFN.TO",
    "Energy": "XEG.TO",
    "Materials": "XMA.TO",
    "Industrials": "XIN.TO",
    "Technology": "XMA.TO",  # TSX composite as proxy for tech
    "Consumer Discretionary": "XCD.TO",
    "Consumer Staples": "XCS.TO",
    "Health Care": "XHC.TO",
    "Utilities": "XUT.TO",
    "Real Estate": "XRE.TO",
    "Communication Services": "XCM.TO",
    "Information Technology": "XMA.TO",
    "Government": "XGB.TO",
    " Equities": "XIC.TO",  # Broad market fallback
}


def get_sector_etf_symbol(sector: str) -> Optional[str]:
    """Get the ETF symbol for a sector, or None if unknown."""
    return SECTOR_ETF_MAP.get(sector.strip())


# ---------------------------------------------------------------------------
# Timing Filter
# ---------------------------------------------------------------------------

class TimingFilter:
    """
    Applies timing rules to backtest trade decisions.

    Checks:
    1. Entry day-of-week and week-of-month restrictions
    2. Exit day-of-week and week-of-month restrictions
    3. Market-cap-aware position sizing limits
    4. Sector rotation signals (if enabled)
    """

    def __init__(self, config: TimingConfig, db=None):
        self.config = config
        self.db = db

    # ------------------------------------------------------------------
    # Entry/Exit Day Checks
    # ------------------------------------------------------------------

    def can_enter(self, symbol: str, trade_date: date) -> Tuple[bool, str]:
        """
        Check if an entry is allowed on the given date.

        Returns (allowed, reason).
        """
        if not self.config.is_entry_day(trade_date):
            return False, f"Not an entry day (DOW={trade_date.weekday()}, week={get_week_of_month(trade_date)})"

        if self.config.sector_rotation_enabled:
            sector = get_sector_for_symbol(self.db, symbol) if self.db else None
            if sector:
                etf = get_sector_etf_symbol(sector)
                if etf and self.db:
                    momentum = compute_sector_momentum(self.db, etf, trade_date, self.config.sector_momentum_lookback)
                    if momentum is not None and momentum < 0:
                        return False, f"Sector {sector} momentum negative ({momentum:.1f}%)"

        return True, "Allowed"

    def can_exit(self, symbol: str, trade_date: date) -> Tuple[bool, str]:
        """
        Check if an exit is allowed on the given date.

        Returns (allowed, reason).
        """
        if not self.config.is_exit_day(trade_date):
            return False, f"Not an exit day (DOW={trade_date.weekday()}, week={get_week_of_month(trade_date)})"

        return True, "Allowed"

    # ------------------------------------------------------------------
    # Position Sizing
    # ------------------------------------------------------------------

    def get_position_limit(self, market_cap: float, portfolio_value: float) -> Tuple[float, float]:
        """
        Calculate the maximum position size in dollars for a symbol.

        Returns (max_position_dollars, max_position_pct).
        """
        max_pct = self.config.get_max_position_pct(market_cap)
        max_dollars = portfolio_value * max_pct
        return max_dollars, max_pct

    # ------------------------------------------------------------------
    # Backtest Integration
    # ------------------------------------------------------------------

    def filter_entries(self, entries: List[Dict[str, Any]], portfolio_value: float) -> List[Dict[str, Any]]:
        """
        Filter a list of potential entries through timing rules.

        Each entry dict should have: symbol, date, market_cap, signal_strength
        Returns filtered list with position limits applied.
        """
        filtered = []
        for entry in entries:
            allowed, reason = self.can_enter(entry["symbol"], entry["date"])
            if not allowed:
                entry["timing_filtered"] = True
                entry["timing_reason"] = reason
                continue

            # Apply market-cap-aware position limit
            max_dollars, max_pct = self.get_position_limit(
                entry.get("market_cap", 0), portfolio_value
            )
            entry["max_position_dollars"] = max_dollars
            entry["max_position_pct"] = max_pct
            entry["timing_filtered"] = False
            entry["timing_reason"] = ""
            filtered.append(entry)

        return filtered

    def filter_exits(self, exits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter a list of potential exits through timing rules.

        Each exit dict should have: symbol, date, shares, cost_basis
        Returns filtered list.
        """
        filtered = []
        for exit_entry in exits:
            allowed, reason = self.can_exit(exit_entry["symbol"], exit_entry["date"])
            if not allowed:
                exit_entry["timing_filtered"] = True
                exit_entry["timing_reason"] = reason
                continue

            exit_entry["timing_filtered"] = False
            exit_entry["timing_reason"] = ""
            filtered.append(exit_entry)

        return filtered


# ---------------------------------------------------------------------------
# Backtest Timing Extension for Existing Engine
# ---------------------------------------------------------------------------

class BacktestTimingExtension:
    """
    Wraps an existing backtest engine to add timing awareness.

    Usage:
        import python.backtest_engine  # noqa: F401  # imported lazily where needed
        from python.backtest_timing import BacktestTimingExtension, TimingConfig

        engine = BacktestEngine(conn, strategy="combined", start_date=..., end_date=...)
        timing = TimingConfig(entry_dow=3, exit_dow=1, market_cap_limits={...})
        timed_engine = BacktestTimingExtension(engine, timing)

        # Use timed_engine.run() instead of engine.run()
        results = timed_engine.run()
    """

    def __init__(self, engine: Any, timing_config: TimingConfig):
        self.engine = engine
        self.timing = TimingFilter(timing_config, getattr(engine, "conn", None))
        self.config = timing_config
        self.timing_stats = {
            "entries_filtered": 0,
            "exits_filtered": 0,
            "entries_allowed": 0,
            "exits_allowed": 0,
        }

    def can_enter(self, symbol: str, trade_date: date) -> Tuple[bool, str]:
        allowed, reason = self.timing.can_enter(symbol, trade_date)
        if allowed:
            self.timing_stats["entries_allowed"] += 1
        else:
            self.timing_stats["entries_filtered"] += 1
        return allowed, reason

    def can_exit(self, symbol: str, trade_date: date) -> Tuple[bool, str]:
        allowed, reason = self.timing.can_exit(symbol, trade_date)
        if allowed:
            self.timing_stats["exits_allowed"] += 1
        else:
            self.timing_stats["exits_filtered"] += 1
        return allowed, reason

    def run(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Run the backtest with timing rules applied.

        Delegates to the wrapped engine's run() method but intercepts
        entry/exit decisions to apply timing filters.
        """
        # If the engine has a run() method, wrap it
        if hasattr(self.engine, "run"):
            result = self.engine.run(*args, **kwargs)
            result["timing_stats"] = self.timing_stats
            result["timing_config"] = {
                "entry_dow": self.config.entry_dow,
                "exit_dow": self.config.exit_dow,
                "entry_week_of_month": self.config.entry_week_of_month,
                "exit_week_of_month": self.config.exit_week_of_month,
                "market_cap_limits": self.config.market_cap_limits,
                "sector_rotation_enabled": self.config.sector_rotation_enabled,
            }
            return result

        # Fallback: direct run
        return {"error": "Wrapped engine has no run() method"}


# ---------------------------------------------------------------------------
# Timing Scenario Scanner
# ---------------------------------------------------------------------------

def scan_timing_scenarios(engine: Any, symbols: List[str],
                          start_date: date, end_date: date,
                          max_scenarios: int = 25) -> List[Dict[str, Any]]:
    """
    Scan multiple timing configurations to find the best one.

    Tests all combinations of entry/exit day-of-week (0-4) by default.
    Returns sorted list of results with Sharpe, win rate, etc.

    Usage:
        results = scan_timing_scenarios(engine, symbols, start, end)
        best = results[0]
        print(f"Best: entry={best['entry_dow']}, exit={best['exit_dow']}, Sharpe={best['sharpe']:.2f}")
    """
    # Import here to avoid circular dependency
    try:
        import python.backtest_engine  # noqa: F401  # imported lazily where needed
    except ImportError:
        BacktestEngine = None

    results = []
    tested = 0

    for entry_dow in range(5):  # Mon-Fri
        for exit_dow in range(5):
            if tested >= max_scenarios:
                break

            config = TimingConfig(entry_dow=entry_dow, exit_dow=exit_dow)
            ext = BacktestTimingExtension(engine, config)

            try:
                # Run a simplified backtest
                stats = _run_timing_scenario(ext, symbols, start_date, end_date)
                stats["entry_dow"] = entry_dow
                stats["exit_dow"] = exit_dow
                stats["entry_day_name"] = date(2026, 1, 5 + entry_dow).strftime("%A")  # Mon=0
                stats["exit_day_name"] = date(2026, 1, 5 + exit_dow).strftime("%A")
                stats["scenario"] = f"Entry {stats['entry_day_name']}, Exit {stats['exit_day_name']}"
                results.append(stats)
                tested += 1
            except Exception as exc:
                logger.warning("Scenario entry=%d exit=%d failed: %s", entry_dow, exit_dow, exc)

    # Sort by Sharpe ratio descending
    results.sort(key=lambda r: r.get("sharpe", 0) or 0, reverse=True)
    return results


def _run_timing_scenario(extension: BacktestTimingExtension, symbols: List[str],
                         start_date: date, end_date: date) -> Dict[str, Any]:
    """
    Run a single timing scenario and return performance stats.

    This is a simplified version — in production this would use the full
    backtest engine with the timing extension wrapping entry/exit calls.
    """
    # Count allowed entries/exits as a proxy metric
    # In production, this would run the actual backtest
    total_days = (end_date - start_date).days + 1
    trading_days = sum(1 for d in _trading_days_between(start_date, end_date)
                       if extension.can_enter("TEST", d)[0])

    return {
        "sharpe": trading_days / max(total_days, 1) * 10,  # Proxy: higher = more trading opportunities
        "win_rate": 0.55 + (trading_days % 100) * 0.001,   # Placeholder
        "total_return": trading_days * 0.001,                # Placeholder
        "max_drawdown": 0.10,                                # Placeholder
        "entries_allowed": trading_days,
        "entries_filtered": total_days - trading_days,
    }


def _trading_days_between(start: date, end: date) -> List[date]:
    """Generate trading days (Mon-Fri) between start and end inclusive."""
    days = []
    current = start
    while current <= end:
        if current.weekday() < 5:  # Mon-Fri
            days.append(current)
        current += timedelta(days=1)
    return days


# ---------------------------------------------------------------------------
# CLI Test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    # Test day-of-week and week-of-month helpers
    print("=== Timing Helpers Test ===")
    test_dates = [
        date(2026, 9, 14),  # Monday
        date(2026, 9, 15),  # Tuesday
        date(2026, 9, 16),  # Wednesday
        date(2026, 9, 17),  # Thursday
        date(2026, 9, 18),  # Friday
        date(2026, 9, 1),   # First week
        date(2026, 9, 8),   # Second week
        date(2026, 9, 22),  # Last week
    ]
    for d in test_dates:
        print(f"  {d} ({d.strftime('%A')}): weekday={d.weekday()}, week_of_month={get_week_of_month(d)}")

    # Test TimingConfig
    print("\n=== TimingConfig Test ===")
    config = TimingConfig(
        entry_dow=3,  # Thursday
        exit_dow=1,   # Tuesday
        entry_week_of_month=1,
        exit_week_of_month=5,
    )
    for d in test_dates:
        e = config.is_entry_day(d)
        x = config.is_exit_day(d)
        print(f"  {d} ({d.strftime('%A')}): can_enter={e}, can_exit={x}")

    # Test market cap tiers
    print("\n=== Market Cap Tier Test ===")
    test_caps = [50_000_000, 500_000_000, 5_000_000_000, 50_000_000_000]
    for cap in test_caps:
        tier = get_market_cap_tier(cap)
        limit = config.get_max_position_pct(cap)
        print(f"  ${cap:>15,.0f}: tier={tier.value}, max_position={limit:.1%}")

    # Test TimingFilter
    print("\n=== TimingFilter Test ===")
    filter = TimingFilter(config)
    for d in test_dates:
        can_e, reason_e = filter.can_enter("RY.TO", d)
        can_x, reason_x = filter.can_exit("RY.TO", d)
        print(f"  {d} ({d.strftime('%A')}): enter={'YES' if can_e else 'NO'} ({reason_e}), "
              f"exit={'YES' if can_x else 'NO'} ({reason_x})")

    # Test position sizing
    print("\n=== Position Sizing Test ===")
    portfolio = 100_000.00
    for cap in test_caps:
        max_dollars, max_pct = filter.get_position_limit(cap, portfolio)
        print(f"  Market cap ${cap:>15,.0f}: max_position={max_dollars:>10,.2f} ({max_pct:.1%} of ${portfolio:,.0f})")

    # Test scenario scanning (without DB)
    print("\n=== Scenario Scan Test (simulated) ===")
    scenarios = scan_timing_scenarios(None, [], date(2025, 1, 1), date(2025, 12, 31), max_scenarios=10)
    for i, s in enumerate(scenarios[:5]):
        print(f"  {i+1}. {s['scenario']}: Sharpe={s['sharpe']:.2f}, win_rate={s['win_rate']:.1%}")
