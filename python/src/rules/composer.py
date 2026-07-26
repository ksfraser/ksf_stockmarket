"""Generic advisor composer: blend rule sets from multiple existing advisors."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "python" / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "python" / "src"))

from python.src.database import get_connection  # type: ignore

logger = logging.getLogger(__name__)

# Keys in risk_rules that are numeric and should be blended via weighted average.
_NUMERIC_RISK_KEYS = (
    "max_positions",
    "stop_pct",
    "atr_multiplier",
    "max_pct_portfolio",
    "max_risk_pct",
    "stop_factor",
)


# ---------------------------------------------------------------------------
# Data access helpers
# ---------------------------------------------------------------------------

def load_advisor_rule_set(strategy_name: str, bucket: str = "default") -> dict[str, Any]:
    """Load the active rule set for a single advisor."""
    conn = get_connection()
    try:
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
            raise ValueError(
                f"No active strategy_rules found for strategy_name='{strategy_name}' bucket='{bucket}'"
            )
        payload: dict[str, Any] = {}
        for key in ("indicators", "bias_criteria", "entry_rules", "exit_rules", "risk_rules"):
            raw = row.get(key)
            if raw is not None:
                try:
                    payload[key] = json.loads(raw) if isinstance(raw, str) else raw
                except json.JSONDecodeError:
                    payload[key] = {}
            else:
                payload[key] = {}
        return payload
    finally:
        conn.close()


def blend_rule_sets(
    advisors: list[dict[str, Any]], weights: list[float]
) -> dict[str, Any]:
    """Blend multiple advisor rule sets into a single composite.

    Numeric risk parameters are blended as weighted averages.
    Dict-based rule collections (entry_rules, exit_rules, bias_criteria)
    and indicators are unioned across advisors.
    """
    if not advisors:
        raise ValueError("At least one advisor rule set is required")
    if len(advisors) != len(weights):
        raise ValueError("advisors and weights must have the same length")

    total = sum(weights)
    if total <= 0:
        raise ValueError("Weights must sum to a positive number")
    norm_weights = [w / total for w in weights]

    blended: dict[str, Any] = {
        "indicators": [],
        "bias_criteria": {},
        "entry_rules": {},
        "exit_rules": {},
        "risk_rules": {},
    }

    for advisor, w in zip(advisors, norm_weights):
        # Indiators: union lists
        for item in advisor.get("indicators", []):
            if isinstance(item, dict) and item not in blended["indicators"]:
                blended["indicators"].append(item)
            elif not isinstance(item, dict) and item not in blended["indicators"]:
                blended["indicators"].append(item)

        # Dict-type rule collections: union keys from all advisors
        for key in ("bias_criteria", "entry_rules", "exit_rules"):
            for sub_key, sub_val in advisor.get(key, {}).items():
                blended[key][sub_key] = sub_val

        # Risk rules: weighted average over numeric keys; copy others verbatim
        risk_src = advisor.get("risk_rules", {})
        for key in _NUMERIC_RISK_KEYS:
            if key in risk_src:
                blended["risk_rules"][key] = blended["risk_rules"].get(key, 0.0) + float(risk_src[key]) * w
        for key, val in risk_src.items():
            if key not in _NUMERIC_RISK_KEYS and key not in blended["risk_rules"]:
                blended["risk_rules"][key] = val

    # Round numeric risk values for cleanliness
    for key in _NUMERIC_RISK_KEYS:
        if key in blended["risk_rules"]:
            blended["risk_rules"][key] = round(blended["risk_rules"][key], 6)

    return blended


def save_composite_strategy(
    user_id: int, name: str, description: str, blended_rules: dict[str, Any]
) -> int:
    """Persist the blended strategy as a new strategy_rules row.

    Returns the new row id.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO strategy_rules
                    (user_id, bucket, strategy_name, description, watchlist, default_timeframe,
                     indicators, bias_criteria, entry_rules, exit_rules, risk_rules, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE
                    description=VALUES(description),
                    watchlist=VALUES(watchlist),
                    default_timeframe=VALUES(default_timeframe),
                    indicators=VALUES(indicators),
                    bias_criteria=VALUES(bias_criteria),
                    entry_rules=VALUES(entry_rules),
                    exit_rules=VALUES(exit_rules),
                    risk_rules=VALUES(risk_rules),
                    is_active=VALUES(is_active),
                    updated_at=NOW()
                """,
                (
                    user_id,
                    "composites",
                    name,
                    description,
                    "[]",
                    "1D",
                    json.dumps(blended_rules.get("indicators", [])),
                    json.dumps(blended_rules.get("bias_criteria", {})),
                    json.dumps(blended_rules.get("entry_rules", {})),
                    json.dumps(blended_rules.get("exit_rules", {})),
                    json.dumps(blended_rules.get("risk_rules", {})),
                    1,
                ),
            )
            new_id = conn.insert_id()
        conn.commit()
        return new_id
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compose custom advisors by blending rule sets from existing advisors."
    )
    parser.add_argument(
        "--blend",
        required=True,
        help="Colon-separated advisor strategy names (e.g. buffett_quality:momentum)",
    )
    parser.add_argument(
        "--weights",
        required=False,
        default=None,
        help="Colon-separated weights (e.g. 0.7:0.3). Defaults to equal weights.",
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Name for the new composite strategy",
    )
    parser.add_argument(
        "--desc",
        required=False,
        default="",
        help="Description for the new composite strategy",
    )
    parser.add_argument(
        "--bucket",
        required=False,
        default="default",
        help="Source bucket for advisor rule sets (default: default)",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Persist the blended strategy to the database",
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=1,
        help="User ID owner for the saved strategy (default: 1)",
    )
    args = parser.parse_args()

    advisor_names = [a.strip() for a in args.blend.split(":") if a.strip()]
    if not advisor_names:
        parser.error("--blend must contain at least one advisor name")

    if args.weights:
        weight_strs = [w.strip() for w in args.weights.split(":") if w.strip()]
        if len(weight_strs) != len(advisor_names):
            print(
                "Error: --weights count must match --blend advisor count",
                file=sys.stderr,
            )
            return 1
        try:
            weights = [float(w) for w in weight_strs]
        except ValueError as exc:
            print(f"Error: invalid weight value: {exc}", file=sys.stderr)
            return 1
    else:
        weights = [1.0] * len(advisor_names)

    total = sum(weights)
    if total <= 0:
        print("Error: weights must sum to a positive number", file=sys.stderr)
        return 1
    norm_weights = [w / total for w in weights]

    print(f"Loading {len(advisor_names)} advisor rule sets from bucket='{args.bucket}'...")
    advisors: list[dict[str, Any]] = []
    for name in advisor_names:
        try:
            rs = load_advisor_rule_set(name, bucket=args.bucket)
            advisors.append(rs)
            print(f"  Loaded: {name}")
        except Exception as exc:
            print(f"Error loading advisor '{name}': {exc}", file=sys.stderr)
            return 1

    print(f"Blending with weights: {' : '.join(f'{w:.3f}' for w in norm_weights)}")
    blended = blend_rule_sets(advisors, norm_weights)

    print("\n--- Blended Strategy ---")
    print(f"Name     : {args.name}")
    print(f"Desc     : {args.desc or '(none)'}")
    source_summary = ", ".join(
        f"{n} ({w:.1%})" for n, w in zip(advisor_names, norm_weights)
    )
    print(f"Advisors : {source_summary}")
    print(f"Indicators ({len(blended['indicators'])}): {json.dumps(blended['indicators'], indent=2)}")
    print(f"Bias ({len(blended['bias_criteria'])}): {json.dumps(blended['bias_criteria'], indent=2)}")
    print(f"Entry ({len(blended['entry_rules'])}): {json.dumps(blended['entry_rules'], indent=2)}")
    print(f"Exit ({len(blended['exit_rules'])}): {json.dumps(blended['exit_rules'], indent=2)}")
    print(f"Risk: {json.dumps(blended['risk_rules'], indent=2)}")

    if args.save:
        print(f"\nSaving composite strategy '{args.name}' for user_id={args.user_id}...")
        new_id = save_composite_strategy(args.user_id, args.name, args.desc or args.name, blended)
        print(f"Saved with id={new_id}")
    else:
        print("\n(Use --save to persist to database)")

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
