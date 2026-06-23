"""Unit tests for advisor base and strategies."""

from __future__ import annotations

import datetime
import sys
import os

# Ensure repo root and python/src are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'python', 'src'))

import pytest
from advisors.base import AdvisorBase, Signal
from advisors.strategies import (
    BuffettQualityStrategy,
    DividendGrowthStrategy,
    MomentumStrategy,
)


@pytest.fixture()
def db():
    from tests.conftest import get_test_db, cleanup_test_data
    conn = get_test_db()
    yield conn
    cleanup_test_data(conn)
    conn.close()


def _seed_buffett_data(db, symbol: str = 'AAPL') -> None:
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO fundamentals (symbol, fetch_date, roe, debt_to_equity, market_cap, gross_margin) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (symbol, '2025-01-01', 18.0, 30.0, 50_000_000_000, 40.0),
        )
        rows = []
        for i in range(260):
            d = datetime.date(2025, 1, 1) + datetime.timedelta(days=i)
            rows.append((
                symbol, str(d), 150.0 + i * 0.1, 151.0 + i * 0.1, 149.0 + i * 0.1, 150.5 + i * 0.1, 1_000_000
            ))
        cur.executemany(
            "REPLACE INTO stockprices (symbol, price_date, open, high, low, close, volume) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            rows,
        )
    db.commit()


def _seed_dividend_data(db, symbol: str = 'RY') -> None:
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO fundamentals (symbol, fetch_date, dividend_yield) VALUES (%s, %s, %s)",
            (symbol, '2025-01-01', 0.035),
        )
        rows = []
        for year in range(2020, 2026):
            amount = 6.0 - (year - 2020) * 0.2
            for q in range(4):
                d = datetime.date(year, 3 + q * 3, 15)
                rows.append((symbol, str(d), amount))
        cur.executemany(
            "REPLACE INTO dividends (symbol, ex_date, amount) VALUES (%s,%s,%s)",
            rows,
        )
        rows2 = []
        for i in range(800):
            d = datetime.date(2022, 1, 1) + datetime.timedelta(days=i)
            rows2.append((symbol, str(d), 100.0 + i * 0.05, 500_000))
        cur.executemany(
            "REPLACE INTO stockprices (symbol, price_date, close, volume) VALUES (%s,%s,%s,%s)",
            rows2,
        )
    db.commit()


def _seed_momentum_data(db, symbol: str = 'MSFT') -> None:
    rows = []
    for i in range(300):
        d = datetime.date(2025, 1, 1) + datetime.timedelta(days=i)
        rows.append((symbol, str(d), 200.0 + i * 0.2, 2_000_000))
    with db.cursor() as cur:
        cur.executemany(
            "REPLACE INTO stockprices (symbol, price_date, close, volume) VALUES (%s,%s,%s,%s)",
            rows,
        )
    db.commit()


class TestAdvisorBase:
    def test_signal_to_dict(self) -> None:
        sig = Signal(symbol="AAPL", action="BUY", weight=0.5, reason="strong", confidence=0.9, meta={"rank": 1})
        d = sig.to_dict()
        assert d["symbol"] == "AAPL"
        assert d["action"] == "BUY"
        assert d["meta"]["rank"] == 1

    def test_should_run_daily(self, db) -> None:
        adv = AdvisorBase(db, config={"schedule": "daily"})
        assert adv.should_run_today(datetime.date(2025, 5, 19))

    def test_should_run_weekly(self, db) -> None:
        adv = AdvisorBase(db, config={"schedule": "monday"})
        assert adv.should_run_today(datetime.date(2025, 5, 19))  # assumed Monday
        assert not adv.should_run_today(datetime.date(2025, 5, 20))

    def test_generate_signals_empty(self, db) -> None:
        adv = AdvisorBase(db, config={"schedule": "daily"})
        adv.slug = "test"
        signals = adv.generate_signals(datetime.date(2025, 5, 19))
        assert signals == []

    def test_on_run_hooks(self, db, caplog) -> None:
        import logging
        caplog.set_level(logging.INFO)
        adv = AdvisorBase(db, config={"schedule": "daily"})
        adv.slug = "test"
        adv.on_run_start(datetime.date(2025, 5, 19))
        assert "starting" in caplog.text.lower()


class TestBuffettQualityStrategy:
    def test_select_universe_returns_candidates(self, db) -> None:
        _seed_buffett_data(db)
        strategy = BuffettQualityStrategy(db, config={"schedule": "daily"})
        universe = strategy.select_universe(datetime.date(2025, 5, 19))
        assert "AAPL" in universe

    def test_select_universe_rejects_low_roe(self, db) -> None:
        _seed_buffett_data(db, symbol="BAD")
        with db.cursor() as cur:
            cur.execute(
                "UPDATE fundamentals SET roe = 5.0 WHERE symbol = 'BAD'",
            )
        db.commit()
        strategy = BuffettQualityStrategy(db, config={"schedule": "daily"})
        universe = strategy.select_universe(datetime.date(2025, 5, 19))
        assert "BAD" not in universe

    def test_score_returns_positive(self, db) -> None:
        _seed_buffett_data(db)
        strategy = BuffettQualityStrategy(db, config={"schedule": "daily"})
        score = strategy.score("AAPL", datetime.date(2025, 5, 19))
        assert score > 0

    def test_generate_signals_ranks(self, db) -> None:
        _seed_buffett_data(db, symbol="AAPL")
        _seed_buffett_data(db, symbol="MSFT")
        strategy = BuffettQualityStrategy(db, config={"schedule": "daily"})
        signals = strategy.generate_signals(datetime.date(2025, 5, 19), max_positions=2)
        assert len(signals) == 2
        assert signals[0].action == "BUY"
        assert signals[0].meta["rank"] == 1


class TestDividendGrowthStrategy:
    def test_select_universe_returns_candidates(self, db) -> None:
        _seed_dividend_data(db)
        strategy = DividendGrowthStrategy(db, config={"schedule": "daily", "lookback_days": 365 * 6})
        universe = strategy.select_universe(datetime.date(2025, 5, 19))
        assert "RY" in universe

    def test_generate_signals(self, db) -> None:
        _seed_dividend_data(db)
        strategy = DividendGrowthStrategy(db, config={"schedule": "daily", "lookback_days": 365 * 6})
        signals = strategy.generate_signals(datetime.date(2025, 5, 19), max_positions=5)
        assert len(signals) >= 1
        assert signals[0].action == "BUY"


class TestMomentumStrategy:
    def test_select_universe_filters(self, db) -> None:
        _seed_momentum_data(db)
        strategy = MomentumStrategy(db, config={"schedule": "daily"})
        universe = strategy.select_universe(datetime.date(2025, 5, 19))
        assert "MSFT" in universe

    def test_generate_signals(self, db) -> None:
        _seed_momentum_data(db)
        strategy = MomentumStrategy(db, config={"schedule": "daily"})
        signals = strategy.generate_signals(datetime.date(2025, 5, 19), max_positions=5)
        assert len(signals) >= 1
