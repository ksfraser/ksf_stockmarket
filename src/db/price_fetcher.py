#!/usr/bin/env python3
"""
Price fetcher interface + yFinance implementation.

Fetchers are external-data callers (yFinance, Google Finance, SEDAR, SEC, etc.).
They do NOT write to storage; they return normalized DTOs.
Storage is the repository's job.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

from .stock_price_dto import StockPriceDTO, to_ohlcv_dataframe

logger = logging.getLogger(__name__)


class PriceFetcher(ABC):
    """Fetch price data from an external source."""

    @abstractmethod
    def fetch_daily(self, symbols: List[str], lookback_days: int = 5,
                    interval: Optional[str] = None) -> List[StockPriceDTO]:
        """Return latest daily bars for symbols.

        ``interval`` is optional; when omitted the fetcher's configured
        interval (``self.interval``) is used.
        """


def _resolve(symbol: str) -> str:
    from python.src.symbol_resolver import resolve_for_yfinance
    return resolve_for_yfinance(symbol)


class YFinanceFetcher(PriceFetcher):
    """Fetches daily OHLCV from yfinance."""

    def __init__(self, period: str = "5d", interval: str = "1d"):
        self.period = period
        self.interval = interval

    def fetch_daily(
        self,
        symbols: List[str],
        lookback_days: int = 5,
        start: Optional[str] = None,
        end: Optional[str] = None,
        period: Optional[str] = None,
        interval: Optional[str] = None,
    ) -> List[StockPriceDTO]:
        if not symbols:
            return []

        tickers = " ".join(symbols)
        kwargs = dict(interval=interval or self.interval, auto_adjust=False, progress=False, threads=True)
        if start and end:
            kwargs.update(start=start, end=end)
        else:
            # Allow an explicit period override (e.g. '5y' for a deep backfill of
            # a newly inserted ticker); otherwise derive from lookback_days.
            use_period = period or self._lookback_to_period(max(1, lookback_days))
            kwargs.update(period=use_period)

        try:
            raw = yf.download(tickers, **kwargs)
        except Exception as exc:
            logger.error("Batch download failed: %s", exc)
            return []

        results: List[StockPriceDTO] = []

        if raw.empty:
            return results

        if isinstance(raw.columns, pd.MultiIndex):
            for sym in symbols:
                ticker = _resolve(sym)
                try:
                    df = raw.xs(ticker, level=1, axis=1).copy()
                except KeyError:
                    continue
                results.extend(self._dataframe_to_dtos(sym, df))
        else:
            if len(symbols) == 1 and not raw.empty:
                results.extend(self._dataframe_to_dtos(symbols[0], raw))

        return results

    @staticmethod
    def _lookback_to_period(lookback_days: int) -> str:
        if lookback_days <= 10:
            return f"{lookback_days}d"
        if lookback_days <= 60:
            return "1mo"
        if lookback_days <= 130:
            return "3mo"
        if lookback_days <= 370:
            return "1y"
        return "2y"

    def _dataframe_to_dtos(self, symbol: str, df: pd.DataFrame) -> List[StockPriceDTO]:
        df = df.dropna(subset=["Close"])
        if df.empty:
            return []

        df.index = pd.to_datetime(df.index)
        currency = "CAD" if _resolve(symbol).endswith(".TO") else "USD"
        dtos: List[StockPriceDTO] = []

        for dt, row in df.iterrows():
            price_date = dt.date().isoformat()
            if isinstance(price_date, str):
                from datetime import datetime as _dt
                price_date = _dt.strptime(price_date, "%Y-%m-%d").date()

            dtos.append(StockPriceDTO(
                symbol=symbol,
                price_date=price_date,
                open=round(float(row["Open"]), 4) if pd.notna(row["Open"]) else None,
                high=round(float(row["High"]), 4) if pd.notna(row["High"]) else None,
                low=round(float(row["Low"]), 4) if pd.notna(row["Low"]) else None,
                close=round(float(row["Close"]), 4) if pd.notna(row["Close"]) else None,
                volume=int(row["Volume"]) if pd.notna(row["Volume"]) else None,
                adjusted_close=round(float(row["Adj Close"]), 4) if pd.notna(row["Adj Close"]) else None,
                dividend=round(float(row["Dividends"]), 6) if pd.notna(row.get("Dividends", None)) else 0.0,
                split_ratio=round(float(row["Stock Splits"]), 4) if pd.notna(row.get("Stock Splits", None)) else 1.0,
                currency=currency,
            ))

        return dtos

    # ── Extended accessors ──────────────────────────────────────────────────
    # Raw yfinance stays centralized HERE (the only module the standardized-
    # access guard allowlists for yfinance). Scripts must call the
    # src/common/market_data.py façade instead of touching yfinance directly.

    def fetch_ohlcv_dataframe(self, symbol: str, period: str = "5d", interval: str = "1d") -> "pd.DataFrame":
        """Return a tz-naive, Date-indexed OHLCV DataFrame for one symbol."""
        dtos = self.fetch_daily([symbol], lookback_days=5, period=period, interval=interval)
        return to_ohlcv_dataframe(dtos)

    def fetch_info(self, symbol: str) -> dict:
        try:
            return dict(yf.Ticker(symbol).info or {})
        except Exception as exc:
            logger.error("fetch_info failed for %s: %s", symbol, exc)
            return {}

    def fetch_options(self, symbol: str) -> List[str]:
        try:
            exps = yf.Ticker(symbol).options
            return list(exps) if exps else []
        except Exception:
            return []

    def fetch_option_chain(self, symbol: str, expiration: str):
        try:
            chain = yf.Ticker(symbol).option_chain(expiration)
            return chain.calls, chain.puts
        except Exception as exc:
            logger.error("fetch_option_chain failed for %s/%s: %s", symbol, expiration, exc)
            return pd.DataFrame(), pd.DataFrame()

    def fetch_news(self, symbol: str) -> List[dict]:
        try:
            news = yf.Ticker(symbol).news
            return list(news) if news else []
        except Exception:
            return []

    def fetch_earnings_dates(self, symbol: str) -> "pd.DataFrame":
        try:
            ed = yf.Ticker(symbol).earnings_dates
            return ed if ed is not None else pd.DataFrame()
        except Exception:
            return pd.DataFrame()
