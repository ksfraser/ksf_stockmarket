#!/usr/bin/env python3
"""Compare ATR trailing-stop multipliers across the same advisor universe.

Runs rules_backtest 3 times with atr_multiplier forced to 2.0, 2.25, 2.5.
Other risk parameters (stop_pct, max_positions, etc.) come from strategy_rules.
"""
from __future__ import annotations

from typing import Any
import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "python" / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "python" / "src"))

from python.src.database import get_connection  # type: ignore
import python.rules_backtest as rb  # type: ignore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run_comparison(start: date, end: date, initial: float, commission: float, frequency: str, slug: str | None = None) -> dict:
    conn = get_connection()
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

    if slug:
        advisors = [a for a in advisors if a["slug"] == slug]

    # Pre-load original risk rules so we can mutate without DB roundtrips
    for adv in advisors:
        adv.setdefault("bucket", "default")
        raw = rb.load_risk_rules(conn, adv["strategy"], adv.get("bucket", "default"))
        adv["_base_risk"] = raw

    multipliers = [2.0, 2.25, 2.5]
    comparison: dict[str, Any] = {"start": start.isoformat(), "end": end.isoformat(), "initial_capital": initial, "multipliers": {}}

    for mult in multipliers:
        logger.info("=== ATR multiplier %.2f ===", mult)
        # Monkey-patch loader so every advisor gets forced atr_multiplier
        original_loader = rb.load_risk_rules

        def patched_loader(conn2, strategy_name, bucket="default"):
            risk = original_loader(conn2, strategy_name, bucket)
            risk["atr_multiplier"] = mult
            return risk

        rb.load_risk_rules = patched_loader  # type: ignore[assignment]

        results = []
        for adv in advisors:
            try:
                res = rb.run_rules_backtest(conn, adv, start, end, initial, commission, frequency)
                results.append(res)
            except Exception:
                logger.exception("Advisor %s backtest crashed", adv["slug"])
                results.append({"slug": adv["slug"], "error": "exception"})

        rb.load_risk_rules = original_loader  # type: ignore[assignment]

        summary_path = REPO_ROOT / "python" / f"rules_backtest_summary_atr_{mult:.2f}.json"
        payload = {
            "generated_at": date.today().isoformat(),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "initial_capital": initial,
            "atr_multiplier": mult,
            "advisors": results,
        }
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)

        comparison["multipliers"][f"{mult:.2f}"] = {
            "summary": str(summary_path),
            "advisors": results,
        }

    conn.close()
    return comparison


def print_comparison(comparison: dict) -> None:
    print("\n=== ATR Multiplier Comparison ===")
    print(f"Period : {comparison['start']} → {comparison['end']}")
    print(f"Capital: ${comparison['initial_capital']:,.2f}")
    print()
    header = f"{'Advisor':<30} {'2.00x':>10} {'2.25x':>10} {'2.50x':>10} {'Best':>8}"
    print(header)
    print("-" * len(header))
    advisors = []
    for m, data in comparison["multipliers"].items():
        for adv in data["advisors"]:
            advisors.append((m, adv))
    slugs = sorted({adv["slug"] for _, data in comparison["multipliers"].items() for adv in data["advisors"]})
    best_counts = {s: [] for s in slugs}
    for slug in slugs:
        vals = {}
        for m in ("2.00", "2.25", "2.50"):
            adv = next((a for a in comparison["multipliers"][m]["advisors"] if a.get("slug") == slug), {})
            vals[m] = adv.get("total_return", adv.get("error", float("-inf")))
        best = max(vals, key=vals.get)
        best_counts[slug].append(best)
        print(f"{slug:<30} {vals['2.00']:>10.2f} {vals['2.25']:>10.2f} {vals['2.50']:>10.2f} {best:>8}")
    print()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Compare ATR multipliers 2.0 vs 2.25 vs 2.5")
    p.add_argument("--start", default="2024-01-01")
    p.add_argument("--end", default=None)
    p.add_argument("--initial", type=float, default=100000.0)
    p.add_argument("--commission", type=float, default=9.95)
    p.add_argument("--frequency", default="weekly", choices=["daily", "weekly", "monthly", "quarterly"])
    p.add_argument("--slug", default=None)
    p.add_argument("--bucket", default="default")
    args = p.parse_args(argv)
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end) if args.end else date.today()
    comparison = run_comparison(start, end, args.initial, args.commission, args.frequency, args.slug)
    print_comparison(comparison)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
