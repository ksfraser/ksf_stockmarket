#!/usr/bin/env python3
"""
indicator_calculator.py — Compute 120 useful TA-Lib indicators for all symbols.

Reads from MySQL stockprices, computes indicators using TA-Lib,
writes to MySQL indicators table.

Usage:
    python3 indicator_calculator.py [--verbose]
"""
import pymysql, numpy as np, json, sys, os, argparse, time
from datetime import date
from config_loader import Config

# Import canonical indicator key registry
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from indicator_keys import ALL_KEYS, ALIASES, resolve_indicator_dict

try:
    import talib
except ImportError:
    print("TA-Lib not installed. Run: pip3 install ta-lib"); sys.exit(1)

# Credentials loaded from Ansible Vault via config_loader
_cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml')
_cfg = Config(_cfg_path) if os.path.exists(_cfg_path) else Config()
MYSQL = dict(
    host=_cfg.data.db_host,
    user=_cfg.data.db_user,
    password=_cfg.db_password,
    database=_cfg.data.db_name,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)

BATCH_INSERT_SIZE = 500

def load_indicator_columns(conn):
    with conn.cursor() as c:
        c.execute("DESCRIBE indicators")
        return [r['Field'] for r in c.fetchall() if r['Field'] not in ('id', 'symbol', 'price_date')]


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

    # Pre-compute all TA-Lib outputs (full series)
    out = {}

    safe = lambda x: float(x) if x is not None and not np.isnan(x) and not np.isinf(x) else None

    # Volatility
    for p, nm in [(7,'natr_7'),(14,'natr_14'),(20,'natr_20')]:
        try:
            r = talib.NATR(h, l, c, timeperiod=p)
            out[nm] = [safe(x) for x in r]
        except: out[nm] = [None]*n

    for p, nm in [(7,'atr_7'),(14,'atr_14'),(20,'atr_20')]:
        try:
            r = talib.ATR(h, l, c, timeperiod=p)
            out[nm] = [safe(x) for x in r]
        except: out[nm] = [None]*n

    try:
        r = talib.TRANGE(h, l, c)
        out['trange'] = [safe(x) for x in r]
    except: out['trange'] = [None]*n

    for p, nm in [(5,'stddev_5'),(10,'stddev_10'),(14,'stddev_14')]:
        try:
            r = talib.STDDEV(c, timeperiod=p, nbdev=1)
            out[nm] = [safe(x) for x in r]
        except: out[nm] = [None]*n

    for p, nm in [(5,'var_5'),(10,'var_10'),(14,'var_14')]:
        try:
            r = talib.VAR(c, timeperiod=p, nbdev=1)
            out[nm] = [safe(x) for x in r]
        except: out[nm] = [None]*n

    # Trend
    for p, nm in [(14,'adx_14'),(21,'adx_21')]:
        try:
            r = talib.ADX(h, l, c, timeperiod=p)
            out[nm] = [safe(x) for x in r]
        except: out[nm] = [None]*n

    for p, nm in [(14,'adxr_14'),(21,'adxr_21')]:
        try:
            r = talib.ADXR(h, l, c, timeperiod=p)
            out[nm] = [safe(x) for x in r]
        except: out[nm] = [None]*n

    # Hilbert
    try:
        r = talib.HT_TRENDLINE(c)
        out['ht_trendline'] = [safe(x) for x in r]
    except: out['ht_trendline'] = [None]*n

    try:
        r = talib.HT_TRENDMODE(c)
        out['ht_trendmode'] = [int(x) if x is not None and not np.isnan(x) else None for x in r]
    except: out['ht_trendmode'] = [None]*n

    try:
        r = talib.HT_DCPERIOD(c)
        out['ht_dcperiod'] = [safe(x) for x in r]
    except: out['ht_dcperiod'] = [None]*n

    try:
        r = talib.HT_DCPHASE(c)
        out['ht_dcphase'] = [safe(x) for x in r]
    except: out['ht_dcphase'] = [None]*n

    try:
        ip, qp = talib.HT_PHASOR(c)
        out['ht_phasor_inphase'] = [safe(x) for x in ip]
        out['ht_phasor_quadrature'] = [safe(x) for x in qp]
    except:
        out['ht_phasor_inphase'] = [None]*n
        out['ht_phasor_quadrature'] = [None]*n

    try:
        s, ls = talib.HT_SINE(c)
        out['ht_sine_sine'] = [safe(x) for x in s]
        out['ht_sine_leadsine'] = [safe(x) for x in ls]
    except:
        out['ht_sine_sine'] = [None]*n
        out['ht_sine_leadsine'] = [None]*n

    # RSI - use canonical keys
    for p, nm in [(3, 'rsi_3'), (7, 'rsi_7'), (14, 'rsi_14'), (21, 'rsi_21')]:
        try:
            r = talib.RSI(c, timeperiod=p)
            out[nm] = [safe(x) for x in r]
        except: out[nm] = [None]*n

    # High 60 - 60-day highest high (for trailing stop calculation)
    try:
        out['high_60'] = [safe(x) for x in talib.MAX(h, timeperiod=60)]
    except: out['high_60'] = [None]*n

    # MACD - use canonical keys
    for fp, sp, sig, prefix in [(8, 21, 5, 'macd_8_21_5'), (12, 26, 9, 'macd_12_26_9'), (24, 52, 18, 'macd_24_52_18')]:
        try:
            m, s, h = talib.MACD(c, fp, sp, sig)
            out[f'{prefix}_macd'] = [safe(x) for x in m]
            out[f'{prefix}_signal'] = [safe(x) for x in s]
            out[f'{prefix}_hist'] = [safe(x) for x in h]
        except:
            out[f'{prefix}_macd'] = [None]*n
            out[f'{prefix}_signal'] = [None]*n
            out[f'{prefix}_hist'] = [None]*n

    # STOCH - use canonical keys
    for fk, sk, sd, prefix in [(5,3,3,'stoch_5_3_3'),(14,3,3,'stoch_14_3_3'),(21,5,5,'stoch_21_5_5')]:
        try:
            k, d = talib.STOCH(h, l, c, fastk_period=fk, slowk_period=sk, slowd_period=sd)
            out[f'{prefix}_k'] = [safe(x) for x in k]
            out[f'{prefix}_d'] = [safe(x) for x in d]
        except:
            out[f'{prefix}_k'] = [None]*n
            out[f'{prefix}_d'] = [None]*n

    # ROC family
    for base, func in [('roc',talib.ROC),('rocp',talib.ROCP),('rocr',talib.ROCR),('rocr100',talib.ROCR100),('mom',talib.MOM)]:
        for p in [7,14,21]:
            nm = f'{base}_{p}'
            try:
                r = func(c, timeperiod=p)
                out[nm] = [safe(x) for x in r]
            except: out[nm] = [None]*n

    # Price transform
    try:
        r = talib.AVGPRICE(o, h, l, c)
        out['avgprice'] = [safe(x) for x in r]
    except: out['avgprice'] = [None]*n

    try:
        r = talib.BOP(o, h, l, c)
        out['bop'] = [safe(x) for x in r]
    except: out['bop'] = [None]*n

    for p, prefix in [(7,'ppo'),(14,'ppo'),(21,'ppo')]:
        try:
            r = talib.PPO(c, fastperiod=12, slowperiod=p, matype=0)
            out[f'{prefix}_{p}'] = [safe(x) for x in r]
        except: out[f'{prefix}_{p}'] = [None]*n

    for p, prefix in [(7,'apo'),(14,'apo'),(21,'apo')]:
        try:
            r = talib.APO(c, fastperiod=12, slowperiod=p, matype=0)
            out[f'{prefix}_{p}'] = [safe(x) for x in r]
        except: out[f'{prefix}_{p}'] = [None]*n

    # Moving averages
    ma_map = {'sma':talib.SMA,'ema':talib.EMA,'wma':talib.WMA,'tema':talib.TEMA,'dema':talib.DEMA,'trima':talib.TRIMA}
    for prefix, func in ma_map.items():
        for p in [5,8,10,20,50,100,200]:
            if prefix in ('tema','dema','trima') and p == 200:
                continue
            try:
                r = func(c, timeperiod=p)
                out[f'{prefix}_{p}'] = [safe(x) for x in r]
            except: out[f'{prefix}_{p}'] = [None]*n

    # KAMA
    for p in [10,20,50]:
        try:
            r = talib.KAMA(c, timeperiod=p)
            out[f'kama_{p}'] = [safe(x) for x in r]
        except: out[f'kama_{p}'] = [None]*n

    # Bollinger Bands
    for period, std in [(5,2.0),(5,2.5),(10,2.0),(10,2.5),(20,2.0),(20,2.5),(50,1.5),(50,2.0),(50,2.5)]:
        sk = str(std).replace('.','_')
        try:
            u, m, lo = talib.BBANDS(c, timeperiod=period, nbdevup=std, nbdevdn=std)
            out[f'bb_{period}_{sk}_upper'] = [safe(x) for x in u]
            out[f'bb_{period}_{sk}_mid'] = [safe(x) for x in m]
            out[f'bb_{period}_{sk}_lower'] = [safe(x) for x in lo]
        except:
            out[f'bb_{period}_{sk}_upper'] = [None]*n
            out[f'bb_{period}_{sk}_mid'] = [None]*n
            out[f'bb_{period}_{sk}_lower'] = [None]*n

    # Linear Regression
    for p in [5,10,14]:
        try:
            r = talib.LINEARREG(c, timeperiod=p)
            out[f'linreg_{p}'] = [safe(x) for x in r]
        except: out[f'linreg_{p}'] = [None]*n

        try:
            r = talib.LINEARREG_INTERCEPT(c, timeperiod=p)
            out[f'linreg_intercept_{p}'] = [safe(x) for x in r]
        except: out[f'linreg_intercept_{p}'] = [None]*n

    for p in [10,14]:
        try:
            r = talib.LINEARREG_SLOPE(c, timeperiod=p)
            out[f'linreg_slope_{p}'] = [safe(x) for x in r]
        except: out[f'linreg_slope_{p}'] = [None]*n

        try:
            r = talib.LINEARREG_ANGLE(c, timeperiod=p)
            out[f'linreg_angle_{p}'] = [safe(x) for x in r]
        except: out[f'linreg_angle_{p}'] = [None]*n

    for p in [5,10,14]:
        try:
            r = talib.TSF(c, timeperiod=p)
            out[f'tsf_{p}'] = [safe(x) for x in r]
        except: out[f'tsf_{p}'] = [None]*n

    # Volume
    try:
        r = talib.OBV(c, v.astype(float))
        out['obv'] = [safe(x) for x in r]
    except: out['obv'] = [None]*n

    try:
        r = talib.AD(h, l, c, v.astype(float))
        out['ad'] = [safe(x) for x in r]
    except: out['ad'] = [None]*n

    try:
        r = talib.ADOSC(h, l, c, v.astype(float), fastperiod=3, slowperiod=10)
        out['adosc'] = [safe(x) for x in r]
    except: out['adosc'] = [None]*n

    # VWAP (Volume-Weighted Average Price) - cumulative per session
    # Calculates running VWAP: sum(typical_price * volume) / sum(volume)
    try:
        tp = (h + l + c) / 3  # Typical price
        cum_tp_vol = np.cumsum(tp * v)
        cum_vol = np.cumsum(v)
        vwap = np.where(cum_vol > 0, cum_tp_vol / cum_vol, np.nan)
        out['vwap'] = [safe(x) for x in vwap]
    except: out['vwap'] = [None]*n

    # Build output rows (only from index 200 onward)
    results = []
    for i in range(200, n):
        vals = {k: v[i] for k, v in out.items()}
        # Resolve canonical + legacy keys for backward compatibility
        vals = resolve_indicator_dict(vals)
        results.append((symbol, dates[i], vals))

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbols', default='ALL')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    conn = pymysql.connect(**MYSQL)
    c = conn.cursor()

    # Create JSON table first
    c.execute("""
        CREATE TABLE IF NOT EXISTS indicators_json (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            price_date DATE NOT NULL,
            data JSON,
            updated_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_sym_date (symbol, price_date),
            INDEX idx_symbol (symbol),
            INDEX idx_updated (updated_date)
        ) ENGINE=InnoDB""")
    conn.commit()

    c.execute("""
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
        ) ENGINE=InnoDB""")
    conn.commit()

    INDICATOR_WIDE_COLUMNS = load_indicator_columns(conn)

    if args.symbols == 'ALL':
        c.execute("SELECT DISTINCT symbol FROM stockprices ORDER BY symbol")
    else:
        syms = [s.strip() for s in args.symbols.split(',')]
        placeholders = ','.join(['%s'] * len(syms))
        c.execute(f"SELECT DISTINCT symbol FROM stockprices WHERE symbol IN ({placeholders}) ORDER BY symbol", syms)

    symbols = [r['symbol'] for r in c.fetchall()]
    print(f"Computing 120 indicators for {len(symbols)} symbols...")

    total_rows = 0
    t0 = time.time()

    for si, sym in enumerate(symbols):
        c.execute("SELECT price_date, open, high, low, close, volume FROM stockprices "
                  "WHERE symbol=%s ORDER BY price_date", (sym,))
        rows = c.fetchall()
        if len(rows) < 250:
            print(f"  {sym}: {len(rows)} rows — skip"); continue

        result = compute_for_symbol(sym, rows)
        if not result: continue

        # Insert in batches using JSON and wide table
        json_chunk = []
        wide_chunk = []
        for symbol, pdate, vals in result:
            dumped = json.dumps(vals)
            json_chunk.append((symbol, pdate, dumped))
            row = (symbol, pdate) + tuple(vals.get(k) for k in INDICATOR_WIDE_COLUMNS)
            wide_chunk.append(row)

        for i in range(0, len(json_chunk), BATCH_INSERT_SIZE):
            jc = json_chunk[i:i+BATCH_INSERT_SIZE]
            wc = wide_chunk[i:i+BATCH_INSERT_SIZE]
            c.executemany(
                "INSERT INTO indicators_json (symbol, price_date, data) VALUES (%s,%s,%s) "
                "ON DUPLICATE KEY UPDATE data=VALUES(data)",
                jc
            )
            c.executemany(
                "INSERT INTO indicators (symbol, price_date, " + ",".join(INDICATOR_WIDE_COLUMNS) + ") VALUES (%s,%s," + ",".join(["%s"] * len(INDICATOR_WIDE_COLUMNS)) + ") "
                "ON DUPLICATE KEY UPDATE " + ",".join(f"{k}=VALUES({k})" for k in INDICATOR_WIDE_COLUMNS),
                wc
            )
            conn.commit()

        total_rows += len(result)
        elapsed = time.time() - t0
        print(f"  [{si+1}/{len(symbols)}] {sym}: {len(result)} rows ({elapsed:.0f}s)")

    print(f"\n✓ {total_rows:,} indicator rows in {time.time()-t0:.0f}s")

    # Verify
    c.execute("SELECT COUNT(*) as cnt FROM indicators_json")
    print(f"  Total in indicators_json: {c.fetchone()['cnt']:,}")

    conn.close()


if __name__ == '__main__':
    main()
