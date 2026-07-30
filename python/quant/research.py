"""AI-augmented research loop scaffold.

Routes a natural-language hypothesis to the appropriate statistical test,
runs it on live or cached data, and returns structured results for the
LLM analyzer or dashboard to interpret.
"""
import json
import logging
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

import numpy as np
import pandas as pd

from quant.statistics import t_test_significant, ols_regression, adf_stationarity, jarque_bera_normality
from quant.probability import expected_value, bayesian_update, rolling_signal_probability

log = logging.getLogger(__name__)


@dataclass
class ResearchResult:
    hypothesis: str
    test_type: str
    is_significant: bool
    metric: float
    p_value: float
    detail: Dict[str, Any]
    recommendation: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str, indent=2)


def route_hypothesis(hypothesis: str, returns: pd.Series, benchmark: Optional[pd.Series] = None) -> ResearchResult:
    """Auto-detect test type from hypothesis keywords, run it, return result."""
    h = hypothesis.lower()

    if any(k in h for k in ['trend', 'stationary', 'unit root', 'adf']):
        stat, p, sig = adf_stationarity(returns)
        return ResearchResult(hypothesis, 'adf_stationarity', sig, stat, p,
                              {'interpretation': 'Stationary (mean-reverting)' if sig else 'Non-stationary (trending)'},
                              recommendation='Consider mean-reversion strategy' if sig else 'Consider trend-following strategy')

    if any(k in h for k in ['normal', 'distribution', 'normality']):
        jb, p, normal = jarque_bera_normality(returns)
        return ResearchResult(hypothesis, 'jarque_bera', not normal, jb, p,
                              {'distribution': 'Normal' if normal else 'Non-normal (fat tails likely)'},
                              recommendation='Use robust/ percentile-based stops' if not normal else 'Parametric methods OK')

    if any(k in h for k in ['vs sp500', 'vs benchmark', 'beta', 'alpha']):
        if benchmark is None:
            return ResearchResult(hypothesis, 'ols_regression', False, 0.0, 1.0,
                                  {'error': 'No benchmark provided'}, 'Provide benchmark series')
        ols = ols_regression(returns, benchmark)
        sig = ols['p_value'] < 0.05
        return ResearchResult(hypothesis, 'ols_regression', sig, ols['beta'], ols['p_value'],
                              {'alpha': ols['alpha'], 'r_squared': ols['r_squared']},
                              recommendation='Statistically significant alpha' if sig and ols['alpha'] > 0 else 'No significant alpha')

    if any(k in h for k in ['beat', ' outperform', 'excess return', 'mean']):
        mu = float(returns.mean())
        t, p, sig = t_test_significant(returns, null_hypothesis=0.0)
        return ResearchResult(hypothesis, 't_test', sig, t, p,
                              {'mean_daily_return': mu, 'annualized': mu * 252},
                              recommendation='Statistically significant positive mean' if sig and mu > 0 else 'No significant edge detected')

    if any(k in h for k in ['expect', 'kelly', 'position size']):
        win_rate = float((returns > 0).mean())
        avg_win = float(returns[returns > 0].mean()) if (returns > 0).any() else 0.0
        avg_loss = abs(float(returns[returns < 0].mean())) if (returns < 0).any() else 0.01
        ev = expected_value([avg_win, -avg_loss], [win_rate, 1 - win_rate])
        from quant.portfolio import half_kelly_position_size
        kelly = half_kelly_position_size(ev, float(returns.var()))
        return ResearchResult(hypothesis, 'kelly_position', kelly > 0, kelly, 0.0,
                              {'win_rate': win_rate, 'avg_win': avg_win, 'avg_loss': avg_loss, 'expected_value': ev},
                              recommendation=f"Half-Kelly: {kelly*100:.2f}% of capital" if kelly > 0 else 'No positive edge')

    # default: rolling hit rate
    hit_rate = rolling_signal_probability(returns > 0, window=min(20, len(returns)))
    recent = float(hit_rate.iloc[-1]) if len(hit_rate) else 0.0
    return ResearchResult(hypothesis, 'rolling_hit_rate', False, recent, 1.0,
                          {'recent_hit_rate': recent},
                          'Specify test type for richer analysis')
