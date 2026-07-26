"""Rule engine for strategy_rules-driven advisor execution."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RuleResult:
    rule_key: str
    passed: bool
    value: Any = None
    meta: dict[str, Any] = field(default_factory=dict)


class RuleEngine:
    """Evaluate rule bundles stored in strategy_rules fields."""

    def __init__(self, db: Any, bucket: str = "default") -> None:
        self.db = db
        self.bucket = bucket

    def load(self, strategy_name: str) -> dict[str, Any]:
        sql = """
            SELECT id, indicators, bias_criteria, entry_rules, exit_rules, risk_rules
            FROM strategy_rules
            WHERE strategy_name = %s AND bucket = %s AND is_active = 1
            ORDER BY updated_at DESC
            LIMIT 1
        """
        with self.db.cursor() as cur:
            cur.execute(sql, (strategy_name, self.bucket))
            row = cur.fetchone()
        if not row:
            return {}
        payload: dict[str, Any] = {}
        for key in ("indicators", "bias_criteria", "entry_rules", "exit_rules", "risk_rules"):
            raw = row.get(key)
            if raw:
                try:
                    payload[key] = json.loads(raw)
                except json.JSONDecodeError:
                    payload[key] = {}
            else:
                payload[key] = {}
        payload["_row_id"] = row.get("id")
        return payload

    def evaluate_entry(
        self, symbol: str, run_date: date, context: dict[str, Any] | None = None
    ) -> RuleResult:
        context = context or {}
        rules = self.load(context.get("strategy_name", ""))
        if not rules:
            return RuleResult(rule_key="entry", passed=False, value=0.0, meta={"error": "no rules"})

        entry_rules = rules.get("entry_rules", {})
        if not entry_rules:
            return RuleResult(rule_key="entry", passed=False, value=0.0, meta={"error": "no entry rules"})

        results: list[RuleResult] = []
        for rule_key, rule in entry_rules.items():
            try:
                res = _eval_rule(self.db, rule_key, rule, symbol, run_date, context)
            except Exception as exc:
                logger.debug("Rule %s failed for %s: %s", rule_key, symbol, exc)
                res = RuleResult(rule_key=rule_key, passed=False, value=None, meta={"error": str(exc)})
            results.append(res)

        if not results:
            return RuleResult(rule_key="entry", passed=False, value=0.0)

        passed = [r for r in results if r.passed]
        value = float(len(passed))
        confidence = min(value / max(len(results), 1), 1.0) if results else 0.0
        meta = {r.rule_key: {"passed": r.passed, "value": r.value, **(r.meta or {})} for r in results}
        return RuleResult(
            rule_key="entry",
            passed=value > 0,
            value=value,
            meta={"score": value, "confidence": confidence, "rules": meta},
        )

    def evaluate_exit(
        self, symbol: str, run_date: date, position: dict[str, Any] | None = None, context: dict[str, Any] | None = None
    ) -> RuleResult:
        context = context or {}
        rules = self.load(context.get("strategy_name", ""))
        if not rules:
            return RuleResult(rule_key="exit", passed=False)

        exit_rules = rules.get("exit_rules", {})
        if not exit_rules:
            return RuleResult(rule_key="exit", passed=False)

        position = position or {}
        hit = False
        for rule_key, rule in exit_rules.items():
            try:
                if _eval_rule(self.db, rule_key, rule, symbol, run_date, context, position=position).passed:
                    hit = True
                    break
            except Exception:
                continue
        return RuleResult(rule_key="exit", passed=hit)


def _eval_rule(db: Any, rule_key: str, rule: dict[str, Any], symbol: str, run_date: date, context: dict[str, Any], position: dict[str, Any] | None = None) -> RuleResult:
    rtype = str(rule.get("type", "")).lower()
    position = position or {}
    value: Any = None

    if rtype == "fundamental":
        field_name = rule.get("field", "")
        op = rule.get("op", ">=")
        threshold = rule.get("threshold", 0)
        lookback = int(rule.get("lookback_days", 365))
        start = run_date - timedelta(days=lookback)
        with db.cursor() as cur:
            cur.execute(
                f"SELECT {field_name} FROM fundamentals WHERE symbol = %s AND fetch_date >= %s ORDER BY fetch_date DESC LIMIT 1",
                (symbol, start),
            )
            row = cur.fetchone()
        raw = row.get(field_name) if row else None
        try:
            value = float(raw) if raw is not None else None
        except (TypeError, ValueError):
            value = None
        if value is not None and str(field_name).lower() == "roe":
            value = _normalize_roe(value)
            threshold = _normalize_roe(float(threshold))
        passed = _compare(value, op, threshold)

        return RuleResult(rule_key=rule_key, passed=passed, value=value, meta={"field": field_name, "op": op, "threshold": threshold})

    if rtype == "price_momentum":
        lookback = int(rule.get("lookback_days", 252))
        cutoff = run_date - timedelta(days=int(rule.get("window_days", 20)))
        start = run_date - timedelta(days=lookback)
        with db.cursor() as cur:
            cur.execute(
                "SELECT close FROM stockprices WHERE symbol = %s AND price_date BETWEEN %s AND %s ORDER BY price_date ASC",
                (symbol, start, cutoff),
            )
            rows = [float(r["close"]) for r in cur.fetchall()]
        if len(rows) < 2:
            return RuleResult(rule_key=rule_key, passed=False, value=0.0)
        value = (rows[-1] - rows[0]) / rows[0] * 100.0 if rows[0] else 0.0
        op = rule.get("op", ">=")
        threshold = float(rule.get("threshold", 0))
        passed = _compare(value, op, threshold)
        return RuleResult(rule_key=rule_key, passed=passed, value=value)

    if rtype == "universe_membership":
        sector = rule.get("sector", "")
        etf = rule.get("etf", "")
        fundamental_sector = rule.get("fundamental_sector", "")
        symbols = []
        if etf and symbol == etf:
            return RuleResult(rule_key=rule_key, passed=True, value=1.0)
        if fundamental_sector:
            start = run_date - timedelta(days=365)
            with db.cursor() as cur:
                cur.execute(
                    "SELECT DISTINCT symbol FROM fundamentals WHERE sector = %s AND fetch_date >= %s ORDER BY symbol LIMIT 40",
                    (fundamental_sector, start),
                )
                symbols = [r["symbol"] for r in cur.fetchall()]
        passed = symbol in symbols
        return RuleResult(rule_key=rule_key, passed=passed, value=1.0 if passed else 0.0, meta={"universe_size": len(symbols)})

    if rtype == "market_trend":
        sym = rule.get("symbol", "SPY")
        lookback = int(rule.get("lookback_days", 40))
        min_days = int(rule.get("min_days", 20))
        start = run_date - timedelta(days=lookback)
        with db.cursor() as cur:
            cur.execute(
                "SELECT close FROM stockprices WHERE symbol = %s AND price_date BETWEEN %s AND %s ORDER BY price_date ASC",
                (sym, start, run_date),
            )
            rows = [float(r["close"]) for r in cur.fetchall()]
        if not rows or len(rows) < min_days:
            return RuleResult(rule_key=rule_key, passed=False, value=None)
        trend_up = rows[-1] > rows[-min_days] if len(rows) > min_days else rows[-1] > rows[0]
        return RuleResult(rule_key=rule_key, passed=trend_up, value=rows[-1] - rows[-min_days])

    if rtype == "exit_price":
        stop_pct = float(rule.get("stop_pct", 0))
        atr_mult = float(rule.get("atr_multiplier", 0))
        period = int(rule.get("atr_period", 14))
        entry_price = float(position.get("cost_basis", 0))
        if entry_price <= 0:
            return RuleResult(rule_key=rule_key, passed=False, value=None)

        last_px = None
        atr = None
        start = run_date - timedelta(days=period * 3)
        with db.cursor() as cur:
            cur.execute(
                "SELECT close FROM stockprices WHERE symbol = %s AND price_date BETWEEN %s AND %s ORDER BY price_date ASC",
                (symbol, start, run_date),
            )
            rows = [float(r["close"]) for r in cur.fetchall()]
        if rows:
            last_px = rows[-1]
            if len(rows) >= 2:
                trs = [abs(rows[i] - rows[i - 1]) for i in range(1, len(rows))]
                atr = sum(trs[-period:]) / min(len(trs), period)

        hit = False
        if atr_mult and atr:
            hit = last_px <= (entry_price - atr_mult * atr)
        elif stop_pct:
            hit = last_px <= (entry_price * (1 - stop_pct))
        return RuleResult(rule_key=rule_key, passed=hit, value={"last_price": last_px, "atr14": atr, "threshold": entry_price - atr_mult * atr if atr else entry_price * (1 - stop_pct)})

    if rtype == "always_true":
        return RuleResult(rule_key=rule_key, passed=True, value=1.0)

    return RuleResult(rule_key=rule_key, passed=False, value=None, meta={"unsupported": rtype})


def _compare(value: Any, op: str, threshold: Any) -> bool:
    if value is None:
        return False
    try:
        value = float(value)
        threshold = float(threshold)
    except (TypeError, ValueError):
        return False
    if op == ">=":
        return value >= threshold
    if op == ">":
        return value > threshold
    if op == "<=":
        return value <= threshold
    if op == "<":
        return value < threshold
    if op == "==" or op == "=":
        return value == threshold
    return False


def _normalize_roe(value: float) -> float:
    """Normalize ROE to percentage scale.

    Some feeds store ROE as 0..1+ (e.g. 1.41 = 141%), others as 0..100+ (e.g. 17.8).
    Heuristic: if value <= 5, assume decimal and multiply by 100.
    """
    if value is None:
        return 0.0
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    if v <= 5:
        return v * 100.0
    return v
