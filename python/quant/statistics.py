"""Statistical utilities for signal validation and alpha testing."""
import numpy as np
import pandas as pd


def t_test_significant(series, null_hypothesis=0.0, alpha=0.05):
    """One-sample t-test. Returns (t_stat, p_value, is_significant)."""
    from scipy import stats
    x = pd.Series(series).dropna()
    if len(x) < 2:
        return 0.0, 1.0, False
    t_stat, p_value = stats.ttest_1samp(x, null_hypothesis)
    return float(t_stat), float(p_value), bool(p_value < alpha)


def ols_regression(y, x):
    """Single-factor OLS: y ~ x. Returns coefficients dict + residuals."""
    import statsmodels.api as sm
    y = pd.Series(y).dropna()
    x = pd.Series(x).dropna()
    idx = y.index.intersection(x.index)
    if len(idx) < 3:
        return {'beta': 0.0, 'alpha': 0.0, 'r_squared': 0.0, 'p_value': 1.0, 'residuals': pd.Series(dtype=float)}
    y, x = y.loc[idx], x.loc[idx]
    x_const = sm.add_constant(x)
    model = sm.OLS(y, x_const).fit()
    return {
        'beta': float(model.params.iloc[1]),
        'alpha': float(model.params.iloc[0]),
        'r_squared': float(model.rsquared),
        'p_value': float(model.pvalues.iloc[1]),
        'residuals': model.resid,
    }


def adf_stationarity(series, maxlag=1):
    """Augmented Dickey-Fuller test. Returns (adf_stat, p_value, is_stationary)."""
    from statsmodels.tsa.stattools import adfuller
    x = pd.Series(series).dropna()
    if len(x) < 4:
        return 0.0, 1.0, False
    result = adfuller(x, maxlag=maxlag, autolag=None)
    return float(result[0]), float(result[1]), bool(result[1] < 0.05)


def jarque_bera_normality(series):
    """Jarque-Bera normality test. Returns (jb_stat, p_value, is_normal)."""
    from statsmodels.stats.stattools import jarque_bera
    x = pd.Series(series).dropna()
    if len(x) < 3:
        return 0.0, 1.0, False
    jb_stat, p_value, _, _ = jarque_bera(x, axis=0)
    return float(jb_stat), float(p_value), bool(p_value > 0.05)


def compute_statistical_validation(returns: pd.Series) -> dict:
    """
    Run the full validation battery on a return series.
    Returns a dict suitable for persisting to signal_validation:
      t_stat, p_value, is_significant,
      normality_p_value, is_normal,
      adf_stat, adf_p_value, is_stationary,
      kelly_pct,
      validation_json (raw results blob)
    """
    from quant.probability import expected_value, rolling_signal_probability
    from quant.portfolio import half_kelly_position_size

    clean = pd.Series(returns).dropna()
    mu   = float(clean.mean()) if len(clean) else 0.0
    var_ = float(clean.var())   if len(clean) else 1.0

    # t-test against null = 0
    t, p, sig = t_test_significant(clean, null_hypothesis=0.0)

    # normality
    _, p_norm, normal = jarque_bera_normality(clean)

    # ADF stationarity on returns (not prices)
    adf, p_adf, stat = adf_stationarity(clean)

    # half-Kelly from expected value of the return distribution
    win_rate = float((clean > 0).mean()) if len(clean) else 0.5
    avg_win  = float(clean[clean > 0].mean()) if (clean > 0).any() else 0.0
    avg_loss = abs(float(clean[clean < 0].mean())) if (clean < 0).any() else 0.01
    ev = expected_value([avg_win, -avg_loss], [win_rate, 1 - win_rate])
    kelly = half_kelly_position_size(ev, var_)

    result = {
        't_stat':           round(t, 4)       if t     else None,
        'p_value':          round(p, 6)       if p     else None,
        'is_significant':   int(bool(sig)),
        'normality_p_value':round(p_norm, 6)  if p_norm else None,
        'is_normal':        int(bool(normal)),
        'adf_stat':         round(adf, 4)     if adf   else None,
        'adf_p_value':      round(p_adf, 6)  if p_adf  else None,
        'is_stationary':    int(bool(stat)),
        'kelly_pct':        round(kelly * 100, 4) if kelly else 0.0,
        'validation_json': {
            'win_rate':     round(win_rate, 4),
            'avg_win':      round(avg_win, 6),
            'avg_loss':     round(avg_loss, 6),
            'expected_val': round(ev, 6),
            'mean_daily':   round(mu, 6),
            'variance':     round(var_, 6),
        },
    }
    return result
