import pymysql
import logging
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)


# Forward declarations / simple dataclasses


class Taxonomy:
    def __init__(self, row: dict[str, Any] | None = None):
        self.id: int = 0
        self.user_id: int | None = None
        self.name: str = ''
        self.type: str = 'custom'
        self.parent_id: int | None = None
        self.is_active: bool = True
        if row:
            self.id = int(row.get('id', 0) or 0)
            self.user_id = int(row['user_id']) if row.get('user_id') is not None else None
            self.name = str(row.get('name', ''))
            self.type = str(row.get('type', 'custom'))
            pid = row.get('parent_id')
            self.parent_id = int(pid) if pid is not None else None
            self.is_active = bool(int(row.get('is_active', 1) or 1))

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'type': self.type,
            'parent_id': self.parent_id,
            'is_active': self.is_active,
        }


class TaxonomyAssignment:
    def __init__(self, row: dict[str, Any] | None = None):
        self.id: int = 0
        self.user_id: int = 0
        self.taxonomy_id: int = 0
        self.symbol: str = ''
        self.weight: float = 0.0
        self.notes: str = ''
        self.created_at: str | None = None
        self.updated_at: str | None = None
        if row:
            self.id = int(row.get('id', 0) or 0)
            self.user_id = int(row.get('user_id', 0) or 0)
            self.taxonomy_id = int(row.get('taxonomy_id', 0) or 0)
            self.symbol = str(row.get('symbol', ''))
            self.weight = float(row.get('weight', 0) or 0)
            self.notes = str(row.get('notes', ''))
            self.created_at = str(row['created_at']) if row.get('created_at') else None
            self.updated_at = str(row['updated_at']) if row.get('updated_at') else None

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'taxonomy_id': self.taxonomy_id,
            'symbol': self.symbol,
            'weight': self.weight,
            'notes': self.notes,
        }


# =====================================================================
# CREATE / UPDATE / DELETE
# =====================================================================

def create_taxonomy(db: pymysql.connections.Connection, user_id: int | None, name: str, type: str, parent_id: int | None = None) -> int | None:
    with db.cursor() as cur:
        cur.execute(
            """INSERT INTO taxonomies (user_id, name, type, parent_id)
               VALUES (%s, %s, %s, %s)""",
            (user_id, name, type, parent_id),
        )
        return int(cur.lastrowid)


def update_taxonomy(db: pymysql.connections.Connection, taxonomy_id: int, **fields) -> None:
    if not fields:
        return
    set_clause = ', '.join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [taxonomy_id]
    with db.cursor() as cur:
        cur.execute(f"UPDATE taxonomies SET {set_clause} WHERE id = %s", values)
    db.commit()


def delete_taxonomy(db: pymysql.connections.Connection, taxonomy_id: int) -> None:
    with db.cursor() as cur:
        cur.execute("DELETE FROM taxonomy_assignments WHERE taxonomy_id = %s", (taxonomy_id,))
        cur.execute("DELETE FROM taxonomies WHERE id = %s", (taxonomy_id,))
    db.commit()


def assign_symbol(db: pymysql.connections.Connection, user_id: int, taxonomy_id: int, symbol: str, weight: float = 0.0, notes: str = '') -> int | None:
    with db.cursor() as cur:
        cur.execute(
            """INSERT INTO taxonomy_assignments (user_id, taxonomy_id, symbol, weight, notes)
               VALUES (%s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE weight = VALUES(weight), notes = VALUES(notes)""",
            (user_id, taxonomy_id, symbol, weight, notes),
        )
        return int(cur.lastrowid)


def remove_assignment(db: pymysql.connections.Connection, assignment_id: int) -> None:
    with db.cursor() as cur:
        cur.execute("DELETE FROM taxonomy_assignments WHERE id = %s", (assignment_id,))
    db.commit()


# =====================================================================
# QUERIES
# =====================================================================

def list_taxonomies(db: pymysql.connections.Connection, user_id: int, include_global: bool = True) -> list[Taxonomy]:
    where = ["is_active = 1"]
    params: list[Any] = []
    if include_global:
        where.append("(user_id IS NULL OR user_id = %s)")
        params.append(user_id)
    else:
        where.append("user_id = %s")
        params.append(user_id)
    sql = f"SELECT * FROM taxonomies WHERE {' AND '.join(where)} ORDER BY type, name"
    with db.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        desc = [d[0] for d in cur.description]
        return [Taxonomy(dict(zip(desc, r))) for r in rows]


def get_assignments_for_user(db: pymysql.connections.Connection, user_id: int, taxonomy_id: int | None = None) -> list[TaxonomyAssignment]:
    sql = "SELECT * FROM taxonomy_assignments WHERE user_id = %s"
    params: list[Any] = [user_id]
    if taxonomy_id is not None:
        sql += " AND taxonomy_id = %s"
        params.append(taxonomy_id)
    sql += " ORDER BY symbol"
    with db.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        desc = [d[0] for d in cur.description]
        return [TaxonomyAssignment(dict(zip(desc, r))) for r in rows]


def get_symbol_taxonomies(db: pymysql.connections.Connection, user_id: int, symbol: str) -> list[dict[str, Any]]:
    sql = """
        SELECT ta.*, t.name AS taxonomy_name, t.type AS taxonomy_type
        FROM taxonomy_assignments ta
        JOIN taxonomies t ON t.id = ta.taxonomy_id
        WHERE ta.user_id = %s AND ta.symbol = %s
        ORDER BY t.type, t.name
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id, symbol))
        return [
            {k: (str(v) if v is not None else '') for k, v in zip([d[0] for d in cur.description], row)}
            for row in cur.fetchall()
        ]


def get_portfolio_allocations(db: pymysql.connections.Connection, user_id: int, taxonomy_id: int) -> dict[str, float]:
    assignments = get_assignments_for_user(db, user_id, taxonomy_id)
    sym_values: dict[str, float] = {}
    with db.cursor() as cur:
        cur.execute(
            "SELECT symbol, cost_basis_total FROM portfolio WHERE user_id = %s AND shares > 0",
            (user_id,),
        )
        rows = cur.fetchall()
        desc = [d[0] for d in cur.description]
        for row in rows:
            data = dict(zip(desc, row))
            total = data.get('cost_basis_total')
            sym_values[data['symbol']] = float(total) if total is not None else 0.0
        for cash_sym in ['CASH-CAD', 'CASH-USD', 'CASH-EUR', 'CASH-GBP', 'CASH-CNY']:
            if cash_sym not in sym_values:
                cur.execute(
                    """SELECT SUM(total) AS total FROM transactions
                       WHERE user_id = %s AND symbol = %s AND account_type = 'portfolio'""",
                    (user_id, cash_sym),
                )
                r = cur.fetchone()
                if r:
                    total = r[0]
                    sym_values[cash_sym] = float(total) if total is not None else 0.0

    total_val = sum(sym_values.values()) or 1.0
    allocations: dict[str, float] = {}
    for a in assignments:
        val = sym_values.get(a.symbol, 0.0)
        allocations[a.symbol] = val / total_val
    return allocations


def seed_common_taxonomies(db: pymysql.connections.Connection) -> None:
    defaults = [
        ('Region', 'region'),
        ('Canada', 'region'),
        ('United States', 'region'),
        ('Europe', 'region'),
        ('Asia', 'region'),
        ('Sector', 'sector'),
        ('Technology', 'sector'),
        ('Healthcare', 'sector'),
        ('Financials', 'sector'),
        ('Consumer', 'sector'),
        ('Energy', 'sector'),
        ('Real Estate', 'sector'),
        ('Strategy', 'strategy'),
        ('Buffett Quality', 'strategy'),
        ('Momentum', 'strategy'),
        ('Bond', 'strategy'),
        ('Balanced', 'strategy'),
    ]
    with db.cursor() as cur:
        for name, type_ in defaults:
            cur.execute(
                "INSERT IGNORE INTO taxonomies (user_id, name, type) VALUES (NULL, %s, %s)",
                (name, type_),
            )
    db.commit()

