import pymysql
import json
import logging
from typing import Any

from python.src.reports.taxonomies import get_assignments_for_user, get_portfolio_allocations

logger = logging.getLogger(__name__)


# =====================================================================
# TARGETS
# =====================================================================

class RebalanceTarget:
    def __init__(self, row: dict[str, Any] | None = None):
        self.id: int = 0
        self.user_id: int = 0
        self.name: str = ''
        self.strategy_name: str | None = None
        self.target_type: str = 'taxonomy'
        self.target_allocations: dict[str, float] = {}
        self.tolerance_pct: float = 5.0
        self.rebalance_frequency: str = 'monthly'
        self.active: bool = True
        if row:
            self.id = int(row.get('id', 0) or 0)
            self.user_id = int(row.get('user_id', 0) or 0)
            self.name = str(row.get('name', ''))
            self.strategy_name = str(row.get('strategy_name', '') or '') or None
            self.target_type = str(row.get('target_type', 'taxonomy'))
            raw = row.get('target_allocations', '{}')
            self.target_allocations = json.loads(raw) if isinstance(raw, str) else (raw or {})
            self.tolerance_pct = float(row.get('tolerance_pct', 5) or 5)
            self.rebalance_frequency = str(row.get('rebalance_frequency', 'monthly'))
            self.active = bool(int(row.get('active', 1) or 1))

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'strategy_name': self.strategy_name,
            'target_type': self.target_type,
            'target_allocations': self.target_allocations,
            'tolerance_pct': self.tolerance_pct,
            'rebalance_frequency': self.rebalance_frequency,
            'active': self.active,
        }


def create_target(db: pymysql.connections.Connection, user_id: int, name: str, target_type: str, target_allocations: dict, tolerance_pct: float = 5.0, rebalance_frequency: str = 'monthly', strategy_name: str | None = None) -> int | None:
    with db.cursor() as cur:
        cur.execute(
            """INSERT INTO rebalancing_targets
               (user_id, name, target_type, target_allocations, tolerance_pct, rebalance_frequency, strategy_name)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (user_id, name, target_type, json.dumps(target_allocations), tolerance_pct, rebalance_frequency, strategy_name),
        )
        return int(cur.lastrowid)


def update_target(db: pymysql.connections.Connection, target_id: int, **fields) -> None:
    if not fields:
        return
    if 'target_allocations' in fields and isinstance(fields['target_allocations'], dict):
        fields['target_allocations'] = json.dumps(fields['target_allocations'])
    set_clause = ', '.join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [target_id]
    with db.cursor() as cur:
        cur.execute(f"UPDATE rebalancing_targets SET {set_clause} WHERE id = %s", values)
    db.commit()


def toggle_target(db: pymysql.connections.Connection, target_id: int, active: bool) -> None:
    with db.cursor() as cur:
        cur.execute("UPDATE rebalancing_targets SET active = %s WHERE id = %s", (1 if active else 0, target_id))
    db.commit()


def delete_target(db: pymysql.connections.Connection, target_id: int) -> None:
    with db.cursor() as cur:
        cur.execute("DELETE FROM rebalancing_targets WHERE id = %s", (target_id,))
    db.commit()


def list_targets(db: pymysql.connections.Connection, user_id: int, active_only: bool = True) -> list[RebalanceTarget]:
    sql = "SELECT * FROM rebalancing_targets WHERE user_id = %s"
    params: list[Any] = [user_id]
    if active_only:
        sql += " AND active = 1"
    sql += " ORDER BY name"
    with db.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        desc = [d[0] for d in cur.description]
        return [RebalanceTarget(dict(zip(desc, r))) for r in rows]


# =====================================================================
# REBALANCE CALCULATION
# =====================================================================

def compute_rebalance(db: pymysql.connections.Connection, user_id: int, target_id: int) -> dict[str, Any]:
    target = _load_target(db, target_id)
    if not target:
        return {'error': 'Target not found'}

    if target.target_type == 'taxonomy':
        current = get_portfolio_allocations(db, user_id, int(next(iter(target.target_allocations.keys())) if False else 0))
        # For taxonomy targets, keys are taxonomy IDs? No — target_allocations should be taxonomy_id -> weight
        actual: dict[str, float] = {}
        for tax_id_str, weight in target.target_allocations.items():
            tax_id = int(tax_id_str)
            alloc = get_portfolio_allocations(db, user_id, tax_id)
            for sym, pct in alloc.items():
                actual[sym] = actual.get(sym, 0.0) + pct
    else:
        actual = {}  # geometric/sector handled similarly

    total = sum(actual.values()) or 1.0
    actual = {k: v / total for k, v in actual.items()}

    drifts: list[dict[str, Any]] = []
    all_syms = sorted(set(list(target.target_allocations.keys()) + list(actual.keys())))
    for sym in all_syms:
        target_pct = float(target.target_allocations.get(str(sym), 0.0))
        actual_pct = float(actual.get(str(sym), 0.0)) * 100
        target_pct *= 100
        drift = abs(actual_pct - target_pct)
        needs = drift > target.tolerance_pct
        drifts.append({
            'symbol': str(sym),
            'target_pct': round(target_pct, 2),
            'actual_pct': round(actual_pct, 2),
            'drift': round(drift, 2),
            'needs_rebalance': needs,
        })
    return {
        'target': target.to_dict(),
        'drifts': sorted(drifts, key=lambda x: x['drift'], reverse=True),
        'needs_rebalance': any(d['needs_rebalance'] for d in drifts),
    }


def _load_target(db: pymysql.connections.Connection, target_id: int) -> RebalanceTarget | None:
    with db.cursor() as cur:
        cur.execute("SELECT * FROM rebalancing_targets WHERE id = %s", (target_id,))
        row = cur.fetchone()
        if not row:
            return None
        desc = [d[0] for d in cur.description]
        return RebalanceTarget(dict(zip(desc, row)))
    return None
