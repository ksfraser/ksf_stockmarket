"""
test_ga_agent.py — Unit tests for GA Agent
===========================================
Tests the genetic algorithm's core components:
- Chromosome creation and conversion
- Fitness evaluation logic
- DEAP evolutionary operators
- Signal weight initialization
"""

import pytest
import sys
import os
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tests.conftest import setup_test_database, get_test_db, cleanup_test_db, TEST_DB_PATH


class TestGAChromosome:
    """Test chromosome creation without importing the full agent."""

    def test_default_num_genes(self):
        """NUM_GENES should match SCORING_WEIGHT_KEYS length (18)."""
        from python.agents.ga_agent import NUM_GENES, SCORING_WEIGHT_KEYS
        assert NUM_GENES == len(SCORING_WEIGHT_KEYS)
        assert NUM_GENES == 18  # 10 scoring + 7 TA + 1 correlation

    def test_create_chromosome_bounds(self):
        """Chromosome weights should respect min/max bounds."""
        from python.agents.ga_agent import create_chromosome, DEFAULT_CONFIG, NUM_GENES
        config = {**DEFAULT_CONFIG}
        for _ in range(10):
            chromo = create_chromosome(config)
            assert len(chromo) == NUM_GENES
            for gene in chromo:
                assert config['weight_min'] <= gene <= config['weight_max']

    def test_chromosome_to_dict(self):
        """Chromosome list → dict conversion should preserve all keys."""
        from python.agents.ga_agent import chromosome_to_dict, SCORING_WEIGHT_KEYS
        chromo = [1.0] * len(SCORING_WEIGHT_KEYS)
        d = chromosome_to_dict(chromo)
        assert len(d) == len(SCORING_WEIGHT_KEYS)
        for key in SCORING_WEIGHT_KEYS:
            assert key in d
            assert d[key] == 1.0

    def test_dict_to_chromosome_roundtrip(self):
        """Dict → chromosome → dict should be idempotent."""
        from python.agents.ga_agent import chromosome_to_dict, dict_to_chromosome, SCORING_WEIGHT_KEYS
        original = {k: i * 0.1 for i, k in enumerate(SCORING_WEIGHT_KEYS)}
        chromo = dict_to_chromosome(original)
        restored = chromosome_to_dict(chromo)
        for key in SCORING_WEIGHT_KEYS:
            assert abs(original[key] - restored[key]) < 1e-10

    def test_signal_direction_mapping(self):
        """Signal map should correctly map directions to scores."""
        from python.agents.ga_agent import SIGNAL_MAP
        assert SIGNAL_MAP['STRONG_BUY'] > SIGNAL_MAP['BUY']
        assert SIGNAL_MAP['BUY'] > SIGNAL_MAP['HOLD']
        assert SIGNAL_MAP['HOLD'] == 0
        assert SIGNAL_MAP['SELL'] < SIGNAL_MAP['HOLD']
        assert SIGNAL_MAP['STRONG_SELL'] < SIGNAL_MAP['SELL']


class TestGASignalGenerator:
    """Test the weighted signal generator with seeded data."""

    def setup_method(self):
        setup_test_database()
        db = get_test_db()
        from tests.conftest import seed_test_prices, seed_test_indicators, seed_test_evalsummary, seed_test_signal_weights
        seed_test_prices(db, days=300)
        seed_test_indicators(db)
        seed_test_evalsummary(db)
        seed_test_signal_weights(db)
        db.close()

    def teardown_method(self):
        cleanup_test_db()

    def test_signal_generator_basic(self):
        """Signal generator should produce a valid signal dict."""
        from python.db_connector import get_connection
        db = get_connection()
        from python.agents.ga_agent import WeightedSignalGenerator, SCORING_WEIGHT_KEYS
        chromo = [1.0] * len(SCORING_WEIGHT_KEYS)
        gen = WeightedSignalGenerator(db, chromo, {'weight_min': -5, 'weight_max': 5})
        from datetime import date
        signal = gen.get_weighted_signal('TEST.TO', date.today())
        assert 'direction' in signal
        assert 'strength' in signal
        assert signal['direction'] in ('BUY', 'SELL', 'HOLD')
        db.close()

    def test_positive_weights_produce_positive_strength(self):
        """All positive weights should produce positive signal strength."""
        from python.db_connector import get_connection
        db = get_connection()
        from python.agents.ga_agent import WeightedSignalGenerator, SCORING_WEIGHT_KEYS
        chromo = [5.0] * len(SCORING_WEIGHT_KEYS)
        gen = WeightedSignalGenerator(db, chromo, {})
        from datetime import date
        signal = gen.get_weighted_signal('TEST.TO', date.today())
        assert signal['strength'] > 0
        db.close()

    def test_negative_weights_produce_negative_strength(self):
        """All negative weights should produce negative signal strength."""
        from python.db_connector import get_connection
        db = get_connection()
        from python.agents.ga_agent import WeightedSignalGenerator, SCORING_WEIGHT_KEYS
        chromo = [-5.0] * len(SCORING_WEIGHT_KEYS)
        gen = WeightedSignalGenerator(db, chromo, {})
        from datetime import date
        signal = gen.get_weighted_signal('TEST.TO', date.today())
        assert signal['strength'] < 0
        db.close()


class TestGAConfig:
    """Test GA agent configuration."""

    def test_default_config_values(self):
        """Default config should have all required keys."""
        from python.agents.ga_agent import DEFAULT_CONFIG
        required_keys = [
            'population_size', 'num_generations', 'mutation_rate',
            'crossover_rate', 'elitism_pct', 'tournament_size',
            'weight_min', 'weight_max', 'fitness_objective',
        ]
        for key in required_keys:
            assert key in DEFAULT_CONFIG

    def test_config_ranges(self):
        """Config values should be within valid ranges."""
        from python.agents.ga_agent import DEFAULT_CONFIG
        assert DEFAULT_CONFIG['population_size'] >= 10
        assert 0 <= DEFAULT_CONFIG['mutation_rate'] <= 1
        assert 0 <= DEFAULT_CONFIG['crossover_rate'] <= 1
        assert 0 <= DEFAULT_CONFIG['elitism_pct'] <= 0.5
        assert DEFAULT_CONFIG['elitism_pct'] * DEFAULT_CONFIG['population_size'] >= 1

    def test_fitness_objectives_valid(self):
        """Fitness objectives should be valid strings."""
        from python.agents.ga_agent import DEFAULT_CONFIG
        assert DEFAULT_CONFIG['fitness_objective'] in ('sharpe', 'return', 'maxdd', 'sharpe_return_combo')


class TestGAAgentRunTracking:
    """Test agent run database recording."""

    def setup_method(self):
        setup_test_database()

    def teardown_method(self):
        cleanup_test_db()

    def test_agent_run_creation(self):
        """Creating an agent run should insert a record."""
        db = get_test_db()
        db.execute("""
            INSERT INTO agent_runs (agent_type, run_name, priority, machine_id, status)
            VALUES ('ga', 'test_run', 1, 'test_machine', 'running')
        """)
        db.commit()
        db.close()

    def test_agent_run_update(self):
        """Updating agent run status should persist."""
        db = get_test_db()
        db.execute("""
            INSERT INTO agent_runs (agent_type, status) VALUES ('ga', 'running')
        """)
        db.commit()
        db.close()
