"""Concrete advisor strategies with real selection logic."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from advisors.base import AdvisorBase, Signal

logger = logging.getLogger(__name__)

_DEFAULTS = {
    "buffett": {
        "min_market_cap": 10_000_000_000,
        "min_roe": 15.0,
        "max_debt_ratio": 50.0,
        "lookback_days": 365,
    },
    "dividend_growth": {
        "min_yield": 2.0,
        "max_yield": 6.0,
        "max_payout_ratio": 60.0,
        "min_consecutive_years": 5,
        "lookback_days": 365 * 3,
    },
    "momentum": {
        "lookback_days": 252,
        "momentum_window": 20,
        "min_price": 5.0,
        "min_volume": 200_000,
        "max_positions": 15,
    },
}


class BuffettQualityStrategy(AdvisorBase):
    name = "Buffett Quality"
    slug = "buffett_quality"

    def select_universe(self, run_date: date) -> list[str]:
        cfg = {**_DEFAULTS["buffett"], **self.config}
        with self.db.cursor() as cur:
            cur.execute(
                f"""
                SELECT f.symbol
                FROM {self._t('fundamentals')} f
                LEFT JOIN {self._t('stockprices')} p ON p.symbol = f.symbol AND p.price_date <= %s
                WHERE f.fetch_date >= %s
                  AND f.roe IS NOT NULL
                  AND f.debt_to_equity IS NOT NULL
                  AND f.market_cap >= %s
                  AND f.roe >= %s
                  AND f.debt_to_equity <= %s
                  AND p.symbol IS NOT NULL
                GROUP BY f.symbol
                """,
                (
                    run_date,
                    run_date - timedelta(days=cfg["lookback_days"]),
                    cfg["min_market_cap"],
                    cfg["min_roe"],
                    cfg["max_debt_ratio"],
                ),
            )
            return [r["symbol"] for r in cur.fetchall()]

    def score(self, symbol: str, run_date: date) -> float:
        cfg = {**_DEFAULTS["buffett"], **self.config}
        with self.db.cursor() as cur:
            cur.execute(
                f"""
                SELECT roe, debt_to_equity, market_cap, gross_margin
                FROM {self._t('fundamentals')}
                WHERE symbol = %s
                  AND fetch_date >= %s
                ORDER BY fetch_date DESC
                LIMIT 1
                """,
                (symbol, run_date - timedelta(days=cfg["lookback_days"])),
            )
            row = cur.fetchone()
        if not row:
            return 0.0
        score = 0.0
        score += min(row["roe"] or 0, 30.0) * 2.0
        score += max(0.0, 100.0 - (row["debt_to_equity"] or 100.0)) * 0.5
        if row.get("market_cap"):
            score += 10.0
        if row.get("gross_margin"):
            score += row["gross_margin"] * 1.0
        return score


class DividendGrowthStrategy(AdvisorBase):
    name = "Dividend Growth"
    slug = "dividend_growth"

    def select_universe(self, run_date: date) -> list[str]:
        cfg = {**_DEFAULTS["dividend_growth"], **self.config}
        with self.db.cursor() as cur:
            cur.execute(
                f"""
                SELECT f.symbol
                FROM {self._t('fundamentals')} f
                WHERE f.fetch_date >= %s
                  AND f.dividend_yield IS NOT NULL
                  AND f.dividend_yield BETWEEN %s AND %s
                """,
                (
                    run_date - timedelta(days=cfg["lookback_days"]),
                    cfg["min_yield"],
                    cfg["max_yield"],
                ),
            )
            return [r["symbol"] for r in cur.fetchall()]

    def score(self, symbol: str, run_date: date) -> float:
        cfg = {**_DEFAULTS["dividend_growth"], **self.config}
        earliest = run_date - timedelta(days=cfg["lookback_days"])
        with self.db.cursor() as cur:
            cur.execute(
                f"""
                SELECT amount, ex_date
                FROM {self._t('dividends')}
                WHERE symbol = %s AND ex_date BETWEEN %s AND %s
                ORDER BY ex_date DESC
                """,
                (symbol, earliest, run_date),
            )
            rows = cur.fetchall()
        if not rows:
            return 0.0
        years: dict[int, float] = {}
        for r in rows:
            y = r["ex_date"].year
            years[y] = years.get(y, 0.0) + float(r["amount"])
        unique_years = sorted(years.items(), reverse=True)
        if len(unique_years) < cfg["min_consecutive_years"]:
            return 0.0
        consecutive = 0
        prev = None
        for _, total in unique_years:
            if prev is not None and total <= prev:
                break
            consecutive += 1
            prev = total
        if consecutive < cfg["min_consecutive_years"]:
            return 0.0
        base = float(unique_years[0][1]) / float(unique_years[-1][1] or 1)
        return 50.0 + (base * 30.0) + (consecutive * 2.0)


class MomentumStrategy(AdvisorBase):
    name = "Momentum"
    slug = "momentum"

    def select_universe(self, run_date: date) -> list[str]:
        cfg = {**_DEFAULTS["momentum"], **self.config}
        start = run_date - timedelta(days=cfg["lookback_days"])
        cutoff = run_date - timedelta(days=cfg["momentum_window"])
        with self.db.cursor() as cur:
            cur.execute(
                f"""
                SELECT symbol,
                       MIN(close) AS older,
                       MAX(close) AS newer,
                       AVG(volume) AS avg_volume
                FROM {self._t('stockprices')}
                WHERE price_date BETWEEN %s AND %s
                GROUP BY symbol
                HAVING avg_volume >= %s
                   AND newer >= %s
                """,
                (start, cutoff, cfg["min_volume"], cfg["min_price"]),
            )
            return [r["symbol"] for r in cur.fetchall()]

    def score(self, symbol: str, run_date: date) -> float:
        cfg = {**_DEFAULTS["momentum"], **self.config}
        start = run_date - timedelta(days=cfg["lookback_days"])
        cutoff = run_date - timedelta(days=cfg["momentum_window"])
        with self.db.cursor() as cur:
            cur.execute(
                f"""
                SELECT close
                FROM {self._t('stockprices')}
                WHERE symbol = %s AND price_date BETWEEN %s AND %s
                ORDER BY price_date ASC
                """,
                (symbol, start, cutoff),
            )
            rows = [float(r["close"]) for r in cur.fetchall()]
        if len(rows) < 2:
            return 0.0
        momentum = (rows[-1] - rows[0]) / rows[0] * 100.0
        return max(momentum, 0.0)
