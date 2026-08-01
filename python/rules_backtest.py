"""Rules-aware advisor backtest runner.

Extends legacy advisor logic with:
- forced rebalance exits even when signal list is empty
- ATR/stop exits on open positions
- daily loss limit flatten
- confidence-weighted position sizing
- rule metadata in trade reasons

Selection/scoring still matches legacy advisor formulas so we can
prove start-to-finish parity with the old `advisor_backtest.py` results.
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import Any

import pymysql

REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "python" / "src") not in __import__("sys").path:
    __import__("sys").path.insert(0, str(REPO_ROOT / "python" / "src"))

from python.src.database import get_connection  # type: ignore
from python.src.rules.risk import (  # type: ignore
    atr_14,
    calc_position_size,
    check_atr_exit,
    check_risk_limits,
    check_reward_risk_ratio,
    check_emergency_buffer,
    check_leverage,
    check_margin_limits,
    check_blacklist_asset,
)

logger = logging.getLogger(__name__)


def get_price(conn: pymysql.connections.Connection, symbol: str, target_date: date) -> float | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT close FROM stockprices WHERE symbol = %s AND price_date <= %s ORDER BY price_date DESC LIMIT 1",
            (symbol, target_date),
        )
        row = cur.fetchone()
        return float(row["close"]) if row else None


def trading_dates(conn: pymysql.connections.Connection, start: date, end: date) -> list[date]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT price_date FROM stockprices WHERE price_date BETWEEN %s AND %s ORDER BY price_date ASC",
            (start, end),
        )
        return [r["price_date"] if isinstance(r["price_date"], date) else date.fromisoformat(str(r["price_date"])) for r in cur.fetchall()]


def _next_business_day(start: date, days: int) -> date:
    cur = start
    added = 0
    while added < days:
        cur = cur + timedelta(days=1)
        if cur.weekday() < 5:
            added += 1
    return cur


def _process_dividends(current_date, cash, positions, trades, conn):
    """Credit dividends to cash for positions held on the ex-dividend date."""
    if not positions:
        return cash
    syms = list(positions.keys())
    placeholders = ', '.join(['%s'] * len(syms))
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT symbol, amount FROM dividends WHERE ex_date = %s AND symbol IN ({placeholders})",
            [current_date] + syms,
        )
        divs = {r['symbol']: float(r['amount']) for r in cur.fetchall()}
    # Fallback: stockprices.dividend column (same date)
    if syms:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT symbol, dividend FROM stockprices WHERE price_date = %s AND dividend > 0 AND symbol IN ({placeholders})",
                [current_date] + syms,
            )
            for r in cur.fetchall():
                sym = r['symbol']
                if sym not in divs:
                    divs[sym] = float(r['dividend'])
    for sym, amount_per_share in divs.items():
        pos = positions.get(sym)
        if not pos:
            continue
        shares = float(pos.get('shares', 0))
        if shares <= 0:
            continue
        dividend = shares * amount_per_share
        cash += dividend
        trades.append({
            'symbol': sym,
            'trade_type': 'DIVIDEND',
            'trade_date': current_date,
            'price': amount_per_share,
            'quantity': shares,
            'commission': 0.0,
            'total_cost': dividend,
            'pnl': dividend,
            'signal_reasons': f'Dividend {sym}: {shares:.0f} shares x ${amount_per_share:.4f} = ${dividend:.2f}',
        })
    return cash


def _upcoming_ex_dividend_dates(conn, symbol, current_date, lookahead_days=5):
    """Return list of (ex_date, amount) for ex-dividend dates within lookahead window."""
    end = current_date + timedelta(days=lookahead_days)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT ex_date, amount FROM dividends WHERE symbol = %s AND ex_date > %s AND ex_date <= %s ORDER BY ex_date ASC",
            (symbol, current_date, end),
        )
        return [(r['ex_date'], float(r['amount'])) for r in cur.fetchall()]


def _dividend_price_impact(conn, symbol, ex_date):
    """Return True if price historically dropped by LESS than the dividend amount on ex-date.
    This means capturing the dividend is beneficial.
    """
    # Get previous close
    with conn.cursor() as cur:
        cur.execute(
            "SELECT close FROM stockprices WHERE symbol = %s AND price_date < %s ORDER BY price_date DESC LIMIT 1",
            (symbol, ex_date),
        )
        prev = cur.fetchone()
    if not prev:
        return False
    prev_close = float(prev['close'])
    # Get ex-date close
    with conn.cursor() as cur:
        cur.execute(
            "SELECT close, dividend FROM stockprices WHERE symbol = %s AND price_date = %s LIMIT 1",
            (symbol, ex_date),
        )
        ex_row = cur.fetchone()
    if not ex_row:
        return False
    ex_close = float(ex_row['close'])
    dividend = float(ex_row.get('dividend') or 0)
    if dividend <= 0:
        return False
    # Calculate actual price drop
    drop = prev_close - ex_close
    # If drop is significantly less than dividend (e.g., < 80% of dividend), it's beneficial
    return drop < (dividend * 0.8)


def _should_defer_sell_for_dividend(conn, symbol, current_date, px):
    """Return True if we should defer selling to capture an upcoming dividend."""
    if px <= 0:
        return False
    upcoming = _upcoming_ex_dividend_dates(conn, symbol, current_date, lookahead_days=3)
    if not upcoming:
        return False
    # Check the nearest upcoming ex-date
    ex_date, amount = upcoming[0]
    # Only defer if dividend is material (> 0.5% of price)
    if amount / px < 0.005:
        return False
    # Only defer if price historically doesn't drop by the full dividend
    if not _dividend_price_impact(conn, symbol, ex_date):
        return False
    return True


def _process_dividend_deferred_sells(current_date, positions, dividend_deferred_sells):
    """Clear deferral flags after the ex-dividend date has passed."""
    for sym in list(dividend_deferred_sells.keys()):
        if current_date > dividend_deferred_sells[sym]:
            del dividend_deferred_sells[sym]


def _maybe_exec_sell_with_dividend_check(conn, slug, strategy_name, pos, trades, current_date, cash, accrual_cash, commission, reason, pending_settlements, dividend_deferred_sells):
    """Execute sell unless it should be deferred for dividend capture."""
    sym = pos["symbol"]
    px = get_price(conn, sym, current_date)
    if not px or px <= 0:
        return cash, accrual_cash, False
    if _should_defer_sell_for_dividend(conn, sym, current_date, px):
        dividend_deferred_sells[sym] = _upcoming_ex_dividend_dates(conn, sym, current_date, lookahead_days=3)[0][0]
        return cash, accrual_cash, False
    cash, accrual_cash = _exec_sell(conn, slug, strategy_name, pos, trades, current_date, cash, accrual_cash, commission, reason, pending_settlements)
    return cash, accrual_cash, True


def _process_settlements(current_date, cash, accrual_cash, positions, trades, commission, slug, strategy_name, pending):
    due = [s for s in pending if s["settlement_date"] == current_date]
    remaining = [s for s in pending if s["settlement_date"] != current_date]
    for s in due:
        if s["type"] == "BUY":
            accrual_cash -= s["amount"]
            positions[s["symbol"]] = {
                "symbol": s["symbol"],
                "shares": s["shares"],
                "cost_basis": s.get("cost_basis", 0),
                "entry_date": current_date,
                "strategy": strategy_name,
                "trigger_reason": "settlement",
            }
        elif s["type"] == "SELL":
            accrual_cash -= s["amount"]
            cash += s["amount"]
    return cash, accrual_cash, positions, remaining


def load_risk_rules(conn: Any, strategy_name: str, bucket: str = "default") -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT risk_rules FROM strategy_rules
            WHERE strategy_name = %s AND bucket = %s AND is_active = 1
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (strategy_name, bucket),
        )
        row = cur.fetchone()
    if not row or not row.get("risk_rules"):
        return {}
    try:
        return json.loads(row["risk_rules"])
    except json.JSONDecodeError:
        return {}


def run_rules_backtest(
    conn: pymysql.connections.Connection,
    advisor: dict[str, Any],
    start_date: date,
    end_date: date,
    initial_capital: float,
    commission: float = 9.95,
    frequency: str = "weekly",
) -> dict[str, Any]:
    slug = advisor["slug"]
    strategy_name = advisor.get("strategy", slug)
    user_id = int(advisor["id"])
    display_name = advisor.get("display_name") or slug
    bucket = advisor.get("bucket", "default")
    risk = load_risk_rules(conn, strategy_name, bucket)

    max_positions = int(risk.get("max_positions", 20))
    stop_pct = float(risk.get("stop_pct", 0.10))
    atr_mult = float(risk.get("atr_multiplier", 0))
    max_pct_portfolio = float(risk.get("max_pct_portfolio", 0.10))
    max_risk_pct = float(risk.get("max_risk_pct", 0.01))
    stop_factor = float(risk.get("stop_factor", 2.0))
    max_daily_loss_pct = float(risk.get("max_daily_loss_pct", 0.05))
    optional = risk.get("optional_rules", {}) or {}
    min_rrr = float(optional.get("min_reward_risk_ratio", 0.0))
    emergency_buffer_target_pct = float(optional.get("emergency_buffer_target_pct", 0.0))
    emergency_buffer_grace_days = int(optional.get("emergency_buffer_grace_days", 0))
    max_leverage_ratio = float(optional.get("max_leverage_ratio", 0.0))
    max_margin_utilization_pct = float(optional.get("max_margin_utilization_pct", 0.0))
    margin_call_buffer_pct = float(optional.get("margin_call_buffer_pct", 0.0))
    margin_call_grace_hours = int(optional.get("margin_call_grace_hours", 0))
    blacklist = list(optional.get("blacklist_asset_classes", []) or [])

    cash = float(initial_capital)
    accrual_cash = 0.0
    positions: dict[str, dict[str, Any]] = {}
    trades: list[dict[str, Any]] = []
    history: list[dict[str, Any]] = []
    days_below_buffer = 0
    pending_settlements: list[dict[str, Any]] = []
    dividend_deferred_sells: dict[str, date] = {}

    dates = trading_dates(conn, start_date, end_date)
    if not dates:
        return {"slug": slug, "error": "No trading data"}

    cache = {
        "fundamentals": _load_latest_fundamentals(conn),
        "sector_etf": _sector_etf_map(),
        "sector_fundamental": _sector_fundamental_map(),
    }

    last_rebalance = start_date - timedelta(days=30)
    rebalance_days = {"daily": 1, "weekly": 7, "monthly": 30, "quarterly": 91}.get(frequency, 7)

    for i, current_date in enumerate(dates):
        cash, accrual_cash, positions, pending_settlements = _process_settlements(
            current_date, cash, accrual_cash, positions, trades, commission, slug, strategy_name, pending_settlements
        )
        cash = _process_dividends(current_date, cash, positions, trades, conn)
        _process_dividend_deferred_sells(current_date, positions, dividend_deferred_sells)
        if (current_date - last_rebalance).days < rebalance_days:
            if i % 5 == 0:
                history.append(_snapshot(current_date, cash, positions, conn))
            continue
        last_rebalance = current_date

        # Daily loss limit before doing anything else
        tv = cash + sum(
            (get_price(conn, k, current_date) or p["cost_basis"]) * p["shares"]
            for k, p in positions.items()
        )
        hit, reason = check_risk_limits(cash, tv, positions, {"max_daily_loss_pct": max_daily_loss_pct})
        if hit:
            for sym in list(positions.keys()):
                pos = positions[sym]
                px = get_price(conn, sym, current_date)
                if px and px > 0:
                    _exec_sell(conn, slug, strategy_name, pos, trades, current_date, cash, accrual_cash, commission, f"daily_loss_limit: {reason}", pending_settlements)
            positions.clear()
            if i % 5 == 0:
                history.append(_snapshot(current_date, cash, positions, conn))
            continue

        # Optional KB-derived rules
        if emergency_buffer_target_pct > 0 or max_leverage_ratio > 0 or max_margin_utilization_pct > 0 or margin_call_buffer_pct > 0:
            position_value = sum(
                p.get("shares", 0) * float(p.get("cost_basis", 0) or 0) for p in positions.values()
            )
            tv = cash + position_value
            hit_buf, _ = check_emergency_buffer(cash, tv, emergency_buffer_target_pct, emergency_buffer_grace_days, days_below_buffer)
            if not hit_buf:
                days_below_buffer += 1
            else:
                days_below_buffer = 0
            if emergency_buffer_grace_days > 0 and days_below_buffer > emergency_buffer_grace_days:
                for sym in list(positions.keys()):
                    pos = positions[sym]
                    px = get_price(conn, sym, current_date)
                    if px and px > 0:
                        _exec_sell(conn, slug, strategy_name, pos, trades, current_date, cash, accrual_cash, commission, "emergency_buffer_exceeded", pending_settlements)
                    if sym in positions:
                        del positions[sym]
                if i % 5 == 0:
                    history.append(_snapshot(current_date, cash, positions, conn))
                continue
            if max_leverage_ratio > 0:
                ok_lev, _ = check_leverage(cash, positions, max_leverage_ratio)
                if not ok_lev:
                    for sym in list(positions.keys()):
                        pos = positions[sym]
                        px = get_price(conn, sym, current_date)
                        if px and px > 0:
                            _exec_sell(conn, slug, strategy_name, pos, trades, current_date, cash, accrual_cash, commission, "leverage_exceeded", pending_settlements)
                        if sym in positions:
                            del positions[sym]
                    if i % 5 == 0:
                        history.append(_snapshot(current_date, cash, positions, conn))
                    continue
            if max_margin_utilization_pct > 0 or margin_call_buffer_pct > 0:
                ok_margin, _ = check_margin_limits(cash, positions, max_margin_utilization_pct, margin_call_buffer_pct, margin_call_grace_hours)
                if not ok_margin:
                    for sym in list(positions.keys()):
                        pos = positions[sym]
                        px = get_price(conn, sym, current_date)
                        if px and px > 0:
                            _exec_sell(conn, slug, strategy_name, pos, trades, current_date, cash, accrual_cash, commission, "margin_limit_exceeded", pending_settlements)
                        if sym in positions:
                            del positions[sym]
                    if i % 5 == 0:
                        history.append(_snapshot(current_date, cash, positions, conn))
                    continue

        # ATR/stop exits on open positions
        for sym in list(positions.keys()):
            pos = positions[sym]
            px = get_price(conn, sym, current_date)
            if not px or px <= 0:
                continue
            hit, meta = check_atr_exit(conn, sym, current_date, pos, {"stop_pct": stop_pct, "atr_multiplier": atr_mult})
            if hit:
                cash, accrual_cash, executed = _maybe_exec_sell_with_dividend_check(conn, slug, strategy_name, pos, trades, current_date, cash, accrual_cash, commission, f"atr_exit last={meta.get('last_price')} threshold={meta.get('threshold')}", pending_settlements, dividend_deferred_sells)
                if executed:
                    del positions[sym]

        # Advisor signals
        try:
            signals = _generate_signals(conn, advisor, current_date, cache)
        except Exception as exc:
            logger.warning("Advisor %s failed on %s: %s", slug, current_date, exc)
            if i % 5 == 0:
                history.append(_snapshot(current_date, cash, positions, conn))
            continue

        if not signals:
            # CRITICAL: still force-exit anything not in new signal list
            target_syms = set()
            for sym in list(positions.keys()):
                if sym in target_syms:
                    continue
                px = get_price(conn, sym, current_date)
                if px and px > 0:
                    cash, accrual_cash, executed = _maybe_exec_sell_with_dividend_check(conn, slug, strategy_name, positions[sym], trades, current_date, cash, accrual_cash, commission, "rebalance_out", pending_settlements, dividend_deferred_sells)
                    if not executed:
                        continue
                if sym in positions:
                    del positions[sym]
            positions.clear()
            if i % 5 == 0:
                history.append(_snapshot(current_date, cash, positions, conn))
            continue

        sells = [s for s in signals if s["action"] == "SELL"]
        buys = [s for s in signals if s["action"] == "BUY"]
        target_syms = {s["symbol"] for s in buys}

        for sym in list(positions.keys()):
            if sym in target_syms:
                continue
            px = get_price(conn, sym, current_date)
            if px and px > 0:
                cash, accrual_cash, executed = _maybe_exec_sell_with_dividend_check(conn, slug, strategy_name, positions[sym], trades, current_date, cash, accrual_cash, commission, "rebalance_out", pending_settlements, dividend_deferred_sells)
                if not executed:
                    continue
            if sym in positions:
                del positions[sym]

        for sig in sells:
            sym = sig["symbol"]
            if sym not in positions:
                continue
            px = get_price(conn, sym, current_date)
            if px and px > 0:
                cash, accrual_cash, executed = _maybe_exec_sell_with_dividend_check(conn, slug, strategy_name, positions[sym], trades, current_date, cash, accrual_cash, commission, sig.get("reason", "signal_exit"), pending_settlements, dividend_deferred_sells)
                if not executed:
                    continue
            if sym in positions:
                del positions[sym]

        tv = cash + sum(
            (get_price(conn, k, current_date) or p["cost_basis"]) * p["shares"]
            for k, p in positions.items()
        )
        for sig in buys:
            sym = sig["symbol"]
            if sym in positions:
                continue
            if len(positions) >= max_positions:
                break
            px = get_price(conn, sym, current_date)
            if not px or px <= 0:
                continue
            confidence = float(sig.get("confidence", sig.get("score", 0)))
            ok_rrr, _ = check_reward_risk_ratio(confidence, stop_pct, max_risk_pct, min_rrr)
            ok_blk, _ = check_blacklist_asset(sym, blacklist)
            if not ok_rrr or not ok_blk:
                continue
            shares, weight = calc_position_size(
                px,
                cash,
                tv,
                confidence,
                max_positions,
                max_pct_portfolio=max_pct_portfolio,
                max_risk_pct=max_risk_pct,
                stop_factor=stop_factor,
            )
            if shares <= 0:
                continue
            cost = shares * px + commission
            if cost > cash:
                shares = int((cash - commission) / px)
                if shares <= 0:
                    continue
                cost = shares * px + commission
            reason = sig.get("reason", "")
            cash, accrual_cash, positions, pending_settlements = _exec_buy(
                conn, slug, strategy_name, sym, px, shares, commission, cash, accrual_cash, positions, trades, current_date, reason, atr_mult, max_positions, stop_pct, pending_settlements
            )

        if i % 5 == 0:
            history.append(_snapshot(current_date, cash, positions, conn))

    final_snap = _snapshot(dates[-1], cash, positions, conn)
    history.append(final_snap)
    final_value = final_snap["total_value"]
    total_return = (final_value - initial_capital) / initial_capital if initial_capital else 0
    years = (end_date - start_date).days / 365.25
    annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
    peak = initial_capital
    max_drawdown = 0.0
    for snap in history:
        v = snap["total_value"]
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak > 0 else 0
        if dd > max_drawdown:
            max_drawdown = dd
    winning = [t for t in trades if t.get("pnl", 0) > 0]
    win_rate = len(winning) / len(trades) if trades else 0
    run_id = _save_run(conn, user_id, slug, display_name, strategy_name, start_date, end_date, initial_capital, final_value, total_return, annualized_return, max_drawdown, len(trades), win_rate, trades)
    logger.info("Rules backtest %s/%s: initial=%.2f final=%.2f return=%.2f%% trades=%d", slug, bucket, initial_capital, final_value, total_return * 100, len(trades))
    return {
        "run_id": run_id,
        "slug": slug,
        "display_name": display_name,
        "strategy": strategy_name,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "initial_capital": initial_capital,
        "final_value": round(final_value, 2),
        "total_return": round(total_return * 100, 2),
        "annualized_return": round(annualized_return * 100, 2),
        "max_drawdown": round(max_drawdown * 100, 2),
        "num_trades": len(trades),
        "win_rate": round(win_rate * 100, 2),
    }


def _generate_signals(conn, advisor, run_date, cache):
    strategy_name = advisor.get("strategy", advisor.get("slug"))
    if strategy_name in ("buffett_quality", "buffett"):
        return _buffett_signals(conn, advisor, run_date, cache)
    if strategy_name in ("dividend_growth", "dividend-growth"):
        return _dividend_signals(conn, advisor, run_date, cache)
    if strategy_name == "momentum":
        return _momentum_signals(conn, advisor, run_date, cache)
    if strategy_name in ("sector",) or advisor.get("slug", advisor.get("strategy", "")).startswith("sector-"):
        return _sector_signals(conn, advisor, run_date, cache)
    if strategy_name == "bond_basket":
        return _bond_signals(advisor, run_date)
    if strategy_name == "balanced_fund":
        return _balanced_signals(conn, advisor, run_date)
    if strategy_name == "vectorvest_safe":
        return _vv_signals(conn, advisor, run_date, cache)
    raise ValueError(f"Unknown strategy {strategy_name}")


def _normalize_roe(value: float) -> float:
    """Normalize ROE to percentage scale."""
    if value is None:
        return 0.0
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    if v <= 5:
        return v * 100.0
    return v


def _buffett_signals(conn, advisor, run_date, cache):
    cfg = {"min_market_cap": 5_000_000, "min_roe": 1.0, "max_debt_ratio": 200.0, "lookback_days": 365}
    fundamentals = cache.get("fundamentals", {})
    signals = []
    max_positions = int(advisor.get("max_positions", 6))
    min_roe = float(cfg["min_roe"])
    max_debt = float(cfg["max_debt_ratio"])
    candidates = []
    for symbol, r in fundamentals.items():
        if r.get("market_cap") is None or r.get("roe") is None or r.get("debt_to_equity") is None:
            continue
        if r["market_cap"] < cfg["min_market_cap"]:
            continue
        roe = _normalize_roe(r["roe"])
        debt = float(r["debt_to_equity"])
        if roe < min_roe or debt > max_debt:
            continue
        score = 0.0
        score += min(roe or 0, 30.0) * 2.0
        score += max(0.0, 100.0 - debt) * 0.5
        score += 10.0
        if r.get("gross_margin"):
            score += float(r["gross_margin"] or 0) * 1.0
        candidates.append((score, symbol, r))
    candidates.sort(key=lambda x: x[0], reverse=True)
    for rank, (score, symbol, r) in enumerate(candidates[:max_positions], 1):
        signals.append({
            "symbol": symbol,
            "action": "BUY",
            "score": score,
            "confidence": min(score / 100.0, 1.0),
            "reason": f"rank={rank} score={score:.2f}",
        })
    return signals


def _dividend_signals(conn, advisor, run_date, cache):
    cfg = {"min_yield": 2.0, "max_yield": 6.0, "lookback_days": 365 * 3, "min_consecutive_years": 5}
    start = run_date - timedelta(days=cfg["lookback_days"])
    with conn.cursor() as cur:
        cur.execute(
            "SELECT symbol, dividend_yield FROM fundamentals WHERE fetch_date >= %s AND dividend_yield BETWEEN %s AND %s",
            (start, cfg["min_yield"], cfg["max_yield"]),
        )
        rows = cur.fetchall()
    signals = []
    max_positions = int(advisor.get("max_positions", 20))
    for r in rows:
        symbol = r["symbol"]
        with conn.cursor() as cur:
            cur.execute("SELECT amount, ex_date FROM dividends WHERE symbol = %s AND ex_date BETWEEN %s AND %s ORDER BY ex_date DESC", (symbol, start, run_date))
            divs = cur.fetchall()
        if not divs:
            continue
        years: dict[int, float] = {}
        for d in divs:
            years[d["ex_date"].year] = years.get(d["ex_date"].year, 0.0) + float(d["amount"])
        unique = sorted(years.items(), reverse=True)
        if len(unique) < cfg["min_consecutive_years"]:
            continue
        consecutive = 0
        prev = None
        for _, total in unique:
            if prev is not None and total <= prev:
                break
            consecutive += 1
            prev = total
        if consecutive < cfg["min_consecutive_years"]:
            continue
        base = float(unique[0][1]) / float(unique[-1][1] or 1)
        score = 50.0 + (base * 30.0) + (consecutive * 2.0)
        signals.append({"symbol": symbol, "action": "BUY", "score": score, "confidence": min(score / 100.0, 1.0), "reason": f"dividend growth score={score:.2f}"})
    signals.sort(key=lambda s: s["score"], reverse=True)
    signals = signals[:max_positions]
    for rank, s in enumerate(signals, 1):
        s["reason"] = f"rank={rank} {s['reason']}"
    return signals


def _momentum_signals(conn, advisor, run_date, cache):
    cfg = {"lookback_days": 252, "momentum_window": 20, "min_price": 5.0, "min_volume": 200000, "max_positions": 15}
    start = run_date - timedelta(days=cfg["lookback_days"])
    cutoff = run_date - timedelta(days=cfg["momentum_window"])
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT symbol, MAX(close) AS newer, AVG(volume) AS avg_volume
            FROM stockprices WHERE price_date BETWEEN %s AND %s
            GROUP BY symbol
            HAVING avg_volume >= %s AND newer >= %s
            """,
            (start, cutoff, cfg["min_volume"], cfg["min_price"]),
        )
        universe = [r["symbol"] for r in cur.fetchall()]
    signals = []
    for sym in universe:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT close FROM stockprices WHERE symbol = %s AND price_date BETWEEN %s AND %s ORDER BY price_date ASC",
                (sym, cutoff, run_date),
            )
            rows = [float(r["close"]) for r in cur.fetchall()]
        if len(rows) < 2:
            continue
        mom = (rows[-1] - rows[0]) / rows[0] * 100.0
        if mom <= 0:
            continue
        signals.append({"symbol": sym, "action": "BUY", "score": mom, "confidence": min(mom / 100.0, 1.0), "reason": f"momentum {mom:.1f}%"})
    signals.sort(key=lambda s: s["score"], reverse=True)
    signals = signals[:int(advisor.get("max_positions", cfg["max_positions"]))]
    for rank, s in enumerate(signals, 1):
        s["reason"] = f"rank={rank} {s['reason']}"
    return signals


def _load_latest_fundamentals(conn) -> dict[str, dict[str, Any]]:
    cache: dict[str, dict[str, Any]] = {}
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT f.symbol, f.roe, f.debt_to_equity, f.market_cap, f.gross_margin, f.dividend_yield, f.sector
            FROM fundamentals f
            INNER JOIN (
                SELECT symbol, MAX(fetch_date) AS max_fd FROM fundamentals GROUP BY symbol
            ) latest ON latest.symbol = f.symbol AND latest.max_fd = f.fetch_date
            """
        )
        for r in cur.fetchall():
            cache[r["symbol"]] = dict(r)
    return cache


def _sector_etf_map() -> dict[str, str]:
    return {
        "Finance": "XFN.TO", "Energy Minerals": "XEG.TO", "Electronic Technology": "XIT.TO",
        "Technology Services": "XIT.TO", "Health Technology": "XIC.TO", "Non-Energy Minerals": "XMA.TO",
        "Real Estate": "XRE.TO", "Industrial Services": "XIC.TO", "Producer Manufacturing": "XIC.TO",
        "Process Industries": "XIC.TO", "Transportation": "XIC.TO", "Retail Trade": "XIC.TO",
        "Consumer Non-Durables": "XIC.TO", "Consumer Durables": "XIC.TO", "Health Services": "XIC.TO",
        "Communication Services": "XIC.TO", "Miscellaneous": "XIC.TO", "Distribution Services": "XIC.TO",
        "Commercial Services": "XIC.TO", "Consumer Services": "XIC.TO", "Utilities": "XIC.TO",
    }


def _sector_fundamental_map() -> dict[str, str]:
    return {
        "Finance": "Financial Services", "Energy Minerals": "Energy", "Electronic Technology": "Technology",
        "Technology Services": "Technology", "Health Technology": "Healthcare", "Non-Energy Minerals": "Basic Materials",
        "Process Industries": "Industrials", "Producer Manufacturing": "Industrials", "Industrial Services": "Industrials",
        "Retail Trade": "Consumer Cyclical", "Consumer Non-Durables": "Consumer Defensive", "Transportation": "Industrials",
        "Utilities": "Utilities", "Real Estate": "Real Estate", "Communication Services": "Communication Services",
        "Miscellaneous": None, "Distribution Services": "Industrials", "Commercial Services": "Industrials",
        "Consumer Services": "Consumer Cyclical",
    }


def _sector_etf(sector, etf_map=None):
    etf_map = etf_map or _sector_etf_map()
    return etf_map.get(sector)


def _sector_fundamental(sector, sector_map=None):
    sector_map = sector_map or _sector_fundamental_map()
    return sector_map.get(sector)


def _sector_signals(conn, advisor, run_date, cache):
    sector = advisor.get("sector", "")
    etf_map = cache.get("sector_etf", _sector_etf_map())
    sector_map = cache.get("sector_fundamental", _sector_fundamental_map())
    etf = _sector_etf(sector, etf_map=etf_map)
    symbols: list[str] = []
    if etf:
        symbols.append(etf)
    fund_sector = _sector_fundamental(sector, sector_map=sector_map)
    if fund_sector:
        start = run_date - timedelta(days=365)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT f.symbol
                FROM fundamentals f
                LEFT JOIN stockprices p ON p.symbol = f.symbol AND p.price_date <= %s
                WHERE f.sector = %s AND f.fetch_date >= %s AND p.symbol IS NOT NULL
                ORDER BY f.symbol
                LIMIT 40
                """,
                (run_date, fund_sector, start),
            )
            symbols.extend([r["symbol"] for r in cur.fetchall()])
    seen: set[str] = set()
    deduped: list[str] = []
    for s in symbols:
        if s and s not in seen:
            seen.add(s)
            deduped.append(s)
    max_positions = int(advisor.get("max_positions", 20))
    fundamentals = cache.get("fundamentals", {})
    signals = []
    for sym in deduped[:max_positions]:
        if sym == etf:
            signals.append({"symbol": sym, "action": "BUY", "score": 100.0, "confidence": 1.0, "reason": f"etf_rank=1 score=100"})
        else:
            start = run_date - timedelta(days=365)
            mc = 0.0
            r = fundamentals.get(sym)
            if r:
                mc = float(r.get("market_cap") or 0)
            signals.append({"symbol": sym, "action": "BUY", "score": max(mc, 0.1), "confidence": 0.1, "reason": f"market_cap rank"})
    signals.sort(key=lambda s: s["score"], reverse=True)
    signals = signals[:max_positions]
    for rank, s in enumerate(signals, 1):
        if s["symbol"] != etf:
            s["reason"] = f"rank={rank} score={s['score']:.2f}"
    return signals


def _bond_signals(advisor, run_date):
    symbols = ["TBIL.TO", "ZGB.TO", "HMP.TO", "ZAG.TO"]
    signals = [{"symbol": s, "action": "BUY", "score": 1.0, "confidence": 1.0, "reason": "bond_basket"} for s in symbols]
    return signals


def _balanced_signals(conn, advisor, run_date):
    equity = advisor.get("equity", "XIC.TO")
    signals = [{"symbol": equity, "action": "BUY", "score": 100.0, "confidence": 0.8, "reason": "equity 60%"}]
    for sym in ["TBIL.TO", "ZGB.TO", "HMP.TO", "ZAG.TO"]:
        signals.append({"symbol": sym, "action": "BUY", "score": 1.0, "confidence": 0.7, "reason": "bond basket 40%"})
    return signals


def _vv_signals(conn, advisor, run_date, cache):
    cfg = {"smooth_r2_min": 0.55, "min_price_days": 200, "market_symbol": "SPY"}
    start = run_date - timedelta(days=cfg["min_price_days"] + 60)
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT symbol FROM stockprices WHERE price_date >= %s GROUP BY symbol HAVING COUNT(*) >= %s", (str(start), cfg["min_price_days"]))
        universe = [r["symbol"] for r in cur.fetchall()]
    signals = []
    for sym in universe:
        with conn.cursor() as cur:
            cur.execute("SELECT price_date, close FROM stockprices WHERE symbol = %s AND price_date >= %s ORDER BY price_date ASC", (sym, str(start)))
            rows = cur.fetchall()
        if len(rows) < 20:
            continue
        closes = [float(r["close"]) for r in rows]
        x = list(range(len(closes)))
        n = len(closes)
        sx = sum(x); sy = sum(closes); sxy = sum(a * b for a, b in zip(x, closes)); sxx = sum(a * a for a in x)
        den = n * sxx - sx * sx
        if den == 0:
            continue
        slope = (n * sxy - sx * sy) / den
        ss_res = sum((closes[i] - (slope * x[i] + sy / n)) ** 2 for i in range(n))
        ss_tot = sum((v - sy / n) ** 2 for v in closes)
        r2 = 1.0 - ss_res / ss_tot if ss_tot else 0.0
        smooth = slope > 0 and r2 >= cfg["smooth_r2_min"]
        price_rising = closes[-1] > closes[-21] if len(closes) > 21 else closes[-1] > closes[0]
        start2 = run_date - timedelta(days=40)
        with conn.cursor() as cur:
            cur.execute("SELECT close FROM stockprices WHERE symbol = %s AND price_date BETWEEN %s AND %s ORDER BY price_date ASC", (cfg["market_symbol"], start2, run_date))
            mkt = [float(r["close"]) for r in cur.fetchall()]
        mkt_ok = mkt[-1] > mkt[-21] if len(mkt) > 21 else (mkt[-1] > mkt[0] if mkt else True)
        today_o = rows[-1]
        y_c = rows[-2]["close"] if len(rows) > 1 else today_o["close"]
        follow = float(today_o["close"]) > float(today_o.get("open", today_o["close"])) and float(today_o["close"]) > y_c
        pass_count = sum([smooth, price_rising, False, mkt_ok, follow])
        if pass_count == 0:
            continue
        signals.append({"symbol": sym, "action": "BUY", "score": float(pass_count), "confidence": min(pass_count / 5.0, 1.0), "reason": f"vv pass={pass_count}/5"})
    signals.sort(key=lambda s: s["score"], reverse=True)
    max_positions = int(advisor.get("max_positions", 20))
    signals = signals[:max_positions]
    for rank, s in enumerate(signals, 1):
        s["reason"] = f"vv pass={s['score']:.0f}/5 rank={rank}"
    return signals


def _exec_sell(conn, slug, strategy_name, pos, trades, current_date, cash, accrual_cash, commission, reason, pending_settlements):
    sym = pos["symbol"]
    px = get_price(conn, sym, current_date)
    if not px or px <= 0:
        px = pos["cost_basis"]
    qty = pos["shares"]
    trade_amount = qty * px
    proceeds = trade_amount - commission
    pnl = proceeds - (qty * pos["cost_basis"])
    accrual_cash += proceeds
    settlement = _next_business_day(current_date, 2)
    pending_settlements.append({
        "settlement_date": settlement,
        "type": "SELL",
        "symbol": sym,
        "amount": proceeds,
        "shares": 0,
    })
    trades.append({
        'symbol': sym,
        'trade_type': 'SELL',
        'trade_date': current_date,
        'price': px,
        'quantity': qty,
        'commission': commission,
        'total_cost': trade_amount,
        'pnl': pnl,
        'signal_reasons': f"Rule {strategy_name} ({slug}): SELL {sym} at ${px:.2f} triggered by {reason}. ATR/stop/rules applied.",
    })
    return cash, accrual_cash


def _exec_buy(conn, slug, strategy_name, symbol, price, shares, commission, cash, accrual_cash, positions, trades, current_date, reason, atr_mult, max_positions, stop_pct, pending_settlements):
    cost = shares * price + commission
    trade_amount = shares * price
    cash -= cost
    accrual_cash += trade_amount
    settlement = _next_business_day(current_date, 2)
    pending_settlements.append({
        "settlement_date": settlement,
        "type": "BUY",
        "symbol": symbol,
        "amount": trade_amount,
        "shares": shares,
        "cost_basis": price,
    })
    positions[symbol] = {
        "symbol": symbol,
        "shares": shares,
        "cost_basis": price,
        "entry_date": current_date,
        "strategy": strategy_name,
        "trigger_reason": reason,
    }
    trades.append({
        'symbol': symbol,
        'trade_type': 'BUY',
        'trade_date': current_date,
        'price': price,
        'quantity': shares,
        'commission': commission,
        'total_cost': trade_amount,
        'signal_reasons': f"Rule {strategy_name} ({slug}): BUY {symbol} at ${price:.2f} {reason} confidence atr_mult={atr_mult} max_positions={max_positions} stop_pct={stop_pct:.0%}",
    })
    return cash, accrual_cash, positions, pending_settlements


def _snapshot(current_date, cash, positions, conn):
    total_value = cash
    for sym, pos in positions.items():
        px = get_price(conn, sym, current_date)
        if px is None:
            px = pos["cost_basis"]
        total_value += pos["shares"] * px
    return {"date": current_date, "cash": cash, "total_value": total_value, "num_positions": len(positions)}


def _save_run(conn, user_id, slug, display_name, strategy, start, end, initial, final, total_return, annualized_return, max_drawdown, num_trades, win_rate, trades):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO backtest_runs (user_id, strategy, parameters, start_date, end_date,
                initial_capital, final_value, total_return, annualized_return, sharpe_ratio, max_drawdown, num_trades, win_rate, status, error_message, completed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'complete', NULL, NOW())
            """,
            (user_id, f"rules:{strategy}:{slug}", json.dumps({"advisor": slug, "mode": "rules"}), start.isoformat(), end.isoformat(), initial, final, total_return, annualized_return, 0.0, max_drawdown, num_trades, win_rate),
        )
        run_id = int(cur.lastrowid)
        for t in trades:
            cur.execute(
                """
                INSERT INTO backtest_trades (backtest_id, symbol, trade_type, trade_date, price, quantity, commission, total_cost, signal_reasons)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (run_id, t["symbol"], t["trade_type"], t["trade_date"].isoformat(), t["price"], t["quantity"], t["commission"], t["total_cost"], t.get("signal_reasons", "")),
            )
    conn.commit()
    return run_id


def main(argv: list[str] | None = None) -> int:
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Run rules-aware advisor backtests")
    p.add_argument("--start", default="2022-01-01")
    p.add_argument("--end", default=None)
    p.add_argument("--initial", type=float, default=100000.0)
    p.add_argument("--commission", type=float, default=9.95)
    p.add_argument("--slug", default=None)
    p.add_argument("--all", action="store_true")
    p.add_argument("--frequency", default="weekly", choices=["daily", "weekly", "monthly", "quarterly"])
    p.add_argument("--reset", action="store_true", help="Delete old runs/trades first")
    p.add_argument("--bucket", default="default")
    args = p.parse_args(argv)
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end) if args.end else date.today()
    conn = get_connection()

    if args.reset:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM backtest_trades WHERE backtest_id IN (SELECT id FROM backtest_runs WHERE strategy LIKE 'rules:%')")
            cur.execute("DELETE FROM backtest_runs WHERE strategy LIKE 'rules:%'")
        conn.commit()
        print("Reset rules backtest rows.")

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT u.id, u.username AS slug, u.display_name,
                   COALESCE(us.setting_value, 'buffett_quality') AS strategy,
                   COALESCE(sec.setting_value, '') AS sector,
                   COALESCE(eq.setting_value, '') AS equity
            FROM users u
            LEFT JOIN user_settings us ON us.user_id = u.id AND us.setting_key = 'advisor_strategy'
            LEFT JOIN user_settings sec ON sec.user_id = u.id AND sec.setting_key = 'advisor_sector'
            LEFT JOIN user_settings eq ON eq.user_id = u.id AND eq.setting_key = 'advisor_equity'
            WHERE u.role = 'advisor' AND u.is_active = 1
            ORDER BY u.id
            """
        )
        advisors = [dict(r) for r in cur.fetchall()]

    if args.slug:
        advisors = [a for a in advisors if a["slug"] == args.slug]

    results = []
    for adv in advisors:
        adv.setdefault("bucket", args.bucket)
        try:
            res = run_rules_backtest(conn, adv, start, end, args.initial, args.commission, args.frequency)
            results.append(res)
        except Exception:
            logger.exception("Rules advisor %s backtest crashed", adv["slug"])
            results.append({"slug": adv["slug"], "error": "exception"})

    summary_path = REPO_ROOT / "python" / "rules_backtest_summary.json"
    payload = {"generated_at": date.today().isoformat(), "start": start.isoformat(), "end": end.isoformat(), "initial_capital": args.initial, "advisors": results}
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    logger.info("Summary written to %s", summary_path)
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
