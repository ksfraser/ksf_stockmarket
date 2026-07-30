"""Probability primitives for signal scoring and Bayesian updating."""
import numpy as np


def expected_value(outcomes, probabilities):
    """Weighted expected value."""
    outcomes = np.asarray(outcomes, dtype=float)
    probabilities = np.asarray(probabilities, dtype=float)
    p_sum = probabilities.sum()
    if p_sum == 0:
        return 0.0
    return float(np.dot(outcomes, probabilities / p_sum))


def conditional_probability(prob_a_given_b, prob_b, prob_a):
    """P(A|B) = P(B|A)*P(A) / P(B) — standard Bayes form."""
    if prob_b == 0:
        return 0.0
    return (prob_a_given_b * prob_a) / prob_b


def bayesian_update(prior, likelihood, evidence):
    """Bayesian posterior: P(H|E) = P(E|H)*P(H) / P(E)."""
    if evidence == 0:
        return prior
    return (likelihood * prior) / evidence


def rolling_signal_probability(signal_series, window=20):
    """Convert a binary signal series into rolling hit-rate probability."""
    import pandas as pd
    s = pd.Series(signal_series).fillna(0)
    return s.rolling(window=window, min_periods=window).mean()
