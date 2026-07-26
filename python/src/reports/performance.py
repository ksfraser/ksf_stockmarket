import logging
from datetime import date, timedelta
from typing import Any
from dataclasses import dataclass

import pymysql
import json

from python.src.reports.taxonomies import get_assignments_for_user

logger = logging.getLogger(__name__)


# =====================================================================
# HELPERS
# =====================================================================

def _rows_to_dicts(rows, desc):
    if rows is None:
        return []
    return [dict(zip(desc, row)) for row in rows]


def _get_price(conn, symbol: str, target_date: date) -> float | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT close FROM stockprices WHERE symbol = %s AND price_date <= %s ORDER BY price_date DESC LIMIT 1",
            (symbol, target_date),
        )
        row = cur.fetchone()
        if not row:
            return None
        val = row[0] if isinstance(row, tuple) else row.get('close')
        return float(val) if val is not None else None


# =====================================================================
# TTWROR — True-Time Weighted Rate of Return
# =====================================================================

def compute_twror(conn: pymysql.connections.Connection, user_id: int, start_date: date, end_date: date) -> dict[str, Any]:
    """
    Calculate TTWROR across all accounts.
    Uses daily portfolio market-value snapshots adjusted for external cash flows.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT trade_date, type, symbol, total, account_type, quantity
            FROM transactions
            WHERE user_id = %s
              AND trade_date BETWEEN %s AND %s
            ORDER BY trade_date ASC
            """,
            (user_id, start_date.isoformat(), end_date.isoformat()),
        )
        tx_rows = cur.fetchall()
        desc = [d[0] for d in cur.description]
    txs = _rows_to_dicts(tx_rows, desc)

    flows: dict[date, float] = {}
    for t in txs:
        d = t['trade_date']
        if isinstance(d, str):
            d = date.fromisoformat(d)
        total = float(t.get('total') or 0)
        acct = str(t.get('account_type', ''))
        typ = str(t.get('type', ''))
        # External flows: DEPOSIT/WITHDRAWAL/DIVIDEND/INTEREST/FEE/TAX
        if typ in ('DEPOSIT', 'WITHDRAWAL', 'DIVIDEND', 'DIVIDEND-RECV', 'INTEREST', 'INTEREST_CHARGE', 'FEE', 'TAX'):
            flows[d] = flows.get(d, 0.0) + total
        else:
            # Trade cash flows: BUY/SELL/SPLIT/TRANSFER/DELIVERY
            # Transfer in same account is not external
            flows[d] = flows.get(d, 0.0) + total

    # Build daily market values
    dates: list[date] = []
    values: list[float] = []
    cur_d = start_date
    while cur_d <= end_date:
        dates.append(cur_d)
        mv = _portfolio_market_value(conn, user_id, cur_d)
        values.append(mv)
        cur_d += timedelta(days=1)

    if not values or all(v == 0 for v in values):
        return {'twror': None, 'irr': None, 'daily_values': [], 'message': 'Insufficient data'}

    # TTWROR = prod(1 + (mt - m{t-1} - CFt) / m{t-1}) - 1
    num = 1.0
    den = 0.0
    for i in range(1, len(dates)):
        prev = values[i - 1]
        curr = values[i]
        cf = flows.get(dates[i], 0.0)
        if prev > 0:
            num *= (curr - cf) / prev
        elif curr > 0:
            den = curr
    if num == 0 and den == 0:
        twror = 0.0
    else:
        twror = num - 1.0

    years = (end_date - start_date).days / 365.25
    annualized = (1 + twror) ** (1 / years) - 1 if years > 0 else 0.0

    return {
        'twror': round(twror * 100, 3),
        'annualized': round(annualized * 100, 3),
        'years': round(years, 2),
        'start': str(start_date),
        'end': str(end_date),
    }


def _portfolio_market_value(conn, user_id: int, as_of: date) -> float:
    with conn.cursor() as cur:
        cur.execute(
            """SELECT p.symbol, p.shares, p.cost_basis, p.account_type, sp.close
               FROM portfolio p
               LEFT JOIN stockprices sp ON sp.symbol = p.symbol AND sp.price_date <= %s
               WHERE p.user_id = %s AND p.shares > 0
               ORDER BY sp.price_date DESC
            """,
            (as_of.isoformat(), user_id),
        )
        rows = cur.fetchall()
        desc = [d[0] for d in cur.description]
    total = 0.0
    for r in rows:
        data = dict(zip(desc, r))
        close = data.get('close')
        price = float(close) if close is not None else float(data.get('cost_basis', 0) or 0)
        total += float(data.get('shares', 0) or 0) * price
    return total


# =====================================================================
# SECURITIES PERFORMANCE
# =====================================================================

def securities_performance(conn, user_id: int, start_date: date, end_date: date, account_type: str | None = None) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        sql = "SELECT symbol, shares, cost_basis, account_type FROM portfolio WHERE user_id = %s AND shares > 0"
        params: list[Any] = [user_id]
        if account_type:
            sql += " AND account_type = %s"
            params.append(account_type)
        cur.execute(sql, params)
        rows = cur.fetchall()
        desc = [d[0] for d in cur.description]
    holdings = _rows_to_dicts(rows, desc)
    results: list[dict[str, Any]] = []
    for h in holdings:
        sym = h['symbol']
        cur_price = _get_price(conn, sym, end_date)
        cost = float(h['cost_basis'] or 0)
        shares = float(h['shares'] or 0)
        mv = shares * cur_price if cur_price else 0
        pnl = mv - cost
        pnl_pct = (pnl / cost * 100) if cost > 0 else 0.0
        results.append({
            'symbol': sym,
            'account_type': h.get('account_type', ''),
            'shares': shares,
            'cost_basis': cost,
            'current_price': cur_price,
            'market_value': mv,
            'pnl': round(pnl, 2),
            'pnl_pct': round(pnl_pct, 2),
        })
    results.sort(key=lambda x: x['pnl'], reverse=True)
    return results


# =====================================================================
# PAYMENTS / DIVIDENDS SUMMARY
# =====================================================================

def payments_summary(conn, user_id: int, start_date: date, end_date: date) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            """SELECT type, SUM(total) AS total, COUNT(*) AS count
               FROM transactions
               WHERE user_id = %s
                 AND trade_date BETWEEN %s AND %s
                 AND type IN ('DIVIDEND', 'DIV-RECV', 'INTEREST', 'INTEREST_CHARGE', 'FEE', 'TAX')
               GROUP BY type
            """,
            (user_id, start_date.isoformat(), end_date.isoformat()),
        )
        rows = cur.fetchall()
        desc = [d[0] for d in cur.description]
    rows = _rows_to_dicts(rows, desc)
    by_type = {r['type']: {'count': int(r['count']), 'total': round(float(r['total'] or 0), 2)} for r in rows}
    dividends = by_type.get('DIVIDEND', {'count': 0, 'total': 0})
    interest = (by_type.get('INTEREST', {'total': 0})['total'] +
                by_type.get('DIV-RECV', {'total': 0})['total'])
    fees = by_type.get('FEE', {'total': 0})['total'] + by_type.get('TAX', {'total': 0})['total']
    return {
        'dividends': dividends,
        'interest': round(interest, 2),
        'fees': round(fees, 2),
        'by_type': by_type,
    }


# =====================================================================
# TAX LOT SUMMARY (FIFO)
# =====================================================================

def tax_lot_summary(conn, user_id: int, symbol: str | None = None) -> list[dict[str, Any]]:
    """Return FIFO lot summary for realized gain/loss reporting."""
    with conn.cursor() as cur:
        sql = """
            SELECT t.symbol, t.trade_date, t.type, t.quantity, t.price, t.total, t.commission, t.account_type
            FROM transactions t
            WHERE t.user_id = %s AND t.symbol <> 'CASH'
              AND t.type IN ('BUY', 'SELL', 'DIV-RECV')
            """
        params: list[Any] = [user_id]
        if symbol:
            sql += " AND t.symbol = %s"
            params.append(symbol)
        sql += " ORDER BY t.trade_date ASC, t.id ASC"
        cur.execute(sql, params)
        rows = cur.fetchall()
        desc = [d[0] for d in cur.description]
    txs = _rows_to_dicts(rows, desc)
    lots: dict[str, list[dict[str, Any]]] = {}
    for t in txs:
        sym = t['symbol']
        typ = t['type']
        qty = float(t['quantity'] or 0)
        price = float(t['price'] or 0)
        total = float(t['total'] or 0)
        comm = float(t['commission'] or 0)
        lots.setdefault(sym, []).append({
            'trade_date': str(t['trade_date']),
            'type': typ,
            'quantity': qty,
            'price': price,
            'total': total,
            'commission': comm,
            'account_type': t['account_type'],
        })
    summary: list[dict[str, Any]] = []
    for sym, sym_lots in lots.items():
        fifo: list[dict[str, Any]] = []
        realized = 0.0
        for lot in sym_lots:
            if lot['type'] == 'BUY':
                fifo.append({'qty': lot['quantity'], 'price': lot['price'], 'cost': lot['total']})
            elif lot['type'] == 'SELL':
                sell_qty = lot['quantity']
                sell_price = lot['price']
                sell_total = lot['total']
                cost = 0.0
                remaining = sell_qty
                while remaining > 0.0001 and fifo:
                    lot0 = fifo[0]
                    take = min(remaining, lot0['qty'])
                    lot_cost = take * lot0['price']
                    proceeds = take * sell_price
                    pnl = proceeds - lot_cost
                    realized += pnl
                    remaining -= take
                    lot0['qty'] -= take
                    lot0['cost'] -= lot_cost
                    if lot0['qty'] < 0.0001:
                        fifo.pop(0)
        open_lots = [l for l in fifo if l['qty'] > 0.0001]
        summary.append({
            'symbol': sym,
            'open_lots': len(open_lots),
            'realized_pnl': round(realized, 2),
            'open_qty': round(sum(l['qty'] for l in open_lots), 4),
        })
    summary.sort(key=lambda x: x['realized_pnl'], reverse=True)
    return summary


# =====================================================================
# HEAT MAP DATA
# =====================================================================

def heat_map_data(conn, user_id: int, valuation_date: date | None = None) -> dict[str, Any]:
    """
    Returns per-symbol performance/size/momentum-like data suitable for a heat map.
    Metrics: 1-week momentum, 1-month momentum, volatility, allocation size.
    """
    if valuation_date is None:
        valuation_date = date.today()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT symbol, shares, cost_basis, account_type FROM portfolio WHERE user_id = %s AND shares > 0",
            (user_id,),
        )
        rows = cur.fetchall()
        desc = [d[0] for d in cur.description]
    holdings = _rows_to_dicts(rows, desc)
    out: list[dict[str, Any]] = []
    for h in holdings:
        sym = h['symbol']
        cur_px = _get_price(conn, sym, valuation_date)
        if not cur_px:
            continue
        px_1w = _get_price(conn, sym, valuation_date - timedelta(days=7))
        px_1m = _get_price(conn, sym, valuation_date - timedelta(days=30))
        px_3m = _get_price(conn, sym, valuation_date - timedelta(days=90))
        mom_1w = ((cur_px / px_1w) - 1) * 100 if px_1w else 0.0
        mom_1m = ((cur_px / px_1m) - 1) * 100 if px_1m else 0.0
        mom_3m = ((cur_px / px_3m) - 1) * 100 if px_3m else 0.0
        mv = float(h['shares'] or 0) * cur_px
        out.append({
            'symbol': sym,
            'account_type': h.get('account_type', ''),
            'market_value': round(mv, 2),
            'mom_1w': round(mom_1w, 2),
            'mom_1m': round(mom_1m, 2),
            'mom_3m': round(mom_3m, 2),
            'allocation_pct': 0.0,  # caller can normalize
        })
    total_mv = sum(x['market_value'] for x in out) or 1.0
    for x in out:
        x['allocation_pct'] = round((x['market_value'] / total_mv) * 100, 2)
    return {
        'valuation_date': str(valuation_date),
        'total_value': round(total_mv, 2),
        'securities': out,
    }
