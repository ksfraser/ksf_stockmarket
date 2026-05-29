"""
test_nn_agent.py — Unit tests for NN Agent
===========================================
Tests:
- Position cap enforcement
- Feature engineering
- Model architecture (forward pass)
- Direction/confidence/weight head outputs
"""

import pytest
import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Lazy imports for ML libraries
torch = None
try:
    import torch
except ImportError:
    pass

from tests.conftest import setup_test_database, get_test_db, seed_test_prices, cleanup_test_db


class TestPositionCaps:
    """Test user position sizing cap enforcement."""

    def setup_method(self):
        setup_test_database()
        db = get_test_db()
        # Seed a specific symbol cap
        c = db.cursor()
        c.execute("INSERT OR IGNORE INTO user_position_caps (cap_type, cap_target, max_position_pct) VALUES ('symbol', 'AAPL', 0.05)")
        db.commit()
        db.close()

    def test_global_default_cap(self):
        """Agent recommending above default cap should be reduced."""
        from python.agents.nn_agent import PositionCapEnforcer
        db = get_test_db()
        enforcer = PositionCapEnforcer(db)
        # 15% is above global default (10%) but below RRSP account cap test would
        # need a different account type. Test with no account specified.
        effective, reason = enforcer.get_effective_weight(0.15, account='CASH')
        assert effective <= 0.10  # Global default cap
        assert 'global' in reason

    def test_symbol_specific_cap(self):
        """Symbol-specific cap should override global."""
        from python.agents.nn_agent import PositionCapEnforcer
        db = get_test_db()
        enforcer = PositionCapEnforcer(db)
        effective, reason = enforcer.get_effective_weight(0.15, symbol='AAPL')
        assert effective <= 0.05  # AAPL-specific cap
        assert 'AAPL' in reason

    def test_region_cap_emerging(self):
        """Emerging market symbols should get lower cap."""
        from python.agents.nn_agent import PositionCapEnforcer
        db = get_test_db()
        enforcer = PositionCapEnforcer(db)
        effective, reason = enforcer.get_effective_weight(0.15, symbol='0941.HK')
        assert effective <= 0.05  # Emerging markets cap
        assert 'EMERGING' in reason

    def test_region_cap_cdn(self):
        """Canadian symbols should get CDN region cap."""
        from python.agents.nn_agent import PositionCapEnforcer
        db = get_test_db()
        enforcer = PositionCapEnforcer(db)
        effective, reason = enforcer.get_effective_weight(0.20, symbol='RY.TO')
        assert effective <= 0.15  # CDN region cap

    def test_below_cap_unchanged(self):
        """Agent recommendation below cap should pass through unchanged."""
        from python.agents.nn_agent import PositionCapEnforcer
        db = get_test_db()
        enforcer = PositionCapEnforcer(db)
        effective, reason = enforcer.get_effective_weight(0.03)
        assert effective == pytest.approx(0.03, abs=0.001)

    def test_clamp_minimum(self):
        """Weight should never go below min_recommended_weight."""
        from python.agents.nn_agent import PositionCapEnforcer, DEFAULT_CONFIG
        db = get_test_db()
        enforcer = PositionCapEnforcer(db)
        effective, _ = enforcer.get_effective_weight(0.0)
        assert effective >= DEFAULT_CONFIG['min_recommended_weight']


class TestFeatureEngineering:
    """Test the feature extraction pipeline."""

    def setup_method(self):
        setup_test_database()
        db = get_test_db()
        seed_test_prices(db, days=300)
        db.close()

    def test_normalize_features_no_nan(self):
        """Normalized features should not contain NaN or Inf."""
        from python.agents.nn_agent import _normalize_features, NUM_FEATURES
        features = [0.0] * NUM_FEATURES
        normalized = _normalize_features(features)
        assert len(normalized) == NUM_FEATURES
        for v in normalized:
            assert not np.isnan(v), f"NaN in feature"
            assert not np.isinf(v), f"Inf in feature"

    def test_price_data_fetch(self):
        """fetch_price_data should return correct columns."""
        from python.db_connector import fetch_price_data
        db = get_test_db()
        df = fetch_price_data(db, 'TEST.TO', lookback=100)
        assert df is not None
        assert len(df) > 0
        for col in ['day_open', 'day_high', 'day_low', 'day_close', 'volume']:
            assert col in df.columns
        db.close()


@pytest.mark.skipif(torch is None, reason="PyTorch not installed")
class TestLSTMModel:
    """Test the LSTM model architecture."""

    def test_model_creation(self):
        """Model should instantiate with default config."""
        from python.agents.nn_agent import LSTMDirectionModel, DEFAULT_CONFIG
        config = {**DEFAULT_CONFIG, 'hidden_size': 32, 'num_layers': 1}
        model = LSTMDirectionModel(config)
        assert model is not None

    def test_forward_pass(self):
        """Forward pass should produce correct output shapes."""
        from python.agents.nn_agent import LSTMDirectionModel, DEFAULT_CONFIG, NUM_FEATURES
        config = {**DEFAULT_CONFIG, 'hidden_size': 32, 'num_layers': 1}
        model = LSTMDirectionModel(config)

        batch_size = 8
        seq_len = config['sequence_length']
        x = torch.randn(batch_size, seq_len, NUM_FEATURES)

        direction_logits, confidence, raw_weight = model(x)

        assert direction_logits.shape == (batch_size, 5)  # 5 classes
        assert confidence.shape == (batch_size,)
        assert raw_weight.shape == (batch_size,)
        assert (confidence >= 0).all() and (confidence <= 1).all()  # Sigmoid
        assert (raw_weight >= 0).all() and (raw_weight <= 1).all()  # Sigmoid

    def test_direction_classes(self):
        """Direction output should be 5 classes."""
        from python.agents.nn_agent import DIRECTION_CLASSES
        assert len(DIRECTION_CLASSES) == 5
        assert DIRECTION_CLASSES == ['STRONG_SELL', 'SELL', 'HOLD', 'BUY', 'STRONG_BUY']

    def test_model_save_load(self):
        """Model should save and load correctly."""
        from python.agents.nn_agent import LSTMDirectionModel, DEFAULT_CONFIG
        import tempfile
        config = {**DEFAULT_CONFIG, 'hidden_size': 16, 'num_layers': 1}
        model = LSTMDirectionModel(config)

        with tempfile.NamedTemporaryFile(suffix='.pt', delete=False) as f:
            path = f.name

        try:
            torch.save({'model_state': model.state_dict(), 'config': config}, path)
            checkpoint = torch.load(path, map_location='cpu')
            model2 = LSTMDirectionModel(config)
            model2.load_state_dict(checkpoint['model_state'])
            assert True  # Load succeeded
        finally:
            os.unlink(path)


class TestNNConfig:
    """Test NN agent configuration."""

    def test_default_config(self):
        """Default config should have all required keys."""
        from python.agents.nn_agent import DEFAULT_CONFIG
        required = ['sequence_length', 'hidden_size', 'num_layers', 'dropout',
                     'learning_rate', 'batch_size', 'epochs',
                     'early_stopping_patience', 'train_split',
                     'confidence_threshold']
        for key in required:
            assert key in DEFAULT_CONFIG

    def test_config_constraints(self):
        """Config values should be reasonable."""
        from python.agents.nn_agent import DEFAULT_CONFIG
        assert DEFAULT_CONFIG['sequence_length'] >= 20
        assert DEFAULT_CONFIG['hidden_size'] >= 16
        assert 0 < DEFAULT_CONFIG['dropout'] < 1
        assert DEFAULT_CONFIG['learning_rate'] < 0.01
        assert 0 < DEFAULT_CONFIG['confidence_threshold'] <= 1
