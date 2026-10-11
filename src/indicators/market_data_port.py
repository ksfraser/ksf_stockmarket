"""
Dependency-Injection ports for external market data, plus no-network stub
implementations used by the test-suite.

The *concrete* yfinance-backed implementations live in
``src/common/market_data.py`` (the only sanctioned yf location per
``scripts/guard_standardized_access.py``). Everything here is pure interface +
canned data so tests never touch the network and never reach the data layer.
"""

from __future__ import annotations

from typing import Dict, List, Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class MarketDataPort(Protocol):
    def get_price_history(self, symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame: ...


@runtime_checkable
class FundamentalsPort(Protocol):
    def get_fundamentals(self, symbol: str) -> Dict: ...


@runtime_checkable
class NewsPort(Protocol):
    def get_news(self, symbol: str) -> Dict: ...


@runtime_checkable
class SectorDataPort(Protocol):
    """Returns the raw inputs ``SectorPerformanceAnalyzer`` needs (no scoring)."""

    def fetch_sector_inputs(self, sector: str) -> Dict: ...


@runtime_checkable
class IndexDataPort(Protocol):
    def get_vix(self) -> float: ...
    def get_index_history(self, symbol: str, period: str = "6mo") -> pd.DataFrame: ...


# --------------------------------------------------------------------------- #
# No-network stubs                                                             #
# --------------------------------------------------------------------------- #
def _stub_hist(prices) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=len(prices), freq="D")
    return pd.DataFrame(
        {
            "Open": prices, "High": [p * 1.01 for p in prices],
            "Low": [p * 0.99 for p in prices], "Close": prices,
            "Volume": [1_000_000] * len(prices),
        },
        index=idx,
    )


_STUB_PRICES = [100, 102, 101, 104, 107, 105, 110, 112, 109, 115,
                118, 116, 121, 120, 125, 128, 126, 131, 130, 135]


class StubMarketData:
    """Implements MarketDataPort + IndexDataPort with deterministic canned data."""

    def get_price_history(self, symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
        return _stub_hist(_STUB_PRICES)

    def get_index_history(self, symbol: str, period: str = "6mo") -> pd.DataFrame:
        return _stub_hist([p * 4 for p in _STUB_PRICES])

    def get_vix(self) -> float:
        return 18.0


class StubFundamentals:
    def get_fundamentals(self, symbol: str) -> Dict:
        return {
            "company_name": symbol, "sector": "Technology", "industry": "Software",
            "pe_trailing": 22.0, "pe_forward": 18.0, "peg_ratio": 1.1,
            "price_to_book": 4.0, "profit_margin": 0.20, "operating_margin": 0.25,
            "gross_margin": 0.70, "roe": 0.18, "roa": 0.10,
            "eps_trailing": 5.0, "eps_forward": 6.0, "book_value": 25.0,
            "dividend_yield": 1.5, "payout_ratio": 0.40,
            "free_cash_flow": 1_000_000_000, "market_cap": 50_000_000_000,
            "shares_outstanding": 1_000_000_000, "revenue_growth": 0.12,
            "beta": 1.1, "debt_to_equity": 0.8, "current_ratio": 2.0,
            "fcf_yield": 2.0,
        }


class StubNews:
    def get_news(self, symbol: str) -> Dict:
        return {
            "recent_news": [
                {"title": "Stub headline", "provider": "Test", "url": "http://x",
                 "summary": "summary", "days_ago": 1},
            ],
            "upcoming_events": [], "earnings": {}, "dividends": {},
        }


class StubSectorData:
    def fetch_sector_inputs(self, sector: str) -> Dict:
        etf_prices = [p * 1.5 for p in _STUB_PRICES]
        peers = ["PEER1", "PEER2"]
        return {
            "etf_symbol": "XLK", "etf_name": "Tech ETF", "etf_pe": 24.0,
            "etf_hist": _stub_hist(etf_prices),
            "etf_info": {"longName": "Tech ETF", "trailingPE": 24.0},
            "peers": [
                {"symbol": s, "name": s, "pe": 20.0, "div_yield": 1.0,
                 "roe": 0.15, "profit_margin": 0.18, "rev_growth": 0.10,
                 "hist": _stub_hist([p * (1.2 if s == "PEER1" else 0.9) for p in etf_prices])}
                for s in peers
            ],
        }
