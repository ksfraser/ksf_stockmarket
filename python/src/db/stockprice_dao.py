"""
stockprice_dao.py — Data Access Object for stockprices writes.

Layer: Data (python/src/db/). Per ARCHITECTURE_PYTHON.md §2, this is
foundational — no business logic here, just CRUD against the stockprices table(s).

Responsibility:
  - Write OHLCV rows to the central stockprices table (ksfraser_stock_market.stockprices).
  - Optionally dual-write to the per-exchange stockprices table
    (ksfraser_sm_<exchange>.stockprices) when write_to_exchange_db=True.
  - Read price rows with exchange-aware routing (resolve symbol→exchange→DB).
  - All writes go through this DAO — no raw INSERT INTO stockprices in business
    scripts.

Storage-tier rule (see ARCHITECTURE_PYTHON.md §11, AGENTS.md):
  - This DAO is for DAILY OHLCV and historical loads — MySQL.
  - Sub-day / intraday data is NOT written here — that goes to SQLite
    price_intraday via the intraday sync path.

Exchange routing:
  - Reads use exchange_routing.resolve_exchange_for_symbol() to find the
    symbol's exchange, then connect to the exchange DB to read prices.
  - Writes always go to the CENTRAL db first (mandatory), then optionally
    to the exchange DB.
  - The nightly migrate_stockprices stored proc copies new central rows to
    exchange DBs as a backstop — dual-write is optional, not required.

Dual-write:
  - Default: write_to_exchange_db=False (central-only, let the proc sync).
  - Set write_to_exchange_db=True to also write to the exchange DB on every
    insert. Use sparingly — the proc is the canonical sync path.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional, Sequence

import pymysql

from db.exchange_routing import (
    EXCHANGE_DB_NAME_PREFIX,
    clear_symbol_exchange_cache,
    exchange_db_name,
    get_exchange_connection,
    normalise_exchange,
    resolve_exchange_db_name_for_symbol,
    resolve_exchange_for_symbol,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data transfer objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PriceRow:
    """One OHLCV row. All monetary values are Decimal to match the DB schema
    (DECIMAL(12,4)). None is allowed for optional fields (open, high, low,
    volume, adj_close, currency, dividend, split_ratio)."""

    symbol: str
    price_date: date
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    close: Optional[Decimal] = None
    volume: Optional[int] = None
    adj_close: Optional[Decimal] = None
    currency: Optional[str] = 'CAD'
    dividend: Optional[Decimal] = None
    split_ratio: Optional[Decimal] = None

    # Exchange metadata (resolved at write time, not stored in the row).
    # Kept here so batch writers can pass it through without re-resolving.
    exchange_raw: Optional[str] = None


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------


class StockPricesDAO:
    """Abstract data access object for stockprices writes and reads.

    Implementations:
      - CentralStockPricesDAO: writes to ksfraser_stock_market.stockprices
        (central DB), with optional dual-write to exchange DBs.
    """

    def write_prices(self, rows: Sequence[PriceRow]) -> int:
        """Insert or update OHLCV rows. Returns the number of rows affected.

        Uses INSERT ... ON DUPLICATE KEY UPDATE so re-runs are idempotent.
        The unique key is (symbol, price_date).
        """
        raise NotImplementedError

    def read_prices(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        exchange_db_name: Optional[str] = None,
    ) -> list[dict]:
        """Read price rows for *symbol*, optionally date-bounded.

        By default reads from the exchange DB for the symbol (resolved via
        symbol_master.exchange → ksfraser_sm_<exchange>.stockprices). Pass
        exchange_db_name to override, or pass a central-db connection to read
        from the central table directly.
        """
        raise NotImplementedError

    def bulk_read_prices(
        self,
        symbols: Sequence[str],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict[str, list[dict]]:
        """Read price rows for multiple symbols. Returns {symbol: [rows]}.

        Symbols without a resolved exchange are skipped with a warning.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Central DAO implementation
# ---------------------------------------------------------------------------


class CentralStockPricesDAO(StockPricesDAO):
    """Write to central stockprices, optionally dual-write to exchange DB.

    Constructor:
        central_db: an open pymysql connection to ksfraser_stock_market.
        write_to_exchange_db: if True, also write to the per-exchange DB.
        default_exchange: fallback exchange when symbol_master has no entry.
    """

    def __init__(
        self,
        central_db: pymysql.connections.Connection,
        *,
        write_to_exchange_db: bool = False,
        default_exchange: str = "tsx",
    ) -> None:
        self._central_db = central_db
        self._write_to_exchange = write_to_exchange_db
        self._default_exchange = default_exchange

        # Pre-built UPSERT SQL for the central table (compiled once).
        self._central_upsert = self._build_upsert_sql("stockprices")

        # Pre-built UPSERT SQL for the exchange table (same schema, different DB).
        if self._write_to_exchange:
            self._exchange_upsert = self._build_upsert_sql("stockprices")
        else:
            self._exchange_upsert = None

    # ------------------------------------------------------------------
    # SQL builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_upsert_sql(table_name: str) -> str:
        """Build the INSERT ... ON DUPLICATE KEY UPDATE SQL for stockprices.

        The column order is: symbol, price_date, open, high, low, close,
        volume, adj_close, currency, dividend, split_ratio.
        """
        cols = [
            "symbol",
            "price_date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adj_close",
            "currency",
            "dividend",
            "split_ratio",
        ]
        col_list = ", ".join(cols)
        val_placeholders = ", ".join(["%s"] * len(cols))
        update_clauses = ", ".join(f"{c}=VALUES({c})" for c in cols[2:])  # skip symbol, price_date (PK)
        return f"INSERT INTO {table_name} ({col_list}) VALUES ({val_placeholders}) ON DUPLICATE KEY UPDATE {update_clauses}"

    # ------------------------------------------------------------------
    # writes
    # ------------------------------------------------------------------

    def write_prices(self, rows: Sequence[PriceRow]) -> int:
        if not rows:
            return 0

        # Resolve exchanges for all symbols up front (single cache, single pass).
        # We need a central-db connection to look up symbol_master.exchange.
        clear_symbol_exchange_cache()
        resolved: dict[str, str] = {}  # symbol -> exchange_raw
        for row in rows:
            sym = row.symbol.upper()
            if sym not in resolved:
                try:
                    ex = resolve_exchange_for_symbol(
                        sym,
                        conn=self._central_db,
                        default_exchange=self._default_exchange,
                    )
                except Exception:
                    ex = self._default_exchange
                    logger.warning(
                        "write_prices: could not resolve exchange for %r, using default %r",
                        sym,
                        ex,
                        exc_info=True,
                    )
                resolved[sym] = ex

        # Build the value tuples in the exact column order the upsert SQL expects.
        # Column order: symbol, price_date, open, high, low, close, volume,
        #               adj_close, currency, dividend, split_ratio
        batches: dict[str, list[tuple]] = {}  # exchange_db_name -> rows
        central_rows: list[tuple] = []

        for row in rows:
            sym = row.symbol.upper()
            ex_raw = resolved.get(sym, self._default_exchange)
            ex_db_name = f"{EXCHANGE_DB_NAME_PREFIX}{normalise_exchange(ex_raw)}"

            # Build the value tuple.
            vals = (
                sym,
                row.price_date,
                row.open,
                row.high,
                row.low,
                row.close,
                row.volume,
                row.adj_close,
                row.currency,
                row.dividend,
                row.split_ratio,
            )
            central_rows.append(vals)

            # Dual-write: collect per-exchange-db batches.
            if self._write_to_exchange and self._exchange_upsert:
                batches.setdefault(ex_db_name, []).append(vals)

        # --- Central write (mandatory) ---
        total_affected = 0
        try:
            with self._central_db.cursor() as cur:
                cur.executemany(self._central_upsert, central_rows)
                self._central_db.commit()
                total_affected = cur.rowcount
            logger.info(
                "write_prices: central write — %d rows affected for %d symbols",
                total_affected,
                len({r[0] for r in central_rows}),
            )
        except Exception:
            self._central_db.rollback()
            logger.error(
                "write_prices: central write failed for %d rows — rolling back",
                len(central_rows),
                exc_info=True,
            )
            raise

        # --- Dual-write to exchange DBs (optional) ---
        if self._write_to_exchange and batches:
            for ex_db_name, ex_rows in batches.items():
                try:
                    ex_conn = get_exchange_connection(
                        ex_rows[0][0],  # symbol from first row
                        database=ex_db_name,
                    )
                    try:
                        with ex_conn.cursor() as cur:
                            cur.executemany(self._exchange_upsert, ex_rows)
                            ex_conn.commit()
                            affected = cur.rowcount
                        logger.info(
                            "write_prices: exchange write — %s: %d rows affected",
                            ex_db_name,
                            affected,
                        )
                        total_affected += affected
                    finally:
                        ex_conn.close()
                except Exception:
                    # Dual-write failure is non-fatal — the nightly migrate proc
                    # will pick up any missing rows. Log and continue.
                    logger.warning(
                        "write_prices: exchange write failed for %s (%d rows) — "
                        "nightly migrate proc will catch up",
                        ex_db_name,
                        len(ex_rows),
                        exc_info=True,
                    )

        return total_affected

    # ------------------------------------------------------------------
    # reads
    # ------------------------------------------------------------------

    def read_prices(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        exchange_db_name: Optional[str] = None,
        *,
        use_central: bool = False,
    ) -> list[dict]:
        """Read prices for *symbol*.

        By default reads from the exchange DB for the symbol (resolved via
        symbol_master.exchange → ksfraser_sm_<exchange>.stockprices).

        Pass *exchange_db_name* to override the exchange DB, or pass
        *use_central=True* to read from the central ksfraser_stock_market
        table directly (useful for cross-exchange queries or when the exchange
        DB may not exist yet).
        """
        sym = (symbol or "").strip().upper()
        if not sym:
            return []

        if use_central:
            # Read from central DB using the DAO's central connection.
            conditions: list[str] = ["symbol = %s"]
            params: list = [sym]
            if start_date is not None:
                conditions.append("price_date >= %s")
                params.append(start_date)
            if end_date is not None:
                conditions.append("price_date <= %s")
                params.append(end_date)
            where = " AND ".join(conditions) if conditions else "1=1"
            sql = f"SELECT symbol, price_date, open, high, low, close, volume, adj_close, currency, dividend, split_ratio FROM stockprices WHERE {where} ORDER BY price_date ASC"
            with self._central_db.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()

        db_name = exchange_db_name
        if db_name is None:
            db_name = resolve_exchange_db_name_for_symbol(
                sym, conn=self._central_db, default_exchange=self._default_exchange
            )

        try:
            ex_conn = get_exchange_connection(sym, database=db_name)
        except Exception:
            logger.warning(
                "read_prices: cannot connect to exchange DB %r for %r — returning empty",
                db_name,
                sym,
                exc_info=True,
            )
            return []

        try:
            conditions: list[str] = ["symbol = %s"]
            params: list = [sym]
            if start_date is not None:
                conditions.append("price_date >= %s")
                params.append(start_date)
            if end_date is not None:
                conditions.append("price_date <= %s")
                params.append(end_date)

            where = " AND ".join(conditions) if conditions else "1=1"
            sql = f"SELECT symbol, price_date, open, high, low, close, volume, adj_close, currency, dividend, split_ratio FROM stockprices WHERE {where} ORDER BY price_date ASC"

            with ex_conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()
        finally:
            ex_conn.close()

    def bulk_read_prices(
        self,
        symbols: Sequence[str],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict[str, list[dict]]:
        """Read prices for multiple symbols, routing each to its exchange DB.

        Returns {symbol: [rows]}. Symbols that fail to resolve or connect are
        omitted from the result with a warning logged.
        """
        result: dict[str, list[dict]] = {}
        for sym in symbols:
            rows = self.read_prices(sym, start_date=start_date, end_date=end_date)
            if rows:
                result[sym] = rows
            else:
                logger.debug("bulk_read_prices: no rows for %r", sym)
        return result


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------


def create_central_stockprice_dao(
    central_db: Optional[pymysql.connections.Connection] = None,
    *,
    write_to_exchange_db: bool = False,
    default_exchange: str = "tsx",
) -> CentralStockPricesDAO:
    """Create a CentralStockPricesDAO, opening the central connection if needed.

    If *central_db* is None, opens a connection to ksfraser_stock_market using
    the same env vars as db_connector (DB_HOST, DB_PORT, DB_USER, DB_PASS).
    """
    import os

    if central_db is None:
        central_db = pymysql.connect(
            host=os.environ.get("DB_HOST", "ksfraser.ca"),
            port=int(os.environ.get("DB_PORT", "3306")),
            user=os.environ.get("DB_USER", "ksfraser_stockmarket"),
            password=os.environ.get("DB_PASS", ""),
            database=os.environ.get("DB_NAME", "ksfraser_stock_market"),
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10,
            autocommit=False,
        )

    return CentralStockPricesDAO(
        central_db,
        write_to_exchange_db=write_to_exchange_db,
        default_exchange=default_exchange,
    )
