#!/usr/bin/env python3
"""Lipper-style peer-relative stock scoring across multiple peer groups
(sector / industry / style_box) plus advisor portfolio effectiveness.

Peer-relative scores: Total Return, Preservation (loss avoidance), Consistent Return
(risk-adjusted) -> percentile-ranked within each peer group -> 1-5; composite = avg of three.
See finance/lipper-stock-scores skill for method and the pitfalls that were hit/fixed.

Run from the stockmarket-app root:
    python3 scripts/compute_lipper_stock_scores.py
"""
import os, re, sys, math, datetime
from collections import defaultdict

# Resolve the centralized DB connector (python/db_connector.py) whether this script
# lives in scripts/ or a dev mount.
_APP_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
_KNOWN_ROOT = '/var/www/stockmarket-app'
for _p in (_APP_ROOT, _KNOWN_ROOT):
    if os.path.isdir(os.path.join(_p, 'python')):
        sys.path.insert(0, _p)
from python.db_connector import get_connection

SQL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'sql', 'lipper_stock_scores.sql')
RF = 0.02


def avg(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def pct_rank_scores(pairs, higher_better=True):
    """pairs: list of (sym, metric). Return {sym: 1..5}, top 20% -> 5."""
    clean = [(s, m) for s, m in pairs if m is not None]
    if not clean:
        return {}
    order = sorted(clean, key=lambda x: x[1])
    n = len(clean)
    out = {}
    for i, (s, m) in enumerate(order):
        rank_from_top = (n - 1 - i) if higher_better else i
        pct = rank_from_top / (n - 1) if n > 1 else 1.0
        out[s] = 5 if pct >= 0.8 else 4 if pct >= 0.6 else 3 if pct >= 0.4 else 2 if pct >= 0.2 else 1
    return out


def rank_groups(groups, metric_fn, higher_better=True):
    """Rank symbols within each peer_group_value separately."""
    out = {}
    for pgv, syms in groups.items():
        pairs = [(s, metric_fn(s)) for s in syms]
        out.update(pct_rank_scores(pairs, higher_better))
    return out


def terciles(vals):
    vals = sorted(v for v in vals if v is not None)
    if not vals:
        return (None, None)
    n = len(vals)
    return (vals[n // 3], vals[2 * n // 3])


def main():
    conn = get_connection()
    cur = conn.cursor()
    # DDL -- strip comments so a ';' inside a -- comment can't break the split
    with open(SQL_FILE) as f:
        sql = f.read()
    sql = re.sub(r'--[^\n]*', '', sql)
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
    for stmt in [s.strip() for s in sql.split(';') if s.strip()]:
        cur.execute(stmt)
    conn.commit()

    cur = conn.cursor(dictionary=True)
    cur2 = conn.cursor(dictionary=True)

    # ---- attributes: sector/industry from fundamentals (latest row), fallback symbol_master ----
    attr = {}
    cur.execute("""SELECT f.symbol, f.sector, f.industry, f.market_cap, f.trailing_pe, f.price_to_book, f.peg_ratio
                   FROM fundamentals f
                   JOIN (SELECT symbol, MAX(fetch_date) md FROM fundamentals GROUP BY symbol) m
                     ON m.symbol=f.symbol AND m.md=f.fetch_date""")
    for r in cur.fetchall():
        attr[r['symbol']] = dict(sector=r['sector'], industry=r['industry'],
                                 market_cap=r['market_cap'], pe=r['trailing_pe'],
                                 pb=r['price_to_book'], peg=r['peg_ratio'])
    cur.execute("SELECT symbol, sector, industry FROM symbol_master WHERE sector IS NOT NULL AND sector<>''")
    for r in cur.fetchall():
        a = attr.setdefault(r['symbol'], {})
        a.setdefault('sector', r['sector'])
        a.setdefault('industry', r['industry'])

    # ---- style_box: size (market_cap terciles) x style (valuation terciles) ----
    caps = [a['market_cap'] for a in attr.values() if a.get('market_cap') is not None]
    cap_lo, cap_hi = terciles(caps)
    for a in attr.values():
        vs = [v for v in (a.get('pe'), a.get('pb'), a.get('peg')) if v is not None and v > 0]
        a['_val'] = sum(vs) / len(vs) if vs else None
    vals = [a['_val'] for a in attr.values() if a.get('_val') is not None]
    val_lo, val_hi = terciles(vals)

    def style_box(a):
        mc = a.get('market_cap')
        size = 'Mid'
        if mc is not None and cap_lo is not None and cap_hi is not None:
            size = 'Small' if mc <= cap_lo else ('Large' if mc >= cap_hi else 'Mid')
        v = a.get('_val')
        style = 'Blend'
        if v is not None and val_lo is not None and val_hi is not None:
            style = 'Value' if v <= val_lo else ('Growth' if v >= val_hi else 'Blend')
        return f"{size} {style}"

    pg = {}
    for s, a in attr.items():
        d = {}
        if a.get('sector'):
            d['sector'] = a['sector']
        if a.get('industry'):
            d['industry'] = a['industry']
        d['style_box'] = style_box(a)
        pg[s] = d

    # only score symbols that actually trade
    cur.execute("SELECT DISTINCT symbol FROM stockprices")
    have = set(r['symbol'] for r in cur.fetchall())
    pg = {s: d for s, d in pg.items() if s in have}

    cur.execute("SELECT MAX(price_date) FROM stockprices")
    asof = cur.fetchone()['MAX(price_date)']
    asof_o = asof.toordinal()
    print("as_of:", asof, "| symbols with attributes & prices:", len(pg))

    # ---- per-symbol metrics (batch-fetch prices in chunks to minimise DB round-trips) ----
    metrics = {}
    syms = list(pg.keys())
    CH = 300
    for ci in range(0, len(syms), CH):
        chunk = syms[ci:ci + CH]
        ph = ', '.join(['%s'] * len(chunk))
        cur.execute(
            f"SELECT symbol, price_date, adj_close FROM stockprices "
            f"WHERE symbol IN ({ph}) ORDER BY symbol, price_date", chunk)
        buf = defaultdict(list)
        for r in cur.fetchall():
            if r['adj_close'] is not None and float(r['adj_close']) > 0:
                buf[r['symbol']].append((r['price_date'].toordinal(), float(r['adj_close'])))
        for s in chunk:
            pairs = buf.get(s, [])
            if len(pairs) < 60:
                continue
            last_c = pairs[-1][1]

            def close_at(years):
                tgt = asof_o - years * 365.25
                for d, c in reversed(pairs):
                    if d <= tgt:
                        return c
                return None

            def ret(years):
                c0 = close_at(years)
                return (last_c / c0 - 1) if c0 else None

            jan1 = datetime.date.fromordinal(asof_o).replace(month=1, day=1).toordinal()
            ytd0 = None
            for d, c in reversed(pairs):
                if d <= jan1:
                    ytd0 = c
                    break
            ytd = (last_c / ytd0 - 1) if ytd0 else None
            r1, r3, r5, r10 = ret(1), ret(3), ret(5), ret(10)

            win = [(d, c) for d, c in pairs if d >= asof_o - 3 * 365.25]
            vol = dd = sharpe = sortino = None
            if len(win) >= 60:
                rets = [win[i][1] / win[i - 1][1] - 1 for i in range(1, len(win)) if win[i - 1][1] > 0]
                if rets:
                    mean_r = sum(rets) / len(rets)
                    var = sum((x - mean_r) ** 2 for x in rets) / len(rets)
                    vol = math.sqrt(var) * math.sqrt(252)
                    downs = [x for x in rets if x < 0]
                    dd = math.sqrt(sum(x * x for x in downs) / len(rets)) * math.sqrt(252)
                    ann = mean_r * 252
                    sharpe = (ann - RF) / vol if vol else None
                    sortino = (ann - RF) / dd if dd else None

            def monthly_neg_sum(years):
                tgt = asof_o - years * 365.25
                sub = [(d, c) for d, c in pairs if d >= tgt]
                if len(sub) < 2:
                    return None
                mlast = {}
                for d, c in sub:
                    mlast[d // 30] = c
                ms = sorted(v for v in mlast.values() if v > 0)
                mrets = [ms[i] / ms[i - 1] - 1 for i in range(1, len(ms)) if ms[i - 1] > 0]
                return sum(x for x in mrets if x < 0)

            p3, p5, p10 = monthly_neg_sum(3), monthly_neg_sum(5), monthly_neg_sum(10)
            metrics[s] = dict(peer_groups=pg[s], ret_1y=r1, ret_3y=r3, ret_5y=r5, ret_10y=r10, ytd=ytd,
                              vol=vol, dd=dd, sharpe=sharpe, sortino=sortino, p3=p3, p5=p5, p10=p10)
    print("computed metrics for", len(metrics), "symbols")

    # ---- ranking within each peer group ----
    by_pg = defaultdict(lambda: defaultdict(list))
    for s, m in metrics.items():
        for pgt, pgv in m['peer_groups'].items():
            if pgv:
                by_pg[pgt][pgv].append(s)

    tr_scores, pr_scores, co_scores = {}, {}, {}
    for pgt in by_pg:
        groups = by_pg[pgt]
        tr_scores[pgt] = rank_groups(groups, lambda s: avg([metrics[s]['ret_3y'], metrics[s]['ret_5y'], metrics[s]['ret_10y']]), True)
        pr_scores[pgt] = rank_groups(groups, lambda s: avg([metrics[s]['p3'], metrics[s]['p5'], metrics[s]['p10']]), True)
        co_scores[pgt] = rank_groups(groups, lambda s: avg([metrics[s]['sharpe'], metrics[s]['sortino']]), True)

    all_scores = {}
    for pgt in by_pg:
        for pgv, syms in by_pg[pgt].items():
            for s in syms:
                tr = tr_scores[pgt].get(s); pr = pr_scores[pgt].get(s); co = co_scores[pgt].get(s)
                if tr is None:
                    continue
                comp = round(avg([tr, pr, co]))
                all_scores[(s, pgt)] = dict(tr=tr, pr=pr, co=co, comp=comp)

    ins = """INSERT INTO lipper_scores
      (symbol,peer_group_type,peer_group_value,as_of,ret_1y,ret_3y,ret_5y,ret_10y,ytd,volatility_3y,downside_dev,
       sharpe_3y,sortino_3y,preservation_score,total_return_score,consistent_score,composite_score,sector_rank_pct)
      VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
      ON DUPLICATE KEY UPDATE peer_group_value=VALUES(peer_group_value),as_of=VALUES(as_of),
      ret_1y=VALUES(ret_1y),ret_3y=VALUES(ret_3y),ret_5y=VALUES(ret_5y),ret_10y=VALUES(ret_10y),ytd=VALUES(ytd),
      volatility_3y=VALUES(volatility_3y),downside_dev=VALUES(downside_dev),sharpe_3y=VALUES(sharpe_3y),
      sortino_3y=VALUES(sortino_3y),preservation_score=VALUES(preservation_score),
      total_return_score=VALUES(total_return_score),consistent_score=VALUES(consistent_score),
      composite_score=VALUES(composite_score),sector_rank_pct=VALUES(sector_rank_pct)"""
    cnt = 0
    lipper_rows = []
    for (s, pgt), sc in all_scores.items():
        pgv = metrics[s]['peer_groups'].get(pgt)
        grp = by_pg[pgt].get(pgv, [])
        le = sum(1 for x in grp if all_scores.get((x, pgt), {}).get('comp', 0) <= sc['comp'])
        pct = round(le / len(grp) * 100, 2) if grp else None
        m = metrics[s]
        lipper_rows.append((s, pgt, pgv, asof, m['ret_1y'], m['ret_3y'], m['ret_5y'], m['ret_10y'], m['ytd'],
                            m['vol'], m['dd'], m['sharpe'], m['sortino'], sc['pr'], sc['tr'], sc['co'], sc['comp'], pct))
        cnt += 1
    BATCH = 1000
    for i in range(0, len(lipper_rows), BATCH):
        cur.executemany(ins, lipper_rows[i:i + BATCH])
    conn.commit()
    print("stored lipper_scores:", cnt)

    # ---- advisor portfolio effectiveness ($-weighted, using 'sector' dimension) ----
    cur.execute("SELECT symbol, adj_close FROM stockprices WHERE (symbol, price_date) IN "
                "(SELECT symbol, MAX(price_date) FROM stockprices GROUP BY symbol)")
    price = {r['symbol']: float(r['adj_close']) for r in cur.fetchall() if r['adj_close'] is not None}
    cur.execute("SELECT user_id, strategy, symbol, shares FROM portfolio")
    agg = defaultdict(lambda: dict(n=0, scored=0, w=0.0, comp=0.0, pres=0.0, tr=0.0, cons=0.0, leaders=0.0))
    for h in cur.fetchall():
        s = h['symbol']; uid = h['user_id']; strat = h['strategy'] or 'DEFAULT'
        sc = all_scores.get((s, 'sector'))
        if not sc:
            continue
        tr, pr, co = sc['tr'], sc['pr'], sc['co']
        if tr is None or co is None:
            continue
        mv = float(h['shares'] or 0) * float(price.get(s, 0))
        a = agg[(uid, strat)]
        a['n'] += 1; a['scored'] += 1; a['w'] += mv
        a['comp'] += co * mv; a['pres'] += (pr or 0) * mv; a['tr'] += tr * mv; a['cons'] += co * mv
        if co == 5:
            a['leaders'] += mv
    pins = """INSERT INTO portfolio_lipper_effectiveness
      (user_id,strategy,n_holdings,scored_holdings,avg_composite,pct_leaders,avg_preservation,
       avg_total_return,avg_consistent,total_market_value,as_of)
      VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
      ON DUPLICATE KEY UPDATE n_holdings=VALUES(n_holdings),scored_holdings=VALUES(scored_holdings),
      avg_composite=VALUES(avg_composite),pct_leaders=VALUES(pct_leaders),avg_preservation=VALUES(avg_preservation),
      avg_total_return=VALUES(avg_total_return),avg_consistent=VALUES(avg_consistent),
      total_market_value=VALUES(total_market_value),as_of=VALUES(as_of)"""
    pc = 0
    for (uid, strat), a in agg.items():
        if a['w'] > 0:
            cur.execute(pins, (uid, strat, a['n'], a['scored'], round(a['comp'] / a['w'], 2),
                               round(a['leaders'] / a['w'] * 100, 2), round(a['pres'] / a['w'], 2),
                               round(a['tr'] / a['w'], 2), round(a['cons'] / a['w'], 2),
                               round(a['w'], 2), asof))
            pc += 1
    conn.commit()
    print("stored portfolio_lipper_effectiveness:", pc)


if __name__ == '__main__':
    main()
