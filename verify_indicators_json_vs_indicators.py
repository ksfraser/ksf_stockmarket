#!/usr/bin/env python3
"""
verify_indicators_json_vs_indicators.py
----------------------------------------------------------------
Compares indicators_json (JSON blob) rows against indicators
(columnar) rows, symbol+price_date by symbol+price_date. For
each JSON row:
  1. Parse JSON, extract all keys.
  2. Check: does every key exist as a column in indicators?
  3. Check: for every column that exists in both, are values within
     epsilon (numerical collinearity)?
  4. Record: columns in indicators that have no JSON key, if any.
  5. Use indicators_json.updated_date as the version/calculation-time
     anchor for drift analysis.

Runs in foreground first on a 1-symbol / 30-row test batch so the
output is inspectable. Once verified clean, the same script can run
destructively (delete verified JSON rows) as a background job.

Requires: DB_PASS env or config.yaml data.db_password.
"""
import sys, os, json, datetime, random, time
from decimal import Decimal, InvalidOperation

import yaml, pymysql

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, 'config.yaml')
if not os.path.exists(CONFIG_PATH):
    raise SystemExit(f"config.yaml not found at {CONFIG_PATH}")

with open(CONFIG_PATH) as f:
    cfg = yaml.safe_load(f)
data_cfg = cfg.get('data', {})
DB_HOST = data_cfg.get('db_host', 'ksfraser.ca')
DB_PORT = int(data_cfg.get('db_port', 3306))
DB_NAME = data_cfg.get('db_name', 'ksf_stock_market')
DB_USER = data_cfg.get('db_user', 'root')
DB_PASS = os.environ.get('DB_PASS') or data_cfg.get('db_password', '')

if not DB_PASS:
    raise SystemExit("No DB password found. Set DB_PASS env or config.yaml data.db_password.")


def connect():
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASS, database=DB_NAME,
        charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def load_indicators_columns(cur):
    """Return ordered list of indicator column names (exclude id, symbol, price_date)."""
    cur.execute("SHOW COLUMNS FROM `indicators`")
    cols = cur.fetchall()
    skip = {'id', 'symbol', 'price_date'}
    return [c['Field'] for c in cols if c['Field'] not in skip]


def sample_json_rows(cur, n=30, by_symbol=True, random_seed=17):
    """
    Sample rows from indicators_json.
    - by_symbol=True: pick 3 symbols (AAPL, 0813.HK, and one random mid-count symbol),
      then 10 rows each → 30 total.
    - by_symbol=False: pick 30 random rows across all symbols.
    """
    cur.execute("SELECT COUNT(DISTINCT symbol) AS cnt FROM indicators_json")
    n_syms = cur.fetchone()['cnt']

    if by_symbol:
        # Fixed anchors
        anchors = ['AAPL', '0813.HK']
        # One random symbol from the distinct set
        cur.execute("SELECT DISTINCT symbol FROM indicators_json ORDER BY RAND() LIMIT 1")
        rnd_sym = cur.fetchone()['symbol']
        anchors.append(rnd_sym)
        rows_out = []
        for sym in anchors:
            cur.execute(
                "SELECT id, symbol, price_date, data, updated_date "
                "FROM indicators_json WHERE symbol = %s "
                "ORDER BY RAND() LIMIT 10",
                (sym,),
            )
            rows_out.extend(cur.fetchall())
        return rows_out
    else:
        cur.execute(
            "SELECT id, symbol, price_date, data, updated_date "
            "FROM indicators_json ORDER BY RAND() LIMIT %s",
            (n,),
        )
        return cur.fetchall()


def parse_json_data(raw):
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def decimal_to_float_safe(v):
    """Convert a value to a float for comparison. Returns None if null/empty."""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return None
    return None


def check_row(jrow, ind_cols, cur, epsilon=1e-6):
    """
    Given one indicators_json row (has id, symbol, price_date, data,
    updated_date), compare its JSON keys/values to indicators (columnar)
    for the same symbol+price_date.

    Returns dict with:
      - json_sympdate_match: bool (did indicators have this symbol+date?)
      - keys_in_json: list of str
      - keys_not_in_indicators: list of str (JSON keys with no corresponding column)
      - columns_missing_in_json: list of str (indicators columns with no JSON key)
      - value_drift: list of (col, json_val, ind_val, abs_diff) for any pair where
        both exist but abs diff > epsilon
      - value_match_count: int (number of pairs where both exist and diff <= epsilon)
      - value_total_pairs: int (number of pairs where both sides have a value)
    """
    jdata = parse_json_data(jrow['data'])
    if jdata is None:
        return {
            'json_parse_fail': True,
            'id': jrow['id'],
            'symbol': jrow['symbol'],
            'price_date': jrow['price_date'],
            'updated_date': jrow['updated_date'].isoformat() if jrow['updated_date'] else None,
            'note': 'JSON parse failed',
        }

    sym = jrow['symbol']
    pdate = jrow['price_date']

    # Load the matching indicators row
    cur.execute(
        "SELECT * FROM indicators WHERE symbol = %s AND price_date = %s",
        (sym, pdate),
    )
    ind_row = cur.fetchone()

    keys_in_json = list(jdata.keys())
    keys_in_json_sorted = sorted(keys_in_json)
    ind_cols_set = set(ind_cols)
    json_keys_set = set(keys_in_json)

    result = {
        'id': jrow['id'],
        'symbol': sym,
        'price_date': pdate.isoformat() if hasattr(pdate, 'isoformat') else str(pdate),
        'updated_date': jrow['updated_date'].isoformat() if jrow['updated_date'] else None,
        'json_parse_ok': True,
        'indicators_row_present': ind_row is not None,
        'keys_in_json': keys_in_json_sorted,
        'n_json_keys': len(keys_in_json),
    }

    if ind_row is None:
        result['note'] = 'No matching indicators row for this symbol+date'
        result['columns_missing_in_json_due_to_no_ind_row'] = []  # can't check
        return result

    # keys in JSON that are NOT in indicators columns
    not_in_ind = [k for k in keys_in_json if k not in ind_cols_set]
    result['keys_not_in_indicators'] = not_in_ind

    # indicators columns that are NOT in JSON keys
    missing_in_json = [c for c in ind_cols if c not in json_keys_set]
    result['columns_missing_in_json'] = missing_in_json

    # Compare values for all overlapping keys
    value_drift = []
    value_match_count = 0
    value_total_pairs = 0

    for key in sorted(json_keys_set & ind_cols_set):
        jv = jdata[key]
        iv = ind_row.get(key)
        jf = decimal_to_float_safe(jv)
        if jf is None:
            # JSON value is non-numeric or null — skip numeric comparison
            continue
        if iv is None:
            # indicator column is NULL — treat as mismatch if JSON has a value
            value_drift.append((key, jv, 'NULL', 'JSON has value but indicators is NULL'))
            continue
        ivf = decimal_to_float_safe(iv)
        if ivf is None:
            continue
        diff = abs(jf - ivf)
        value_total_pairs += 1
        if diff > epsilon:
            value_drift.append((key, jv, iv, diff))
        else:
            value_match_count += 1

    result['value_match_count'] = value_match_count
    result['value_total_pairs'] = value_total_pairs
    result['value_drift'] = value_drift
    result['value_match_pct'] = (value_match_count / max(value_total_pairs, 1)) * 100

    # Also note: are there json keys whose values are non-numeric (strings, objects)?
    non_numeric_json_keys = []
    for k in keys_in_json:
        v = jdata[k]
        if not isinstance(v, (int, float, Decimal)) and v is not None:
            non_numeric_json_keys.append((k, type(v).__name__, v))
    result['non_numeric_json_keys'] = non_numeric_json_keys

    return result


def run_test_batch(n=30, by_symbol=True, random_seed=17, epsilon=1e-6, delete_after_verify=False):
    print(f"=== indicators_json vs indicators verification ===", flush=True)
    print(f"  Test batch: {n} rows, by_symbol={by_symbol}, random_seed={random_seed}, epsilon={epsilon}", flush=True)
    print(f"  Delete verified rows after check: {delete_after_verify}", flush=True)
    print(f"  DB: {DB_HOST}:{DB_PORT}/{DB_NAME}  user={DB_USER}", flush=True)
    print(f"  Started: {datetime.datetime.now().isoformat()}", flush=True)
    print("-" * 70, flush=True)

    conn = connect()
    try:
        cur = conn.cursor()

        ind_cols = load_indicators_columns(cur)
        print(f"  indicators has {len(ind_cols)} indicator columns", flush=True)

        rows = sample_json_rows(cur, n=n, by_symbol=by_symbol, random_seed=random_seed)
        print(f"  Sampled {len(rows)} indicators_json rows for testing", flush=True)

        if not rows:
            print("  No rows sampled — nothing to do.", flush=True)
            return

        # Print which symbols / dates are in the sample
        print("\n  Sample rows:", flush=True)
        for r in rows:
            pdate = r['price_date'].isoformat() if hasattr(r['price_date'], 'isoformat') else str(r['price_date'])
            upd = r['updated_date'].isoformat() if r['updated_date'] else 'NULL'
            print(f"    id={r['id']:10d}  sym={r['symbol']:8s}  date={pdate}  updated={upd}", flush=True)

        print("\n  --- Per-row checks ---", flush=True)

        verified_ids = []
        drift_rows = []
        parse_fail = []
        no_ind_match = []
        non_numeric_rows = []

        for r in rows:
            res = check_row(r, ind_cols, cur, epsilon=epsilon)
            is_ok = (
                res.get('indicators_row_present', False)
                and len(res.get('keys_not_in_indicators', [])) == 0
                and len(res.get('columns_missing_in_json', [])) == 0
                and len(res.get('value_drift', [])) == 0
                and res.get('value_total_pairs', 0) > 0  # at least some numerics compared
            )

            if res.get('json_parse_fail'):
                parse_fail.append(res)
                print(f"  [PARSE FAIL] id={res['id']:10d} sym={res['symbol']:8s} date={res['price_date']}  {res.get('note','')}", flush=True)
                continue

            if not res.get('indicators_row_present'):
                no_ind_match.append(res)
                print(f"  [NO IND MATCH] id={res['id']:10d} sym={res['symbol']:8s} date={res['price_date']}  (no indicators row for this symbol+date)", flush=True)
                # Can't verify -> keep the row
                continue

            if res.get('non_numeric_json_keys'):
                for k, tname, v in res['non_numeric_json_keys']:
                    print(f"  [NON-NUMERIC JSON] id={res['id']:10d} sym={res['symbol']:8s} date={res['price_date']}  key={k} type={tname} val={v}", flush=True)

            n_json_keys = res['n_json_keys']
            n_not_in_ind = len(res.get('keys_not_in_indicators', []))
            n_missing_in_json = len(res.get('columns_missing_in_json', []))
            n_drift = len(res.get('value_drift', []))
            n_pairs = res.get('value_total_pairs', 0)
            n_match = res.get('value_match_count', 0)

            status = "[OK]" if is_ok else "[ISSUE]"
            print(f"  {status} id={res['id']:10d} sym={res['symbol']:8s} date={res['price_date']}  "
                  f"updated={res['updated_date']}  "
                  f"json_keys={n_json_keys:3d}  "
                  f"keys_not_in_ind={n_not_in_ind}  "
                  f"ind_cols_missing_in_json={n_missing_in_json}  "
                  f"drift_pairs={n_drift}  "
                  f"value_match={n_match}/{n_pairs} ({res.get('value_match_pct',0):.1f}%)", flush=True)

            if n_not_in_ind:
                for k in res['keys_not_in_indicators']:
                    print(f"      KEY-ONLY-IN-JSON: {k}", flush=True)
            if n_missing_in_json:
                for c in res['columns_missing_in_json'][:10]:
                    print(f"      IND-COL-MISSING-IN-JSON: {c}", flush=True)
                if n_missing_in_json > 10:
                    print(f"      ... +{n_missing_in_json - 10} more", flush=True)
            if n_drift:
                for col, jv, iv, diff in res['value_drift'][:5]:
                    print(f"      DRIFT: {col:25s}  json={jv}  ind={iv}  abs_diff={diff}", flush=True)
                if n_drift > 5:
                    print(f"      ... +{n_drift - 5} more drift pairs", flush=True)

            if is_ok:
                verified_ids.append(res['id'])
            else:
                drift_rows.append(res)

        # Summary
        print("\n" + "=" * 70, flush=True)
        print("  SUMMARY", flush=True)
        print(f"    Rows tested                 : {len(rows)}", flush=True)
        print(f"    JSON parse failures         : {len(parse_fail)}", flush=True)
        print(f"    No matching indicators row  : {len(no_ind_match)}", flush=True)
        print(f"    Verified clean (would delete): {len(verified_ids)}", flush=True)
        print(f"    Has issues (not deleted)    : {len(drift_rows)}", flush=True)

        if drift_rows:
            print("\n  Drifting rows (NOT deleted):", flush=True)
            for r in drift_rows:
                print(f"    id={r['id']:10d} sym={r['symbol']:8s} date={r['price_date']}  updated={r['updated_date']}", flush=True)

        if parse_fail:
            print("\n  Parse-fail rows (NOT deleted):", flush=True)
            for r in parse_fail:
                print(f"    id={r['id']:10d} sym={r['symbol']:8s} date={r['price_date']}  updated={r['updated_date']}", flush=True)

        if no_ind_match:
            print("\n  Rows with no indicators match (NOT deleted) — sample of symbols/dates:", flush=True)
            seen_syms = set()
            for r in no_ind_match[:20]:
                print(f"    id={r['id']:10d} sym={r['symbol']:8s} date={r['price_date']}  updated={r['updated_date']}", flush=True)
                seen_syms.add(r['symbol'])
            if len(no_ind_match) > 20:
                print(f"    ... +{len(no_ind_match) - 20} more (syms: {sorted(seen_syms)})", flush=True)

        # Deletion phase (only if requested, and only for verified clean rows)
        if delete_after_verify and verified_ids:
            print(f"\n  -- Deleting {len(verified_ids)} verified-clean indicators_json rows --", flush=True)
            start_del = time.time()
            try:
                # Delete in batches to avoid huge IN list
                batch_size = 1000
                total_deleted = 0
                for i in range(0, len(verified_ids), batch_size):
                    batch = verified_ids[i:i + batch_size]
                    placeholders = ','.join(['%s'] * len(batch))
                    cur.execute(
                        f"DELETE FROM indicators_json WHERE id IN ({placeholders})",
                        batch,
                    )
                    total_deleted += cur.rowcount
                    print(f"    Deleted {len(batch)} rows (cumulative {total_deleted})", flush=True)
                conn.commit()
                elapsed = time.time() - start_del
                print(f"    Committed. Total deleted: {total_deleted} rows in {elapsed:.2f}s", flush=True)
                # Re-count
                cur.execute("SELECT COUNT(*) AS cnt FROM indicators_json")
                new_cnt = cur.fetchone()['cnt']
                print(f"    indicators_json rows now: {new_cnt}", flush=True)
            except Exception as e:
                conn.rollback()
                print(f"    DELETE FAILED — rolled back: {e}", flush=True)
        elif delete_after_verify and not verified_ids:
            print("\n  No verified-clean rows to delete.", flush=True)

    finally:
        conn.close()

    print(f"\n  Finished: {datetime.datetime.now().isoformat()}", flush=True)


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description="Verify indicators_json vs indicators, optionally delete verified rows.")
    p.add_argument('--n', type=int, default=30, help='Rows to test')
    p.add_argument('--by-symbol', action='store_true', default=True, help='Sample by symbol (3 symbols × 10 rows)')
    p.add_argument('--random-seed', type=int, default=17, help='Random seed for sampling')
    p.add_argument('--epsilon', type=float, default=1e-6, help='Numerical drift tolerance')
    p.add_argument('--delete-after-verify', action='store_true', default=False, help='Delete rows verified as clean (destructive)')
    p.add_argument('--symbols', nargs='*', help='Override symbol selection: supply exact symbols to test')
    args = p.parse_args()

    if args.symbols:
        # Use exact symbols, pull 10 rows each
        # We'll monkeypatch sample via a custom function inline
        # Simpler: just call run_test_batch with a custom sampling done here
        conn = connect()
        try:
            cur = conn.cursor()
            ind_cols = load_indicators_columns(cur)
            rows_out = []
            for sym in args.symbols:
                cur.execute(
                    "SELECT id, symbol, price_date, data, updated_date "
                    "FROM indicators_json WHERE symbol = %s "
                    "ORDER BY RAND() LIMIT 10",
                    (sym,),
                )
                rows_out.extend(cur.fetchall())
            print(f"Using explicit symbols: {args.symbols} → {len(rows_out)} rows", flush=True)
            # Now feed into check_row manually
            verified = []
            issues = []
            for r in rows_out:
                res = check_row(r, ind_cols, cur, epsilon=args.epsilon)
                if res.get('json_parse_fail'):
                    issues.append(('PARSE', res))
                elif not res.get('indicators_row_present'):
                    issues.append(('NO_IND', res))
                else:
                    is_ok = (len(res.get('keys_not_in_indicators',[]))==0 and
                             len(res.get('columns_missing_in_json',[]))==0 and
                             len(res.get('value_drift',[]))==0 and
                             res.get('value_total_pairs',0)>0)
                    if is_ok:
                        verified.append(res['id'])
                    else:
                        issues.append(('ISSUE', res))
            # print summary
            print(f"\n{dict:}", flush=True)
            # ... compact printout ...
            print(f"Total: {len(rows_out)} rows, {len(verified)} clean, {len(issues)} issues", flush=True)
            for kind, res in issues[:20]:
                print(f"  [{kind}] id={res['id']} sym={res['symbol']} date={res['price_date']}  updated={res['updated_date']}", flush=True)
            if len(issues) > 20:
                print(f"  ... +{len(issues)-20} more", flush=True)
            if args.delete_after_verify and verified:
                print(f"\nDeleting {len(verified)} verified rows...", flush=True)
                for i in range(0, len(verified), 1000):
                    batch = verified[i:i+1000]
                    cur.execute(f"DELETE FROM indicators_json WHERE id IN ({','.join(['%s']*len(batch))})", batch)
                    conn.commit()
                    print(f"  Deleted {len(batch)} (cum {i+len(batch)})", flush=True)
                cur.execute("SELECT COUNT(*) AS cnt FROM indicators_json")
                print(f"indicators_json now: {cur.fetchone()['cnt']} rows", flush=True)
        finally:
            conn.close()
    else:
        run_test_batch(
            n=args.n,
            by_symbol=args.by_symbol,
            random_seed=args.random_seed,
            epsilon=args.epsilon,
            delete_after_verify=args.delete_after_verify,
        )
