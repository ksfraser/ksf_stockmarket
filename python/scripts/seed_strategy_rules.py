"""Seed strategy_rules for all active advisors + clones."""
#!/usr/bin/env python3

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "python" / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "python" / "src"))

from python.src.database import get_connection  # type: ignore


BASE_RISK = {
    "max_positions": 20,
    "stop_pct": 0.10,
    "atr_multiplier": 0,
    "max_pct_portfolio": 0.10,
    "max_risk_pct": 0.01,
    "stop_factor": 2.0,
}

BUY_AND_HOLD_BIAS = {"type": "market_trend", "symbol": "SPY", "lookback_days": 40, "min_days": 20, "op": ">=", "threshold": 0}


def pct(num, denom):
    return round((num - denom) / denom * 100, 2) if denom else 0.0


RULES = [
    {
        "strategy_name": "buffett_quality",
        "bucket": "default",
        "description": "Buffett quality rules: high ROE, low debt, large cap, good margins",
        "indicators": "[]",
        "bias_criteria": json.dumps({"market_trend": BUY_AND_HOLD_BIAS}),
        "entry_rules": json.dumps({
            "market_cap": {"type": "fundamental", "field": "market_cap", "op": ">=", "threshold": 5000000, "lookback_days": 365},
            "roe": {"type": "fundamental", "field": "roe", "op": ">=", "threshold": 1.0, "lookback_days": 365},
            "debt_ratio": {"type": "fundamental", "field": "debt_to_equity", "op": "<=", "threshold": 200.0, "lookback_days": 365},
        }),
        "exit_rules": json.dumps({"rebalance_out": {"type": "always_true"}}),
        "risk_rules": json.dumps({**BASE_RISK, "stop_pct": 0.12, "atr_multiplier": 2.5, "optional_rules": {"min_reward_risk_ratio": 0.0, "emergency_buffer_target_pct": 0.0, "emergency_buffer_grace_days": 0, "max_leverage_ratio": 0.0, "margin_call_buffer_pct": 0.0, "max_margin_utilization_pct": 0.0, "margin_call_grace_hours": 0, "blacklist_asset_classes": []}}),
    },
    {
        "strategy_name": "buffett_quality",
        "bucket": "conservative",
        "description": "Buffett conservative: tighter risk, lower position sizing",
        "indicators": "[]",
        "bias_criteria": json.dumps({"market_trend": BUY_AND_HOLD_BIAS}),
        "entry_rules": json.dumps({
            "market_cap": {"type": "fundamental", "field": "market_cap", "op": ">=", "threshold": 10000000, "lookback_days": 365},
            "roe": {"type": "fundamental", "field": "roe", "op": ">=", "threshold": 12.0, "lookback_days": 365},
            "debt_ratio": {"type": "fundamental", "field": "debt_to_equity", "op": "<=", "threshold": 100.0, "lookback_days": 365},
        }),
        "exit_rules": json.dumps({"rebalance_out": {"type": "always_true"}}),
        "risk_rules": json.dumps({**BASE_RISK, "max_positions": 12, "stop_pct": 0.08, "atr_multiplier": 2.5, "max_pct_portfolio": 0.08, "max_risk_pct": 0.005, "optional_rules": {"min_reward_risk_ratio": 0.0, "emergency_buffer_target_pct": 0.0, "emergency_buffer_grace_days": 0, "max_leverage_ratio": 0.0, "margin_call_buffer_pct": 0.0, "max_margin_utilization_pct": 0.0, "margin_call_grace_hours": 0, "blacklist_asset_classes": []}}),
    },
    {
        "strategy_name": "buffett_quality",
        "bucket": "aggressive",
        "description": "Buffett aggressive: looser filters, higher risk",
        "indicators": "[]",
        "bias_criteria": json.dumps({"market_trend": BUY_AND_HOLD_BIAS}),
        "entry_rules": json.dumps({
            "market_cap": {"type": "fundamental", "field": "market_cap", "op": ">=", "threshold": 1000000, "lookback_days": 365},
            "roe": {"type": "fundamental", "field": "roe", "op": ">=", "threshold": 0.5, "lookback_days": 365},
            "debt_ratio": {"type": "fundamental", "field": "debt_to_equity", "op": "<=", "threshold": 300.0, "lookback_days": 365},
        }),
        "exit_rules": json.dumps({"rebalance_out": {"type": "always_true"}}),
        "risk_rules": json.dumps({**BASE_RISK, "max_positions": 30, "stop_pct": 0.15, "atr_multiplier": 2.5, "max_pct_portfolio": 0.15, "max_risk_pct": 0.02, "optional_rules": {"min_reward_risk_ratio": 0.0, "emergency_buffer_target_pct": 0.0, "emergency_buffer_grace_days": 0, "max_leverage_ratio": 0.0, "margin_call_buffer_pct": 0.0, "max_margin_utilization_pct": 0.0, "margin_call_grace_hours": 0, "blacklist_asset_classes": []}}),
    },
    {
        "strategy_name": "dividend_growth",
        "bucket": "default",
        "description": "Dividend growth rules",
        "indicators": "[]",
        "bias_criteria": "{}",
        "entry_rules": json.dumps({"yield_range": {"type": "fundamental", "field": "dividend_yield", "op": ">=", "threshold": 2.0, "lookback_days": 1095}}),
        "exit_rules": json.dumps({"rebalance_out": {"type": "always_true"}}),
        "risk_rules": json.dumps({**BASE_RISK, "optional_rules": {"min_reward_risk_ratio": 0.0, "emergency_buffer_target_pct": 0.0, "emergency_buffer_grace_days": 0, "max_leverage_ratio": 0.0, "margin_call_buffer_pct": 0.0, "max_margin_utilization_pct": 0.0, "margin_call_grace_hours": 0, "blacklist_asset_classes": []}}),
    },
    {
        "strategy_name": "momentum",
        "bucket": "default",
        "description": "Momentum rules",
        "indicators": "[]",
        "bias_criteria": "{}",
        "entry_rules": json.dumps({"momentum": {"type": "price_momentum", "lookback_days": 252, "window_days": 20, "op": ">=", "threshold": 0}}),
        "exit_rules": json.dumps({"rebalance_out": {"type": "always_true"}}),
        "risk_rules": json.dumps({**BASE_RISK, "max_positions": 15, "stop_pct": 0.12, "atr_multiplier": 2.5, "optional_rules": {"min_reward_risk_ratio": 0.0, "emergency_buffer_target_pct": 0.0, "emergency_buffer_grace_days": 0, "max_leverage_ratio": 0.0, "margin_call_buffer_pct": 0.0, "max_margin_utilization_pct": 0.0, "margin_call_grace_hours": 0, "blacklist_asset_classes": []}}),
    },
    {
        "strategy_name": "bond_basket",
        "bucket": "default",
        "description": "Fixed bond ETF basket",
        "indicators": "[]",
        "bias_criteria": "{}",
        "entry_rules": json.dumps({"always_buy": {"type": "always_true"}}),
        "exit_rules": json.dumps({"rebalance_out": {"type": "always_true"}}),
        "risk_rules": json.dumps({**BASE_RISK, "max_positions": 10, "stop_pct": 0.05, "atr_multiplier": 1.0, "max_pct_portfolio": 0.20, "optional_rules": {"min_reward_risk_ratio": 0.0, "emergency_buffer_target_pct": 0.0, "emergency_buffer_grace_days": 0, "max_leverage_ratio": 0.0, "margin_call_buffer_pct": 0.0, "max_margin_utilization_pct": 0.0, "margin_call_grace_hours": 0, "blacklist_asset_classes": []}}),
    },
    {
        "strategy_name": "balanced_fund",
        "bucket": "default",
        "description": "60/40 equity/bond balanced fund",
        "indicators": "[]",
        "bias_criteria": "{}",
        "entry_rules": json.dumps({"always_buy": {"type": "always_true"}}),
        "exit_rules": json.dumps({"rebalance_out": {"type": "always_true"}}),
        "risk_rules": json.dumps({**BASE_RISK, "max_positions": 10, "stop_pct": 0.05, "atr_multiplier": 1.0, "max_pct_portfolio": 0.20, "optional_rules": {"min_reward_risk_ratio": 0.0, "emergency_buffer_target_pct": 0.0, "emergency_buffer_grace_days": 0, "max_leverage_ratio": 0.0, "margin_call_buffer_pct": 0.0, "max_margin_utilization_pct": 0.0, "margin_call_grace_hours": 0, "blacklist_asset_classes": []}}),
    },
    {
        "strategy_name": "sector",
        "bucket": "default",
        "description": "Generic sector rules",
        "indicators": "[]",
        "bias_criteria": "{}",
        "entry_rules": json.dumps({"sector_membership": {"type": "universe_membership"}}),
        "exit_rules": json.dumps({"rebalance_out": {"type": "always_true"}}),
        "risk_rules": json.dumps({**BASE_RISK, "optional_rules": {"min_reward_risk_ratio": 0.0, "emergency_buffer_target_pct": 0.0, "emergency_buffer_grace_days": 0, "max_leverage_ratio": 0.0, "margin_call_buffer_pct": 0.0, "max_margin_utilization_pct": 0.0, "margin_call_grace_hours": 0, "blacklist_asset_classes": []}}),
    },
]


def bucket_for(name):
    base = ["buffett_quality", "dividend_growth", "momentum", "bond_basket", "balanced_fund", "sector"]
    return name if name in base else "sector_clones"


# Sector advisor clones
SECTOR_ADVISORS = [
    ("sector-consumer-non-durables", "Consumer Non-Durables", "Consumer Non-Durables", "Consumer Defensive"),
    ("sector-electronic-technology", "Electronic Technology", "Electronic Technology", "Technology"),
    ("sector-energy-minerals", "Energy Minerals", "Energy Minerals", "Energy"),
    ("sector-finance", "Finance", "Finance", "Financial Services"),
    ("sector-health-technology", "Health Technology", "Health Technology", "Healthcare"),
    ("sector-industrial-services", "Industrial Services", "Industrial Services", "Industrials"),
    ("sector-miscellaneous", "Miscellaneous", "Miscellaneous", None),
    ("sector-non-energy-minerals", "Non-Energy Minerals", "Non-Energy Minerals", "Basic Materials"),
    ("sector-process-industries", "Process Industries", "Process Industries", "Industrials"),
    ("sector-producer-manufacturing", "Producer Manufacturing", "Producer Manufacturing", "Industrials"),
    ("sector-retail-trade", "Retail Trade", "Retail Trade", "Consumer Cyclical"),
    ("sector-technology-services", "Technology Services", "Technology Services", "Technology"),
    ("sector-transportation", "Transportation", "Transportation", "Industrials"),
]

SECTOR_RULE = {
    "indicators": "[]",
    "bias_criteria": "{}",
    "entry_rules": json.dumps({"sector_membership": {"type": "universe_membership"}}),
    "exit_rules": json.dumps({"rebalance_out": {"type": "always_true"}}),
    "risk_rules": json.dumps({**BASE_RISK, "optional_rules": {"min_reward_risk_ratio": 0.0, "emergency_buffer_target_pct": 0.0, "emergency_buffer_grace_days": 0, "max_leverage_ratio": 0.0, "margin_call_buffer_pct": 0.0, "max_margin_utilization_pct": 0.0, "margin_call_grace_hours": 0, "blacklist_asset_classes": []}}),
}

for slug, disp, sec, fund in SECTOR_ADVISORS:
    RULES.append({
        **SECTOR_RULE,
        "strategy_name": "sector",
        "bucket": "default",
        "description": f"{disp} rules",
    })


def main():
    conn = get_connection()
    inserted = 0
    with conn.cursor() as cur:
        for rule in RULES:
            sql = """
                INSERT INTO strategy_rules (user_id, bucket, strategy_name, description, watchlist, default_timeframe,
                    indicators, bias_criteria, entry_rules, exit_rules, risk_rules, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE
                    description=VALUES(description), watchlist=VALUES(watchlist), default_timeframe=VALUES(default_timeframe),
                    indicators=VALUES(indicators), bias_criteria=VALUES(bias_criteria), entry_rules=VALUES(entry_rules),
                    exit_rules=VALUES(exit_rules), risk_rules=VALUES(risk_rules), is_active=VALUES(is_active), updated_at=NOW()
            """
            cur.execute(sql, (
                1,
                rule["bucket"],
                rule["strategy_name"],
                rule["description"],
                "[]",
                "1D",
                rule["indicators"],
                rule["bias_criteria"],
                rule["entry_rules"],
                rule["exit_rules"],
                rule["risk_rules"],
                1,
            ))
            inserted += 1
    conn.commit()
    conn.close()
    print(f"Seeded/updated {inserted} strategy_rules rows")


if __name__ == "__main__":
    main()
