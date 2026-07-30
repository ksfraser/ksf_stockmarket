"""Portfolio math: covariance, PCA risk decomposition, half-Kelly sizing."""
import numpy as np
import pandas as pd


def sample_covariance(returns_df):
    """Sample covariance matrix from a returns DataFrame (assets as columns)."""
    clean = returns_df.dropna(axis=1, how='all').dropna(axis=0, how='all')
    if clean.shape[0] < 2:
        return pd.DataFrame()
    return clean.cov()


def pca_risk_decomposition(returns_df, n_components=None):
    """Eigendecomposition of covariance matrix. Returns eigenvalues/vectors."""
    cov = sample_covariance(returns_df)
    if cov.empty:
        return {'eigenvalues': np.array([]), 'eigenvectors': np.array([]), 'explained_variance': np.array([])}
    vals, vecs = np.linalg.eigh(cov.values)
    idx = np.argsort(vals)[::-1]
    vals, vecs = vals[idx], vecs[:, idx]
    total = vals.sum() if vals.sum() > 0 else 1.0
    return {
        'eigenvalues': vals,
        'eigenvectors': vecs,
        'explained_variance': vals / total,
        'assets': list(cov.columns),
    }


def portfolio_variance(weights, cov_matrix):
    """w^T Σ w — portfolio variance given weights and covariance matrix."""
    w = np.asarray(weights, dtype=float)
    cov = np.asarray(cov_matrix, dtype=float)
    if w.shape[0] != cov.shape[0]:
        raise ValueError("weights length must match covariance matrix dimension")
    return float(w @ cov @ w)


def half_kelly_position_size(expected_return, variance, confidence=0.5, max_capital_fraction=0.02):
    """Half-Kelly: f* = 0.5 * (mu / sigma^2), capped at max_capital_fraction."""
    if variance <= 0:
        return 0.0
    kelly = confidence * (expected_return / variance)
    position = 0.5 * kelly
    return float(min(position, max_capital_fraction))


def risk_contribution(weights, cov_matrix):
    """Marginal risk contribution per asset: (Σ w)_i * w_i."""
    w = np.asarray(weights, dtype=float)
    sig = np.asarray(cov_matrix, dtype=float)
    port_vol = np.sqrt(portfolio_variance(w, sig))
    if port_vol == 0:
        return [0.0] * len(w)
    marginal = sig @ w
    return [float(marginal[i] * w[i] / port_vol) for i in range(len(w))]
