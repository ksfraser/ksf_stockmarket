#!/usr/bin/env python3
"""
SQLite implementation of StockPriceRepository.

Target table: price_intraday (open/high/low/close matching domain names).

Normalized storage contract:
  symbol      = canonical yfinance ticker (e.g. 'SU.TO', 'AW-UN.TO', 'V')
  base_symbol = instrument base (e.g. 'SU', 'AW')
  exchange    = 'TO' | 'V' | 'O' | 'X' | 'US'
  unit_class  = '' | 'UN' | 'B'  (trust/preferred class)

Every write is resolved through symbol_resolver so only ONE canonical spelling
ever lands in the table -- the source of the old 'SU' vs 'SU.TO' duplication bug.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from datetime import date
from typing import List, Optional, Sequence

from .stock_price_dto import StockPriceDTO
from .stock_price_repository import StockPriceRepository
from .connection import DataSource
from .symbol_resolver import resolve_for_yfinance, decompose_ticker


class SQLitePriceRepository(StockPriceRepository):
    _SQL_INSERT = """
        INSERT OR REPLACE INTO price_intraday
            (symbol, base_symbol, exchange, unit_class,
             price_date, open, high, low, close, volume, currency, dividend)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    _SQL_SELECT = """
        SELECT symbol, price_date, open, high, low, close, volume, currency, dividend
        FROM price_intraday
        WHERE symbol = ?
          AND (? IS NULL OR price_date >= ?)
          AND (? IS NULL OR price_date <= ?)
        ORDER BY price_date ASC
    """
    _SQL_LATEST = """
        SELECT symbol, price_date, open, high, low, close, volume, currency, dividend
        FROM price_intraday
        WHERE symbol = ?
        ORDER BY price_date DESC
        LIMIT ?
    """
    _SQL_EXISTS = """
        SELECT 1 FROM price_intraday
        WHERE symbol = ? AND price_date = ?
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_schema()

    def _conn(self) -> sqlite3.Connection:
        return DataSource.sqlite_connection(self.db_path)

    def _ensure_schema(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS price_intraday (
                    symbol      TEXT NOT NULL,
                    base_symbol TEXT,
                    exchange    TEXT,
                    unit_class  TEXT,
                    price_date  DATE NOT NULL,
                    open        REAL,
                    high        REAL,
                    low         REAL,
                    close       REAL,
                    volume      INTEGER,
                    currency    TEXT DEFAULT 'USD',
                    dividend    REAL DEFAULT 0.0,
                    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (symbol, price_date)
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_price_exchange "
                "ON price_intraday(exchange)"
            )
            conn.commit()

    @staticmethod
    def _resolve_parts(dto: StockPriceDTO):
        """Return (canonical_symbol, base_symbol, exchange, unit_class).

        Normalizes the stored ticker to the canonical yfinance spelling via
        resolve_for_yfinance so writes match reads (get_latest/get_by_range/exists
        all resolve the incoming symbol before querying). The fetcher passes the
        *raw* caller symbol, which for bare TSX bases (e.g. 'SU') differs from the
        canonical 'SU.TO' -- writing the raw form made those rows unreadable.

        This is SAFE with respect to dual-listed names: resolve_for_yfinance keeps
        NYSE twins bare (CM/RY -> CM/RY), so 'CM' and 'CM.TO' stay distinct and are
        never collapsed. The old "don't resolve here" rule was written against an
        earlier resolver that promoted bare symbols to .TO; that rule no longer
        exists, so normalizing on write is now correct and required.
        """
        canon = resolve_for_yfinance(dto.symbol)
        parts = decompose_ticker(canon)
        return canon, parts['base_symbol'], parts['exchange'], parts['unit_class']

    @staticmethod
    def _row_to_dto(row: sqlite3.Row) -> StockPriceDTO:
        return StockPriceDTO(
            symbol=row["symbol"],
            price_date=date.fromisoformat(row["price_date"]),
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row["volume"],
            currency=row["currency"] or "USD",
            dividend=row["dividend"] if "dividend" in row.keys() else 0.0,
        )

    def save(self, dto: StockPriceDTO) -> None:
        canon, base, ex, uc = self._resolve_parts(dto)
        with self._conn() as conn:
            conn.execute(
                self._SQL_INSERT,
                (
                    canon, base, ex, uc,
                    str(dto.price_date),
                    dto.open, dto.high, dto.low, dto.close,
                    dto.volume, dto.currency,
                    dto.dividend if dto.dividend is not None else 0.0,
                ),
            )

    def save_all(self, dtos: Sequence[StockPriceDTO]) -> int:
        count = 0
        with self._conn() as conn:
            for dto in dtos:
                canon, base, ex, uc = self._resolve_parts(dto)
                conn.execute(
                    self._SQL_INSERT,
                    (
                        canon, base, ex, uc,
                        str(dto.price_date),
                        dto.open, dto.high, dto.low, dto.close,
                        dto.volume, dto.currency,
                        dto.dividend if dto.dividend is not None else 0.0,
                    ),
                )
                count += 1
        return count

    def get_latest(self, symbol: str, n: int = 1) -> List[StockPriceDTO]:
        canon = resolve_for_yfinance(symbol)
        with self._conn() as conn:
            rows = conn.execute(self._SQL_LATEST, (canon, n)).fetchall()
        return [self._row_to_dto(r) for r in rows][::-1]

    def get_by_range(
        self,
        symbol: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
    ) -> List[StockPriceDTO]:
        canon = resolve_for_yfinance(symbol)
        with self._conn() as conn:
            rows = conn.execute(
                self._SQL_SELECT,
                (canon, str(start) if start else None, str(start) if start else None,
                 str(end) if end else None, str(end) if end else None),
            ).fetchall()
        return [self._row_to_dto(r) for r in rows]

    def exists(self, symbol: str, price_date: date) -> bool:
        canon = resolve_for_yfinance(symbol)
        with self._conn() as conn:
            row = conn.execute(self._SQL_EXISTS, (canon, str(price_date))).fetchone()
        return row is not None

    def is_stale(self, symbol: str, max_age_hours: float = 24.0) -> bool:
        """True if latest cached bar is older than max_age_hours."""
        latest = self.get_latest(symbol, 1)
        if not latest:
            return True
        from datetime import datetime, timedelta
        updated = datetime.combine(latest[0].price_date, datetime.min.time())
        return datetime.now() - updated > timedelta(hours=max_age_hours)
