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

try:
    import talib
except ImportError:
    print("TA-Lib not installed. Run: pip3 install ta-lib"); sys.exit(1)

MYSQL = dict(host='ksfraser.ca', user='ksfraser_stockmarket',
             password='Zaqwsx9sm1@', database='ksfraser_stock_market',
             charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)

BATCH_INSERT_SIZE = 500


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

    # Oscillators
    for p, nm in [(7,'rsi_7'),(14,'rsi_14'),(21,'rsi_21')]:
        try:
            r = talib.RSI(c, timeperiod=p)
            out[nm] = [safe(x) for x in r]
        except: out[nm] = [None]*n

    # MACD
    for fp, sp, sig, prefix in [(8,21,5,'macd_8_21_5'),(12,26,9,'macd_12_26_9'),(24,52,18,'macd_24_52_18')]:
        try:
            m, s, h = talib.MACD(c, fp, sp, sig)
            out[f'{prefix}_macd'] = [safe(x) for x in m]
            out[f'{prefix}_signal'] = [safe(x) for x in s]
        except:
            out[f'{prefix}_macd'] = [None]*n
            out[f'{prefix}_signal'] = [None]*n

    # STOCH
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
        for p in [5,10,20,50,100,200]:
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

    # Build output rows (only from index 200 onward)
    results = []
    for i in range(200, n):
        vals = {k: v[i] for k, v in out.items()}
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
    c.execute("""CREATE TABLE IF NOT EXISTS indicators_json (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        price_date DATE NOT NULL,
        data JSON,
        UNIQUE KEY uk_sym_date (symbol, price_date),
        INDEX idx_symbol (symbol)
    ) ENGINE=InnoDB""")
    conn.commit()

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

        # Insert in batches using JSON
        batch = []
        for symbol, pdate, vals in result:
            batch.append((symbol, pdate, json.dumps(vals)))

        for i in range(0, len(batch), BATCH_INSERT_SIZE):
            chunk = batch[i:i+BATCH_INSERT_SIZE]
            c.executemany("INSERT IGNORE INTO indicators_json (symbol, price_date, data) VALUES (%s,%s,%s)", chunk)
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
