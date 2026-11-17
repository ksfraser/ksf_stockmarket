#!/usr/bin/env python3
"""
MariaDB implementation of StockPriceRepository.

Target table: stockprices (production schema).
Columns: symbol, price_date, open, high, low, close, volume,
         adj_close, dividend, split_ratio, currency, id
"""
from __future__ import annotations

import pymysql
from datetime import date
from typing import List, Optional, Sequence

from .stock_price_dto import StockPriceDTO
from .stock_price_repository import StockPriceRepository


class MariaDBStockPriceRepository(StockPriceRepository):
    _COLUMN_MAP = {
        "symbol": "symbol",
        "price_date": "price_date",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume",
        "adjusted_close": "adj_close",
        "dividend": "dividend",
        "split_ratio": "split_ratio",
        "currency": "currency",
    }

    _INSERT_SQL = """
        INSERT INTO stockprices
            (symbol, price_date, open, high, low, close, volume,
             adj_close, dividend, split_ratio, currency)
        VALUES
            (%(symbol)s, %(price_date)s, %(open)s, %(high)s, %(low)s, %(close)s,
             %(volume)s, %(adjusted_close)s, %(dividend)s, %(split_ratio)s, %(currency)s)
        ON DUPLICATE KEY UPDATE
            open       = VALUES(open),
            high       = VALUES(high),
            low        = VALUES(low),
            close      = VALUES(close),
            volume     = VALUES(volume),
            adj_close  = VALUES(adj_close),
            dividend   = VALUES(dividend),
            split_ratio= VALUES(split_ratio),
            currency   = VALUES(currency)
    """

    _SELECT_SQL = """
        SELECT symbol, price_date, open, high, low, close, volume,
               adj_close, dividend, split_ratio, currency
        FROM stockprices
        WHERE symbol = %s
          AND (%s IS NULL OR price_date >= %s)
          AND (%s IS NULL OR price_date <= %s)
        ORDER BY price_date ASC
    """

    _LATEST_SQL = """
        SELECT symbol, price_date, open, high, low, close, volume,
               adj_close, dividend, split_ratio, currency
        FROM stockprices
        WHERE symbol = %s
        ORDER BY price_date DESC
        LIMIT %s
    """

    _EXISTS_SQL = "SELECT 1 FROM stockprices WHERE symbol = %s AND price_date = %s"

    def __init__(self, host: str, user: str, password: str, database: str, **kwargs):
        self._cfg = dict(host=host, user=user, password=password, database=database,
                         charset=kwargs.get("charset", "utf8mb4"))
        try:
            with self._conn() as conn:
                self._validate_columns(conn)
        except Exception as exc:
            raise RuntimeError(
                f"MariaDBStockPriceRepository schema validation failed: {exc}"
            ) from exc

    def _conn(self) -> pymysql.connections.Connection:
        return pymysql.connect(**self._cfg)

    def _validate_columns(self, conn) -> None:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'stockprices'",
                (self._cfg["database"],),
            )
            existing = {row[0].lower() for row in cur.fetchall()}

        missing = {
            col for col in self._COLUMN_MAP.values()
            if col.lower() not in existing
        }
        if missing:
            raise RuntimeError(
                f"stockprices is missing expected columns: {sorted(missing)}"
            )

    @staticmethod
    def _row_to_dto(row) -> StockPriceDTO:
        return StockPriceDTO(
            symbol=row["symbol"],
            price_date=row["price_date"],
            open=row.get("open"),
            high=row.get("high"),
            low=row.get("low"),
            close=row.get("close"),
            volume=row.get("volume"),
            adjusted_close=row.get("adj_close"),
            day_change=None,
            bid=None,
            ask=None,
        )

    def save(self, dto: StockPriceDTO) -> None:
        self.save_all([dto])

    def save_all(self, dtos: Sequence[StockPriceDTO]) -> int:
        if not dtos:
            return 0
        rows = [self._dto_to_params(d) for d in dtos]
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.executemany(self._INSERT_SQL, rows)
                conn.commit()
        return len(rows)

    def get_latest(self, symbol: str, n: int = 1) -> List[StockPriceDTO]:
        with self._conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(self._LATEST_SQL, (symbol, n))
                rows = cur.fetchall()
        dtos = [self._row_to_dto(r) for r in rows]
        dtos.reverse()  # oldest→newest
        return dtos

    def get_by_range(
        self,
        symbol: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
    ) -> List[StockPriceDTO]:
        with self._conn() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(
                    self._SELECT_SQL,
                    (
                        symbol,
                        str(start) if start else None,
                        str(start) if start else None,
                        str(end) if end else None,
                        str(end) if end else None,
                    ),
                )
                rows = cur.fetchall()
        return [self._row_to_dto(r) for r in rows]

    def exists(self, symbol: str, price_date: date) -> bool:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(self._EXISTS_SQL, (symbol, str(price_date)))
                return cur.fetchone() is not None

    def is_stale(self, symbol: str, max_age_hours: float = 24.0) -> bool:
        latest = self.get_latest(symbol, 1)
        if not latest:
            return True
        from datetime import datetime, timedelta
        updated = datetime.combine(latest[0].price_date, datetime.min.time())
        return datetime.now() - updated > timedelta(hours=max_age_hours)

    def _dto_to_params(self, dto: StockPriceDTO) -> dict:
        return {
            "symbol": dto.symbol,
            "price_date": str(dto.price_date),
            "open": dto.open,
            "high": dto.high,
            "low": dto.low,
            "close": dto.close,
            "volume": dto.volume,
            "adjusted_close": dto.adjusted_close,
            "dividend": 0.0,
            "split_ratio": 1.0,
            "currency": dto.currency,
        }
