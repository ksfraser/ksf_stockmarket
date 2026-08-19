#!/usr/bin/env python3
"""Lipper-style peer-relative scoring for stocks by sector + advisor portfolio effectiveness.

For each stock with price history we compute, over 3/5/10-yr windows:
  - Total Return       (dividend-adjusted cumulative return)
  - Preservation       (loss avoidance = sum of negative monthly returns; less negative = better)
  - Consistent Return   (risk-adjusted: Sharpe / Sortino over trailing 3y)
Each measure is percentile-ranked WITHIN the stock's sector peer group and mapped to a
1-5 Lipper Leader-style score (top 20% = 5). composite_score = average of the three.

Advisor portfolios (portfolio table) are then aggregated, weighted by market value, into
portfolio_lipper_effectiveness so we can see how well a book scores.

Sector source: symbol_master (fallback fundamentals). Price source: stockprices (adj_close).
"""
import os, math, datetime, pymysql
from collections import defaultdict

SQL_FILE = '/var/www/stockmarket-app/sql/lipper_stock_scores.sql'
RF = 0.02  # risk-free rate used for Sharpe/Sortino


def avg(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def pct_rank_scores(pairs, higher_better=True):
    """pairs: list of (sym, metric). Return {sym: 1..5}, top 20% -> 5."""
    clean = [(s, m) for s, m in pairs if m is not None]
    if not clean:
        return {}
    # ascending by metric; best is last if higher_better else first
    order = sorted(clean, key=lambda x: x[1])
    n = len(clean)
    out = {}
    for i, (s, m) in enumerate(order):
        rank_from_top = (n - 1 - i) if higher_better else i
        pct = rank_from_top / (n - 1) if n > 1 else 1.0  # 1.0 = best
        out[s] = 5 if pct >= 0.8 else 4 if pct >= 0.6 else 3 if pct >= 0.4 else 2 if pct >= 0.2 else 1
    return out


def main():
    conn = pymysql.connect(host=os.environ['DB_HOST'], user=os.environ['DB_USER'],
                           password=os.environ['DB_PASS'], database=os.environ['DB_NAME'],
                           charset='utf8mb4')
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # DDL (idempotent) -- strip comments first so ';' inside a -- comment can't break the split
    import re
    with open(SQL_FILE) as f:
        sql = f.read()
    sql = re.sub(r'--[^\n]*', '', sql)
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
    for stmt in [s.strip() for s in sql.split(';') if s.strip()]:
        cur.execute(stmt)
    conn.commit()

    # sector map
    sec = {}
    cur.execute("SELECT symbol, sector, industry FROM symbol_master WHERE sector IS NOT NULL AND sector<>''")
    for r in cur.fetchall():
        sec[r['symbol']] = {'sector': r['sector'], 'industry': r.get('industry')}
    cur.execute("SELECT symbol, sector, industry FROM fundamentals WHERE sector IS NOT NULL AND sector<>''")
    for r in cur.fetchall():
        if r['symbol'] not in sec:
            sec[r['symbol']] = {'sector': r['sector'], 'industry': r.get('industry')}
    print("symbols with sector:", len(sec))

    cur.execute("SELECT MAX(price_date) FROM stockprices")
    asof = cur.fetchone()['MAX(price_date)']
    asof_o = asof.toordinal()
    print("as_of:", asof)

    # per-symbol metrics
    metrics = {}
    cur2 = conn.cursor(pymysql.cursors.DictCursor)
    q = "SELECT price_date, adj_close FROM stockprices WHERE symbol=%s ORDER BY price_date"
    for s in sec:
        cur2.execute(q, (s,))
        rows = cur2.fetchall()
        if not rows:
            continue
        pairs = [(r['price_date'].toordinal(), float(r['adj_close']))
                 for r in rows if r['adj_close'] is not None and float(r['adj_close']) > 0]
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

        # YTD: first close on/after Jan 1 of as_of's year
        jan1 = datetime.date.fromordinal(asof_o).replace(month=1, day=1).toordinal()
        ytd0 = None
        for d, c in reversed(pairs):
            if d <= jan1:
                ytd0 = c
                break
        ytd = (last_c / ytd0 - 1) if ytd0 else None

        r1, r3, r5, r10 = ret(1), ret(3), ret(5), ret(10)

        # trailing 3y daily returns -> vol / downside / sharpe / sortino
        win = [(d, c) for d, c in pairs if d >= asof_o - 3 * 365.25]
        vol = dd = sharpe = sortino = None
        if len(win) >= 60:
            rets = [win[i][1] / win[i - 1][1] - 1 for i in range(1, len(win))]
            mean_r = sum(rets) / len(rets)
            var = sum((x - mean_r) ** 2 for x in rets) / len(rets)
            vol = math.sqrt(var) * math.sqrt(252)
            downs = [x for x in rets if x < 0]
            dd = math.sqrt(sum(x * x for x in downs) / len(rets)) * math.sqrt(252) if rets else None
            ann = mean_r * 252
            sharpe = (ann - RF) / vol if vol else None
            sortino = (ann - RF) / dd if dd else None

        # preservation = sum of negative monthly returns over 3/5/10y windows
        def monthly_neg_sum(years):
            tgt = asof_o - years * 365.25
            sub = [(d, c) for d, c in pairs if d >= tgt]
            if len(sub) < 2:
                return None
            mlast = {}
            for d, c in sub:
                mlast[d // 30] = c  # ~month bucket
            ms = sorted(v for v in mlast.values() if v > 0)
            mrets = [ms[i] / ms[i - 1] - 1 for i in range(1, len(ms)) if ms[i - 1] > 0]
            return sum(x for x in mrets if x < 0)

        p3, p5, p10 = monthly_neg_sum(3), monthly_neg_sum(5), monthly_neg_sum(10)
        metrics[s] = dict(sector=sec[s]['sector'], industry=sec[s]['industry'],
                          ret_1y=r1, ret_3y=r3, ret_5y=r5, ret_10y=r10, ytd=ytd,
                          vol=vol, dd=dd, sharpe=sharpe, sortino=sortino,
                          p3=p3, p5=p5, p10=p10)
    print("computed metrics for", len(metrics), "symbols")

    # within-sector percentile ranks
    by_sector = defaultdict(list)
    for s, m in metrics.items():
        by_sector[m['sector']].append(s)

    tr_pairs, pres_pairs, cons_pairs = defaultdict(list), defaultdict(list), defaultdict(list)
    for s, m in metrics.items():
        sn = m['sector']
        tr_pairs[sn].append((s, avg([m['ret_3y'], m['ret_5y'], m['ret_10y']])))
        pres_pairs[sn].append((s, avg([m['p3'], m['p5'], m['p10']])))      # less-negative = higher = better
        cons_pairs[sn].append((s, avg([m['sharpe'], m['sortino']])))

    tr_scores, pres_scores, cons_scores = {}, {}, {}
    for sn in by_sector:
        tr_scores.update(pct_rank_scores(tr_pairs[sn], higher_better=True))
        pres_scores.update(pct_rank_scores(pres_pairs[sn], higher_better=True))
        cons_scores.update(pct_rank_scores(cons_pairs[sn], higher_better=True))

    ins = """INSERT INTO lipper_stock_scores
      (symbol,sector,industry,as_of,ret_1y,ret_3y,ret_5y,ret_10y,ytd,volatility_3y,downside_dev,
       sharpe_3y,sortino_3y,preservation_score,total_return_score,consistent_score,composite_score,sector_rank_pct)
      VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
      ON DUPLICATE KEY UPDATE sector=VALUES(sector),industry=VALUES(industry),as_of=VALUES(as_of),
      ret_1y=VALUES(ret_1y),ret_3y=VALUES(ret_3y),ret_5y=VALUES(ret_5y),ret_10y=VALUES(ret_10y),ytd=VALUES(ytd),
      volatility_3y=VALUES(volatility_3y),downside_dev=VALUES(downside_dev),sharpe_3y=VALUES(sharpe_3y),
      sortino_3y=VALUES(sortino_3y),preservation_score=VALUES(preservation_score),
      total_return_score=VALUES(total_return_score),consistent_score=VALUES(consistent_score),
      composite_score=VALUES(composite_score),sector_rank_pct=VALUES(sector_rank_pct)"""
    cnt = 0
    for s, m in metrics.items():
        tr = tr_scores.get(s)
        if tr is None:
            continue
        pr = pres_scores.get(s)
        co = cons_scores.get(s)
        comp = round(avg([x for x in (tr, pr, co) if x is not None]))
        secsize = len(by_sector[m['sector']])
        # sector_rank_pct: % of sector with composite <= this symbol's composite
        le = sum(1 for x in by_sector[m['sector']]
                 if (round(avg([y for y in (tr_scores.get(x), pres_scores.get(x), cons_scores.get(x)) if y is not None])) <= comp))
        sector_rank_pct = round(le / secsize * 100, 2)
        cur.execute(ins, (s, m['sector'], m['industry'], asof, m['ret_1y'], m['ret_3y'], m['ret_5y'],
                          m['ret_10y'], m['ytd'], m['vol'], m['dd'], m['sharpe'], m['sortino'],
                          pr, tr, co, comp, sector_rank_pct))
        cnt += 1
    conn.commit()
    print("stored lipper_stock_scores:", cnt)

    # advisor portfolio effectiveness (weighted by market value)
    cur.execute("SELECT symbol, adj_close FROM stockprices WHERE (symbol, price_date) IN "
                "(SELECT symbol, MAX(price_date) FROM stockprices GROUP BY symbol)")
    price = {r['symbol']: float(r['adj_close']) for r in cur.fetchall() if r['adj_close'] is not None}

    cur.execute("SELECT user_id, strategy, symbol, shares FROM portfolio")
    agg = defaultdict(lambda: dict(n=0, scored=0, w=0.0, comp=0.0, pres=0.0, tr=0.0, cons=0.0, leaders=0.0))
    for h in cur.fetchall():
        s = h['symbol']
        uid = h['user_id']
        strat = h['strategy'] or 'DEFAULT'
        tr = tr_scores.get(s)
        pr = pres_scores.get(s)
        co = cons_scores.get(s)
        if tr is None or co is None:
            continue
        mv = float(h['shares'] or 0) * float(price.get(s, 0))
        a = agg[(uid, strat)]
        a['n'] += 1
        a['scored'] += 1
        a['w'] += mv
        a['comp'] += co * mv
        a['pres'] += (pr or 0) * mv
        a['tr'] += tr * mv
        a['cons'] += co * mv
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
