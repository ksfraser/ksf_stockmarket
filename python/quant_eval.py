#!/usr/bin/env python3
"""
Quant Strategy Evaluation Module
Derived from ai-quant-workbench concepts: OLS, Bayes, Half-Kelly position sizing
"""

import numpy as np
import pandas as pd
from scipy import stats
import pymysql
import json
import sys

MYSQL = {
    'host': 'ksfraser.ca',
    'user': 'ksfraser_stockmarket',
    'password': 'Zaqwsx9sm1@',
    'database': 'ksfraser_stock_market',
    'autocommit': True
}

def get_symbol_returns(symbol, days=252):
    """Fetch daily returns for a symbol from ta_indicators table."""
    conn = pymysql.connect(**MYSQL)
    c = conn.cursor()
    c.execute("""
        SELECT price_date, close FROM ta_indicators 
        WHERE symbol = %s AND close IS NOT NULL
        ORDER BY price_date DESC LIMIT %s
    """, (symbol, days))
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        return None
    
    df = pd.DataFrame(rows, columns=['date', 'close'])
    df = df.sort_values('date')
    df['return'] = df['close'].pct_change()
    return df['return'].dropna()

def ols_regression(symbol_signal, benchmark='SPY'):
    """
    Single-factor OLS regression of signal returns on benchmark.
    Returns alpha, beta, r-squared, p-value.
    """
    sig_ret = get_symbol_returns(symbol_signal)
    bench_ret = get_symbol_returns(benchmark)
    
    if sig_ret is None or bench_ret is None:
        return {'error': f'Insufficient data for {symbol_signal} or {benchmark}'}
    
    # Align returns
    df = pd.DataFrame({'sig': sig_ret, 'bench': bench_ret}).dropna()
    
    X = df['bench'].values
    Y = df['sig'].values
    
    # Add constant for alpha
    X_with_const = np.column_stack([np.ones(len(X)), X])
    
    # OLS solution
    beta_alpha = np.linalg.lstsq(X_with_const, Y, rcond=None)[0]
    alpha, beta = beta_alpha
    
    # R-squared
    Y_pred = X_with_const @ beta_alpha
    ss_res = np.sum((Y - Y_pred) ** 2)
    ss_tot = np.sum((Y - Y.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    
    # T-test for alpha
    residuals = Y - Y_pred
    se_alpha = np.sqrt(np.sum(residuals**2) / (len(Y) - 2)) * np.sqrt(1/len(Y) + df['bench'].mean()**2 / np.sum((X - X.mean())**2))
    t_stat = alpha / se_alpha if se_alpha > 0 else 0
    p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=len(Y) - 2))
    
    return {
        'alpha': round(alpha, 6),
        'beta': round(beta, 4),
        'r_squared': round(r2, 4),
        'p_value': round(p_value, 4),
        'observations': len(Y)
    }

def bayes_update(prior, likelihood_given_signal, likelihood_given_no_signal):
    """
    Bayesian probability update.
    prior: prior probability (e.g., 0.40)
    likelihood_given_signal: P(signal|event) (e.g., 0.70)
    likelihood_given_no_signal: P(signal|no event) (e.g., 0.40)
    Returns posterior probability.
    """
    numerator = likelihood_given_signal * prior
    denominator = numerator + likelihood_given_no_signal * (1 - prior)
    posterior = numerator / denominator if denominator > 0 else prior
    return round(posterior, 4)

def half_kelly(edge_percent, win_rate, cap_pct=0.02):
    """
    Half-Kelly position sizing with hard cap.
    edge_percent: expected edge (e.g., 0.05 for 5%)
    win_rate: probability of winning (e.g., 0.68)
    cap_pct: max position size (default 2%)
    """
    # Kelly formula: f* = p - q/a where p=win_rate, q=1-p, a=edge
    if edge_percent <= 0 or win_rate <= 0 or win_rate >= 1:
        return 0
    
    # Simplified Kelly: f* = edge / (win_rate * (1 - win_rate)) adjusted
    # More standard: f* = (p * a - q) / a where a = win_rate - (1-win_rate) for edge=prob diff
    # For expected value: f* = edge / (avg_win/avg_loss) approximation
    # Using simplified: f* = p - q = 2*p - 1 for binary edge
    f_star = (win_rate * edge_percent - (1 - win_rate)) / edge_percent
    f_star = max(0, min(f_star, 1))  # Bound 0-1
    
    # Half-Kelly
    half_kelly = f_star / 2
    
    # Apply hard cap
    return round(min(half_kelly, cap_pct), 4)

def evaluate_strategy(rule_id):
    """Run full evaluation on a strategy rule."""
    conn = pymysql.connect(**MYSQL)
    c = conn.cursor()
    
    c.execute("SELECT * FROM strategy_rules WHERE id = %s", (rule_id,))
    rule = c.fetchone()
    conn.close()
    
    if not rule:
        return {'error': 'Strategy rule not found'}
    
    result = {
        'rule_id': rule_id,
        'rule_name': rule[2],
        'bucket': rule[3]
    }
    
    # Get watchlist (symbols to evaluate)
    watchlist = json.loads(rule[4] or '[]')
    
    if watchlist:
        evaluations = []
        for symbol in watchlist[:5]:  # Limit for performance
            ols = ols_regression(symbol)
            if 'error' not in ols:
                # Position size based on R-squared as confidence
                pos_size = half_kelly(0.05, ols['r_squared'], 0.02)
                ols['position_size'] = pos_size
            evaluations.append({'symbol': symbol, 'ols': ols})
        
        result['evaluations'] = evaluations
    
    return result

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python quant_eval.py <command> [args]")
        print("Commands: ols <symbol> [benchmark], kelly <edge> <win_rate>, bayes <prior> <lik_sig> <lik_no>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == 'ols' and len(sys.argv) >= 3:
        benchmark = sys.argv[3] if len(sys.argv) > 3 else 'SPY'
        print(json.dumps(ols_regression(sys.argv[2], benchmark), indent=2))
    
    elif cmd == 'kelly' and len(sys.argv) >= 4:
        edge = float(sys.argv[2]) / 100
        win = float(sys.argv[3]) / 100
        print(json.dumps({'half_kelly_position': f"{half_kelly(edge, win)*100:.2f}%"}))
    
    elif cmd == 'bayes' and len(sys.argv) >= 5:
        prior = float(sys.argv[2])
        lik_sig = float(sys.argv[3])
        lik_no = float(sys.argv[4])
        print(json.dumps({'posterior': bayes_update(prior, lik_sig, lik_no)}))
    
    elif cmd == 'evaluate' and len(sys.argv) >= 3:
        print(json.dumps(evaluate_strategy(int(sys.argv[2])), indent=2))