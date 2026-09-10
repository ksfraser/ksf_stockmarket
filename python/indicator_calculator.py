#!/usr/bin/env python3
"""
indicator_calculator.py — Compute 120 useful TA-Lib indicators for all symbols.

Reads from MySQL stockprices, computes indicators using TA-Lib,
writes to MySQL indicators_json + indicators tables via adapter framework.

Usage:
    python3 indicator_calculator.py [--verbose] [--symbols SYM1,SYM2] [--limit N]
"""
import json, sys, os, argparse, time
from datetime import date
import numpy as np

try:
    import talib
except ImportError:
    print("TA-Lib not installed. Run: pip3 install ta-lib"); sys.exit(1)

# ── Adapter framework ────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import Database, MySQLAdapter, SQLiteAdapter
from config_loader import Config
from indicator_keys import ALL_KEYS, ALIASES, resolve_indicator_dict

_cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml')
_cfg = Config(_cfg_path) if os.path.exists(_cfg_path) else Config()

# Backend selection: DB_BACKEND env or default mysql
_BACKEND = os.environ.get('DB_BACKEND', 'mysql').lower()

if _BACKEND == 'sqlite':
    _db_path = os.environ.get('SQLITE_PATH',
                os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'ksf_stockmarket.db'))
    os.makedirs(os.path.dirname(os.path.abspath(_db_path)), exist_ok=True)
    db = Database(SQLiteAdapter(_db_path))
else:
    db = Database(MySQLAdapter(
        host=getattr(_cfg.data, 'db_host', 'ksfraser.ca'),
        user=getattr(_cfg.data, 'db_user', 'ksfraser_stockmarket'),
        password=getattr(_cfg, 'db_password', None) or os.getenv('DB_PASSWORD', ''),
        database=getattr(_cfg.data, 'db_name', 'ksfraser_stock_market'),
        port=int(getattr(_cfg.data, 'port', 3306)),
    ))

BATCH_INSERT_SIZE = 500


def load_indicator_columns(conn):
    cols = conn.fetchall("DESCRIBE indicators")
    return [r['Field'] for r in cols if r['Field'] not in ('id', 'symbol', 'price_date')]


def compute_for_symbol(symbol, rows):
    """Compute all 120 indicators for one symbol. Returns list of (symbol, date, vals_dict)."""
    n = len(rows)
    if n < 200:
        return []

    c = np.array([r['close'] for r in rows], dtype=np.float64)
    h = np.array([r['high'] for r in rows], dtype=np.float64)
    l = np.array([r['low'] for r in rows], dtype=np.float64)
    v = np.array([r['volume'] if r['volume'] else 0 for r in rows], dtype=np.float64)
    o = np.array([r['open'] for r in rows], dtype=np.float64)
    dates = [r['price_date'] for r in rows]

    out = {}

    def safe(x):
        return float(x) if x is not None and not np.isnan(x) and not np.isinf(x) else None

    # Volatility
    for p, nm in [(7, 'natr_7'), (14, 'natr_14'), (20, 'natr_20')]:
        try:
            r = talib.NATR(h, l, c, timeperiod=p)
            out[nm] = [safe(x) for x in r]
        except Exception:
            out[nm] = [None] * n

    for p, nm in [(7, 'atr_7'), (14, 'atr_14'), (20, 'atr_20')]:
        try:
            r = talib.ATR(h, l, c, timeperiod=p)
            out[nm] = [safe(x) for x in r]
        except Exception:
            out[nm] = [None] * n

    try:
        r = talib.TRANGE(h, l, c)
        out['trange'] = [safe(x) for x in r]
    except Exception:
        out['trange'] = [None] * n

    for p, nm in [(5, 'stddev_5'), (10, 'stddev_10'), (14, 'stddev_14')]:
        try:
            r = talib.STDDEV(c, timeperiod=p)
            out[nm] = [safe(x) for x in r]
        except Exception:
            out[nm] = [None] * n

    for p, nm in [(5, 'var_5'), (10, 'var_10'), (14, 'var_14')]:
        try:
            r = talib.VAR(c, timeperiod=p)
            out[nm] = [safe(x) for x in r]
        except Exception:
            out[nm] = [None] * n

    # Trend
    for p, nm in [(14, 'adx_14'), (21, 'adx_21')]:
        try:
            r = talib.ADX(h, l, c, timeperiod=p)
            out[nm] = [safe(x) for x in r]
        except Exception:
            out[nm] = [None] * n

    for p, nm in [(14, 'adxr_14'), (21, 'adxr_21')]:
        try:
            r = talib.ADXR(h, l, c, timeperiod=p)
            out[nm] = [safe(x) for x in r]
        except Exception:
            out[nm] = [None] * n

    try:
        r = talib.HT_TRENDLINE(c)
        out['ht_trendline'] = [safe(x) for x in r]
    except Exception:
        out['ht_trendline'] = [None] * n

    try:
        r = talib.HT_TRENDMODE(c)
        out['ht_trendmode'] = [int(x) if x is not None else None for x in r]
    except Exception:
        out['ht_trendmode'] = [None] * n

    try:
        r = talib.HT_DCPERIOD(h, l, c)
        out['ht_dcperiod'] = [safe(x) for x in r]
    except Exception:
        out['ht_dcperiod'] = [None] * n

    try:
        r = talib.HT_DCPHASE(h, l, c)
        out['ht_dcphase'] = [safe(x) for x in r]
    except Exception:
        out['ht_dcphase'] = [None] * n

    try:
        r = talib.HT_PHASOR(h, l, c)
        inphase, quadrature = zip(*r)
        out['ht_phasor_inphase'] = [safe(x) for x in inphase]
        out['ht_phasor_quadrature'] = [safe(x) for x in quadrature]
    except Exception:
        out['ht_phasor_inphase'] = [None] * n
        out['ht_phasor_quadrature'] = [None] * n

    try:
        r = talib.HT_SINE(h, l, c)
        sine, leadsine = zip(*r)
        out['ht_sine_sine'] = [safe(x) for x in sine]
        out['ht_sine_leadsine'] = [safe(x) for x in leadsine]
    except Exception:
        out['ht_sine_sine'] = [None] * n
        out['ht_sine_leadsine'] = [None] * n

    # Momentum
    for p, nm in [(7, 'rsi_7'), (14, 'rsi_14'), (21, 'rsi_21')]:
        try:
            r = talib.RSI(c, timeperiod=p)
            out[nm] = [safe(x) for x in r]
        except Exception:
            out[nm] = [None] * n

    for fast, slow, sig, nm in [(8, 21, 5, 'macd_8_21_5_macd'), (12, 26, 9, 'macd_12_26_9_macd'), (24, 52, 18, 'macd_24_52_18_macd')]:
        try:
            macd, signal, hist = talib.MACD(c, fastperiod=fast, slowperiod=slow, signalperiod=sig)
            out[nm] = [safe(x) for x in macd]
            out[nm.replace('_macd', '_signal')] = [safe(x) for x in signal]
            out[nm.replace('_macd', '_histogram')] = [safe(x) for x in hist]
        except Exception:
            out[nm] = [None] * n
            out[nm.replace('_macd', '_signal')] = [None] * n
            out[nm.replace('_macd', '_histogram')] = [None] * n

    for p, q, nm in [(5, 3, 'stoch_5_3_3_k'), (5, 3, 'stoch_5_3_3_d'), (14, 3, 'stoch_14_3_3_k'), (14, 3, 'stoch_14_3_3_d'), (21, 5, 'stoch_21_5_5_k'), (21, 5, 'stoch_21_5_5_d')]:
        try:
            if '14' in nm or '21' in nm:
                slowk, slowd = talib.STOCH(h, l, c, fastk_period=p, slowk_period=3, slowd_period=3, slowk_matype=0, slowd_matype=0)
            else:
                slowk, slowd = talib.STOCH(h, l, c, fastk_period=p, slowk_period=3, slowd_period=3, slowk_matype=0, slowd_matype=0)
            if 'k' in nm:
                out[nm] = [safe(x) for x in slowk]
            else:
                out[nm] = [safe(x) for x in slowd]
        except Exception:
            out[nm] = [None] * n

    for p, nm in [(7, 'roc_7'), (14, 'roc_14'), (21, 'roc_21')]:
        try:
            r = talib.ROC(c, timeperiod=p)
            out[nm] = [safe(x) for x in r]
        except Exception:
            out[nm] = [None] * n

    for p, nm in [(7, 'rocp_7'), (14, 'rocp_14'), (21, 'rocp_21')]:
        try:
            r = talib.ROCP(c, timeperiod=p)
            out[nm] = [safe(x) for x in r]
        except Exception:
            out[nm] = [None] * n

    for p, nm in [(7, 'rocr_7'), (14, 'rocr_14'), (21, 'rocr_21')]:
        try:
            r = talib.ROCR(c, timeperiod=p)
            out[nm] = [safe(x) for x in r]
        except Exception:
            out[nm] = [None] * n

    for p, nm in [(7, 'rocr100_7'), (14, 'rocr100_14'), (21, 'rocr100_21')]:
        try:
            r = talib.ROCR100(c, timeperiod=p)
            out[nm] = [safe(x) for x in r]
        except Exception:
            out[nm] = [None] * n

    for p, nm in [(7, 'mom_7'), (14, 'mom_14'), (21, 'mom_21')]:
        try:
            r = talib.MOM(c, timeperiod=p)
            out[nm] = [safe(x) for x in r]
        except Exception:
            out[nm] = [None] * n

    try:
        out['avgprice'] = [safe((o[i] + h[i] + l[i] + c[i]) / 4) for i in range(n)]
    except Exception:
        out['avgprice'] = [None] * n

    try:
        r = talib.BOP(o, h, l, c)
        out['bop'] = [safe(x) for x in r]
    except Exception:
        out['bop'] = [None] * n

    for p, nm in [(7, 'ppo_7'), (14, 'ppo_14'), (21, 'ppo_21')]:
        try:
            r = talib.PPO(c, fastperiod=p, slowperiod=2 * p, matype=0)
            out[nm] = [safe(x) for x in r]
        except Exception:
            out[nm] = [None] * n

    for p, nm in [(7, 'apo_7'), (14, 'apo_14'), (21, 'apo_21')]:
        try:
            r = talib.APO(c, fastperiod=p, slowperiod=2 * p, matype=0)
            out[nm] = [safe(x) for x in r]
        except Exception:
            out[nm] = [None] * n

    # Moving averages
    for p, nm in [(5, 'sma_5'), (10, 'sma_10'), (20, 'sma_20'), (50, 'sma_50'), (100, 'sma_100'), (200, 'sma_200')]:
        try:
            r = talib.SMA(c, timeperiod=p)
            out[nm] = [safe(x) for x in r]
        except Exception:
            out[nm] = [None] * n

    for p, nm in [(5, 'ema_5'), (10, 'ema_10'), (20, 'ema_20'), (50, 'ema_50'), (100, 'ema_100'), (200, 'ema_200')]:
        try:
            r = talib.EMA(c, timeperiod=p)
            out[nm] = [safe(x) for x in r]
        except Exception:
            out[nm] = [None] * n

    for p, nm in [(5, 'wma_5'), (10, 'wma_10'), (100, 'wma_100'), (200, 'wma_200')]:
        try:
            r = talib.WMA(c, timeperiod=p)
            out[nm] = [safe(x) for x in r]
        except Exception:
            out[nm] = [None] * n

    for p, nm in [(5, 'tema_5'), (10, 'tema_10'), (50, 'tema_50')]:
        try:
            r = talib.TEMA(c, timeperiod=p)
            out[nm] = [safe(x) for x in r]
        except Exception:
            out[nm] = [None] * n

    for p, nm in [(5, 'dema_5'), (10, 'dema_10'), (50, 'dema_50')]:
        try:
            r = talib.DEMA(c, timeperiod=p)
            out[nm] = [safe(x) for x in r]
        except Exception:
            out[nm] = [None] * n

    for p, nm in [(5, 'trima_5'), (10, 'trima_10'), (50, 'trima_50')]:
        try:
            r = talib.TRIMA(c, timeperiod=p)
            out[nm] = [safe(x) for x in r]
        except Exception:
            out[nm] = [None] * n

    try:
        r = talib.KAMA(c, timeperiod=10)
        out['kama_10'] = [safe(x) for x in r]
    except Exception:
        out['kama_10'] = [None] * n

    try:
        r = talib.KAMA(c, timeperiod=20)
        out['kama_20'] = [safe(x) for x in r]
    except Exception:
        out['kama_20'] = [None] * n

    try:
        r = talib.KAMA(c, timeperiod=50)
        out['kama_50'] = [safe(x) for x in r]
    except Exception:
        out['kama_50'] = [None] * n

    # Volume
    try:
        r = talib.OBV(c, v)
        out['obv'] = [int(x) if x is not None else None for x in r]
    except Exception:
        out['obv'] = [None] * n

    try:
        r = talib.AD(h, l, c, v)
        out['ad'] = [safe(x) for x in r]
    except Exception:
        out['ad'] = [None] * n

    try:
        r = talib.ADOSC(h, l, c, v.astype(float), fastperiod=3, slowperiod=10)
        out['adosc'] = [safe(x) for x in r]
    except Exception:
        out['adosc'] = [None] * n

    # VWAP (Volume-Weighted Average Price) - cumulative per session
    try:
        tp = (h + l + c) / 3
        cum_tp_vol = np.cumsum(tp * v)
        cum_vol = np.cumsum(v)
        vwap = np.where(cum_vol > 0, cum_tp_vol / cum_vol, np.nan)
        out['vwap'] = [safe(x) for x in vwap]
    except Exception:
        out['vwap'] = [None] * n

    # Build output rows (only from index 200 onward)
    results = []
    for i in range(200, n):
        vals = {k: v[i] for k, v in out.items()}
        vals = resolve_indicator_dict(vals)
        results.append((symbol, dates[i], vals))

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbols', default='ALL')
    parser.add_argument('--limit', type=int, default=0, help='Max symbols to process in this run')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    with db.connect() as conn:
        # Ensure tables exist
        conn.execute("""
            CREATE TABLE IF NOT EXISTS indicators_json (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                price_date DATE NOT NULL,
                data JSON,
                updated_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_sym_date (symbol, price_date),
                INDEX idx_symbol (symbol),
                INDEX idx_updated (updated_date)
            ) ENGINE=InnoDB
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS indicators (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                price_date DATE NOT NULL,
                natr_7 decimal(10,6), natr_14 decimal(10,6), natr_20 decimal(10,6),
                atr_7 decimal(10,6), atr_14 decimal(10,6), atr_20 decimal(10,6),
                trange decimal(10,6),
                stddev_5 decimal(10,6), stddev_10 decimal(10,6), stddev_14 decimal(10,6),
                var_5 decimal(10,6), var_10 decimal(10,6), var_14 decimal(10,6),
                adx_14 decimal(10,6), adx_21 decimal(10,6),
                adxr_14 decimal(10,6), adxr_21 decimal(10,6),
                ht_trendline decimal(12,4), ht_trendmode tinyint(4),
                ht_dcperiod decimal(8,2), ht_dcphase decimal(8,2),
                ht_phasor_inphase decimal(10,6), ht_phasor_quadrature decimal(10,6),
                ht_sine_sine decimal(10,6), ht_sine_leadsine decimal(10,6),
                rsi_7 decimal(8,4), rsi_14 decimal(8,4), rsi_21 decimal(8,4),
                macd_8_21_5_macd decimal(10,6), macd_8_21_5_signal decimal(10,6),
                macd_12_26_9_macd decimal(10,6), macd_12_26_9_signal decimal(10,6),
                macd_24_52_18_macd decimal(10,6), macd_24_52_18_signal decimal(10,6),
                stoch_5_3_3_k decimal(8,4), stoch_5_3_3_d decimal(8,4),
                stoch_14_3_3_k decimal(8,4), stoch_14_3_3_d decimal(8,4),
                stoch_21_5_5_k decimal(8,4), stoch_21_5_5_d decimal(8,4),
                roc_7 decimal(10,6), roc_14 decimal(10,6), roc_21 decimal(10,6),
                rocp_7 decimal(10,6), rocp_14 decimal(10,6), rocp_21 decimal(10,6),
                rocr_7 decimal(10,6), rocr_14 decimal(10,6), rocr_21 decimal(10,6),
                rocr100_7 decimal(10,4), rocr100_14 decimal(10,4), rocr100_21 decimal(10,4),
                mom_7 decimal(12,4), mom_14 decimal(12,4), mom_21 decimal(12,4),
                avgprice decimal(12,4), bop decimal(10,6),
                ppo_7 decimal(10,6), ppo_14 decimal(10,6), ppo_21 decimal(10,6),
                apo_7 decimal(10,6), apo_14 decimal(10,6), apo_21 decimal(10,6),
                sma_5 decimal(12,4), sma_10 decimal(12,4), sma_20 decimal(12,4),
                sma_50 decimal(12,4), sma_100 decimal(12,4), sma_200 decimal(12,4),
                ema_5 decimal(12,4), ema_10 decimal(12,4), ema_20 decimal(12,4),
                ema_50 decimal(12,4), ema_100 decimal(12,4), ema_200 decimal(12,4),
                wma_5 decimal(12,4), wma_10 decimal(12,4), wma_100 decimal(12,4), wma_200 decimal(12,4),
                tema_5 decimal(12,4), tema_10 decimal(12,4), tema_50 decimal(12,4),
                dema_5 decimal(12,4), dema_10 decimal(12,4), dema_50 decimal(12,4),
                trima_5 decimal(12,4), trima_10 decimal(12,4), trima_50 decimal(12,4),
                kama_10 decimal(12,4), kama_20 decimal(12,4), kama_50 decimal(12,4),
                obv bigint(20), ad decimal(16,4), adosc decimal(12,4),
                linreg_5 decimal(12,4), linreg_10 decimal(12,4), linreg_14 decimal(12,4),
                linreg_intercept_5 decimal(12,4), linreg_intercept_10 decimal(12,4), linreg_intercept_14 decimal(12,4),
                linreg_slope_10 decimal(10,6), linreg_slope_14 decimal(10,6),
                linreg_angle_10 decimal(10,6), linreg_angle_14 decimal(10,6),
                tsf_5 decimal(12,4), tsf_14 decimal(12,4),
                UNIQUE KEY uk_sym_date (symbol, price_date),
                INDEX idx_symbol (symbol)
            ) ENGINE=InnoDB
        """)

        # Retention: keep 1990+
        pruned = conn.execute("DELETE FROM indicators_json WHERE price_date < %s", ('1990-01-01',))
        if pruned:
            print(f"  Pruned {pruned} rows before 1990 from indicators_json")

        INDICATOR_WIDE_COLUMNS = load_indicator_columns(conn)

        if args.symbols == 'ALL':
            rows = conn.fetchall("SELECT DISTINCT symbol FROM stockprices ORDER BY symbol")
        else:
            syms = [s.strip() for s in args.symbols.split(',')]
            placeholders = ','.join(['%s'] * len(syms))
            rows = conn.fetchall(f"SELECT DISTINCT symbol FROM stockprices WHERE symbol IN ({placeholders}) ORDER BY symbol", tuple(syms))

        symbols = [r['symbol'] for r in rows]
        if args.limit:
            symbols = symbols[:args.limit]
        print(f"Computing 120 indicators for {len(symbols)} symbols...")

        total_rows = 0
        t0 = time.time()

        for si, sym in enumerate(symbols):
            rows = conn.fetchall(
                "SELECT price_date, open, high, low, close, volume FROM stockprices WHERE symbol=%s ORDER BY price_date",
                (sym,)
            )
            if len(rows) < 250:
                print(f"  {sym}: {len(rows)} rows — skip")
                continue

            result = compute_for_symbol(sym, rows)
            if not result:
                continue

            json_chunk = []
            wide_chunk = []
            for symbol, pdate, vals in result:
                dumped = json.dumps(vals)
                json_chunk.append((symbol, pdate, dumped))
                row = (symbol, pdate) + tuple(vals.get(k) for k in INDICATOR_WIDE_COLUMNS)
                wide_chunk.append(row)

            for i in range(0, len(json_chunk), BATCH_INSERT_SIZE):
                jc = json_chunk[i:i + BATCH_INSERT_SIZE]
                wc = wide_chunk[i:i + BATCH_INSERT_SIZE]
                conn.executemany(
                    "INSERT INTO indicators_json (symbol, price_date, data) VALUES (%s,%s,%s) "
                    "ON DUPLICATE KEY UPDATE data=VALUES(data)",
                    jc
                )
                conn.executemany(
                    "INSERT INTO indicators (symbol, price_date, " + ",".join(INDICATOR_WIDE_COLUMNS) +
                    ") VALUES (%s,%s," + ",".join(["%s"] * len(INDICATOR_WIDE_COLUMNS)) + ") "
                    "ON DUPLICATE KEY UPDATE " + ",".join(f"{k}=VALUES({k})" for k in INDICATOR_WIDE_COLUMNS),
                    wc
                )

            total_rows += len(result)
            elapsed = time.time() - t0
            print(f"  [{si+1}/{len(symbols)}] {sym}: {len(result)} rows ({elapsed:.0f}s)")

        print(f"\n✓ {total_rows:,} indicator rows in {time.time()-t0:.0f}s")
        cnt = conn.fetchone("SELECT COUNT(*) as cnt FROM indicators_json")
        print(f"  Total in indicators_json: {cnt['cnt']:,}")


if __name__ == '__main__':
    main()
