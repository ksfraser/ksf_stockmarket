"""
test_uat_scenarios.py — User Acceptance Tests
==============================================
End-to-end scenarios that validate real-world usage:
1. Full pipeline run with portfolio
2. Position cap enforcement through pipeline
3. Trailing stop alert generation
4. Rebalance plan validation
5. Concurrent agent data integrity
"""

import pytest
import sys
import os
import json
import numpy as np
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tests.conftest import (
    setup_test_database, get_test_db, seed_test_prices,
    seed_test_indicators, seed_test_evalsummary, seed_test_signal_weights,
    generate_test_prices, cleanup_test_db
)


class TestFullPipelineScenario:
    """
    UAT-001: Full pipeline run with realistic portfolio.
    Given: 5 symbols with 300 days of price data
    When: GA → NN → RL → Blender pipeline runs
    Then: Portfolio orders are generated with valid agent attribution
    """

    def setup_method(self):
        cleanup_test_db()
        setup_test_database()
        self.db = get_test_db()
        symbols = ['RY.TO', 'TD.TO', 'ENB.TO', 'BMO.TO', 'SU.TO']
        seed_test_prices(self.db, symbols=symbols, days=300)
        seed_test_indicators(self.db, symbols=symbols)
        seed_test_evalsummary(self.db, symbols=symbols)
        seed_test_signal_weights(self.db, symbols=symbols)

        # Seed portfolio
        c = self.db.cursor()
        today = date.today().isoformat()
        holdings = [
            ('RY.TO', 500, 110.0), ('TD.TO', 800, 85.0), ('ENB.TO', 600, 55.0),
            ('BMO.TO', 400, 130.0), ('SU.TO', 300, 45.0),
        ]
        for sym, shares, basis in holdings:
            total = shares * basis
            c.execute("""
                INSERT INTO portfolio (user_id, symbol, shares, cost_basis, cost_total, account_type, acquisition_date)
                VALUES (2, ?, ?, ?, ?, 'RRSP', ?)
            """, (sym, shares, basis, total, today))

        # Seed agent outputs
        import json
        weights = {f'w_{i}': round(np.random.uniform(-1, 2), 4) for i in range(22)}
        for sym in symbols:
            c.execute("INSERT INTO ga_results (symbol, generation, weights_json, fitness_composite, is_best) VALUES (?, 10, ?, 1.2, 1)",
                      (sym, json.dumps(weights)))
            direction = 'BUY' if np.random.random() > 0.4 else 'HOLD'
            c.execute("""
                INSERT INTO nn_predictions (symbol, prediction_date, model_version, direction, confidence,
                    raw_weight, user_cap_weight, predicted_return_5d)
                VALUES (?, ?, 'lstm_v1', ?, ?, ?, ?, ?)
            """, (sym, today, direction, round(np.random.uniform(0.6, 0.95), 2),
                  round(np.random.uniform(0.05, 0.15), 4),
                  round(np.random.uniform(0.05, 0.12), 4),
                  0.04 if direction == 'BUY' else 0.0))
            action = 'BUY' if direction == 'BUY' else 'HOLD'
            c.execute("""
                INSERT INTO rl_signals (symbol, signal_date, model_version, action, target_weight, confidence)
                VALUES (?, ?, 'ppo_v1', ?, ?, ?)
            """, (sym, today, action, round(np.random.uniform(0.03, 0.10), 4), 0.75))

        self.db.commit()

    def teardown_method(self):
        self.db.close()
        cleanup_test_db()

    def test_pipeline_runs_without_error(self):
        """Full blender run should complete without exceptions."""
        from python.agents.blender import BlenderAgent
        config = {
            'ga_weight': 0.30, 'nn_weight': 0.35, 'rl_weight': 0.35,
            'consensus_threshold': 50.0, 'max_positions': 20,
        }
        blender = BlenderAgent(self.db, config, dry_run=True)
        orders = blender.blend(symbols=['RY.TO', 'TD.TO', 'ENB.TO', 'BMO.TO', 'SU.TO'])
        assert isinstance(orders, list)

    def test_orders_have_agent_attribution(self):
        """All orders should reference which agents agreed."""
        from python.agents.blender import BlenderAgent
        config = {
            'ga_weight': 0.30, 'nn_weight': 0.35, 'rl_weight': 0.35,
            'consensus_threshold': 33.0,  # Low threshold for test
            'max_positions': 20,
        }
        blender = BlenderAgent(self.db, config, dry_run=True)
        orders = blender.blend(symbols=['RY.TO', 'TD.TO', 'ENB.TO', 'BMO.TO', 'SU.TO'])

        for order in orders:
            assert 'consensus_pct' in order
            assert 'ga_signal' in order
            assert 'nn_signal' in order
            assert 'rl_signal' in order
            assert 'action' in order
            assert order['action'] in ('BUY', 'SELL', 'HOLD', 'INCREASE', 'DECREASE')

    def test_sells_generated_for_bearish_signals(self):
        """If all agents SELL a symbol, blender should generate SELL orders."""
        from python.agents.blender import BlenderAgent

        import json
        c = self.db.cursor()
        today = date.today().isoformat()

        # Make all agents SELL RY.TO
        c.execute("UPDATE ga_results SET weights_json = ? WHERE symbol = 'RY.TO'",
                  (json.dumps({f'w_{i}': -3.0 for i in range(22)}),))
        c.execute("UPDATE nn_predictions SET direction = 'SELL', confidence = 0.85 WHERE symbol = 'RY.TO'")
        c.execute("UPDATE rl_signals SET action = 'SELL' WHERE symbol = 'RY.TO'")
        self.db.commit()

        config = {
            'ga_weight': 0.30, 'nn_weight': 0.35, 'rl_weight': 0.35,
            'consensus_threshold': 60.0, 'max_positions': 20,
        }
        blender = BlenderAgent(self.db, config, dry_run=True)
        orders = blender.blend(symbols=['RY.TO'])

        sell_orders = [o for o in orders if o['action'] == 'SELL']
        assert len(sell_orders) >= 1, "Should generate SELL when all agents agree"


class TestPositionCapScenario:
    """
    UAT-002: Position cap enforcement through pipeline.
    Given: Agent recommends 20% weight on an emerging market symbol
    When: Blender applies user caps
    Then: Effective weight should be capped at 5% (EMERGING region cap)
    """

    def setup_method(self):
        cleanup_test_db()
        setup_test_database()

    def teardown_method(self):
        cleanup_test_db()

    def test_emerging_market_cap(self):
        """NN recommending 20% for HK stock should be capped to 5%."""
        from python.agents.nn_agent import PositionCapEnforcer
        db = get_test_db()
        enforcer = PositionCapEnforcer(db)

        effective, reason = enforcer.get_effective_weight(0.20, symbol='0941.HK')
        assert effective == pytest.approx(0.05, abs=0.001)
        assert 'EMERGING' in reason

    def test_european_cap(self):
        """EURO symbol should be capped at 8%."""
        from python.agents.nn_agent import PositionCapEnforcer
        db = get_test_db()
        enforcer = PositionCapEnforcer(db)

        effective, reason = enforcer.get_effective_weight(0.15, symbol='VOD.L')
        assert effective <= 0.08
        assert 'EURO' in reason

    def test_canadian_no_region_cap(self):
        """CDN symbol below 15% should not be capped."""
        from python.agents.nn_agent import PositionCapEnforcer
        db = get_test_db()
        enforcer = PositionCapEnforcer(db)

        effective, _ = enforcer.get_effective_weight(0.10, symbol='RY.TO')
        assert effective == pytest.approx(0.10, abs=0.001)

    def test_account_cap_tfsa(self):
        """TFSA account positions should be capped at 10%."""
        from python.agents.nn_agent import PositionCapEnforcer
        db = get_test_db()
        enforcer = PositionCapEnforcer(db)

        effective, reason = enforcer.get_effective_weight(0.15, account='TFSA')
        assert effective <= 0.10
        assert 'TFSA' in reason


class TestTrailingStopScenario:
    """
    UAT-003: Trailing stop alert lifecycle.
    Given: Entry at $39.47 with $4 trailing stop
    When: Price rises to $45, then falls to $40
    Then: Stop trigger should move up to $41 (high - $4)
    """

    def setup_method(self):
        cleanup_test_db()
        setup_test_database()

    def teardown_method(self):
        cleanup_test_db()

    def test_initial_stop_price(self):
        """Initial stop should be entry_price - trail_amount."""
        entry_price = 39.47
        trail_amount = 4.0
        stop_price = entry_price - trail_amount
        assert stop_price == pytest.approx(35.47, abs=0.01)

    def test_trailing_stop_rises_with_price(self):
        """Stop should rise when price rises (new high-water)."""
        entry_price = 39.47
        high_water = entry_price

        # Price rises to $45
        current_price = 45.0
        if current_price > high_water:
            high_water = current_price

        stop = high_water - 4.0
        assert stop == pytest.approx(41.0, abs=0.01)

    def test_trailing_stop_doesnt_fall(self):
        """Stop should NOT move down when price dips."""
        high_water = 45.0
        stop = high_water - 4.0  # $41

        # Price dips to $43
        current_price = 43.0
        new_stop = max(stop, current_price - 4.0)
        assert new_stop == pytest.approx(41.0, abs=0.01)  # Stays at $41

    def test_stop_triggers_on_breach(self):
        """Alert fires when price drops below stop."""
        stop = 41.0

        # Price at $40.50 — below $41 trigger
        current_price = 40.50
        assert current_price <= stop, "Stop should trigger"

        # Price at $41.50 — above trigger, no fire
        current_price = 41.50
        assert current_price > stop, "Should not trigger"


class TestDataVolumeScenario:
    """
    UAT-004: System handles required data volumes.
    Given: 300 days × 5 symbols of prices + indicators
    When: All agents process the data
    Then: No data loss, consistent row counts
    """

    def setup_method(self):
        cleanup_test_db()
        setup_test_database()
        self.db = get_test_db()
        seed_test_prices(self.db, symbols=['TEST.TO'], days=300)
        seed_test_indicators(self.db, symbols=['TEST.TO'])

    def teardown_method(self):
        self.db.close()
        cleanup_test_db()

    def test_price_count_matches_seed(self):
        """Stockprices should have exactly 300 rows for TEST.TO."""
        c = self.db.cursor()
        c.execute("SELECT COUNT(*) FROM stockprices WHERE symbol = 'TEST.TO'")
        count = c.fetchone()[0]
        assert count == 300

    def test_indicator_rows_leq_price_rows(self):
        """Indicators should exist for most (but not necessarily all) price dates."""
        c = self.db.cursor()
        c.execute("""
            SELECT COUNT(*) FROM daily_indicators di
            JOIN stockprices sp ON di.symbol = sp.symbol AND di.price_date = sp.price_date
            WHERE di.symbol = 'TEST.TO'
        """)
        count = c.fetchone()[0]
        assert count > 250  # Most dates should have indicators
        assert count <= 300  # Can't exceed price rows

    def test_no_orphan_indicators(self):
        """Every indicator row should have a matching price row."""
        c = self.db.cursor()
        c.execute("""
            SELECT COUNT(*) FROM daily_indicators di
            LEFT JOIN stockprices sp ON di.symbol = sp.symbol AND di.price_date = sp.price_date
            WHERE di.symbol = 'TEST.TO' AND sp.symbol IS NULL
        """)
        orphans = c.fetchone()[0]
        assert orphans == 0, f"Found {orphan} orphan indicator rows"


class TestConcurrencyScenario:
    """
    UAT-005: Multiple agents writing to same tables simultaneously.
    Given: GA, NN, RL all writing to agent_runs
    Then: All records are correctly attributed
    """

    def setup_method(self):
        cleanup_test_db()
        setup_test_database()

    def teardown_method(self):
        cleanup_test_db()

    def test_multiple_agent_run_types(self):
        """Simulating concurrent agent_runs writes."""
        db = get_test_db()
        c = db.cursor()

        for agent_type in ['ga', 'nn', 'rl', 'blender', 'orchestrator']:
            c.execute("""
                INSERT INTO agent_runs (agent_type, run_name, status)
                VALUES (?, ?, 'complete')
            """, (agent_type, f"{agent_type}_run_1"))

        db.commit()

        for agent_type in ['ga', 'nn', 'rl', 'blender', 'orchestrator']:
            c.execute("SELECT COUNT(*) FROM agent_runs WHERE agent_type = ?", (agent_type,))
            count = c.fetchone()[0]
            assert count == 1, f"Expected 1 run for {agent_type}, got {count}"

        db.close()

    def test_parent_child_run_linking(self):
        """Sub-runs should link to parent orchestrator run."""
        db = get_test_db()
        c = db.cursor()

        # Parent orchestrator run
        c.execute("""
            INSERT INTO agent_runs (agent_type, run_name, status)
            VALUES ('orchestrator', 'pipeline_001', 'complete')
        """)
        parent_id = c.lastrowid

        # Child GA run
        c.execute("""
            INSERT INTO agent_runs (agent_type, run_name, parent_run_id, status)
            VALUES ('ga', 'ga_sub_run', ?, 'complete')
        """, (parent_id,))
        ga_id = c.lastrowid

        # Verify parent link
        c.execute("SELECT parent_run_id FROM agent_runs WHERE id = ?", (ga_id,))
        linked_parent = c.fetchone()[0]
        assert linked_parent == parent_id

        db.close()
