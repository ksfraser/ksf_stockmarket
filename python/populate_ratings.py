#!/usr/bin/env python3
"""
populate_ratings.py — Compute and store rating scores for screener filtering.

Writes to tradingview_screener_results with preset names:
  - buffett
  - zacks
  - vectorvest
  - exit_risk

Each row JSON includes `score`, `checks`, and supporting metrics.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

from python.db_connector import get_connection

MARKET = "local"
LIMIT = 5000


def _sql_date(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def load_symbols() -> list[str]:
    db = get_connection()
    cur = db.cursor(dictionary=True)
    cur.execute(
        "SELECT symbol FROM fundamentals "
        "GROUP BY symbol ORDER BY COUNT(*) DESC LIMIT %s",
        (LIMIT,),
    )
    symbols = [r["symbol"] for r in cur.fetchall()]
    cur.close()
    db.close()
    return symbols


def load_fundamentals(symbol: str) -> dict[str, Any] | None:
    db = get_connection()
    cur = db.cursor(dictionary=True)
    cur.execute(
        "SELECT * FROM fundamentals WHERE symbol = %s ORDER BY fetch_date DESC LIMIT 1",
        (symbol,),
    )
    row = cur.fetchone()
    cur.close()
    db.close()
    if not row:
        return None
    return dict(row)


def load_indicators(symbol: str) -> dict[str, Any] | None:
    db = get_connection()
    cur = db.cursor(dictionary=True)
    cur.execute(
        "SELECT * FROM indicators WHERE symbol = %s ORDER BY price_date DESC LIMIT 1",
        (symbol,),
    )
    row = cur.fetchone()
    cur.close()
    db.close()
    if not row:
        return None
    return dict(row)


def load_price_history(symbol: str, days: int = 365) -> list[dict[str, Any]]:
    db = get_connection()
    cur = db.cursor(dictionary=True)
    start = _sql_date(date.today() - timedelta(days=days + 30))
    cur.execute(
        "SELECT price_date, open, high, low, close, volume "
        "FROM stockprices WHERE symbol = %s AND price_date >= %s ORDER BY price_date ASC",
        (symbol, start),
    )
    rows = cur.fetchall()
    cur.close()
    db.close()
    return [dict(r) for r in rows]


def calc_buffett(f: dict[str, Any] | None, ind: dict[str, Any] | None, close: float = 0) -> dict[str, Any]:
    if not f:
        return {"score": None, "total": 0, "max": 100, "checks": {}, "reason": "no fundamentals"}
    checks = {}
    score = 0
    tests = [
        ("ROE > 15%", (f.get("roe") or 0) > 0.15, 15),
        ("D/E < 0.5", (f.get("debt_to_equity") or 99) < 0.5, 15),
        ("Margin > 10%", (f.get("profit_margin") or 0) > 0.10, 10),
        ("Positive FCF", (f.get("free_cash_flow") or 0) > 0, 15),
        ("Payout < 60%", 0 < (f.get("payout_ratio") or 1) < 0.60, 10),
        ("Rev Growth+", (f.get("revenue_growth") or 0) > 0, 10),
        ("CR > 1.5", (f.get("current_ratio") or 0) > 1.5, 10),
        ("Beta < 1.2", 0 < (f.get("beta") or 99) < 1.2, 5),
        ("P/E < 25x", 0 < (f.get("trailing_pe") or 100) < 25, 5),
    ]
    for name, passed, pts in tests:
        checks[name] = bool(passed)
        if passed:
            score += pts
    return {"score": score, "total": score, "max": 100, "checks": checks}


def _linear_regression(ys: list[float]) -> tuple[float, float]:
    n = len(ys)
    if n < 2:
        return 0.0, 0.0
    xs = list(range(n))
    sx = sum(xs)
    sy = sum(ys)
    sxy = sum(a * b for a, b in zip(xs, ys))
    sxx = sum(a * a for a in xs)
    den = n * sxx - sx * sx
    if den == 0:
        return 0.0, 0.0
    slope = (n * sxy - sx * sy) / den
    intercept = (sy - slope * sx) / n
    ss_res = sum((ys[i] - (slope * xs[i] + intercept)) ** 2 for i in range(n))
    ss_tot = sum((yi - sy / n) ** 2 for yi in ys)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return slope, r2


def calc_vectorvest(symbol: str) -> dict[str, Any]:
    history = load_price_history(symbol)
    closes = [float(r["close"]) for r in history]
    n = len(closes)
    checks: dict[str, Any] = {}
    pass_count = 0

    # 1) Smooth uptrend
    if n >= 60:
        sample = closes[-250:]
        slope, r2 = _linear_regression(sample)
        smooth = bool(slope > 0 and r2 >= 0.55)
        checks["smooth_uptrend"] = {
            "passed": smooth,
            "label": "Smooth Uptrend",
            "detail": f"R²={round(r2, 2)} {'✓' if smooth else '✗'}",
        }
        if smooth:
            pass_count += 1
    else:
        checks["smooth_uptrend"] = {"passed": False, "label": "Smooth Uptrend", "detail": "insufficient data"}

    # 2) Price rising
    price_rising = bool(n > 20 and closes[-1] > closes[-21])
    checks["price_rising"] = {
        "passed": price_rising,
        "label": "Price Rising (20D)",
        "detail": "close > 20d ago ✓" if price_rising else "close < 20d ago ✗",
    }
    if price_rising:
        pass_count += 1

    # 3) Earnings rising (fundamentals)
    fund = load_fundamentals(symbol)
    earnings_rising = False
    if fund:
        for key in ("forward_eps", "earnings_growth", "trailing_eps"):
            val = fund.get(key)
            try:
                if val is not None and float(val) > 0:
                    earnings_rising = True
                    break
            except (TypeError, ValueError):
                pass
    checks["earnings_rising"] = {
        "passed": earnings_rising,
        "label": "Earnings Rising",
        "detail": "positive eps/growth ✓" if earnings_rising else "no positive earnings ✗",
    }
    if earnings_rising:
        pass_count += 1

    # 4) Market trend — skipped in standalone evaluation
    checks["market_ok"] = {"passed": None, "label": "Market Trend (SPY)", "detail": "N/A"}

    # 5) Follow-through
    follow = False
    if n >= 2 and history:
        c = float(history[-1]["close"])
        o = float(history[-1].get("open", c))
        yc = float(history[-2]["close"])
        follow = bool(c > o and c > yc)
    checks["follow_through"] = {
        "passed": follow,
        "label": "Follow-Through",
        "detail": "close > open & > yday ✓" if follow else "no follow-through ✗",
    }
    if follow:
        pass_count += 1

    score = pass_count * 20
    return {
        "score": score,
        "pass_count": pass_count,
        "max": 5,
        "checks": checks,
        "symbol": symbol,
    }


def calc_zacks(f: dict[str, Any] | None, ind: dict[str, Any] | None, close: float = 0) -> dict[str, Any]:
    if not f:
        return {
            "score": None,
            "rank": None,
            "rank_text": "N/A",
            "composite": None,
            "value_grade": "N/A",
            "growth_grade": "N/A",
            "momentum_grade": "N/A",
            "vgm_grade": "N/A",
            "value_pct": 0,
            "growth_pct": 0,
            "momentum_pct": 0,
            "vgm_pct": 0,
            "checks": {"Fundamental data not available": False},
        }

    value_score = 0
    max_value = 0
    checks: dict[str, bool] = {}

    # Value 40
    try:
        pe = float(f.get("trailing_pe") or 0)
    except (TypeError, ValueError):
        pe = 0
    if pe > 0:
        checks["P/E < 20x"] = pe < 20
        max_value += 10
        if pe < 15:
            value_score += 10
        elif pe < 20:
            value_score += 7
        elif pe < 30:
            value_score += 4
    try:
        pb = float(f.get("price_to_book") or 0)
    except (TypeError, ValueError):
        pb = 0
    if pb > 0:
        checks["P/B < 2.0"] = pb < 2.0
        max_value += 10
        if pb < 1.0:
            value_score += 10
        elif pb < 2.0:
            value_score += 7
        elif pb < 3.0:
            value_score += 4
    try:
        fcf = float(f.get("free_cash_flow") or 0)
        mkt = float(f.get("market_cap") or 0)
    except (TypeError, ValueError):
        fcf = 0
        mkt = 0
    if fcf and mkt > 0:
        fcf_yield = fcf / mkt
        checks["FCF Yield > 3%"] = fcf_yield > 0.03
        max_value += 10
        if fcf_yield > 0.06:
            value_score += 10
        elif fcf_yield > 0.03:
            value_score += 7
        elif fcf_yield > 0.01:
            value_score += 4
    try:
        de = float(f.get("debt_to_equity") or -1)
    except (TypeError, ValueError):
        de = -1
    if de >= 0:
        checks["D/E < 0.8"] = de < 0.8
        max_value += 10
        if de < 0.3:
            value_score += 10
        elif de < 0.8:
            value_score += 7
        elif de < 1.5:
            value_score += 4

    value_pct = min(100, (value_score / max_value) * 100) if max_value > 0 else 0
    value_grade = (
        "A" if value_pct >= 90 else "B" if value_pct >= 80 else "C" if value_pct >= 70 else "D" if value_pct >= 60 else "F"
    )

    growth_score = 0
    max_growth = 0
    try:
        eg = float(f.get("earnings_growth") or 0)
    except (TypeError, ValueError):
        eg = 0
    if eg:
        checks["EPS Growth > 10%"] = eg > 0.10
        max_growth += 15
        if eg > 0.20:
            growth_score += 15
        elif eg > 0.10:
            growth_score += 10
        elif eg > 0:
            growth_score += 5
    try:
        rg = float(f.get("revenue_growth") or 0)
    except (TypeError, ValueError):
        rg = 0
    if rg:
        checks["Revenue Growth > 5%"] = rg > 0.05
        max_growth += 15
        if rg > 0.15:
            growth_score += 15
        elif rg > 0.05:
            growth_score += 10
        elif rg > 0:
            growth_score += 5

    growth_pct = min(100, (growth_score / max_growth) * 100) if max_growth > 0 else 0
    growth_grade = (
        "A" if growth_pct >= 90 else "B" if growth_pct >= 80 else "C" if growth_pct >= 70 else "D" if growth_pct >= 60 else "F"
    )

    momentum_score = 0
    try:
        sma200 = float((ind or {}).get("sma_200") or 0)
    except (TypeError, ValueError):
        sma200 = 0
    if sma200 > 0 and close > 0:
        vs_sma = close / sma200
        checks["Price > SMA200"] = vs_sma > 1.0
        if vs_sma > 1.05:
            momentum_score += 10
        elif vs_sma > 1.0:
            momentum_score += 7
        elif vs_sma > 0.95:
            momentum_score += 4
    try:
        rsi = float((ind or {}).get("rsi_14") or 0)
    except (TypeError, ValueError):
        rsi = 0
    if rsi:
        checks["RSI 30-65"] = 30 <= rsi <= 65
        if 40 <= rsi <= 60:
            momentum_score += 10
        elif 30 <= rsi <= 70:
            momentum_score += 6
        elif 20 <= rsi <= 80:
            momentum_score += 3

    momentum_pct = min(100, (momentum_score / 20) * 100) if 20 else 0
    momentum_grade = (
        "A"
        if momentum_pct >= 90
        else "B"
        if momentum_pct >= 80
        else "C"
        if momentum_pct >= 70
        else "D"
        if momentum_pct >= 60
        else "F"
    )

    vgm_pct = round((value_pct + growth_pct + momentum_pct) / 3, 1)
    vgm_grade = (
        "A"
        if vgm_pct >= 90
        else "B"
        if vgm_pct >= 80
        else "C"
        if vgm_pct >= 70
        else "D"
        if vgm_pct >= 60
        else "F"
    )
    composite = round((value_pct * 0.40) + (growth_pct * 0.30) + (momentum_pct * 0.20) + (vgm_pct * 0.10), 1)
    rank = 5
    if composite >= 90:
        rank = 1
    elif composite >= 80:
        rank = 2
    elif composite >= 70:
        rank = 3
    elif composite >= 60:
        rank = 4
    rank_text = {1: "Strong Buy", 2: "Buy", 3: "Hold", 4: "Sell", 5: "Strong Sell"}[rank]

    return {
        "score": composite,
        "rank": rank,
        "rank_text": rank_text,
        "composite": composite,
        "value_grade": value_grade,
        "growth_grade": growth_grade,
        "momentum_grade": momentum_grade,
        "vgm_grade": vgm_grade,
        "value_pct": round(value_pct, 1),
        "growth_pct": round(growth_pct, 1),
        "momentum_pct": round(momentum_pct, 1),
        "vgm_pct": round(vgm_pct, 1),
        "checks": checks,
    }


def calc_exit_risk(f: dict[str, Any] | None, ind: dict[str, Any] | None, close: float = 0) -> dict[str, Any]:
    if not close or close <= 0:
        return {"composite_exit_risk": None, "individual_signals": {}, "signal_weights": {}, "n_signals_triggered": 0, "n_signals_total": 0}
    weights = {}
    signals = {}
    triggered = 0
    total = 0

    # trailing stop
    if ind and ind.get("atr_14") and ind.get("high_60"):
        total += 1
        weights["trailing_stop_breach"] = 0.20
        stop = float(ind["high_60"]) - (3.0 * float(ind["atr_14"]))
        hit = close < stop
        signals["trailing_stop_breach"] = hit
        if hit:
            triggered += 1
    # rsi overbought
    if ind and ind.get("rsi_14"):
        total += 1
        weights["rsi_overbought"] = 0.10
        rsi = float(ind["rsi_14"])
        hit = rsi > 65
        signals["rsi_overbought"] = hit
        if hit:
            triggered += 1
    # ma200 breakdown
    if ind and ind.get("sma_200") and float(ind["sma_200"]) > 0:
        total += 1
        weights["ma200_breakdown"] = 0.15
        vs = close / float(ind["sma_200"])
        hit = vs < 0.95
        signals["ma200_breakdown"] = hit
        if hit:
            triggered += 1
    # bb upper
    if ind and ind.get("bb_20_2_0_upper") and ind.get("bb_20_2_0_lower"):
        total += 1
        weights["bb_upper_touch"] = 0.10
        upper = float(ind["bb_20_2_0_upper"])
        lower = float(ind["bb_20_2_0_lower"])
        pos = (close - lower) / (upper - lower) if upper != lower else 0.5
        hit = pos > 0.95
        signals["bb_upper_touch"] = hit
        if hit:
            triggered += 1
    # roe deterioration
    if f and f.get("roe") is not None:
        total += 1
        weights["roe_deterioration"] = 0.10
        hit = float(f.get("roe", 0)) < 0.10
        signals["roe_deterioration"] = hit
        if hit:
            triggered += 1
    # debt/equity rise
    if f and f.get("debt_to_equity") is not None:
        total += 1
        weights["debt_equity_rise"] = 0.10
        hit = float(f.get("debt_to_equity", 0)) > 0.60
        signals["debt_equity_rise"] = hit
        if hit:
            triggered += 1
    # fcf negative
    if f and f.get("free_cash_flow") is not None:
        total += 1
        weights["fcf_negative"] = 0.10
        hit = float(f.get("free_cash_flow", 0)) < 0
        signals["fcf_negative"] = hit
        if hit:
            triggered += 1
    # pe extreme
    if f and f.get("trailing_pe"):
        total += 1
        weights["pe_extreme"] = 0.08
        try:
            hit = 0 < float(f.get("trailing_pe", 0)) > 25
        except (TypeError, ValueError):
            hit = False
        signals["pe_extreme"] = hit
        if hit:
            triggered += 1

    composite = triggered / total if total > 0 else 0
    return {
        "composite_exit_risk": round(composite, 4),
        "individual_signals": signals,
        "signal_weights": weights,
        "n_signals_triggered": triggered,
        "n_signals_total": total,
    }


def store(preset: str, market: str, symbol: str, payload: dict[str, Any]) -> None:
    db = get_connection()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute(
            """
            INSERT INTO tradingview_screener_results (preset_name, market, symbol, data, run_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
                data = VALUES(data),
                run_at = VALUES(run_at)
            """,
            (preset, market, symbol, json.dumps(payload, default=str)),
        )
        db.commit()
    finally:
        cur.close()
        db.close()


def run() -> None:
    symbols = load_symbols()
    print(f"Loaded {len(symbols)} symbols for rating population.")
    count = 0
    for symbol in symbols:
        f = load_fundamentals(symbol)
        ind = load_indicators(symbol)
        close = 0
        if ind and ind.get("close"):
            try:
                close = float(ind["close"])
            except (TypeError, ValueError):
                close = 0

        buffett = calc_buffett(f, ind, close)
        zacks = calc_zacks(f, ind, close)
        vectorvest = calc_vectorvest(symbol)
        exit_risk = calc_exit_risk(f, ind, close)

        buffett_payload = {
            "score": buffett.get("total"),
            "checks": buffett.get("checks", {}),
            "reason": buffett.get("reason"),
            "symbol": symbol,
        }
        zacks_payload = {
            "score": zacks.get("composite"),
            "rank": zacks.get("rank"),
            "rank_text": zacks.get("rank_text"),
            "composite": zacks.get("composite"),
            "value_grade": zacks.get("value_grade"),
            "growth_grade": zacks.get("growth_grade"),
            "momentum_grade": zacks.get("momentum_grade"),
            "vgm_grade": zacks.get("vgm_grade"),
            "value_pct": zacks.get("value_pct"),
            "growth_pct": zacks.get("growth_pct"),
            "momentum_pct": zacks.get("momentum_pct"),
            "vgm_pct": zacks.get("vgm_pct"),
            "checks": zacks.get("checks", {}),
            "symbol": symbol,
        }
        vv_payload = {
            "score": vectorvest.get("score"),
            "pass_count": vectorvest.get("pass_count"),
            "max": vectorvest.get("max"),
            "checks": vectorvest.get("checks", {}),
            "symbol": symbol,
        }
        exit_payload = {
            "composite_exit_risk": exit_risk.get("composite_exit_risk"),
            "individual_signals": exit_risk.get("individual_signals", {}),
            "signal_weights": exit_risk.get("signal_weights", {}),
            "n_signals_triggered": exit_risk.get("n_signals_triggered", 0),
            "n_signals_total": exit_risk.get("n_signals_total", 0),
            "symbol": symbol,
        }

        store("buffett", MARKET, symbol, buffett_payload)
        store("zacks", MARKET, symbol, zacks_payload)
        store("vectorvest", MARKET, symbol, vv_payload)
        store("exit_risk", MARKET, symbol, exit_payload)
        count += 1
        if count % 100 == 0:
            print(f"  processed {count}/{len(symbols)}...")

    print(f"Done. Populated ratings for {count} symbols across 4 presets.")


if __name__ == "__main__":
    run()
