"""Repository for evaluation score writes.

Writes use the existing centralized db_connector.get_connection().
Each method maps exactly to production table columns — no extra columns like
``source``/``source_date``/``is_llm_generated`` are inserted.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now()


def _iso_date(v: Optional[date]) -> Optional[str]:
    return v.isoformat() if v is not None else None


def _float(v: Optional[Any]) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
        if f != f:  # NaN
            return None
        return f
    except (TypeError, ValueError):
        return None


# ── motleyfool ──────────────────────────────────────────────────────


def save_motleyfool(conn: Any, ev: Dict[str, Any]) -> None:
    sql = """
        INSERT INTO `motleyfool`
          (`symbol`,
           `simplebusiness`,`reasonablevaluation`,`corefocus`,
           `doubledigitsales`,`risingcashflow`,`risingbookvalue`,
           `improvingmargins`,`risingroe`,`insiderownership`,`regulardividend`,
           `score`)
        VALUES (%(symbol)s, %(simple_business)s, %(reasonable_valuation)s, %(core_focus)s,
                %(doubledigit_sales)s, %(rising_cashflow)s, %(rising_bookvalue)s,
                %(improving_margins)s, %(rising_roe)s, %(insider_ownership)s,
                %(regular_dividend)s, %(score)s)
        ON DUPLICATE KEY UPDATE
           `simplebusiness` = VALUES(`simplebusiness`),
           `reasonablevaluation` = VALUES(`reasonablevaluation`),
           `corefocus` = VALUES(`corefocus`),
           `doubledigitsales` = VALUES(`doubledigitsales`),
           `risingcashflow` = VALUES(`risingcashflow`),
           `risingbookvalue` = VALUES(`risingbookvalue`),
           `improvingmargins` = VALUES(`improvingmargins`),
           `risingroe` = VALUES(`risingroe`),
           `insiderownership` = VALUES(`insiderownership`),
           `regulardividend` = VALUES(`regulardividend`),
           `score` = VALUES(`score`),
           `lastupdate` = NOW()
    """
    params = {
        "symbol": str(ev.get("symbol", "")),
        "simple_business": _as_bool(ev.get("simple_business")),
        "reasonable_valuation": _as_bool(ev.get("reasonable_valuation")),
        "core_focus": _as_bool(ev.get("core_focus")),
        "doubledigit_sales": _as_bool(ev.get("doubledigit_sales")),
        "rising_cashflow": _as_bool(ev.get("rising_cashflow")),
        "rising_bookvalue": _as_bool(ev.get("rising_bookvalue")),
        "improving_margins": _as_bool(ev.get("improving_margins")),
        "rising_roe": _as_bool(ev.get("rising_roe")),
        "insider_ownership": _as_bool(ev.get("insider_ownership")),
        "regular_dividend": _as_bool(ev.get("regular_dividend")),
        "score": int(ev.get("score", 0) or 0),
    }
    with conn.cursor() as cur:
        cur.execute(sql, params)
    conn.commit()


# ── tenets ─────────────────────────────────────────────────────────


def save_tenets(conn: Any, symbol: str, items: Sequence[Dict[str, Any]]) -> None:
    sql = """
        INSERT INTO `tenets` (`symbol`, `name`, `passed`, `detail`, `lasteval`)
        VALUES (%s, %s, %s, %s, NOW())
        ON DUPLICATE KEY UPDATE
          `passed` = VALUES(`passed`),
          `detail` = VALUES(`detail`),
          `lasteval` = VALUES(`lasteval`)
    """
    with conn.cursor() as cur:
        for item in items:
            cur.execute(
                sql,
                (
                    str(symbol),
                    str(item.get("name", "")),
                    1 if _as_bool(item.get("passed")) else 0,
                    str(item.get("detail", ""))[:65535],
                ),
            )
    conn.commit()


# ── single-row eval tables (evalbusiness / evalmanagement / evalmarket) ─


def _save_eval_single(
    conn: Any,
    table: str,
    ev: Dict[str, Any],
    extra_sets: Optional[List[str]] = None,
    extra_values: Optional[List[Any]] = None,
) -> None:
    col = "`score`"
    sets = [f"{col} = VALUES({col})"]
    if extra_sets:
        sets.extend(extra_sets or [])
    sql = f"""
        INSERT INTO `{table}` (`symbol`, `score`, `summary`, `lasteval`)
        VALUES (%(symbol)s, %(score)s, %(summary)s, %(lasteval)s)
        ON DUPLICATE KEY UPDATE
          `score` = VALUES(`score`),
          `summary` = VALUES(`summary`),
          `lasteval` = VALUES(`lasteval`),
          {', '.join(sets)}
    """
    params: Dict[str, Any] = {
        "symbol": str(ev.get("symbol", "")),
        "score": int(ev.get("score", 0) or 0),
        "summary": str(ev.get("summary", "") or "")[:65535],
        "lasteval": _now(),
    }
    if extra_values:
        params.update(extra_values)
    with conn.cursor() as cur:
        cur.execute(sql, params)
    conn.commit()


def save_evalbusiness(conn: Any, ev: Dict[str, Any]) -> None:
    _save_eval_single(conn, "evalbusiness", ev)


def save_evalmanagement(conn: Any, ev: Dict[str, Any]) -> None:
    _save_eval_single(conn, "evalmanagement", ev)


def save_evalmarket(conn: Any, ev: Dict[str, Any]) -> None:
    # evalmarket schema: symbol + score + summary + lasteval, no price_date
    _save_eval_single(conn, "evalmarket", ev)


# ── evaluation_scores ───────────────────────────────────────────────


def save_evaluation_scores(conn: Any, ev: Dict[str, Any]) -> None:
    sql = """
        INSERT INTO `evaluation_scores`
          (`symbol`, `eval_type`, `domain`, `score`, `max_score`, `grade`, `note`, `created_by`)
        VALUES (%(symbol)s, %(eval_type)s, %(domain)s, %(score)s, %(max_score)s,
                %(grade)s, %(note)s, %(created_by)s)
        ON DUPLICATE KEY UPDATE
          `score` = VALUES(`score`),
          `max_score` = VALUES(`max_score`),
          `grade` = VALUES(`grade`),
          `note` = VALUES(`note`),
          `created_by` = VALUES(`created_by`),
          `updated_at` = NOW()
    """
    params = {
        "symbol": str(ev.get("symbol", "")),
        "eval_type": str(ev.get("eval_type", "")),
        "domain": str(ev.get("domain", "")),
        "score": int(ev.get("score", 0) or 0),
        "max_score": int(ev.get("max_score", 100) or 100),
        "grade": str(ev.get("grade", "F")),
        "note": str(ev.get("note", "")) if ev.get("note") is not None else None,
        "created_by": str(ev.get("created_by", "system")),
    }
    with conn.cursor() as cur:
        cur.execute(sql, params)
    conn.commit()


def save_evalsummary(conn: Any, ev: Dict[str, Any]) -> None:
    sql = """
        INSERT INTO `evalsummary`
          (`symbol`, `price_date`, `close`,
           `consensus_signal`, `consensus_strength`, `atr_position_size`,
           `portfolio_weight`, `strategy_json`)
        VALUES (%(symbol)s, %(price_date)s, %(close)s,
                %(consensus_signal)s, %(consensus_strength)s, %(atr_position_size)s,
                %(portfolio_weight)s, %(strategy_json)s)
        ON DUPLICATE KEY UPDATE
          `close` = VALUES(`close`),
          `consensus_signal` = VALUES(`consensus_signal`),
          `consensus_strength` = VALUES(`consensus_strength`),
          `atr_position_size` = VALUES(`atr_position_size`),
          `portfolio_weight` = VALUES(`portfolio_weight`),
          `strategy_json` = VALUES(`strategy_json`)
    """
    params = {
        "symbol": str(ev.get("symbol", "")),
        "price_date": _iso_date(ev.get("price_date")),
        "close": _float(ev.get("close")),
        "consensus_signal": _as_int(ev.get("consensus_signal")),
        "consensus_strength": _float(ev.get("consensus_strength")),
        "atr_position_size": _float(ev.get("atr_position_size")),
        "portfolio_weight": _float(ev.get("portfolio_weight")),
        "strategy_json": str(ev.get("strategy_json", "")) if ev.get("strategy_json") is not None else None,
    }
    with conn.cursor() as cur:
        cur.execute(sql, params)
    conn.commit()


# ── helpers ────────────────────────────────────────────────────────


def _as_bool(v: Any) -> Optional[int]:
    if v is None:
        return None
    if isinstance(v, bool):
        return 1 if v else 0
    try:
        return 1 if int(v) else 0
    except (TypeError, ValueError):
        return None


def _as_int(v: Any) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
