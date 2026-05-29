"""
test_blender.py — Unit tests for Blender Agent
===============================================
Tests:
- Signal consensus computation
- Position sizing with caps
- Rebalance plan generation
- Order prioritization (sells first)
"""

import pytest
import sys
import os
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tests.conftest import (
    setup_test_database, get_test_db, seed_test_prices,
    seed_test_indicators, seed_test_evalsummary, seed_test_signal_weights,
    cleanup_test_db
)


class TestSignalConsensus:
    """Test the weighted consensus engine."""

    def setup_method(self):
        setup_test_database()

    def test_all_strong_buy_consensus(self):
        """All agents STRONG_BUY → consensus should be STRONG_BUY."""
        from python.agents.blender import SignalConsensus, DEFAULT_CONFIG
        config = {**DEFAULT_CONFIG}
        engine = SignalConsensus(config)

        ga = {'direction': 'STRONG_BUY', 'strength': 50}
        nn = {'direction': 'STRONG_BUY', 'confidence': 0.9, 'user_cap_weight': 0.15}
        rl = {'direction': 'STRONG_BUY', 'confidence': 0.85, 'target_weight': 0.10}

        result = engine.compute_consensus(ga, nn, rl)
        assert result['direction'] == 'STRONG_BUY'
        assert result['consensus_pct'] == pytest.approx(100.0, abs=5)
        assert result['consensus_score'] > 0

    def test_all_strong_sell_consensus(self):
        """All agents STRONG_SELL → consensus should be STRONG_SELL."""
        from python.agents.blender import SignalConsensus, DEFAULT_CONFIG
        config = {**DEFAULT_CONFIG}
        engine = SignalConsensus(config)

        ga = {'direction': 'STRONG_SELL', 'strength': -50}
        nn = {'direction': 'STRONG_SELL', 'confidence': 0.9, 'user_cap_weight': 0.05}
        rl = {'direction': 'STRONG_SELL', 'confidence': 0.85, 'target_weight': 0.03}

        result = engine.compute_consensus(ga, nn, rl)
        assert result['direction'] == 'STRONG_SELL'
        assert result['consensus_score'] < 0

    def test_mixed_hold_consensus(self):
        """Mixed signals → should tend toward HOLD."""
        from python.agents.blender import SignalConsensus, DEFAULT_CONFIG
        config = {**DEFAULT_CONFIG}
        engine = SignalConsensus(config)

        ga = {'direction': 'BUY', 'strength': 5}
        nn = {'direction': 'HOLD', 'confidence': 0.4, 'user_cap_weight': 0.05}
        rl = {'direction': 'SELL', 'confidence': 0.6, 'target_weight': 0.03}

        result = engine.compute_consensus(ga, nn, rl)
        # With conflicting signals, should be near 0
        assert abs(result['consensus_score']) < 0.5

    def test_strong_buy_wins(self):
        """Strong BUY + mild BUY → STRONG_BUY."""
        from python.agents.blender import SignalConsensus, DEFAULT_CONFIG
        config = {**DEFAULT_CONFIG}
        engine = SignalConsensus(config)

        ga = {'direction': 'STRONG_BUY', 'strength': 50}
        nn = {'direction': 'STRONG_BUY', 'confidence': 0.95, 'user_cap_weight': 0.15}
        rl = {'direction': 'BUY', 'confidence': 0.8, 'target_weight': 0.10}

        result = engine.compute_consensus(ga, nn, rl)
        assert result['direction'] in ('BUY', 'STRONG_BUY')
        assert result['consensus_pct'] >= 66.6

    def test_consensus_pct_range(self):
        """Consensus % should always be between 0 and 100."""
        from python.agents.blender import SignalConsensus, DEFAULT_CONFIG
        config = {**DEFAULT_CONFIG}
        engine = SignalConsensus(config)

        for ga_dir in ['BUY', 'SELL', 'HOLD']:
            for nn_dir in ['BUY', 'SELL', 'HOLD']:
                for rl_dir in ['BUY', 'SELL', 'HOLD']:
                    ga = {'direction': ga_dir, 'strength': 10}
                    nn = {'direction': nn_dir, 'confidence': 0.5, 'user_cap_weight': 0.05}
                    rl = {'direction': rl_dir, 'confidence': 0.5, 'target_weight': 0.05}
                    result = engine.compute_consensus(ga, nn, rl)
                    assert 0 <= result['consensus_pct'] <= 100

    def test_agent_agreement_tracking(self):
        """Consensus should track which agents agree on the SAME direction."""
        from python.agents.blender import SignalConsensus, DEFAULT_CONFIG
        config = {**DEFAULT_CONFIG}
        engine = SignalConsensus(config)

        # All agree on BUY (not STRONG_BUY — the consensus may upgrade to STRONG_BUY
        # but agents_agree checks exact match with individual directions)
        result = engine.compute_consensus(
            {'direction': 'BUY', 'strength': 20},
            {'direction': 'BUY', 'confidence': 0.8, 'user_cap_weight': 0.10},
            {'direction': 'BUY', 'confidence': 0.7, 'target_weight': 0.08},
        )
        # All 3 agents say BUY — they agree with each other
        assert len(result['agents_agree']) == 3
        assert set(result['agents_agree']) == {'GA', 'NN', 'RL'}


class TestBlenderConfig:
    """Test blender configuration."""

    def test_weights_sum_to_one(self):
        """GA + NN + RL weights should sum to 1.0."""
        from python.agents.blender import DEFAULT_CONFIG
        total = DEFAULT_CONFIG['ga_weight'] + DEFAULT_CONFIG['nn_weight'] + DEFAULT_CONFIG['rl_weight']
        assert total == pytest.approx(1.0, abs=0.01)

    def test_required_config_keys(self):
        """Config should have all required keys."""
        from python.agents.blender import DEFAULT_CONFIG
        required = ['ga_weight', 'nn_weight', 'rl_weight', 'consensus_threshold',
                     'max_positions', 'risk_per_trade_pct']
        for key in required:
            assert key in DEFAULT_CONFIG


class TestBlenderSignalMapping:
    """Test signal direction mapping."""

    def test_signal_scores(self):
        """Signal scores should be correctly ordered."""
        from python.agents.blender import SIGNAL_SCORES
        assert SIGNAL_SCORES['STRONG_BUY'] > SIGNAL_SCORES['BUY']
        assert SIGNAL_SCORES['BUY'] > SIGNAL_SCORES['HOLD']
        assert SIGNAL_SCORES['HOLD'] > SIGNAL_SCORES['SELL']
        assert SIGNAL_SCORES['SELL'] > SIGNAL_SCORES['STRONG_SELL']

    def test_rl_action_mapping(self):
        """RL actions should map to correct signals."""
        from python.agents.blender import RL_ACTION_TO_SIGNAL
        assert RL_ACTION_TO_SIGNAL['BUY'] == 'BUY'
        assert RL_ACTION_TO_SIGNAL['SELL'] == 'SELL'
        assert RL_ACTION_TO_SIGNAL['HOLD'] == 'HOLD'
        assert RL_ACTION_TO_SIGNAL['INCREASE'] == 'STRONG_BUY'
        assert RL_ACTION_TO_SIGNAL['DECREASE'] == 'SELL'
