"""Generic advisor pipeline integration.

Wires `strategy_pipeline.py` capabilities into the advisor/rule runner stack:
- oscillator toggles (RSI, MACD, Stochastic, Bollinger)
- candlestick timeframe validation (daily / weekly / monthly)
- combo voting / consensus
- parameter sweep runner with DB persistence
- user-designed advisor backtest/forward-walk entrypoint

This module is intentionally decoupled from web routes; call it from CLI,
cron, or higher-level app hooks.
"""
from __future__ import annotations

import json
import logging
import math
import os
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
)

logger = logging.getLogger(__name__)

DEFAULT_TIME_FRAMES = ["1D", "1W", "1M"]

# ============================================================================
# Indicator / oscillator toggles
# ============================================================================

def default_indicator_set() -> dict[str, bool]:
    return {
        "rsi": True,
        "macd": True,
        "stoch": True,
        "bbands": True,
        "atr": True,
        "doji": True,
        "hammer": True,
        "engulfing": True,
        "sma_cross": True,
        "donchian": True,
    }


def normalize_indicator_set(raw: dict[str, Any] | None) -> dict[str, bool]:
    if not raw:
        return default_indicator_set()
    out = default_indicator_set()
    for k, v in raw.items():
        if k in out:
            out[k] = bool(v)
    return out


# ============================================================================
# Rule loading helpers
# ============================================================================

def load_rule_set(conn: pymysql.connections.Connection, strategy_name: str, bucket: str = "default") -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT indicators, bias_criteria, entry_rules, exit_rules, risk_rules
            FROM strategy_rules
            WHERE strategy_name = %s AND bucket = %s AND is_active = 1
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (strategy_name, bucket),
        )
        row = cur.fetchone()
    if not row:
        return {}
    out: dict[str, Any] = {}
    for key in ("indicators", "bias_criteria", "entry_rules", "exit_rules", "risk_rules"):
        raw = row.get(key)
        if not raw:
            out[key] = {} if key == "risk_rules" else []
            continue
        try:
            out[key] = json.loads(raw)
        except json.JSONDecodeError:
            out[key] = {} if key == "risk_rules" else []
    return out


def load_risk_defaults(conn, strategy_name, bucket="default"):
    rules = load_rule_set(conn, strategy_name, bucket)
    return rules.get("risk_rules", {})


# ============================================================================
# Timeframe-aware candlestick scoring
# ============================================================================

def timeframed_candle_score(conn, symbol: str, run_date: date, timeframe: str = "1D") -> float:
    """Return a naive candlestick score for the requested timeframe.

    Daily = rows from stockprices.
    Weekly = resample from daily to weekly.
    Monthly = resample from daily to monthly.
    """
    if timeframe == "1D":
        start = run_date - timedelta(days=20)
        sql = """
            SELECT day_open AS open, day_high AS high, day_low AS low, day_close AS close
            FROM stockprices
            WHERE symbol = %s AND price_date BETWEEN %s AND %s
            ORDER BY price_date ASC
        """
        params = (symbol, start, run_date)
    elif timeframe == "1W":
        start = run_date - timedelta(days=120)
        sql = """
            SELECT
                SUBDATE(price_date, INTERVAL (WEEKDAY(price_date)) DAY) AS week_start,
                MIN(day_low) AS low, MAX(day_high) AS high,
                MAX(day_close) AS close, MIN(day_open) AS open
            FROM stockprices
            WHERE symbol = %s AND price_date BETWEEN %s AND %s
            GROUP BY week_start
            ORDER BY week_start ASC
        """
        params = (symbol, start, run_date)
    elif timeframe == "1M":
        start = run_date - timedelta(days=365)
        sql = """
            SELECT
                DATE_FORMAT(price_date, '%%Y-%%m-01') AS month_start,
                MIN(day_low) AS low, MAX(day_high) AS high,
                MAX(day_close) AS close, MIN(day_open) AS open
            FROM stockprices
            WHERE symbol = %s AND price_date BETWEEN %s AND %s
            GROUP BY month_start
            ORDER BY month_start ASC
        """
        params = (symbol, start, run_date)
    else:
        return 0.0

    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    if not rows or len(rows) < 2:
        return 0.0

    score = 0.0
    prev = rows[-2]
    last = rows[-1]
    body = abs(last["close"] - last["open"])
    rng = last["high"] - last["low"] + 1e-10
    upper = last["high"] - max(last["close"], last["open"])
    lower = min(last["close"], last["open"]) - last["low"]

    if body / rng < 0.1:
        score -= 5
    if lower > 2 * body and upper < body:
        score += 15
    if upper > 2 * body and lower < body:
        score -= 15
    if (
        last["close"] > last["open"]
        and prev["close"] <= prev["open"]
        and body > abs(prev["close"] - prev["open"])
    ):
        score += 20
    if last["close"] > last["open"] and prev["close"] > prev["open"]:
        score += 10
    if last["close"] < last["open"] and prev["close"] < prev["open"]:
        score -= 10

    return max(min(score, 100.0), -100.0)


# ============================================================================
# Combo / consensus voter
# ============================================================================

def consensus_buy_signals(signals_by_strategy: dict[str, list[dict[str, Any]]], min_agree: int = 2) -> list[dict[str, Any]]:
    """Return BUY signals that appear in at least `min_agree` strategies."""
    sym_votes: dict[str, list[dict[str, Any]]] = {}
    for sigs in signals_by_strategy.values():
        for s in sigs:
            if s.get("action") != "BUY":
                continue
            sym = s.get("symbol")
            if not sym:
                continue
            sym_votes.setdefault(sym, []).append(s)

    out = []
    for sym, votes in sym_votes.items():
        if len(votes) < min_agree:
            continue
        best = max(votes, key=lambda x: x.get("score", 0.0))
        merged = dict(best)
        merged["confidence"] = min(len(votes) / max(len(signals_by_strategy), 1), 1.0)
        merged["reason"] = f"combo_{len(votes)}_of_{len(signals_by_strategy)} {merged.get('reason', '')}"
        out.append(merged)
    out.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return out


# ============================================================================
# Parameter sweep runner
# ============================================================================

def run_param_sweep(
    conn: pymysql.connections.Connection,
    advisors: list[dict[str, Any]],
    param_grid: dict[str, list[Any]],
    start_date: date,
    end_date: date,
    initial_capital: float = 100000.0,
    frequency: str = "weekly",
    user_id: int = 1,
) -> list[dict[str, Any]]:
    """Run every advisor × parameter-combo combination and persist results."""
    from itertools import product

    keys = list(param_grid.keys())
    values = [param_grid[k] for k in keys]
    results: list[dict[str, Any]] = []
    combos = list(product(*values))

    for adv in advisors:
        slug = adv["slug"]
        strategy_name = adv.get("strategy", slug)
        bucket = adv.get("bucket", "default")
        for combo in combos:
            params = dict(zip(keys, combo))
            try:
                res = _run_single_with_overrides(conn, adv, start_date, end_date, initial_capital, frequency, params)
                res.setdefault("slug", slug)
                res.setdefault("strategy", strategy_name)
                res.setdefault("params", json.dumps(params))
                results.append(res)
                _persist_sweep_result(conn, user_id, slug, strategy_name, start_date, end_date, params, res)
            except Exception as exc:
                logger.exception("Sweep %s/%s crashed: %s", slug, bucket, exc)
                results.append({"slug": slug, "error": str(exc), "params": json.dumps(params)})
    conn.commit()
    return results


def run_combo_sweep(
    conn: pymysql.connections.Connection,
    advisors: list[dict[str, Any]],
    start_date: date,
    end_date: date,
    initial_capital: float = 100000.0,
    frequency: str = "weekly",
    user_id: int = 1,
    max_combo_size: int = 4,
) -> list[dict[str, Any]]:
    from itertools import combinations

    results: list[dict[str, Any]] = []
    names = [a["slug"] for a in advisors]
    for size in range(2, min(len(names) + 1, max_combo_size + 1)):
        for combo in combinations(names, size):
            try:
                res = _run_combo_backtest(conn, combo, advisors, start_date, end_date, initial_capital, frequency)
                res.setdefault("combo_names", ":".join(combo))
                res.setdefault("combo_size", size)
                res.setdefault("strategy", "combo")
                results.append(res)
                _persist_sweep_result(conn, user_id, ":".join(combo), "combo", start_date, end_date, {"combo": list(combo)}, res)
            except Exception as exc:
                logger.exception("Combo %s crashed: %s", combo, exc)
                results.append({"combo_names": ":".join(combo), "error": str(exc)})
    conn.commit()
    return results


# ============================================================================
# Backtest / forward-walk entrypoints
# ============================================================================

def backtest_user_advisor(
    conn: pymysql.connections.Connection,
    strategy_name: str,
    bucket: str,
    start_date: date,
    end_date: date,
    initial_capital: float = 100000.0,
    frequency: str = "weekly",
    commission: float = 9.95,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    advisor = {
        "id": 1,
        "slug": strategy_name,
        "strategy": strategy_name,
        "display_name": strategy_name,
        "bucket": bucket,
    }
    if overrides:
        advisor.update(overrides)
    return _run_single_with_overrides(conn, advisor, start_date, end_date, initial_capital, frequency, {})


def forward_walk(
    conn: pymysql.connections.Connection,
    strategy_name: str,
    bucket: str,
    start_date: date,
    end_date: date,
    lookback_years: int = 3,
    step_months: int = 6,
    initial_capital: float = 100000.0,
    frequency: str = "weekly",
    commission: float = 9.95,
) -> list[dict[str, Any]]:
    """Run rolling forward-walk backtests."""
    results: list[dict[str, Any]] = []
    step = timedelta(days=30 * step_months)
    lookback = timedelta(days=365 * lookback_years)
    window_start = start_date
    idx = 1
    while window_start + lookback <= end_date:
        window_end = min(window_start + lookback, end_date)
        try:
            res = backtest_user_advisor(
                conn, strategy_name, bucket, window_start, window_end,
                initial_capital=initial_capital, frequency=frequency, commission=commission,
            )
            res.update({"walk_id": idx, "window_start": str(window_start), "window_end": str(window_end)})
            results.append(res)
        except Exception as exc:
            logger.exception("Forward walk %s crashed: %s", idx, exc)
            results.append({"walk_id": idx, "window_start": str(window_start), "error": str(exc)})
        window_start += step
        idx += 1
    return results


# ============================================================================
# Internal helpers
# ============================================================================

def _run_single_with_overrides(conn, advisor, start_date, end_date, initial_capital, frequency, overrides):
    # Local import keeps optional dependency lazy
    from python.rules_backtest import run_rules_backtest  # type: ignore
    merged = dict(advisor)
    if overrides:
        merged.update({k: v for k, v in overrides.items() if k not in ("slug", "strategy", "display_name", "bucket", "id")})
    return run_rules_backtest(conn, merged, start_date, end_date, initial_capital, commission=9.95, frequency=frequency)


def _run_combo_backtest(conn, combo_names, advisors, start_date, end_date, initial_capital, frequency):
    signals_by_strategy = {}
    for name in combo_names:
        adv = next((a for a in advisors if a["slug"] == name), None)
        if not adv:
            adv = {"id": 1, "slug": name, "strategy": name, "display_name": name, "bucket": "default"}
        dates = trading_dates(conn, start_date, end_date)
        if not dates:
            return {"error": "no_dates"}
        cache = {"fundamentals": _load_latest_fundamentals(conn), "sector_etf": _sector_etf_map(), "sector_fundamental": _sector_fundamental_map()}
        sigs = []
        for d in dates:
            try:
                sigs.append(_generate_signals(conn, adv, d, cache))
            except Exception:
                sigs.append([])
        signals_by_strategy[name] = sigs

    # Reuse the same execution loop with combo-generated signals
    cash = float(initial_capital)
    positions: dict[str, dict[str, Any]] = {}
    trades: list[dict[str, Any]] = []
    history: list[dict[str, Any]] = []
    dates = trading_dates(conn, start_date, end_date)
    if not dates:
        return {"error": "no_dates"}

    rebalance_days = {"daily": 1, "weekly": 7, "monthly": 30, "quarterly": 91}.get(frequency, 7)
    last_rebalance = start_date - timedelta(days=30)

    for i, current_date in enumerate(dates):
        if (current_date - last_rebalance).days < rebalance_days:
            if i % 5 == 0:
                history.append(_snapshot(current_date, cash, positions, conn))
            continue
        last_rebalance = current_date

        combined = []
        for name in combo_names:
            if i < len(signals_by_strategy.get(name, [])):
                combined.extend(signals_by_strategy[name][i])

        combo_sigs = consensus_buy_signals({name: combined for name in combo_names}, min_agree=2)
        sells = [s for s in combo_sigs if s.get("action") == "SELL"]
        buys = [s for s in combo_sigs if s.get("action") == "BUY"]

        if not combo_sigs:
            for sym in list(positions.keys()):
                px = get_price(conn, sym, current_date)
                if px and px > 0:
                    pos = positions[sym]
                    qty = pos["shares"]
                    proceeds = qty * px - 9.95
                    cash += proceeds
                    trades.append({"symbol": sym, "trade_type": "SELL", "trade_date": current_date, "price": px, "quantity": qty, "commission": 9.95, "total_cost": -proceeds, "pnl": proceeds - qty * pos["cost_basis"], "signal_reasons": "rebalance_out"})
                    del positions[sym]
            if i % 5 == 0:
                history.append(_snapshot(current_date, cash, positions, conn))
            continue

        target_syms = {s["symbol"] for s in buys}
        for sym in list(positions.keys()):
            if sym in target_syms:
                continue
            px = get_price(conn, sym, current_date)
            if px and px > 0:
                pos = positions[sym]
                qty = pos["shares"]
                proceeds = qty * px - 9.95
                cash += proceeds
                trades.append({"symbol": sym, "trade_type": "SELL", "trade_date": current_date, "price": px, "quantity": qty, "commission": 9.95, "total_cost": -proceeds, "pnl": proceeds - qty * pos["cost_basis"], "signal_reasons": "rebalance_out"})
                del positions[sym]

        for sig in buys:
            sym = sig["symbol"]
            if sym in positions:
                continue
            px = get_price(conn, sym, current_date)
            if not px or px <= 0:
                continue
            shares = int((cash * 0.1) / px)
            if shares <= 0:
                continue
            cost = shares * px + 9.95
            if cost > cash:
                shares = int((cash - 9.95) / px)
                if shares <= 0:
                    continue
                cost = shares * px + 9.95
            cash -= cost
            positions[sym] = {"symbol": sym, "shares": shares, "cost_basis": px, "entry_date": current_date}
            trades.append({"symbol": sym, "trade_type": "BUY", "trade_date": current_date, "price": px, "quantity": shares, "commission": 9.95, "total_cost": cost, "signal_reasons": f"combo {sig.get('reason','')}"})

        if i % 5 == 0:
            history.append(_snapshot(current_date, cash, positions, conn))

    final_value = cash + sum((get_price(conn, k, dates[-1]) or p["cost_basis"]) * p["shares"] for k, p in positions.items())
    total_return = (final_value - initial_capital) / initial_capital if initial_capital else 0
    years = (end_date - start_date).days / 365.25
    annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
    wins = [t for t in trades if t.get("pnl", 0) > 0]
    win_rate = len(wins) / len(trades) if trades else 0
    return {
        "slug": ":".join(combo_names),
        "strategy": "combo",
        "display_name": " + ".join(combo_names),
        "combo_names": ":".join(combo_names),
        "start_date": str(start_date),
        "end_date": str(end_date),
        "initial_capital": initial_capital,
        "final_value": round(final_value, 2),
        "total_return": round(total_return * 100, 2),
        "annualized_return": round(annualized_return * 100, 2),
        "num_trades": len(trades),
        "win_rate": round(win_rate * 100, 2),
        "max_drawdown": 0.0,
    }


def _persist_sweep_result(conn, user_id, slug, strategy, start, end, params, result):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO backtest_runs (user_id, strategy, parameters, start_date, end_date,
                initial_capital, final_value, total_return, annualized_return, sharpe_ratio, max_drawdown, num_trades, win_rate, status, error_message, completed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'complete', NULL, NOW())
            """,
            (
                user_id,
                f"rules:sweep:{strategy}:{slug}",
                json.dumps({"advisor": slug, "mode": "sweep", "params": params}),
                start.isoformat() if hasattr(start, "isoformat") else str(start),
                end.isoformat() if hasattr(end, "isoformat") else str(end),
                float(result.get("initial_capital", 100000.0)),
                float(result.get("final_value", 0.0)),
                float(result.get("total_return", 0.0)) / 100.0,
                float(result.get("annualized_return", 0.0)) / 100.0,
                0.0,
                float(result.get("max_drawdown", 0.0)) / 100.0,
                int(result.get("num_trades", 0)),
                float(result.get("win_rate", 0.0)) / 100.0,
            ),
        )
        run_id = int(cur.lastrowid)
        for t in result.get("trades", []):
            cur.execute(
                """
                INSERT INTO backtest_trades (backtest_id, symbol, trade_type, trade_date, price, quantity, commission, total_cost, signal_reasons)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    run_id,
                    t["symbol"],
                    t["trade_type"],
                    t["trade_date"].isoformat() if hasattr(t["trade_date"], "isoformat") else str(t["trade_date"]),
                    float(t["price"]),
                    int(t["quantity"]),
                    float(t["commission"]),
                    float(t["total_cost"]),
                    t.get("signal_reasons", ""),
                ),
            )
    conn.commit()


# ============================================================================
# Data access helpers mirrored from rules_backtest.py
# ==================================================================================================================================================

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


def _load_latest_fundamentals(conn: pymysql.connections.Connection) -> dict[str, dict[str, Any]]:
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
        "Communication Services": "XIC.TO", "Distribution Services": "XIC.TO", "Commercial Services": "XIC.TO",
        "Consumer Services": "XIC.TO", "Utilities": "XIC.TO",
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
    return [{"symbol": s, "action": "BUY", "score": 1.0, "confidence": 1.0, "reason": "bond_basket"} for s in ["TBIL.TO", "ZGB.TO", "HMP.TO", "ZAG.TO"]]


def _balanced_signals(conn, advisor, run_date):
    equity = advisor.get("equity", "XIC.TO")
    out = [{"symbol": equity, "action": "BUY", "score": 100.0, "confidence": 0.8, "reason": "equity 60%"}]
    for sym in ["TBIL.TO", "ZGB.TO", "HMP.TO", "ZAG.TO"]:
        out.append({"symbol": sym, "action": "BUY", "score": 1.0, "confidence": 0.7, "reason": "bond basket 40%"})
    return out


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
        follow = float(today_o["close"]) > float(today_o.get("open", today_o["close"])) and float(today_o["close"]) > float(y_c)
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


def _snapshot(current_date, cash, positions, conn):
    total_value = cash
    for sym, pos in positions.items():
        with conn.cursor() as cur:
            cur.execute("SELECT close FROM stockprices WHERE symbol = %s AND price_date <= %s ORDER BY price_date DESC LIMIT 1", (sym, current_date))
            row = cur.fetchone()
        px = float(row["close"]) if row else pos.get("cost_basis", 0)
        total_value += pos["shares"] * px
    return {"date": current_date, "cash": cash, "total_value": total_value, "num_positions": len(positions)}
