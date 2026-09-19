#!/usr/bin/env python3
"""
stock_analysis_writer.py
=========================

Generate periodic stock analysis write-ups (pre-earnings, post-earnings,
quarterly check) and store them as rows in the stock_analysis table.

SAFETY CHECKLIST (per write-up):
  1. Resolve symbol → name/sector/industry from symbol_master (authoritative).
  2. Bake name+sector+industry into write-up header so identity mismatches
     are visible in the output.
  3. Verify price data exists for the symbol before writing.
  4. If earnings calendar has no entry in next 3 months → flag in
     stock_news_alerts (alert_type='earnings_calendar_gap').
  5. If no news in last 14 days → flag in stock_news_alerts
     (alert_type='no_recent_news').
  6. Idempotent: skip (symbol, period_type, period_date) if already exists.

NEWS ANALYSIS QUEUE (rate-limited per symbol):
  - Every news row in news_feeds gets queued for LLM analysis.
  - Per-symbol throttle: only 1 analysis run per stock per 2 days.
  - All news for a stock within the window is batched together.

Tables touched:
  - stock_competitors   (read: competitor list per symbol)
  - stock_analysis      (write: write-up rows)
  - stock_news_alerts   (write: flags for missing data)
  - news_feeds          (read: news for freshness check)
  - symbol_news         (read: fallback news source)
  - earnings_calendar   (read: upcoming/recent earnings)
  - symbol_master       (read: name, sector, industry, exchange)
  - fundamentals        (read: P/E, yield, market cap, ATR)
  - analyst_targets     (read: consensus targets)
  - sector_rankings    (read: sector rank)

Usage:
    python3 stock_analysis_writer.py              # pre-earnings (default)
    python3 stock_analysis_writer.py --post       # post-earnings (last 5 days)
    python3 stock_analysis_writer.py --quarterly  # quarterly check (portfolio)
    python3 stock_analysis_writer.py --atr        # ATR-sweep write-ups
    python3 stock_analysis_writer.py --news-check # only run news freshness checks
    python3 stock_analysis_writer.py --earnings-gap # only check earnings calendar gaps
"""

import sys, re, json, logging
from datetime import date, datetime, timedelta
from pathlib import Path

# Match the import order: python/src/ MUST come before python/ because
# python/src/db/ (no __init__.py) holds exchange_routing.py, and if python/
# (which has a real db/__init__.py package) shadows it, db.exchange_routing breaks.
# Insert IN REVERSE so the last insert(0, ...) wins: python/src/ → 0, python/ → 1.
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
_PY_SRC = _REPO_ROOT / 'python' / 'src'
_PY_ROOT = _REPO_ROOT / 'python'

# Python auto-adds the script's directory at sys.path[0] — verify it's there but don't force reorder
if str(_SCRIPT_DIR) not in sys.path[:3]:
    sys.path.insert(0, str(_SCRIPT_DIR))

# Insert python/ first, then python/src/ on top so python/src wins position 0
if str(_PY_ROOT) not in sys.path:
    sys.path.insert(0, str(_PY_ROOT))
if str(_PY_SRC) not in sys.path:
    sys.path.insert(0, str(_PY_SRC))

from src.db.stockprice_dao import create_central_stockprice_dao
from config_loader import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger('stock_analysis_writer')


# ── DB helpers ────────────────────────────────────────────────────────────────

def get_conn():
    """Return a pymysql connection to the central DB.

    Loads credentials from config_loader (config.yaml + Ansible Vault), then
    falls back to the .env file, then os.environ, then hardcoded defaults.
    """
    import os
    cfg = Config()
    d = cfg.get('data', {})
    host = d.get('host') or os.environ.get('DB_HOST', 'ksfraser.ca')
    port = int(d.get('port') or os.environ.get('DB_PORT', 3306))
    user = d.get('user') or os.environ.get('DB_USER', 'ksfraser_stockmarket')
    password = (
        d.get('password')
        or os.environ.get('DB_PASS')
        or os.environ.get('DB_PASSWORD')
        or ''
    )
    name = d.get('database') or os.environ.get('DB_NAME', 'ksfraser_stock_market')
    charset = d.get('charset') or os.environ.get('DB_CHARSET', 'utf8mb4')

    # .env fallback if env vars not set and config is empty
    if not password or password == '' or password == 'None':
        env_path = Path('/home/ksf_stockmarket/ksf_stockmarket/.env')
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    if k.strip() == 'DB_PASS':
                        password = v.strip()
                        break

    import pymysql
    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=name,
        charset=charset,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
        autocommit=True,
    )


def q_one(conn, sql, params=()):
    with conn.cursor() as c:
        c.execute(sql, params)
        return c.fetchone()


def q_all(conn, sql, params=()):
    with conn.cursor() as c:
        c.execute(sql, params)
        return c.fetchall()


def upsert(conn, sql, params=()):
    with conn.cursor() as c:
        c.execute(sql, params)
        conn.commit()
        return c.lastrowid


def upsert_or_increment(conn, table, unique_cols, increment_col, set_cols):
    """Upsert: insert if (unique_cols) doesn't exist, else increment
    increment_col and update set_cols. Returns row id.

    set_cols may overlap with unique_cols — overlapping keys are excluded
    from the INSERT column list (they're in the WHERE clause already).
    """
    where = ' AND '.join([f"{k}=%s" for k in unique_cols])
    all_unique_params = list(unique_cols.values())
    row = q_one(conn, f"SELECT id, {increment_col} FROM {table} WHERE {where}", all_unique_params)
    if row:
        new_val = row[increment_col] + 1
        updates = ', '.join([f"{k}=%s" for k in set_cols] + [f"{increment_col}=%s"])
        params = list(set_cols.values()) + [new_val] + all_unique_params
        upsert(conn, f"UPDATE {table} SET {updates} WHERE {where}", params)
        log.info(f"  incremented {table} {increment_col} to {new_val} for {unique_cols}")
        return row['id']
    else:
        # Exclude keys that appear in both set_cols and unique_cols from the INSERT
        overlap = set(set_cols.keys()) & set(unique_cols.keys())
        insert_cols = {k: v for k, v in set_cols.items() if k not in overlap}
        cols = ', '.join(list(insert_cols.keys()) + list(unique_cols.keys()) + [increment_col])
        vals = ', '.join(['%s'] * (len(insert_cols) + len(unique_cols) + 1))
        params = list(insert_cols.values()) + all_unique_params + [1]
        rid = upsert(conn, f"INSERT INTO {table} ({cols}) VALUES ({vals})", params)
        log.info(f"  created {table} id={rid} for {unique_cols}")
        return rid


def upsert_or_insert_queue(conn, news_id, source_table, symbol, status='pending', extra_cols=None):
    """Insert into news_analysis_queue if not exists, else skip.
    Handles the unique key (news_id, news_source_table)."""
    existing = q_one(conn,
        "SELECT id FROM news_analysis_queue WHERE news_id=%s AND news_source_table=%s",
        (news_id, source_table))
    if existing:
        return existing['id']
    sql = """
        INSERT INTO news_analysis_queue
            (news_id, news_source_table, symbol, status, created_at)
        VALUES (%s,%s,%s,%s,%s)
    """
    if extra_cols:
        cols = ', '.join(['news_id','news_source_table','symbol','status','created_at'] + list(extra_cols.keys()))
        vals = ', '.join(['%s']*5 + ['%s']*len(extra_cols))
        params = [news_id, source_table, symbol, status, datetime.now()] + list(extra_cols.values())
        rid = upsert(conn, f"INSERT INTO news_analysis_queue ({cols}) VALUES ({vals})", params)
    else:
        rid = upsert(conn, sql, (news_id, source_table, symbol, status, datetime.now()))
    return rid


# ── Price helpers ─────────────────────────────────────────────────────────────

def latest_price(conn, sym):
    dao = create_central_stockprice_dao(central_db=conn)
    rows = dao.read_prices(sym, use_central=True)
    if not rows:
        return None
    # DAO returns ascending by price_date; latest = last row
    cur = rows[-1]
    prev = rows[-2] if len(rows) > 1 else None
    change = ((float(cur['close']) - float(prev['close'])) / float(prev['close']) * 100) if prev and prev.get('close') and float(prev['close']) > 0 else None
    return {
        'symbol': sym,
        'close': float(cur['close']),
        'open': float(cur['open']) if cur.get('open') is not None else None,
        'high': float(cur['high']) if cur.get('high') is not None else None,
        'low': float(cur['low']) if cur.get('low') is not None else None,
        'volume': int(cur['volume']) if cur.get('volume') is not None else 0,
        'price_date': str(cur['price_date']),
        'prev_close': float(prev['close']) if prev and prev.get('close') else None,
        'change_pct': change,
    }


def price_before(conn, sym, dt):
    with conn.cursor() as c:
        c.execute(
            "SELECT close, price_date FROM stockprices WHERE symbol=%s AND price_date<=%s ORDER BY price_date DESC LIMIT 1",
            (sym, dt))
        return c.fetchone()


def has_recent_prices(conn, sym, days=5):
    """Check if symbol has price data within last `days` days."""
    cutoff = date.today() - timedelta(days=days)
    r = q_one(conn, "SELECT COUNT(*) as cnt FROM stockprices WHERE symbol=%s AND price_date>=%s",
              (sym, cutoff))
    return (r['cnt'] or 0) > 0


# ── Metadata helpers ──────────────────────────────────────────────────────────

def resolve_symbol(conn, sym):
    """Resolve symbol to authoritative name, sector, industry, exchange.
    Returns dict or None if not found. This is the identity double-check."""
    r = q_one(conn, "SELECT symbol, name, sector, industry, exchange, currency, is_portfolio, is_watchlist FROM symbol_master WHERE symbol=%s AND is_active=1", (sym,))
    if not r:
        # Fallback: try symbol_status
        r = q_one(conn, "SELECT resolved_symbol as symbol, name, exchange, currency, NULL as sector, NULL as industry, 0 as is_portfolio, 0 as is_watchlist FROM symbol_status WHERE symbol=%s", (sym,))
    if not r:
        return None
    return {
        'symbol': r['symbol'],
        'name': r['name'],
        'sector': r['sector'],
        'industry': r['industry'],
        'exchange': r['exchange'],
        'currency': r.get('currency', 'CAD'),
        'is_portfolio': bool(r.get('is_portfolio', 0)),
        'is_watchlist': bool(r.get('is_watchlist', 0)),
    }


def get_competitors(conn, sym):
    rows = q_all(conn, "SELECT competitor, is_primary, notes FROM stock_competitors WHERE symbol=%s ORDER BY is_primary DESC, competitor", (sym,))
    return [{'symbol': r['competitor'], 'is_primary': bool(r['is_primary']), 'notes': r['notes']} for r in rows]


def get_comp_prices(conn, syms):
    out = {}
    for s in syms:
        p = latest_price(conn, s)
        if p:
            out[s] = p
    return out


def get_fundamentals(conn, sym):
    r = q_one(conn, "SELECT * FROM fundamentals WHERE symbol=%s ORDER BY fetch_date DESC LIMIT 1", (sym,))
    return r if r else {}


def get_analyst_targets(conn, sym):
    """Latest analyst price targets. Returns list of dicts or empty list
    if table doesn't exist or has different schema (graceful fallback)."""
    try:
        rows = q_all(conn, "SELECT target_price as price_target, recommendation as firm, source as analyst_name, date FROM analyst_targets WHERE ticker=%s ORDER BY date DESC LIMIT 20", (sym,))
        return rows
    except Exception:
        return []


def analyst_agreement(conn, sym):
    """% of recent targets above current price. Returns dict or None."""
    targets = get_analyst_targets(conn, sym)
    if not targets:
        return None
    lp = latest_price(conn, sym)
    if not lp:
        return None
    price = lp['close']
    above = sum(1 for t in targets if t.get('price_target') and float(t['price_target']) > price)
    return {'num': len(targets), 'num_above': above, 'pct_above': (above/len(targets)*100) if targets else 0,
            'targets': targets, 'current_price': price}


def get_sector_rank(conn, sym):
    return q_one(conn, "SELECT * FROM sector_rankings WHERE symbol=%s ORDER BY last_updated DESC LIMIT 1", (sym,))


def get_earnings_for_date(conn, sym, report_date):
    return q_one(conn, "SELECT * FROM earnings_calendar WHERE ticker=%s AND report_date=%s", (sym, report_date))


def get_upcoming_earnings(conn, days=14):
    cutoff = date.today() + timedelta(days=days)
    rows = q_all(conn,
        "SELECT ticker, report_date, eps_estimate, eps_actual, revenue_estimate, revenue_actual, surprise_pct, is_beat, is_miss "
        "FROM earnings_calendar WHERE report_date BETWEEN %s AND %s ORDER BY report_date",
        (date.today(), cutoff))
    return rows


def get_recent_earnings(conn, days=5):
    since = date.today() - timedelta(days=days)
    rows = q_all(conn,
        "SELECT ticker, report_date, eps_estimate, eps_actual, revenue_estimate, revenue_actual, surprise_pct, is_beat, is_miss "
        "FROM earnings_calendar WHERE report_date BETWEEN %s AND %s ORDER BY report_date DESC",
        (since, date.today()))
    return rows


def portfolio_or_watchlist(conn):
    rows = q_all(conn, "SELECT symbol FROM symbol_master WHERE (is_portfolio=1 OR is_watchlist=1) AND is_active=1")
    return [r['symbol'] for r in rows]


def atr_flagged_symbols(conn):
    rows = q_all(conn,
        "SELECT DISTINCT symbol FROM atr_stop_optimization WHERE bounce_back_rate < 0.70 ORDER BY symbol")
    return [r['symbol'] for r in rows] if rows else []


def get_recent_news_count(conn, sym, days=14):
    """Count news items for symbol in last `days` days from news_feeds."""
    cutoff = date.today() - timedelta(days=days)
    r = q_one(conn,
        "SELECT COUNT(*) as cnt FROM news_feeds WHERE symbol_filter=%s AND published>=%s",
        (sym, cutoff))
    return r['cnt'] if r else 0


def get_news_for_symbol(conn, sym, days=14):
    """Get recent news items for a symbol."""
    cutoff = date.today() - timedelta(days=days)
    rows = q_all(conn,
        "SELECT id, title, url, source, published, summary, category FROM news_feeds WHERE symbol_filter=%s AND published>=%s ORDER BY published DESC",
        (sym, cutoff))
    if not rows:
        # Fallback to symbol_news
        rows = q_all(conn,
            "SELECT id, title, url, source, date as published, summary, '' as category FROM symbol_news WHERE symbol=%s AND date>=%s ORDER BY date DESC LIMIT 20",
            (sym, cutoff))
    return rows


def get_last_news_analysis_date(conn, sym):
    """Get the last date we ran LLM analysis for this symbol's news."""
    r = q_one(conn,
        "SELECT MAX(created_at) as last_run FROM news_analysis_queue WHERE symbol=%s",
        (sym,))
    if r and r['last_run']:
        return datetime.fromisoformat(r['last_run'].isoformat()) if hasattr(r['last_run'], 'isoformat') else None
    return None


def queue_news_for_analysis(conn, sym, news_items, force=False):
    """Queue news items for LLM analysis with 2-day per-symbol throttle.
    news_items: list of dicts with at least 'id' and optionally 'source_table'."""
    if not news_items:
        return 0
    last_run = get_last_news_analysis_date(conn, sym)
    now = datetime.now()
    if last_run and not force:
        days_since = (now - last_run).days
        if days_since < 2:
            log.info(f"  news analysis for {sym}: skipped (last run {days_since} day(s) ago, throttle 2 days)")
            return 0
    count = 0
    for n in news_items:
        nid = n['id']
        src_table = n.get('source_table', 'news_feeds') if isinstance(n, dict) else 'news_feeds'
        existing = q_one(conn,
            "SELECT id FROM news_analysis_queue WHERE news_id=%s AND news_source_table=%s",
            (nid, src_table))
        if not existing:
            upsert(conn,
                "INSERT INTO news_analysis_queue (news_id, news_source_table, symbol, status, created_at) VALUES (%s,%s,%s,%s,%s)",
                (nid, src_table, sym, 'pending', now))
            count += 1
    if count:
        log.info(f"  queued {count} news items for {sym} LLM analysis")
    return count


# ── Format helpers ────────────────────────────────────────────────────────────

def fp(p):
    if p is None: return 'N/A'
    return f"${p:,.2f}"


def pp(p):
    if p is None: return 'N/A'
    return f"{p:+.2f}%"


def fv(v):
    if v is None or v == 0: return 'N/A'
    if v >= 1e6: return f"{v/1e6:.1f}M"
    if v >= 1e3: return f"{v/1e3:.0f}K"
    return f"{v}"


def fl(v):
    if v is None: return 'N/A'
    v = float(v)
    if abs(v) >= 1e12: return f"${v/1e12:.2f}T"
    if abs(v) >= 1e9: return f"${v/1e9:.2f}B"
    if abs(v) >= 1e6: return f"${v/1e6:.1f}M"
    if abs(v) >= 1e3: return f"${v/1e3:.0f}K"
    return f"${v:,.2f}"


def fr(v, s=''):
    if v is None: return 'N/A'
    return f"{v:.2f}{s}"


# ── Safety: identity verification ─────────────────────────────────────────────

def verify_identity(conn, sym, meta):
    """Double-check that the symbol's DB identity matches what we expect.
    Raises a flag if name/sector seem wrong (e.g. symbol_master has wrong data)."""
    issues = []
    if not meta:
        issues.append(f"Symbol {sym} not found in symbol_master or symbol_status — identity unknown")
        return issues
    # If symbol_master has a name that looks like a ticker (all caps, short), flag it
    name = meta['name']
    if name and len(name) < 5 and name == name.upper():
        issues.append(f"Symbol {sym}: name '{name}' looks like a ticker, not a company name — verify symbol_master entry")
    return issues


# ── Safety: earnings calendar cross-check ─────────────────────────────────────

def check_earnings_calendar_gaps(conn, symbol_list, months=3):
    """For each symbol in symbol_list, check if earnings_calendar has entries
    in the next `months` months. Flag gaps in stock_news_alerts."""
    future_cutoff = date.today() + timedelta(days=months*30)
    flags = []
    for sym in symbol_list:
        r = q_one(conn,
            "SELECT COUNT(*) as cnt FROM earnings_calendar WHERE ticker=%s AND report_date BETWEEN %s AND %s",
            (sym, date.today(), future_cutoff))
        if not r or r['cnt'] == 0:
            log.warning(f"  earnings calendar gap: {sym} has no earnings entries in next {months} months")
            flags.append(sym)
    return flags


# ── Safety: news freshness check ──────────────────────────────────────────────

def check_news_freshness(conn, symbol_list, days=14):
    """For each symbol, check if there's recent news. Flag symbols with
    no news in last `days` days in stock_news_alerts."""
    flags = []
    for sym in symbol_list:
        cnt = get_recent_news_count(conn, sym, days)
        if cnt == 0:
            log.warning(f"  no recent news: {sym} has 0 news items in last {days} days")
            flags.append(sym)
    return flags


def create_news_alert(conn, sym, alert_type, severity, message, details=None, source='stock_analysis_writer.py'):
    """Create or increment a stock_news_alerts entry."""
    extras = {
        'symbol': sym,
        'alert_type': alert_type,
        'severity': severity,
        'message': message,
        'source': source,
        'created_by': source,
    }
    if details:
        extras['details'] = json.dumps(details)
    rid = upsert_or_increment(conn, 'stock_news_alerts',
                              {'symbol': sym, 'alert_type': alert_type},
                              'flag_count',
                              extras)
    return rid


# ── Pre-earnings write-up ─────────────────────────────────────────────────────

def write_pre_earnings(conn, sym, report_date, erow=None):
    p = latest_price(conn, sym)
    if not p:
        log.warning(f"  {sym}: no price data — skipping pre-earnings write-up")
        return None
    meta = resolve_symbol(conn, sym)
    if not meta:
        log.warning(f"  {sym}: cannot resolve identity — skipping")
        return None

    # Safety: identity verification
    id_issues = verify_identity(conn, sym, meta)
    if id_issues:
        for issue in id_issues:
            log.warning(f"  IDENTITY CHECK {sym}: {issue}")
        # Still proceed but flag it
        create_news_alert(conn, sym, 'name_mismatch',
                          'warning',
                          f"Identity verification flagged: {'; '.join(id_issues)}",
                          {'symbol': sym, 'resolved_name': meta['name']})

    fund = get_fundamentals(conn, sym)
    targets = get_analyst_targets(conn, sym)
    agree = analyst_agreement(conn, sym)
    comps = get_competitors(conn, sym)
    cprices = get_comp_prices(conn, [c['symbol'] for c in comps])
    srank = get_sector_rank(conn, sym)
    today = date.today()
    d = (report_date - today).days

    crows = []
    for c in comps:
        cp = cprices.get(c['symbol'])
        if not cp: continue
        crows.append({'symbol': c['symbol'], 'change': cp['change_pct'], 'close': cp['close'],
                      'volume': cp['volume'], 'label': '★ primary' if c['is_primary'] else 'peer',
                      'notes': c['notes']})

    this_pe = float(fund['pe_ratio']) if fund and fund.get('pe_ratio') else None
    comp_pes = []
    for c in comps:
        cp = cprices.get(c['symbol'])
        if not cp: continue
        cf = get_fundamentals(conn, c['symbol'])
        if cf and cf.get('pe_ratio'):
            comp_pes.append((c['symbol'], float(cf['pe_ratio']), cp['close']))
    pe_txt = ''
    if this_pe and comp_pes:
        avg_pe = sum(x[1] for x in comp_pes)/len(comp_pes)
        cheaper = 'cheaper' if this_pe < avg_pe else 'more expensive'
        pe_txt = f"\n**Valuation context:** P/E {fr(this_pe,'×')} vs {len(comp_pes)} peers averaging {fr(avg_pe,'×')} — {cheaper} than peer group on earnings multiple. "

    atr_txt = ''
    if fund and fund.get('atr_14'):
        atr = float(fund['atr_14'])
        atr_pct = (atr/p['close']*100) if p['close'] > 0 else 0
        atr_txt = f"\n**Volatility:** ATR(14) = ${atr:,.2f} ({atr_pct:.1f}% of price). "

    parts = [
        f"# {sym} — Pre-Earnings Watch ({meta['name']})",
        '',
        f"**Company:** {meta['name']}",
        f"**Sector:** {meta['sector'] or 'N/A'} ({meta['industry'] or 'N/A'})",
        f"**Exchange:** {meta['exchange'] or 'N/A'}",
        f"**Report date:** {report_date} — **{d} days away**",
        '',
        '---',
        '',
        '## Current Price',
        '',
        f"| | |",
        f"|---|---|",
        f"| Price | {fp(p['close'])} |",
        f"| Change (vs prev close) | {pp(p['change_pct'])} |",
        f"| Volume | {fv(p['volume'])} |",
        f"| Date | {p['price_date']} |",
        '',
        atr_txt,
        '## What the Market is Saying',
        '',
    ]
    if agree:
        parts.append(f"**Analyst consensus:** {agree['num_above']}/{agree['num']} recent targets above current price ({pp(agree['pct_above'])} bullish). ")
        if agree['targets']:
            vals = [float(t['price_target']) for t in agree['targets'] if t['price_target']]
            if vals:
                parts.append(f"Range: {fp(min(vals))} – {fp(max(vals))}, consensus ~{fp(sum(vals)/len(vals))}. ")
    if srank:
        parts.append(f"**Sector rank:** #{srank['sector_rank']}/{srank.get('sector_total','N/A')} in {srank['sector']} (score: {srank.get('sector_score','N/A')}). ")
    parts.append('')

    parts.append(f"## Peer Comparison (as of {p['price_date']})")
    parts.append('')
    if crows:
        parts.append('| Competitor | Price | Change | Vol | Note |')
        parts.append('|---|---|---|---|---|')
        for r in sorted(crows, key=lambda x: x['change'] if x['change'] is not None else -999, reverse=True):
            parts.append(f"| {r['symbol']} {r['label']} | {fp(r['close'])} | {pp(r['change'])} | {fv(r['volume'])} | {r['notes']} |")
    else:
        parts.append("_No competitor data loaded._")
    parts.append('')
    parts.append(pe_txt)

    if erow:
        parts.append('## What is Expected')
        parts.append('')
        eps_e = f"expected {fp(float(erow['eps_estimate'])) if erow.get('eps_estimate') else 'N/A'}"
        if erow.get('eps_actual'):
            eps_e += f" (actual: {fp(float(erow['eps_actual']))})"
        parts.append(f"- **EPS estimate:** {eps_e}")
        rev_e = f"expected {fl(erow['revenue_estimate']) if erow.get('revenue_estimate') else 'N/A'}"
        if erow.get('revenue_actual'):
            rev_e += f" (actual: {fl(erow['revenue_actual'])})"
        parts.append(f"- **Revenue estimate:** {rev_e}")
        if erow.get('surprise_pct'):
            parts.append(f"- **Surprise:** {float(erow['surprise_pct']):+.1f}%")
        parts.append('')

    parts.append(f"---")
    parts.append(f"*Pre-earnings analysis generated {today} by stock_analysis_writer.py. For informational purposes only.*")

    body = '\n'.join(parts)
    src_syms = json.dumps([c['symbol'] for c in comps if c['symbol'] in cprices])

    return {
        'symbol': sym,
        'period_type': 'pre_earnings',
        'period_date': today,
        'earnings_date': report_date,
        'close_price': str(p['close']),
        'prev_close': str(p['prev_close']) if p['prev_close'] else None,
        'source_symbols': src_syms,
        'body_md': body,
        'word_count': len(body.split()),
        'title': f"Pre-Earnings: {sym} ({meta['name']}) — {report_date}",
    }


# ── Post-earnings write-up ────────────────────────────────────────────────────

def write_post_earnings(conn, sym, report_date, erow=None):
    p = latest_price(conn, sym)
    if not p: return None
    meta = resolve_symbol(conn, sym)
    if not meta: return None

    pre = price_before(conn, sym, report_date)
    chg_since = None
    if pre and p['close'] > 0 and pre['close'] and float(pre['close']) > 0:
        chg_since = (p['close'] - float(pre['close'])) / float(pre['close']) * 100

    comps = get_competitors(conn, sym)
    cprices = get_comp_prices(conn, [c['symbol'] for c in comps])
    agree = analyst_agreement(conn, sym)
    today = date.today()

    crows = []
    for c in comps:
        cp = cprices.get(c['symbol'])
        if not cp: continue
        crows.append({'symbol': c['symbol'], 'change': cp['change_pct'], 'close': cp['close'],
                      'volume': cp['volume'], 'label': '★ primary' if c['is_primary'] else 'peer',
                      'notes': c['notes']})

    peer_chg = [r['change'] for r in crows if r['change'] is not None]
    avg_peer = sum(peer_chg)/len(peer_chg) if peer_chg else None

    parts = [
        f"# {sym} — Post-Earnings Recap ({meta['name']})",
        '',
        f"**Company:** {meta['name']}",
        f"**Sector:** {meta['sector'] or 'N/A'} ({meta['industry'] or 'N/A'})",
        f"**Report date:** {report_date}",
        f"**Latest close:** {fp(p['close'])} on {p['price_date']} ({pp(p['change_pct'])} day)",
        '',
        '---',
        '',
    ]
    if chg_since is not None and pre:
        arrow = '▲' if chg_since >= 0 else '▼'
        parts += [
            '## Price Action Around Earnings',
            '',
            f"- Pre-report close ({pre['price_date']}): **{fp(float(pre['close']))}**",
            f"- Latest close ({p['price_date']}): **{fp(p['close'])}**",
            f"- Change since report: **{arrow} {pp(chg_since)}**",
            '',
        ]

    parts += ['## What Was Expected', '']
    if erow:
        e = erow
        eps_e = f"expected {fp(float(e['eps_estimate'])) if e.get('eps_estimate') else 'N/A'}"
        eps_a = f" → reported **{fp(float(e['eps_actual']))}" if e.get('eps_actual') else ''
        if e.get('surprise_pct'):
            eps_a += f" ({float(e['surprise_pct']):+.1f}% vs est)" if e.get('surprise_pct') else ''
            eps_a += '**' if eps_a else ''
        parts.append(f"- EPS: {eps_e}{eps_a}")
        rev_e = f"expected {fl(e['revenue_estimate']) if e.get('revenue_estimate') else 'N/A'}"
        rev_a = f" → reported **{fl(e['revenue_actual'])}**" if e.get('revenue_actual') else ''
        parts.append(f"- Revenue: {rev_e}{rev_a}")
        if e.get('is_beat'):
            parts.append("- **Result: BEAT** estimates.")
        elif e.get('is_miss'):
            parts.append("- **Result: MISS** estimates.")
        else:
            parts.append("- Mixed or pending.")
        parts.append('')

    parts += ['## Analyst Reaction', '']
    if agree:
        parts.append(f"- {agree['num_above']}/{agree['num']} targets above current price ({pp(agree['pct_above'])} bullish)")
        if agree['targets']:
            vals = [float(t['price_target']) for t in agree['targets'] if t['price_target']]
            if vals:
                parts.append(f"- Range: {fp(min(vals))} – {fp(max(vals))}")
        parts.append('')
    else:
        parts.append('- No analyst targets loaded.')
        parts.append('')

    parts += ['## How Peers Fared (same day)', '']
    if crows:
        parts.append('| Competitor | Price | Change | Vol | Note |')
        parts.append('|---|---|---|---|---|')
        for r in sorted(crows, key=lambda x: x['change'] if x['change'] is not None else -999, reverse=True):
            parts.append(f"| {r['symbol']} {r['label']} | {fp(r['close'])} | {pp(r['change'])} | {fv(r['volume'])} | {r['notes']} |")
        if avg_peer is not None:
            vs = 'outperformed' if (p['change_pct'] or 0) > avg_peer else 'underperformed'
            parts.append(f"\n**Peer avg:** {pp(avg_peer)}. {sym} **{vs}** its peer group.")
    else:
        parts.append('_No peer data available._')
    parts.append('')
    parts.append(f"---")
    parts.append(f"*Post-earnings recap generated {today} by stock_analysis_writer.py. For informational purposes only.*")

    body = '\n'.join(parts)
    src_syms = json.dumps([c['symbol'] for c in comps if c['symbol'] in cprices])

    return {
        'symbol': sym,
        'period_type': 'post_earnings',
        'period_date': today,
        'earnings_date': report_date,
        'close_price': str(p['close']),
        'prev_close': str(p['prev_close']) if p['prev_close'] else None,
        'source_symbols': src_syms,
        'body_md': body,
        'word_count': len(body.split()),
        'title': f"Post-Earnings: {sym} ({meta['name']}) — {report_date}",
    }


# ── Quarterly check ───────────────────────────────────────────────────────────

def write_quarterly_check(conn, sym):
    p = latest_price(conn, sym)
    if not p: return None
    meta = resolve_symbol(conn, sym)
    if not meta: return None

    fund = get_fundamentals(conn, sym)
    agree = analyst_agreement(conn, sym)
    comps = get_competitors(conn, sym)
    cprices = get_comp_prices(conn, [c['symbol'] for c in comps])
    srank = get_sector_rank(conn, sym)
    today = date.today()
    ago90 = today - timedelta(days=90)

    old = price_before(conn, sym, ago90)
    qchg = None
    if old and p['close'] > 0 and old['close'] and float(old['close']) > 0:
        qchg = (p['close'] - float(old['close'])) / float(old['close']) * 100

    crows = []
    for c in comps:
        cp = cprices.get(c['symbol'])
        if not cp: continue
        crows.append({'symbol': c['symbol'], 'change': cp['change_pct'], 'close': cp['close'],
                      'volume': cp['volume'], 'label': '★ primary' if c['is_primary'] else 'peer',
                      'notes': c['notes']})

    peer_chg = [r['change'] for r in crows if r['change'] is not None]
    avg_peer = sum(peer_chg)/len(peer_chg) if peer_chg else None
    vs_peer = ''
    if avg_peer is not None:
        d = (p['change_pct'] or 0) - avg_peer
        vs_peer = f"{sym} is {'outperforming' if d > 0 else 'underperforming'} its peer group by {abs(d):.1f} pp today."

    parts = [
        f"# {sym} — Quarterly Check ({meta['name']})",
        '',
        f"**Company:** {meta['name']}",
        f"**Sector:** {meta['sector'] or 'N/A'} ({meta['industry'] or 'N/A'})",
        f"**Exchange:** {meta['exchange'] or 'N/A'}",
        f"**As of:** {p['price_date']}",
        '',
        '---',
        '',
        '## Price & Performance',
        '',
        '| | |',
        '|---|---|',
        f"| Current price | {fp(p['close'])} |",
        f"| Day change | {pp(p['change_pct'])} |",
        f"| Volume | {fv(p['volume'])} |",
    ]
    if qchg is not None and old:
        parts += [f"| ~90-day change | {pp(qchg)} (from {fp(float(old['close']))} on {old['price_date']}) |"]
    else:
        parts += ["| ~90-day change | N/A |"]
    parts += ['', '## Peer Comparison', '']

    if crows:
        parts += ['| Competitor | Price | Change | Vol | Note |', '|---|---|---|---|---|']
        for r in sorted(crows, key=lambda x: x['change'] if x['change'] is not None else -999, reverse=True):
            parts.append(f"| {r['symbol']} {r['label']} | {fp(r['close'])} | {pp(r['change'])} | {fv(r['volume'])} | {r['notes']} |")
        if avg_peer is not None:
            parts.append(f"\n**Peer avg day change:** {pp(avg_peer)}. {vs_peer}")
    else:
        parts += ['_No competitor data loaded._', '']
    parts += ['', '## Analyst Snapshot', '']
    if agree:
        parts.append(f"- **Consensus:** {agree['num_above']}/{agree['num']} targets above current price ({pp(agree['pct_above'])} bullish)")
        if agree['targets']:
            vals = [float(t['price_target']) for t in agree['targets'] if t['price_target']]
            if vals:
                parts.append(f"- **Target range:** {fp(min(vals))} – {fp(max(vals))}")
        parts.append('')
    else:
        parts += ['- No analyst targets loaded.', '']
    if srank:
        parts.append(f"**Sector rank:** #{srank['sector_rank']}/{srank.get('sector_total','N/A')} in {srank['sector']}")
        parts.append('')
    if fund and fund.get('pe_ratio'):
        this_pe = float(fund['pe_ratio'])
        fwd = float(fund['forward_pe']) if fund.get('forward_pe') else None
        parts.append(f"**Valuation:** P/E (TTM) {fr(this_pe,'×')}" + (f", Forward {fr(fwd,'×')}" if fwd else ""))
        parts.append('')
    if fund and fund.get('dividend_yield'):
        parts.append(f"- **Dividend yield:** {float(fund['dividend_yield']):.2f}%")
    if fund and fund.get('market_cap'):
        parts.append(f"- **Market cap:** {fl(fund['market_cap'])}")
    parts += ['', '---', f'*Quarterly check generated {today} by stock_analysis_writer.py. For informational purposes only.*']

    body = '\n'.join(parts)
    src_syms = json.dumps([c['symbol'] for c in comps if c['symbol'] in cprices])

    return {
        'symbol': sym,
        'period_type': 'quarterly_check',
        'period_date': today,
        'close_price': str(p['close']),
        'prev_close': str(p['prev_close']) if p['prev_close'] else None,
        'source_symbols': src_syms,
        'body_md': body,
        'word_count': len(body.split()),
        'title': f"Quarterly Check: {sym} ({meta['name']}) — {today}",
    }


# ── ATR-sweep write-up ────────────────────────────────────────────────────────

def write_atr_sweep(conn, sym):
    p = latest_price(conn, sym)
    if not p: return None
    meta = resolve_symbol(conn, sym)
    if not meta: return None

    fund = get_fundamentals(conn, sym)
    srank = get_sector_rank(conn, sym)
    comps = get_competitors(conn, sym)
    cprices = get_comp_prices(conn, [c['symbol'] for c in comps])

    atr_row = q_one(conn,
        "SELECT atr_multiple, n_drops, bounce_back_rate, avg_recovery_days, max_drawdown_atr, recommended "
        "FROM atr_stop_optimization WHERE symbol=%s ORDER BY ts DESC LIMIT 1", (sym,))

    today = date.today()
    parts = [
        f"# {sym} — ATR Sweep Analysis ({meta['name']})",
        '',
        f"**Company:** {meta['name']}",
        f"**Sector:** {meta['sector'] or 'N/A'} ({meta['industry'] or 'N/A'})",
        f"**As of:** {p['price_date']}",
        '',
        '---',
        '',
        '## Price',
        '',
        f"| | |",
        f"|---|---|",
        f"| Price | {fp(p['close'])} |",
        f"| Day change | {pp(p['change_pct'])} |",
        f"| Volume | {fv(p['volume'])} |",
        '',
    ]
    if atr_row:
        parts += [
            '## ATR Sweep Results',
            '',
            f"- **ATR multiple tested:** {atr_row['atr_multiple']}×",
            f"- **Drawdowns analyzed:** {atr_row['n_drops']}",
            f"- **Bounce-back rate:** {float(atr_row['bounce_back_rate'])*100 if atr_row['bounce_back_rate'] else 'N/A'}%",
            f"- **Avg recovery days:** {atr_row['avg_recovery_days']}",
            f"- **Max drawdown (ATR):** {atr_row['max_drawdown_atr']}× ATR",
            f"- **Recommended:** {'YES' if atr_row['recommended'] else 'NO'}",
            '',
        ]
    if srank:
        parts += [
            '## Sector Context',
            '',
            f"- **Sector rank:** #{srank['sector_rank']}/{srank.get('sector_total','N/A')} in {srank['sector']}",
            '',
        ]
    if comps and cprices:
        parts += ['## Peer Prices', '']
        parts.append('| Competitor | Price | Change | Note |')
        parts.append('|---|---|---|---|')
        for c in sorted(comps, key=lambda x: x['symbol']):
            cp = cprices.get(c['symbol'])
            if cp:
                parts.append(f"| {c['symbol']} | {fp(cp['close'])} | {pp(cp['change_pct'])} | {c['notes']} |")
        parts += ['', '']
    parts += [
        '---',
        f'*ATR sweep analysis generated {today} by stock_analysis_writer.py. For informational purposes only.*',
    ]

    body = '\n'.join(parts)
    src_syms = json.dumps([c['symbol'] for c in comps if c['symbol'] in cprices])
    return {
        'symbol': sym,
        'period_type': 'atr_sweep',
        'period_date': today,
        'close_price': str(p['close']),
        'prev_close': str(p['prev_close']) if p['prev_close'] else None,
        'source_symbols': src_syms,
        'body_md': body,
        'word_count': len(body.split()),
        'title': f"ATR Sweep: {sym} — {today}",
    }


# ── Save ─────────────────────────────────────────────────────────────────────

def save_analysis(conn, a):
    existing = q_one(conn,
        "SELECT id FROM stock_analysis WHERE symbol=%s AND period_type=%s AND period_date=%s",
        (a['symbol'], a['period_type'], a['period_date']))
    if existing:
        log.info(f"  skip {a['symbol']} {a['period_type']} {a['period_date']} (id={existing['id']})")
        return existing['id']
    sql = """
        INSERT INTO stock_analysis
            (symbol, period_type, period_date, earnings_date, title,
             close_price, prev_close, body_md, generated_by, word_count, source_symbols)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    rid = upsert(conn, sql, (
        a['symbol'], a['period_type'], a['period_date'],
        a.get('earnings_date'), a.get('title'),
        a.get('close_price'), a.get('prev_close'),
        a['body_md'], 'stock_analysis_writer.py', a['word_count'], a.get('source_symbols'),
    ))
    log.info(f"  wrote {a['symbol']} {a['period_type']} {a['period_date']} (id={rid})")
    return rid


# ── Safety checks standalone ──────────────────────────────────────────────────

def run_earnings_gap_check(conn):
    """Check all portfolio/watchlist symbols for earnings calendar gaps."""
    log.info("=== Earnings calendar gap check ===")
    syms = portfolio_or_watchlist(conn)
    log.info(f"  {len(syms)} portfolio/watchlist symbols")
    gaps = check_earnings_calendar_gaps(conn, syms, months=3)
    for sym in gaps:
        meta = resolve_symbol(conn, sym)
        name = meta['name'] if meta else sym
        create_news_alert(conn, sym, 'earnings_calendar_gap', 'info',
                          f"No earnings calendar entries for {sym} ({name}) in next 3 months. Verify earnings_calendar or add manually.",
                          {'symbol': sym, 'name': name, 'window_months': 3})
    log.info(f"  {len(gaps)} symbols with earnings calendar gaps flagged")


def run_news_freshness_check(conn):
    """Check all portfolio/watchlist symbols for news freshness."""
    log.info("=== News freshness check ===")
    syms = portfolio_or_watchlist(conn)
    log.info(f"  {len(syms)} portfolio/watchlist symbols")
    stale = check_news_freshness(conn, syms, days=14)
    for sym in stale:
        meta = resolve_symbol(conn, sym)
        name = meta['name'] if meta else sym
        create_news_alert(conn, sym, 'no_recent_news', 'warning',
                          f"No news found for {sym} ({name}) in last 14 days. News feed may be broken or symbol untracked.",
                          {'symbol': sym, 'name': name, 'window_days': 14})
    log.info(f"  {len(stale)} symbols with no recent news flagged")

    # For symbols WITH news, queue for LLM analysis (rate-limited)
    log.info("=== News analysis queue (2-day throttle) ===")
    queued = 0
    for sym in syms:
        news = get_news_for_symbol(conn, sym, days=14)
        if news:
            nids = [n['id'] for n in news]
            c = queue_news_for_analysis(conn, sym, nids)
            queued += c
    log.info(f"  {queued} news items queued for LLM analysis")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    conn = get_conn()
    try:
        if '--post' in sys.argv:
            do_post_earnings(conn)
        elif '--quarterly' in sys.argv:
            do_quarterly(conn)
        elif '--atr' in sys.argv:
            do_atr(conn)
        elif '--news-check' in sys.argv:
            run_news_freshness_check(conn)
        elif '--earnings-gap' in sys.argv:
            run_earnings_gap_check(conn)
        else:
            do_pre_earnings(conn)
    finally:
        conn.close()


def do_pre_earnings(conn):
    log.info("=== Pre-earnings write-ups (next 14 days) ===")
    rows = get_upcoming_earnings(conn, 14)
    log.info(f"  {len(rows)} earnings in next 14 days")
    if not rows:
        syms = portfolio_or_watchlist(conn)
        log.info(f"  No upcoming earnings; doing quarterly pre-check for {len(syms)} symbols")
        written = 0
        for sym in syms:
            # Generic pre-earnings: use next 30 days as window
            a = write_pre_earnings(conn, sym, date.today() + timedelta(days=30))
            if a:
                save_analysis(conn, a)
                written += 1
        log.info(f"  Wrote {written} pre-earnings write-ups (generic)")
        return
    written = 0
    for r in rows:
        sym = r['ticker']
        rd = r['report_date']
        if isinstance(rd, str):
            rd = date.fromisoformat(rd[:10])
        a = write_pre_earnings(conn, sym, rd, erow=r)
        if a:
            save_analysis(conn, a)
            written += 1
    log.info(f"  Wrote {written} pre-earnings write-ups")


def do_post_earnings(conn):
    log.info("=== Post-earnings write-ups (last 5 days) ===")
    rows = get_recent_earnings(conn, 5)
    log.info(f"  {len(rows)} earnings in last 5 days")
    if not rows:
        log.info("  No recent earnings — nothing to do")
        return
    written = 0
    for r in rows:
        sym = r['ticker']
        rd = r['report_date']
        if isinstance(rd, str):
            rd = date.fromisoformat(rd[:10])
        a = write_post_earnings(conn, sym, rd, erow=r)
        if a:
            save_analysis(conn, a)
            written += 1
    log.info(f"  Wrote {written} post-earnings write-ups")


def do_quarterly(conn):
    log.info("=== Quarterly check write-ups ===")
    syms = portfolio_or_watchlist(conn)
    log.info(f"  {len(syms)} portfolio/watchlist symbols")
    written = 0
    for sym in syms:
        a = write_quarterly_check(conn, sym)
        if a:
            save_analysis(conn, a)
            written += 1
    log.info(f"  Wrote {written} quarterly check write-ups")


def do_atr(conn):
    log.info("=== ATR-sweep write-ups ===")
    syms = atr_flagged_symbols(conn)
    log.info(f"  {len(syms)} ATR-flagged symbols")
    written = 0
    for sym in syms:
        a = write_atr_sweep(conn, sym)
        if a:
            save_analysis(conn, a)
            written += 1
    log.info(f"  Wrote {written} ATR-sweep write-ups")


if __name__ == '__main__':
    main()
