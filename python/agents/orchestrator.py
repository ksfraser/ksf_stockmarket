#!/usr/bin/env python3
"""
orchestrator.py — Multi-Agent Pipeline Orchestrator
=====================================================
Manages the full agent pipeline: priority queue, worker assignment,
and cron scheduling. Reads from agent_configs for tunable parameters.

Pipeline (in order):
  1. GA Agent     — Evolve signal weights (nightly, all symbols)
  2. NN Agent     — LSTM predictions (nightly, after GA)
  3. RL Agent     — PPO policy learning (weekly)
  4. Blender      — Consensus + rebalance plan (pre-market daily)

Priority tiers:
  Tier 1 (P1): Holdings — what you currently own
  Tier 2 (P2): Active BUY recommendations
  Tier 3a (P3): CDN exploration
  Tier 3b (P3): US exploration
  Tier 3c (P3): European exploration
  Tier 3d (P3): Emerging markets
  Tier 4 (P4): Full universe scan (monthly)

Usage:
  python3 orchestrator.py                         # Run full pipeline (respects tiers)
  python3 orchestrator.py --tier 1               # Run tier 1 only (holdings)
  python3 orchestrator.py --agent ga             # Run single agent
  python3 orchestrator.py --agent blender        # Run blender only
  python3 orchestrator.py --list                 # Show queue status
  python3 orchestrator.py --dry-run              # Don't execute agents
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from python.db_connector import get_connection, get_active_symbols

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ===========================================================================
# CONFIGURATION
# ===========================================================================

DEFAULT_CONFIG = {
    'tier1_symbols_per_run': 50,
    'tier2_symbols_per_run': 100,
    'exploration_symbols_per_run': 200,
    'run_timeout_sec': 3600,
    'retry_count': 3,
    'parallel_workers': 4,
    'workdir': '/home/ksf_stockmarket/ksf_stockmarket',
}

# Agent execution order and their Python scripts
AGENT_PIPELINE = [
    {'name': 'ga',     'script': 'python/agents/ga_agent.py',     'tier': 1, 'schedule': 'nightly'},
    {'name': 'nn',     'script': 'python/agents/nn_agent.py',     'tier': 1, 'schedule': 'nightly'},
    {'name': 'rl',     'script': 'python/agents/rl_agent.py',     'tier': 2, 'schedule': 'weekly'},
    {'name': 'blender','script': 'python/agents/blender.py',      'tier': 1, 'schedule': 'daily'},
]

# Region suffixes for tier 3 exploration
REGION_SUFFIXES = {
    'CDN':     ['.TO', '.CN', '.V'],
    'USA':     [],  # US tickers often have no suffix
    'EURO':    ['.L', '.PA', '.DE', '.AS', '.MI', '.BR', '.SW', '.VI', '.OL'],
    'EMERGING':['.SI', '.HK', '.T', '.BO', '.NS', '.SS', '.SA', '.MX', '.JO'],
}


# ===========================================================================
# PRIORITY QUEUE
# ===========================================================================

class PriorityQueue:
    """
    Manages work assignment across tiers.
    Higher priority (lower number) = processed first.
    """

    def __init__(self, conn, config: dict):
        self.conn = conn
        self.config = config

    def get_tier1_symbols(self) -> List[str]:
        """Tier 1: Current holdings — highest priority."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT symbol FROM portfolio
            WHERE is_active = 1 AND shares > 0
            ORDER BY symbol
            LIMIT %s
        """, (self.config['tier1_symbols_per_run'],))
        symbols = [row[0] for row in cursor.fetchall()]
        cursor.close()
        logger.info(f"  Tier 1 (holdings): {len(symbols)} symbols")
        return symbols

    def get_tier2_symbols(self) -> List[str]:
        """Tier 2: Active BUY recommendations — from recent blender orders."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT symbol FROM portfolio_orders
            WHERE status IN ('pending', 'approved')
              AND action IN ('BUY', 'INCREASE')
              AND order_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            ORDER BY consensus_pct DESC
            LIMIT %s
        """, (self.config['tier2_symbols_per_run'],))
        symbols = [row[0] for row in cursor.fetchall()]
        cursor.close()
        logger.info(f"  Tier 2 (buy recs): {len(symbols)} symbols")
        return symbols

    def get_exploration_symbols(self, region: str = None) -> List[str]:
        """Tier 3: Exploration symbols by region."""
        limit = self.config['exploration_symbols_per_run']

        if region and region in REGION_SUFFIXES:
            suffixes = REGION_SUFFIXES[region]
            # Use LIKE for each suffix
            conditions = ' OR '.join(['symbol LIKE %s' for _ in suffixes])
            params = [f'%{s}' for s in suffixes]
            query = f"""
                SELECT DISTINCT symbol FROM stockprices
                WHERE {conditions}
                  AND price_date >= DATE_SUB(CURDATE(), INTERVAL 5 DAY)
                ORDER BY symbol
                LIMIT %s
            """
            params.append(limit)
        else:
            query = """
                SELECT DISTINCT symbol FROM stockprices
                WHERE price_date >= DATE_SUB(CURDATE(), INTERVAL 5 DAY)
                ORDER BY symbol
                LIMIT %s
            """
            params = [limit]

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        symbols = [row[0] for row in cursor.fetchall()]
        cursor.close()
        logger.info(f"  Tier 3 ({region or 'global'}): {len(symbols)} symbols")
        return symbols

    def get_all_symbols(self) -> List[str]:
        """Get all symbols for full universe scan."""
        return get_active_symbols(self.conn)

    def build_queue(self, tiers: List[int] = None,
                     regions: List[str] = None) -> List[Dict[str, Any]]:
        """
        Build the full processing queue.
        Returns list of {agent, symbols, tier, priority} dicts.
        """
        tiers = tiers or [1, 2, 3]
        regions = regions or ['CDN', 'USA', 'EURO', 'EMERGING']

        queue = []
        all_symbols = set()

        for agent in AGENT_PIPELINE:
            agent_name = agent['name']

            if 1 in tiers:
                # Tier 1: holdings
                symbols = self.get_tier1_symbols()
                new_symbols = [s for s in symbols if s not in all_symbols]
                if new_symbols:
                    queue.append({
                        'agent': agent_name,
                        'symbols': new_symbols,
                        'tier': 1,
                        'priority': 1,
                    })
                all_symbols.update(new_symbols)

            if 2 in tiers and agent_name in ('ga', 'nn'):
                # Tier 2: buy recs
                symbols = self.get_tier2_symbols()
                new_symbols = [s for s in symbols if s not in all_symbols]
                if new_symbols:
                    queue.append({
                        'agent': agent_name,
                        'symbols': new_symbols,
                        'tier': 2,
                        'priority': 2,
                    })
                all_symbols.update(new_symbols)

            if 3 in tiers and agent_name in ('ga', 'nn'):
                # Tier 3: exploration by region
                for region in regions:
                    symbols = self.get_exploration_symbols(region)
                    new_symbols = [s for s in symbols if s not in all_symbols]
                    if new_symbols:
                        queue.append({
                            'agent': agent_name,
                            'symbols': new_symbols,
                            'tier': 3,
                            'priority': 3,
                            'region': region,
                        })
                    all_symbols.update(new_symbols)

        # Blender always runs last with all accumulated symbols
        if all_symbols:
            queue.append({
                'agent': 'blender',
                'symbols': list(all_symbols),
                'tier': 1,
                'priority': 5,
            })

        logger.info(f"Queue: {len({q['agent'] for q in queue})} agents, "
                     f"{len(all_symbols)} unique symbols")
        return queue


# ===========================================================================
# AGENT RUNNER
# ===========================================================================

class AgentRunner:
    """Runs individual agent scripts and tracks results."""

    def __init__(self, workdir: str, timeout: int = 3600, dry_run: bool = False):
        self.workdir = workdir
        self.timeout = timeout
        self.dry_run = dry_run

    def run(self, agent_name: str, symbols: List[str],
            extra_args: dict = None) -> dict:
        """Run an agent script. Returns result dict."""
        script = None
        for a in AGENT_PIPELINE:
            if a['name'] == agent_name:
                script = a['script']
                break

        if not script:
            raise ValueError(f"Unknown agent: {agent_name}")

        symbols_str = ','.join(symbols)
        script_path = os.path.join(self.workdir, script)

        cmd = ['python3', script_path, '--symbols', symbols_str]

        if extra_args:
            for k, v in extra_args.items():
                cmd.extend([f'--{k}', str(v)])

        logger.info(f"  Running: {agent_name} ({len(symbols)} symbols)")
        logger.info(f"    Command: {' '.join(cmd[:5])}... [+{len(cmd)-5} args]")

        if self.dry_run:
            logger.info(f"    DRY RUN — skipping execution")
            return {'status': 'dry_run', 'agent': agent_name, 'symbols': len(symbols)}

        start = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=self.workdir,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            elapsed = time.time() - start

            if result.returncode == 0:
                # Try to parse JSON output
                output = result.stdout.strip()
                parsed = None
                for line in reversed(output.split('\n')):
                    line = line.strip()
                    if line.startswith('{'):
                        try:
                            parsed = json.loads(line)
                        except json.JSONDecodeError:
                            pass
                        break

                logger.info(f"    ✅ {agent_name} complete ({elapsed:.0f}s)")
                return {
                    'status': 'success',
                    'agent': agent_name,
                    'symbols': len(symbols),
                    'elapsed': elapsed,
                    'result': parsed,
                }
            else:
                logger.error(f"    ❌ {agent_name} failed (exit {result.returncode})")
                logger.error(f"    stderr: {result.stderr[:500]}")
                return {
                    'status': 'failed',
                    'agent': agent_name,
                    'symbols': len(symbols),
                    'elapsed': elapsed,
                    'error': result.stderr[:200],
                }
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start
            logger.error(f"    ⏰ {agent_name} timed out after {elapsed:.0f}s")
            return {
                'status': 'timeout',
                'agent': agent_name,
                'symbols': len(symbols),
                'elapsed': elapsed,
            }
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"    💥 {agent_name} error: {e}")
            return {
                'status': 'error',
                'agent': agent_name,
                'symbols': len(symbols),
                'elapsed': elapsed,
                'error': str(e),
            }


# ===========================================================================
# ORCHESTRATOR — Main class
# ===========================================================================

class Orchestrator:
    """
    Main pipeline orchestrator. Manages priority queue and agent execution.
    """

    def __init__(self, conn, config: dict, dry_run: bool = False):
        self.conn = conn
        self.config = {**DEFAULT_CONFIG, **config}
        self.runner = AgentRunner(
            workdir=self.config['workdir'],
            timeout=self.config['run_timeout_sec'],
            dry_run=dry_run,
        )
        self.queue_manager = PriorityQueue(conn, self.config)
        self.run_id = None
        self.results = []

    def _create_run(self) -> int:
        """Create agent_runs entry for this orchestrator run."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO agent_runs
                (agent_type, run_name, priority, machine_id, status,
                 symbol_target, started_at)
            VALUES ('orchestrator', %s, 1, %s, 'running', NULL, NOW())
        """, (
            f"PIPELINE_{date.today().isoformat()}",
            os.uname().nodename,
        ))
        self.conn.commit()
        run_id = cursor.lastrowid
        cursor.close()
        return run_id

    def run_pipeline(self, tiers: List[int] = None,
                     regions: List[str] = None,
                     agents: List[str] = None) -> List[dict]:
        """
        Run the full agent pipeline.
        
        Args:
            tiers: Which priority tiers to process [1, 2, 3]
            regions: Which regions for tier 3 ['CDN', 'USA', 'EURO', 'EMERGING']
            agents: Which agents to run ['ga', 'nn', 'rl', 'blender']
        """
        self.run_id = self._create_run()
        start_time = time.time()

        logger.info(f"{'='*60}")
        logger.info(f"ORCHESTRATOR PIPELINE — Run #{self.run_id}")
        logger.info(f"{'='*60}")

        # Build queue
        queue = self.queue_manager.build_queue(tiers=tiers, regions=regions)

        # Filter by requested agents
        if agents:
            queue = [q for q in queue if q['agent'] in agents]

        if not queue:
            logger.info("No work in queue.")
            return []

        total_symbols = sum(len(q['symbols']) for q in queue)
        logger.info(f"Pipeline: {len(queue)} agent tasks, {total_symbols} total symbols")

        # Execute pipeline (sequential — each agent depends on previous)
        all_results = []
        for task in queue:
            agent_name = task['agent']
            symbols = task['symbols']
            tier = task['tier']

            logger.info(f"\n--- Tier {tier}: {agent_name.upper()} "
                        f"({len(symbols)} symbols) ---")

            extra_args = {}
            if agent_name == 'nn':
                extra_args['epochs'] = 50  # Shorter epochs for nightly runs
            elif agent_name == 'ga':
                extra_args['generations'] = 30  # Fewer generations for speed
            elif agent_name == 'blender':
                extra_args['dry_run'] = 'false'

            result = self.runner.run(agent_name, symbols, extra_args)
            result['tier'] = tier
            result['region'] = task.get('region')
            all_results.append(result)

            # Update agent_runs with parent link
            self._link_sub_run(result)

        elapsed = time.time() - start_time
        successes = sum(1 for r in all_results if r['status'] == 'success')
        failures = sum(1 for r in all_results if r['status'] != 'success')

        logger.info(f"\n{'='*60}")
        logger.info(f"PIPELINE COMPLETE — {successes}/{len(all_results)} agents succeeded")
        logger.info(f"   Elapsed: {elapsed:.0f}s")
        if failures:
            logger.warning(f"   Failures: {failures}")
        logger.info(f"{'='*60}")

        # Update orchestrator run
        self._update_run('complete' if failures == 0 else 'complete', all_results)

        return all_results

    def _link_sub_run(self, result: dict):
        """Link sub-agent runs to this orchestrator parent run."""
        # sub-agents create their own agent_runs entries
        # We'd need to update them with parent_run_id — but they don't know it
        # For now, we just log the relationship
        if result.get('result', {}).get('run_id'):
            pass  # TODO: update parent_run_id on sub-agent runs

    def _update_run(self, status: str, results: List[dict]):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE agent_runs
            SET status = %s,
                completed_at = NOW(),
                duration_sec = TIMESTAMPDIFF(SECOND, started_at, NOW()),
                result_json = %s
            WHERE id = %s
        """, (
            status,
            json.dumps({
                'agent_results': {r['agent']: r['status'] for r in results},
                'total_agents': len(results),
                'total_symbols': sum(r.get('symbols', 0) for r in results),
            }),
            self.run_id,
        ))
        self.conn.commit()
        cursor.close()

    def print_status(self, results: List[dict]):
        """Print a summary table of all agent results."""
        print(f"\n{'='*70}")
        print(f"PIPELINE STATUS — {date.today()}")
        print(f"{'='*70}")
        print(f"  {'Agent':12s} {'Tier':5s} {'Status':12s} {'Symbols':>8s} {'Time':>8s}")
        print(f"  {'─'*12} {'─'*5} {'─'*12} {'─'*8} {'─'*8}")
        for r in results:
            status_icon = '✅' if r['status'] == 'success' else '❌' if r['status'] == 'failed' else '⏭️'
            region = f" ({r.get('region', '')})" if r.get('region') else ""
            print(f"  {r['agent']+region:12s} {r.get('tier', '-'):>5} "
                  f"{status_icon} {r['status']:12s} {r.get('symbols', 0):>8,d} "
                  f"{r.get('elapsed', 0):>7.0f}s")
        print(f"{'='*70}")


# ===========================================================================
# CRON SCHEDULER SETUP
# ===========================================================================

def setup_cron_jobs(config: dict):
    """
    Set up cron jobs for the new agent pipeline.
    Returns list of cron job configurations.
    """
    jobs = [
        {
            'name': 'GA Agent — Weight Optimization (Nightly)',
            'schedule': '0 22 * * 1-5',  # 10 PM weekdays
            'command': f'python3 {config["workdir"]}/python/agents/ga_agent.py --generations 30',
            'deliver': 'local',
        },
        {
            'name': 'NN Agent — Direction Prediction (Nightly)',
            'schedule': '0 23 * * 1-5',  # 11 PM weekdays (after GA)
            'command': f'python3 {config["workdir"]}/python/agents/nn_agent.py --epochs 50',
            'deliver': 'local',
        },
        {
            'name': 'RL Agent — Policy Learning (Weekly)',
            'schedule': '0 2 * * 0',  # 2 AM Sundays
            'command': f'python3 {config["workdir"]}/python/agents/rl_agent.py --episodes 100',
            'deliver': 'local',
        },
        {
            'name': 'Blender — Rebalance Plan (Pre-Market)',
            'schedule': '30 7 * * 2-6',  # 7:30 AM Tue-Sat
            'command': f'python3 {config["workdir"]}/python/agents/blender.py --dry-run',
            'deliver': 'discord',
        },
        {
            'name': 'Orchestrator — Full Pipeline (Weekly)',
            'schedule': '0 1 * * 0',  # 1 AM Sundays
            'command': f'python3 {config["workdir"]}/python/agents/orchestrator.py --tiers 1,2',
            'deliver': 'discord',
        },
    ]
    return jobs


# ===========================================================================
# CLI
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Orchestrator — Multi-Agent Pipeline Manager'
    )
    parser.add_argument('--tiers', type=str, default='1',
                        help='Comma-separated tiers to process (1,2,3)')
    parser.add_argument('--regions', type=str, default='CDN,USA,EURO,EMERGING',
                        help='Comma-separated regions for tier 3')
    parser.add_argument('--agents', type=str, default=None,
                        help='Comma-separated agents to run (ga,nn,rl,blender)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would run, but do not execute')
    parser.add_argument('--list', action='store_true',
                        help='List pipeline status and exit')
    parser.add_argument('--setup-cron', action='store_true',
                        help='Print cron job configurations')

    args = parser.parse_args()

    if args.setup_cron:
        config = {**DEFAULT_CONFIG}
        jobs = setup_cron_jobs(config)
        print("\n# Suggested cron jobs for ksf_stockmarket pipeline:")
        print("# Add these via: cronjob create --prompt '...' --schedule '...'\n")
        for job in jobs:
            print(f"# {job['name']}")
            print(f"# Schedule: {job['schedule']}")
            print(f"# Command:  {job['command']}")
            print(f"# Deliver:  {job['deliver']}")
            print()
        return

    conn = get_connection()

    tiers = [int(t) for t in args.tiers.split(',')]
    regions = [r.strip() for r in args.regions.split(',')]
    agents = None
    if args.agents:
        agents = [a.strip() for a in args.agents.split(',')]

    orch = Orchestrator(conn, DEFAULT_CONFIG, dry_run=args.dry_run)

    try:
        results = orch.run_pipeline(
            tiers=tiers,
            regions=regions,
            agents=agents,
        )
        orch.print_status(results)

        if args.list:
            # Show queue details
            qm = PriorityQueue(conn, DEFAULT_CONFIG)
            queue = qm.build_queue(tiers=tiers, regions=regions)
            print(f"\n{'='*70}")
            print(f"QUEUE DETAILS")
            print(f"{'='*70}")
            for task in queue:
                region = f" [{task.get('region', '')}]" if task.get('region') else ""
                print(f"  Tier {task['tier']} | {task['agent'].upper()}{region} "
                      f"| {len(task['symbols'])} symbols")

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
