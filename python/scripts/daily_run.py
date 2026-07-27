#!/usr/bin/env python3
"""
daily_run.py — Unified daily investment monitor.

Stages (configurable via CLI --stages or --skip):
  1. ingest_prices   : daily_pipeline --mode indicators / fetch_prices
  2. calc_indicators : indicator_calculator (new candles since last run)
  3. advisor_signals : run_advisor_recommendations.py (daily cron job)
  4. alert_watcher   : alert queue processing → LLM/template → Discord
  5. emit_notifications : advisor notifier queue drain
  6. summary         : write JSON summary to ~/.hermes/cron/output/

Usage:
  python3 scripts/daily_run.py                        # all stages
  python3 scripts/daily_run.py --stages ingest_prices,advisor_signals
  python3 scripts/daily_run.py --skip alert_watcher
  python3 scripts/daily_run.py --dry-run              # print plan only
  python3 scripts/daily_run.py --status               # show last run summary
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('daily_run')

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PYTHON_DIR = _REPO_ROOT / 'python'
_OUT_DIR = Path.home() / '.hermes' / 'cron' / 'output'
_OUT_FILE = _OUT_DIR / 'daily_run_latest.json'

# Ordered stage definitions: (name, command_parts)
# Each command runs from _PYTHON_DIR with PYTHONPATH=.:python:python/src
STAGES = [
    ('ingest_prices', [
        sys.executable, str(_PYTHON_DIR / 'daily_pipeline.py'), '--mode', 'indicators'
    ]),
    ('calc_indicators', [
        sys.executable, str(_PYTHON_DIR / 'indicator_calculator.py')
    ]),
    ('advisor_signals', [
        sys.executable, str(_PYTHON_DIR / 'scripts' / 'run_advisor_recommendations.py')
    ]),
    ('alert_watcher', [
        sys.executable,
        str(_REPO_ROOT / 'scripts' / 'alert_monitor_daemon.py'),
    ]),
]

ENV_BASE = {
    'PYTHONPATH': '.:python:python/src',
    'HOME': str(Path.home()),
}


def _run_stage(name: str, cmd: list[str], dry_run: bool = False) -> dict[str, Any]:
    """Run a single stage and capture result."""
    result = {
        'stage': name,
        'command': ' '.join(str(c) for c in cmd),
        'started_at': datetime.utcnow().isoformat() + 'Z',
        'exit_code': None,
        'stdout': '',
        'stderr': '',
        'ok': False,
    }
    if dry_run:
        logger.info('[DRY-RUN] Would run: %s', result['command'])
        result['ok'] = True
        result['stdout'] = '(dry-run)'
        return result

    logger.info('Stage start: %s', name)
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(_PYTHON_DIR),
            env={**os.environ, **ENV_BASE},
            capture_output=True,
            text=True,
            timeout=1800,
        )
        result['exit_code'] = proc.returncode
        result['stdout'] = proc.stdout[-4000:] if proc.stdout else ''
        result['stderr'] = proc.stderr[-4000:] if proc.stderr else ''
        result['ok'] = proc.returncode == 0
        if proc.returncode == 0:
            logger.info('Stage OK: %s', name)
        else:
            logger.error('Stage FAIL %s rc=%s stderr=%s', name, proc.returncode, proc.stderr[-500:])
    except subprocess.TimeoutExpired:
        result['ok'] = False
        result['stderr'] = 'timeout after 1800s'
        logger.error('Stage TIMEOUT: %s', name)
    except Exception as exc:
        result['ok'] = False
        result['stderr'] = str(exc)
        logger.error('Stage ERROR %s: %s', name, exc)
    return result


def _write_summary(results: list[dict[str, Any]], run_date: str) -> Path:
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        'run_date': run_date,
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'stages': results,
        'overall': all(r['ok'] for r in results),
    }
    _OUT_FILE.write_text(json.dumps(summary, indent=2))
    return _OUT_FILE


def _resolve_stages(requested: str | None, skip: str | None) -> list[tuple[str, list[str]]]:
    if requested:
        names = {n.strip() for n in requested.split(',') if n.strip()}
        return [(n, cmd) for n, cmd in STAGES if n in names]
    if skip:
        skip_names = {n.strip() for n in skip.split(',') if n.strip()}
        return [(n, cmd) for n, cmd in STAGES if n not in skip_names]
    return STAGES


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Unified daily investment monitor')
    parser.add_argument('--stages', help='Comma-separated stage names to run')
    parser.add_argument('--skip', help='Comma-separated stage names to omit')
    parser.add_argument('--dry-run', action='store_true', help='Print plan only')
    parser.add_argument('--status', action='store_true', help='Show last run summary and exit')
    args = parser.parse_args(argv)

    if args.status:
        if _OUT_FILE.exists():
            print(_OUT_FILE.read_text())
            return 0
        print('No previous run summary found.')
        return 1

    run_date = date.today().isoformat()
    stages = _resolve_stages(args.stages, args.skip)
    if not stages:
        logger.warning('No stages selected.')
        return 1

    logger.info('daily_run start date=%s stages=%s', run_date, ','.join(n for n, _ in stages))
    results = []
    for name, cmd in stages:
        res = _run_stage(name, cmd, dry_run=args.dry_run)
        results.append(res)
        if not res['ok'] and not args.dry_run:
            logger.warning('Stage %s failed; continuing to next stage', name)

    out = _write_summary(results, run_date)
    overall = all(r['ok'] for r in results)
    logger.info('daily_run complete overall=%s summary=%s', overall, out)
    return 0 if overall else 2


if __name__ == '__main__':
    sys.exit(main())
