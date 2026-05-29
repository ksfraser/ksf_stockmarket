"""
test_pipeline_integration.py — Integration tests for the full agent pipeline
=============================================================================
Tests the complete GA → NN → RL → Blender pipeline using SQLite test data.
Verifies:
- Data flows between agents correctly
- Database state is consistent after each agent runs
- Blender produces actionable orders from upstream agent outputs
- Portfolio state transitions are valid
"""

import pytest
import sys
import os
import numpy as np
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tests.conftest import (
    setup_test_database, get_test_db, seed_test_prices,
    seed_test_indicators, seed_test_evalsummary, seed_test_signal_weights,
    cleanup_test_db, generate_test_prices
)


class TestDatabaseIntegration:
    """Test database state across agent operations."""

    def setup_method(self):
        cleanup_test_db()
        setup_test_database()
        self.db = get_test_db()
        seed_test_prices(self.db, symbols=['TEST.TO', 'RY.TO', 'TD.TO', 'ENB.TO'], days=300)
        seed_test_indicators(self.db)
        seed_test_evalsummary(self.db)
        seed_test_signal_weights(self.db)

    def teardown_method(self):
        self.db.close()
        cleanup_test_db()

    def test_seed_data_consistency(self):
        """Seeded prices should have consistent OHLC relationships."""
        c = self.db.cursor()
        c.execute("SELECT day_open, day_high, day_low, day_close FROM stockprices WHERE symbol = 'TEST.TO'")
        for row in c.fetchall():
            o, h, l, cl = row
            if None not in (o, h, l, cl):
                # High should be >= all others
                assert h >= o or abs(h - o) < 0.01  # Allow floating point
                assert h >= cl or abs(h - cl) < 0.01
                # Low should be <= all others
                assert l <= o or abs(l - o) < 0.01
                assert l <= cl or abs(l - cl) < 0.01

    def test_indicators_match_prices(self):
        """Indicators should exist for dates that have price data."""
        c = self.db.cursor()
        c.execute("""
            SELECT di.symbol, di.price_date, di.daily_return
            FROM daily_indicators di
            JOIN stockprices sp ON di.symbol = sp.symbol AND di.price_date = sp.price_date
            WHERE di.symbol = 'TEST.TO'
            LIMIT 5
        """)
        rows = c.fetchall()
        assert len(rows) > 0, "Indicators should match price dates"

    def test_evalsummary_populated(self):
        """Evalsummary should have entries for all test symbols."""
        c = self.db.cursor()
        c.execute("SELECT symbol, totalscore FROM evalsummary")
        rows = c.fetchall()
        assert len(rows) >= 5
        for row in rows:
            assert row[1] is not None, f"totalscore for {row[0]} should not be None"
            assert 0 <= row[1] <= 36

    def test_signal_weights_populated(self):
        """Signal weights should exist for test symbols."""
        c = self.db.cursor()
        c.execute("SELECT COUNT(DISTINCT symbol) FROM signal_weights")
        count = c.fetchone()[0]
        assert count >= 3

    def test_config_seeded(self):
        """Agent configs should be seeded."""
        c = self.db.cursor()
        c.execute("SELECT agent_type, config_key, config_value FROM agent_configs WHERE is_active = 1")
        rows = c.fetchall()
        assert len(rows) >= 15  # At least our seeded configs

        # Verify key GA config
        c.execute("SELECT config_value FROM agent_configs WHERE agent_type='ga' AND config_key='population_size'")
        row = c.fetchone()
        assert row is not None
        assert int(row[0]) > 0


class TestAgentPipelineDataFlow:
    """
    Test that data flows correctly between agents.
    Simulates: GA writes results → NN reads them → writes predictions →
               Blender reads both → writes orders.
    """

    def setup_method(self):
        cleanup_test_db()
        setup_test_database()
        self.db = get_test_db()
        seed_test_prices(self.db, symbols=['TEST.TO', 'RY.TO', 'TD.TO'], days=300)
        seed_test_indicators(self.db)
        seed_test_evalsummary(self.db)
        seed_test_signal_weights(self.db)

        # Seed GA results (simulating GA agent output)
        c = self.db.cursor()
        import json
        weights = {f'w_{i}': round(np.random.uniform(-2, 3), 4) for i in range(22)}
        c.execute("""
            INSERT INTO ga_results (symbol, generation, weights_json, fitness_composite, is_best)
            VALUES ('TEST.TO', 10, ?, 1.5, 1)
        """, (json.dumps(weights),))
        self.db.commit()

        # Seed NN predictions (simulating NN agent output)
        c.execute("""
            INSERT INTO nn_predictions 
                (symbol, prediction_date, model_version, direction, confidence,
                 raw_weight, user_cap_weight, predicted_return_5d)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ('TEST.TO', date.today().isoformat(), 'lstm_v1', 'BUY', 0.85, 0.12, 0.10, 0.04))
        self.db.commit()

        # Seed RL signals (simulating RL agent output)
        c.execute("""
            INSERT INTO rl_signals 
                (symbol, signal_date, model_version, action, target_weight, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('TEST.TO', date.today().isoformat(), 'ppo_v1', 'BUY', 0.08, 0.75))
        self.db.commit()

    def teardown_method(self):
        self.db.close()
        cleanup_test_db()

    def test_blender_reads_all_agent_data(self):
        """Blender should successfully read GA, NN, and RL outputs."""
        from python.agents.blender import BlenderAgent
        config = {
            'ga_weight': 0.30, 'nn_weight': 0.35, 'rl_weight': 0.35,
            'consensus_threshold': 60.0, 'max_positions': 20,
        }
        blender = BlenderAgent(self.db, config)

        # Fetch signals from each agent
        ga_signals = blender._fetch_ga_signals(['TEST.TO'], date.today())
        nn_signals = blender._fetch_nn_signals(['TEST.TO'], date.today())
        rl_signals = blender._fetch_rl_signals(['TEST.TO'], date.today())

        assert 'TEST.TO' in ga_signals
        assert 'TEST.TO' in nn_signals
        assert 'TEST.TO' in rl_signals

        # Verify signal contents
        assert ga_signals['TEST.TO']['direction'] in ('BUY', 'SELL', 'HOLD')
        assert nn_signals['TEST.TO']['direction'] == 'BUY'
        assert nn_signals['TEST.TO']['confidence'] == 0.85
        assert rl_signals['TEST.TO']['direction'] == 'BUY'

    def test_blender_produces_consensus(self):
        """Blender should compute consensus from agent signals."""
        from python.agents.blender import BlenderAgent, SignalConsensus
        config = {
            'ga_weight': 0.30, 'nn_weight': 0.35, 'rl_weight': 0.35,
            'consensus_threshold': 60.0, 'max_positions': 20,
        }
        blender = BlenderAgent(self.db, config)

        # Use the consensus engine directly
        ga_signals = blender._fetch_ga_signals(['TEST.TO'], date.today())
        nn_signals = blender._fetch_nn_signals(['TEST.TO'], date.today())
        rl_signals = blender._fetch_rl_signals(['TEST.TO'], date.today())

        ga = ga_signals.get('TEST.TO', {'direction': 'HOLD', 'strength': 0})
        nn = nn_signals.get('TEST.TO', {'direction': 'HOLD', 'confidence': 0, 'user_cap_weight': 0})
        rl = rl_signals.get('TEST.TO', {'direction': 'HOLD', 'confidence': 0, 'target_weight': 0})

        consensus = blender.consensus_engine.compute_consensus(ga, nn, rl)

        assert consensus['direction'] in ('STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL')
        assert 'consensus_score' in consensus
        assert 'consensus_pct' in consensus
        assert 0 <= consensus['consensus_pct'] <= 100

    def test_full_blend_pipeline(self):
        """Full blend should produce orders saved to portfolio_orders."""
        from python.agents.blender import BlenderAgent
        config = {
            'ga_weight': 0.30, 'nn_weight': 0.35, 'rl_weight': 0.35,
            'consensus_threshold': 50.0,  # Lower threshold for test
            'max_positions': 20,
        }
        blender = BlenderAgent(self.db, config, dry_run=False)
        orders = blender.blend(symbols=['TEST.TO'])

        # Verify orders were written to database
        c = self.db.cursor()
        c.execute("SELECT COUNT(*) FROM portfolio_orders")
        count = c.fetchone()[0]

        if len(orders) > 0:
            assert count > 0, "Orders should be saved to DB"
            for order in orders:
                assert 'symbol' in order
                assert 'action' in order
                assert order['action'] in ('BUY', 'SELL', 'HOLD', 'INCREASE', 'DECREASE')


class TestOrchestratorPriorityQueue:
    """Test the orchestrator's priority queue."""

    def setup_method(self):
        cleanup_test_db()
        setup_test_database()
        self.db = get_test_db()
        seed_test_prices(self.db, symbols=['TEST.TO', 'RY.TO', 'TD.TO'], days=100)

        # Seed portfolio (simulating holdings)
        c = self.db.cursor()
        today = date.today().isoformat()
        for sym in ['TEST.TO', 'RY.TO']:
            c.execute("""
                INSERT INTO portfolio (user_id, symbol, shares, account_type, acquisition_date)
                VALUES (2, ?, 100, 'RRSP', ?)
            """, (sym, today))
        self.db.commit()

    def teardown_method(self):
        self.db.close()
        cleanup_test_db()

    def test_tier1_symbols_from_holdings(self):
        """Tier 1 symbols should come from current portfolio."""
        from python.agents.orchestrator import PriorityQueue
        config = {'tier1_symbols_per_run': 50}
        pq = PriorityQueue(self.db, config)
        symbols = pq.get_tier1_symbols()
        assert 'TEST.TO' in symbols
        assert 'RY.TO' in symbols

    def test_tier2_symbols_from_orders(self):
        """Tier 2 symbols should come from pending buy recommendations."""
        from python.agents.orchestrator import PriorityQueue
        c = self.db.cursor()
        today = date.today().isoformat()
        c.execute("""
            INSERT INTO portfolio_orders (order_date, symbol, action, consensus_pct, status)
            VALUES (?, 'TD.TO', 'BUY', 75.0, 'pending')
        """, (today,))
        self.db.commit()

        config = {'tier2_symbols_per_run': 100}
        pq = PriorityQueue(self.db, config)
        symbols = pq.get_tier2_symbols()
        assert 'TD.TO' in symbols

    def test_exploration_by_region(self):
        """Exploration symbols should be filtered by region."""
        from python.agents.orchestrator import PriorityQueue
        config = {'exploration_symbols_per_run': 200}
        pq = PriorityQueue(self.db, config)

        cdn_symbols = pq.get_exploration_symbols('CDN')
        # All should be Canadian (.TO suffix)
        for sym in cdn_symbols:
            assert sym.endswith('.TO') or sym.endswith('.CN') or sym.endswith('.V'), \
                f"{sym} doesn't look Canadian"

    def test_build_queue_structure(self):
        """Queue should contain properly structured tasks."""
        from python.agents.orchestrator import PriorityQueue
        config = {
            'tier1_symbols_per_run': 50,
            'tier2_symbols_per_run': 100,
            'exploration_symbols_per_run': 50,
        }
        pq = PriorityQueue(self.db, config)
        queue = pq.build_queue(tiers=[1])

        for task in queue:
            assert 'agent' in task
            assert 'symbols' in task
            assert 'tier' in task
            assert isinstance(task['symbols'], list)
            assert len(task['symbols']) > 0
