"""
exchange_routing.py — Exchange-to-database routing for the stockprices split.

Architecture:
  - symbol_master.exchange  →  normalise_exchange()  →  ksfraser_sm_<normalised>
  - Today all exchanges share host=ksfraser.ca, user=ksfraser_stockmarket.
  - The database name is the only variable (see exchange_db_name()).

Storage-tier rule (see docs/ARCHITECTURE_PYTHON.md §11 and AGENTS.md):
  - Sub-day / intraday data  →  SQLite (price_intraday), never MySQL.
  - Daily OHLCV + fundamentals + calculated values  →  MySQL, unless the
    value is only valid for the day (e.g. an intraday signal that resets).
  - All MySQL writes go through a StockPricesDAO / repository — no raw SQL
    in business scripts.

Exchange normalisation:
  - The stored procs do REPLACE(exchange, '.', '_'). We mirror that so the
    code and the procs stay consistent.
  - TSX.V  →  tsx_v  (the only period-bearing exchange today).
  - Future odd exchange names (hyphens, spaces, etc.) fall through the same
    sanitise_exchange_name() pipeline; if a name still isn't DB-safe after
    normalisation, that's a configuration error caught at connect time.

Multi-host / per-exchange host-user-db lookup:
  - Today: every exchange lives on ksfraser.ca / ksfraser_stockmarket.
  - The get_exchange_connection() function has a documented stub in its
    except block for when we need per-exchange (host, user, password, database).
  - When that day comes, the intended sources (pick one, keep others commented):
      (a) DB table  ksf_exchange_routing(exchange_raw, host, user, password, database, active)
      (b) JSON file  config/exchange_routing.json  (loaded at startup, watched)
      (c) env vars   DB_HOST_<EXCHANGE>, DB_USER_<EXCHANGE>, DB_NAME_<EXCHANGE>
  - The ksfraser_ prefix is retained even if we move back to self-hosting, to
    keep the move impact minimal. If a future provider removes the prefix
    requirement we can strip it in this layer (one place).

Connection sharing:
  - Exchange connections reuse the same credentials as the central connector
    (db_connector.get_connection() / env vars DB_USER, DB_NAME, DB_PASS, DB_HOST).
  - We read those env vars directly rather than importing db_connector, because
    db_connector lives at python/db_connector.py (repo root) while this module
    lives at python/src/db/ and the two are not on the same import path. The
    credential source of truth is the environment, which is shared — that is
    what "use the common connector" means here: one source of truth for
    credentials, no hardcoded passwords.
  - If db_connector ever changes its credential source, update _default_host(),
    _default_user(), _default_password() to match (one place).
"""

from __future__ import annotations

import logging
import os
import re
from typing import Optional

import pymysql  # only used in the connect path; not imported at module import by callers

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Credential source of truth (shared with the central connector)
# ---------------------------------------------------------------------------

# These read the same env vars as python/db_connector.get_connection(), so
# there is exactly one source of truth for credentials. No password is
# hardcoded here. If db_connector changes how it sources credentials, mirror
# the change here.


def _default_host() -> str:
    return os.environ.get("DB_HOST", "ksfraser.ca")


def _default_port() -> int:
    try:
        return int(os.environ.get("DB_PORT", "3306"))
    except ValueError:
        return 3306


def _default_user() -> str:
    return os.environ.get("DB_USER", "ksfraser_stockmarket")


def _default_password() -> str:
    return os.environ.get("DB_PASS", "")


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

# Characters that are legal in MySQL identifiers but unusual in exchange names.
# We keep alphanumerics and underscores; everything else becomes an underscore.
_EXCHANGE_SANITISE_RE = re.compile(r"[^A-Za-z0-9_]+")

# Prefix applied to every exchange database name. Retained even if we move back
# to self-hosting, to minimise moving impact. If a future provider removes the
# prefix requirement, strip it here (one place).
EXCHANGE_DB_NAME_PREFIX = "ksfraser_sm_"


def normalise_exchange(raw: str) -> str:
    """Normalise a raw exchange name into a DB-safe suffix.

    Mirrors the stored-proc logic: REPLACE(exchange, '.', '_'), plus a broader
    sanitisation so future odd exchange names don't produce invalid database
    names.

    Examples:
        TSX.V   →  tsx_v
        TSX     →  tsx
        NYSE    →  nyse
        "TSX.V" →  tsx_v   (whitespace trimmed)
    """
    if not raw:
        raise ValueError("exchange name must not be empty")
    s = raw.strip().lower()
    # Mirror the stored proc: period → underscore.
    s = s.replace(".", "_")
    # Collapse any other non-identifier characters to a single underscore.
    s = _EXCHANGE_SANITISE_RE.sub("_", s)
    # Collapse runs of underscores and trim edges.
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        raise ValueError(f"exchange name normalised to empty string: {raw!r}")
    if s != raw.strip().lower():
        logger.info("normalise_exchange: %r -> %r", raw, s)
    return s


def exchange_db_name(exchange_raw: str) -> str:
    """Return the database name for an exchange.

    Formulaic routing:  ksfraser_sm_<normalised_exchange>

    Examples:
        TSX.V   →  ksfraser_sm_tsx_v
        TSX     →  ksfraser_sm_tsx
        NYSE    →  ksfraser_sm_nyse
    """
    return f"{EXCHANGE_DB_NAME_PREFIX}{normalise_exchange(exchange_raw)}"


# ---------------------------------------------------------------------------
# Symbol → exchange resolution
# ---------------------------------------------------------------------------

# Cache of (symbol, default_exchange) -> raw exchange name, populated by
# resolve_exchange_for_symbol(). Cleared when the caller wants a fresh lookup.
_symbol_exchange_cache: dict[str, str] = {}


def clear_symbol_exchange_cache() -> None:
    """Drop the symbol→exchange cache. Call when symbol_master may have changed."""
    _symbol_exchange_cache.clear()


def resolve_exchange_for_symbol(
    symbol: str,
    *,
    conn: Optional[pymysql.connections.Connection] = None,
    default_exchange: str = "tsx",
) -> str:
    """Return the raw exchange name for *symbol* from symbol_master.

    Looks up symbol_master.exchange. If the symbol isn't in symbol_master, or
    symbol_master has no exchange for it, returns *default_exchange*.

    Results are cached per call-session so repeated lookups for the same symbol
    with the same *default_exchange* don't hit the DB. Call
    clear_symbol_exchange_cache() when symbol_master may have changed, or when
    the default changes and you want a fresh lookup.
    """
    sym = (symbol or "").strip().upper()
    if not sym:
        return default_exchange
    cache_key = (sym, default_exchange)
    if cache_key in _symbol_exchange_cache:
        return _symbol_exchange_cache[cache_key]

    raw_exchange: str = default_exchange
    if conn is not None:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT exchange FROM symbol_master WHERE symbol = %s",
                    (sym,),
                )
                row = cur.fetchone()
            if row and row["exchange"]:
                raw_exchange = str(row["exchange"]).strip() or default_exchange
        except Exception:
            # If we can't look up the exchange, fall back to the default.
            # The caller (repository) will still write to the central DB, so
            # this is non-fatal — we just route the exchange-db write to the
            # default exchange DB instead of the correct one.
            logger.warning(
                "resolve_exchange_for_symbol: lookup failed for %r, using default %r",
                sym,
                default_exchange,
                exc_info=True,
            )

    _symbol_exchange_cache[sym] = raw_exchange
    return raw_exchange


# ---------------------------------------------------------------------------
# Connection routing
# ---------------------------------------------------------------------------

# Default host and credentials source. Today all exchanges live on the same
# host/user as the central database. When exchanges are split across hosts, this
# is the layer that changes (see the except stub below).


def get_exchange_connection(
    symbol: str,
    *,
    conn: Optional[pymysql.connections.Connection] = None,
    default_exchange: str = "tsx",
    database: Optional[str] = None,
) -> pymysql.connections.Connection:
    """Return a live connection to the exchange database for *symbol*.

    Today this means:
        host     = ksfraser.ca
        port     = 3306 (from DB_PORT env, default 3306)
        user     = ksfraser_stockmarket (from DB_USER env)
        password = DB_PASS (same as central connector)
        database = ksfraser_sm_<normalised exchange for symbol>

    If *database* is passed explicitly, it is used as the database name
    (useful for testing or for when the caller has already resolved the
    exchange DB name).

    .. _multi_host_stub:

    **Future multi-host / per-exchange host-user-db lookup (STUB)**

    When exchanges move to separate hosts or separate DB users, this function
    is the place to resolve (host, user, password, database) per exchange.
    The intended sources, in order of preference (pick one, keep others
    commented for reference):

    (a) DB table  ``ksf_exchange_routing``
        ``CREATE TABLE ksf_exchange_routing (
            exchange_raw VARCHAR(50) PRIMARY KEY,
            host VARCHAR(100) NOT NULL,
            user VARCHAR(100) NOT NULL,
            password VARCHAR(255) NOT NULL,
            database VARCHAR(100) NOT NULL,
            active TINYINT DEFAULT 1,
            INDEX idx_active (active)
        )``
        Looked up once per exchange and cached. The routing table lives on the
        central DB so every writer sees the same mapping. Password stored
        encrypted at rest (ksf_crypto) or via Ansible Vault at deploy time.

    (b) JSON file  ``config/exchange_routing.json``
        Loaded at process start and re-read on SIGHUP or a file-watch polling
        loop. Good when the routing lives with the app config rather than the
        DB. Format::

            { "TSX.V": {"host": "ksfraser.ca", "user": "ksfraser_stockmarket",
                         "database": "ksfraser_sm_tsx_v"},
              "NYSE":  {"host": "db2.example.com", "user": "ksf_nyse",
                         "database": "ksf_nyse_prices"} }

    (c) Environment variables
        ``DB_HOST_<EXCHANGE>``, ``DB_USER_<EXCHANGE>``, ``DB_NAME_<EXCHANGE>``
        where ``<EXCHANGE>`` is the normalised exchange name uppercased. Simple
        but noisy; good for a small number of split exchanges.

    The stub below catches connection failures and logs where the lookup would
    go. It does NOT try any of the above today — those are future paths. When
    we activate one, replace the ``except`` block contents with the lookup and
    retry, and remove the stub comment.
    """
    if database:
        db_name = database
    else:
        raw_ex = resolve_exchange_for_symbol(
            symbol, conn=conn, default_exchange=default_exchange
        )
        db_name = exchange_db_name(raw_ex)

    try:
        return pymysql.connect(
            host=_default_host(),
            port=_default_port(),
            user=_default_user(),
            password=_default_password(),
            database=db_name,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10,
            autocommit=False,
        )
    except Exception as exc:
        # -- multi_host_stub -------------------------------------------------
        # Connection failed. Today this means either the exchange DB doesn't
        # exist yet, or the credentials are wrong, or we're offline. In the
        # future this is where we'd look up (host, user, password, database)
        # from the routing source described above and retry once.
        #
        # Placeholder for when we activate a routing source:
        #
        #   try:
        #       route = lookup_exchange_route(raw_ex)  # (a) table / (b) json / (c) env
        #   except Exception as route_exc:
        #       logger.error("cannot resolve routing for %r: %s", raw_ex, route_exc)
        #       raise exc  # give up, surface the original connection error
        #
        #   try:
        #       return pymysql.connect(
        #           host=route["host"], port=route.get("port", 3306),
        #           user=route["user"], password=route["password"],
        #           database=route["database"], charset="utf8mb4",
        #           cursorclass=pymysql.cursors.DictCursor,
        #           connect_timeout=10, autocommit=False,
        #       )
        #   except Exception as retry_exc:
        #       logger.error("routing lookup succeeded but connect failed for %r: %s",
        #                    raw_ex, retry_exc)
        #       raise
        #
        # Today: log and re-raise so the caller (repository) can decide whether
        # to skip the exchange-db write and rely on the nightly migrate proc.
        logger.error(
            "get_exchange_connection failed for %r -> %r: %s",
            symbol,
            db_name,
            exc,
        )
        raise


# ---------------------------------------------------------------------------
# Convenience: resolve the exchange DB name without connecting
# ---------------------------------------------------------------------------

def resolve_exchange_db_name_for_symbol(
    symbol: str,
    *,
    conn: Optional[pymysql.connections.Connection] = None,
    default_exchange: str = "tsx",
) -> str:
    """Return the exchange database name for *symbol* without opening a connection.

    Convenience wrapper around resolve_exchange_for_symbol + exchange_db_name.
    Useful when the caller only needs the name (e.g. to log it or to pass it to
    another function that opens its own connection).
    """
    raw_ex = resolve_exchange_for_symbol(
        symbol, conn=conn, default_exchange=default_exchange
    )
    return exchange_db_name(raw_ex)
