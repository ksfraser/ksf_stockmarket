#!/usr/bin/env python3
"""
Param Correlation / Redundancy Analysis (REQ-09)

Uses `signal_type_accuracy` (from WeightOptimizer) and `signal_weights`
to compute correlation between signal types. Identifies redundant params
(e.g., MA_ALIGN vs SMA200 correlation, RSI vs STOCH overlap).
"""
import sqlite3, json, sys
sys.path.insert(0, '.')
from optimization.weight_optimizer import DEFAULT_WEIGHTS

SCHEMA_CHECK = """
SELECT name FROM sqlite_master WHERE type='table' AND name='signal_type_accuracy';
"""

def compute_param_correlation(conn: sqlite3.Connection) -> dict:
    c = conn.cursor()
    # Check if accuracy table exists (populated by WeightOptimizer)
    c.execute(SCHEMA_CHECK)
    if not c.fetchall():
        return {'error': 'signal_type_accuracy table not found; run WeightOptimizer first'}

    # Get accuracy data per ticker and signal type
    c.execute("SELECT ticker, signal_type, win_rate FROM signal_type_accuracy WHERE occurrences > 2")
    rows = c.fetchall()
    if not rows:
        return {'error': 'No accuracy data found; run backtest optimization first'}

    # Build correlation matrix (simplified: compare per-ticker accuracy vectors)
    from collections import defaultdict
    ticker_sig_accuracy = defaultdict(dict)
    for ticker, sig, win_rate in rows:
        ticker_sig_accuracy[ticker][sig] = win_rate

    # Compute pairwise correlation across tickers (Pearson approximation)
    import math
    sig_types = list(DEFAULT_WEIGHTS.keys())
    correlations = {}
    for i, s1 in enumerate(sig_types):
        for s2 in sig_types[i+1:]:
            pairs = []
            for ticker in ticker_sig_accuracy:
                if s1 in ticker_sig_accuracy[ticker] and s2 in ticker_sig_accuracy[ticker]:
                    pairs.append((ticker_sig_accuracy[ticker][s1], ticker_sig_accuracy[ticker][s2]))
            if len(pairs) > 1:
                x_vals = [p[0] for p in pairs]
                y_vals = [p[1] for p in pairs]
                # Pearson correlation approximation
                n = len(x_vals)
                mean_x = sum(x_vals) / n
                mean_y = sum(y_vals) / n
                cov = sum((x_vals[i] - mean_x) * (y_vals[i] - mean_y) for i in range(n))
                std_x = math.sqrt(sum((x - mean_x)**2 for x in x_vals) / max(n-1, 1))
                std_y = math.sqrt(sum((y - mean_y)**2 for y in y_vals) / max(n-1, 1))
                corr = cov / (std_x * std_y) if std_x > 0 and std_y > 0 else 0
                correlations[f"{s1}_vs_{s2}"] = {
                    'correlation': round(corr, 4),
                    'n_tickers': n,
                    'redundancy_level': 'HIGH' if corr > 0.8 else 'MODERATE' if corr > 0.5 else 'LOW',
                    'note': f"Parameters with correlation >0.8 may stand in for each other; review weight allocation."
                }
    return correlations

if __name__ == '__main__':
    conn = sqlite3.connect(':memory:')  # Use actual DB in production
    result = compute_param_correlation(conn)
    print(json.dumps(result, indent=2))
