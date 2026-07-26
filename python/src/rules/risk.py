"""Risk management, ATR stops, position sizing for rules engine."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def atr_14(db: Any, symbol: str, as_of: date, lookback_days: int = 60) -> float | None:
    start = as_of - timedelta(days=lookback_days)
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT close FROM stockprices
            WHERE symbol = %s AND price_date BETWEEN %s AND %s
            ORDER BY price_date ASC
            """,
            (symbol, start, as_of),
        )
        rows = [float(r["close"]) for r in cur.fetchall()]
    if len(rows) < 2:
        return None
    trs = [abs(rows[i] - rows[i - 1]) for i in range(1, len(rows))]
    period = min(14, len(trs))
    return sum(trs[-period:]) / period


def calc_position_size(
    price: float,
    cash: float,
    portfolio_value: float,
    confidence: float,
    max_positions: int,
    *,
    max_pct_portfolio: float = 0.10,
    max_risk_pct: float = 0.01,
    stop_factor: float = 2.0,
    min_allocation_pct: float = 0.02,
) -> tuple[int, float]:
    if price <= 0 or portfolio_value <= 0:
        return 0, 0.0
    confidence = max(confidence, 0.0)
    weight = max(min_allocation_pct, confidence * (1.0 / max(max_positions, 1)))
    weight = min(weight, max_pct_portfolio)
    allocation = portfolio_value * weight
    if allocation > cash:
        allocation = cash - max(9.95, allocation * 0.005)
    shares = int(allocation / price)
    if shares <= 0:
        return 0, 0.0
    stop_size = price * max_risk_pct
    if stop_size <= 0:
        stop_size = price * 0.01
    risk_dollars = portfolio_value * max_risk_pct
    shares_by_risk = int(risk_dollars / stop_size) if stop_size > 0 else shares
    return max(0, min(shares, shares_by_risk)), weight


def check_risk_limits(
    cash: float,
    total_value: float,
    positions: dict[str, dict[str, Any]],
    rule: dict[str, Any],
) -> tuple[bool, str]:
    max_daily_loss = float(rule.get("max_daily_loss_pct", 1.0))
    if total_value <= 0:
        return False, ""
    loss_pct = (total_value - (cash + sum((p["shares"] * p.get("cost_basis", 0)) for p in positions.values()))) / total_value
    if loss_pct >= max_daily_loss:
        return True, f"max_daily_loss {loss_pct:.2%} >= {max_daily_loss:.2%}"
    return False, ""


def check_atr_exit(
    db: Any,
    symbol: str,
    as_of: date,
    position: dict[str, Any],
    rule: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    stop_pct = float(rule.get("stop_pct", 0))
    atr_mult = float(rule.get("atr_multiplier", 0))
    if stop_pct <= 0 and atr_mult <= 0:
        return False, {}
    entry_price = float(position.get("cost_basis", 0))
    if entry_price <= 0:
        return False, {}
    atr_val = atr_14(db, symbol, as_of)
    last_px = None
    start = as_of - __import__("datetime").timedelta(days=14)
    with db.cursor() as cur:
        cur.execute(
            "SELECT close FROM stockprices WHERE symbol = %s AND price_date <= %s ORDER BY price_date DESC LIMIT 1",
            (symbol, as_of),
        )
        row = cur.fetchone()
        last_px = float(row["close"]) if row else None
    if last_px is None or atr_val is None:
        return False, {}
    threshold = entry_price - atr_mult * atr_val if atr_mult > 0 else entry_price * (1 - stop_pct)
    hit = last_px <= threshold
    meta = {"last_price": last_px, "atr14": atr_val, "threshold": threshold, "stop_pct": stop_pct, "atr_mult": atr_mult}
    return hit, meta

def check_reward_risk_ratio(signal_confidence, stop_pct, max_risk_pct, min_rrr):
    if min_rrr <= 0:
        return True, {"min_rrr": 0}
    effective_stop = max(stop_pct, max_risk_pct)
    if effective_stop <= 0:
        return True, {"reason": "no_stop"}
    ratio = signal_confidence / effective_stop
    meta = {"confidence": signal_confidence, "effective_stop": effective_stop, "ratio": ratio, "min_rrr": min_rrr}
    return ratio >= min_rrr, meta


def check_emergency_buffer(cash, total_value, min_buffer_pct, grace_days=0, days_below=0):
    if min_buffer_pct <= 0 or total_value <= 0:
        return True, {"buffer_pct": cash / total_value if total_value > 0 else 0, "min_buffer_pct": min_buffer_pct, "grace_days": grace_days, "days_below": days_below}
    buffer_pct = cash / total_value
    below = buffer_pct < min_buffer_pct
    meta = {"buffer_pct": buffer_pct, "min_buffer_pct": min_buffer_pct, "grace_days": grace_days, "days_below": days_below}
    return not below or days_below < grace_days, meta


def check_leverage(cash, positions, max_leverage_ratio):
    if max_leverage_ratio <= 0:
        return True, {"max_leverage_ratio": 0}
    position_value = sum(
        p.get("shares", 0) * float(p.get("cost_basis", 0) or 0) for p in positions.values()
    )
    portfolio = cash + position_value
    leverage = (cash + position_value) / cash if cash > 0 else float('inf')
    meta = {"leverage_ratio": leverage if leverage != float('inf') else 0, "max_leverage_ratio": max_leverage_ratio, "portfolio": portfolio, "cash": cash}
    return leverage <= max_leverage_ratio, meta


def check_margin_limits(cash, positions, max_utilization_pct, margin_buffer_pct, margin_call_grace_hours):
    if max_utilization_pct <= 0 and margin_buffer_pct <= 0:
        return True, {"max_utilization_pct": 0, "margin_buffer_pct": 0}
    position_value = sum(
        p.get("shares", 0) * float(p.get("cost_basis", 0) or 0) for p in positions.values()
    )
    equity = cash + position_value
    margin_used = position_value if cash <= 0 else 0.0
    utilization = margin_used / equity if equity > 0 else 0.0
    meta = {"margin_utilization_pct": utilization, "max_utilization_pct": max_utilization_pct, "margin_buffer_pct": margin_buffer_pct, "grace_hours": margin_call_grace_hours}
    ok_util = utilization <= (max_utilization_pct or 1.0)
    ok_buffer = True
    if margin_buffer_pct > 0 and cash < equity * margin_buffer_pct:
        ok_buffer = False
    return ok_util and ok_buffer, meta


def check_blacklist_asset(symbol, blacklist):
    if not blacklist or not symbol:
        return True, {"blacklist": []}
    s = symbol.lower()
    hit = [x for x in blacklist if x.lower() in s]
    meta = {"symbol": symbol, "blacklist_hits": hit, "blacklist": list(blacklist)}
    return len(hit) == 0, meta
