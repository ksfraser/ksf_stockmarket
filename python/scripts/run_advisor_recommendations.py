#!/usr/bin/env python3
"""
run_advisor_recommendations.py — Daily advisor recommendation + notification cron.

For each active advisor:
  1. Generate today's signals
  2. For each user who hired the advisor (user_advisors.is_active=1):
     - Write advisor_recommendations rows
     - Deliver via notification preferences (email/discord/whatsapp)
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from typing import Any

from python.src.advisors.repository import AdvisorRepository
from python.src.notifications.advisor_notifier import AdvisorNotifier, ensure_env
ensure_env()


try:
    from python.src.database import get_connection as _get_connection
except Exception:
    from python.db_connector import get_connection as _get_connection  # type: ignore

logger = logging.getLogger(__name__)


def _load_strategy_map() -> dict[str, type]:
    try:
        from python.src.advisors import (
            BuffettQualityStrategy,
            DividendGrowthStrategy,
            MomentumStrategy,
            SectorStrategy,
            BondBasketStrategy,
            BalancedFundStrategy,
            VectorVestSafeStockStrategy,
        )
        return {
            'buffett_quality': BuffettQualityStrategy,
            'dividend_growth': DividendGrowthStrategy,
            'momentum': MomentumStrategy,
            'sector': SectorStrategy,
            'bond_basket': BondBasketStrategy,
            'balanced_fund': BalancedFundStrategy,
            'vectorvest_safe': VectorVestSafeStockStrategy,
        }
    except Exception:
        return {}


def _users_for_advisor(db: Any, advisor_id: int) -> list[int]:
    with db.cursor() as cur:
        cur.execute(
            "SELECT user_id FROM user_advisors WHERE advisor_id = %s AND is_active = 1",
            (advisor_id,),
        )
        return [int(r['user_id']) for r in cur.fetchall()]


def run_for_date(run_date: date, slug: str | None = None) -> None:
    db = _get_connection()
    repo = AdvisorRepository(db)
    notifier = AdvisorNotifier(db)
    strategy_map = _load_strategy_map()
    advisors = repo.get_active_advisors()
    if slug:
        advisors = [a for a in advisors if a['slug'] == slug]

    if not advisors:
        logger.info('No active advisors for filter=%s', slug)
        return

    for adv in advisors:
        advisor_id = int(adv['id'])
        strategy_name = adv.get('strategy') or 'buffett_quality'
        schedule = adv.get('schedule') or 'daily'
        max_positions = int(adv.get('max_positions') or 20)

        strategy_cls = strategy_map.get(strategy_name)
        if not strategy_cls:
            logger.error('Unknown strategy %s for advisor %s', strategy_name, adv['slug'])
            continue

        try:
            instance = strategy_cls(db, config={'schedule': schedule})
            instance.slug = adv['slug']
            if not instance.should_run_today(run_date):
                logger.info('Advisor %s not eligible on %s (%s)', adv['slug'], run_date, schedule)
                continue

            signals = instance.generate_signals(run_date, max_positions=max_positions)
        except Exception as exc:
            logger.exception('Advisor %s signal generation failed', adv['slug'])
            continue

        users = _users_for_advisor(db, advisor_id)
        if not users:
            logger.info('Advisor %s has no hired users', adv['slug'])
            continue

        for sig in signals:
            for user_id in users:
                try:
                    rec_id = notifier.queue_recommendation(
                        user_id=user_id,
                        advisor_id=advisor_id,
                        symbol=sig.symbol,
                        action=sig.action,
                        price=0.0,
                        max_price=None,
                        stop_limit=None,
                        notes=f"{sig.reason} confidence={sig.confidence:.2f}",
                        signal_reasons=sig.reason,
                    )
                    notifier.deliver(rec_id)
                except Exception:
                    logger.exception('Failed recommendation delivery user=%s advisor=%s symbol=%s',
                                     user_id, adv['slug'], sig.symbol)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='Run advisor recommendations + notifications')
    p.add_argument('--date', required=True, help='Run date YYYY-MM-DD')
    p.add_argument('--slug', default=None, help='Limit to a single advisor slug')
    return p


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
    args = build_parser().parse_args(argv)
    try:
        run_date = date.fromisoformat(args.date)
    except (TypeError, ValueError):
        logger.error('Invalid --date: %s', args.date)
        return 2
    try:
        run_for_date(run_date, slug=args.slug)
    except Exception:
        logger.exception('Recommendation run crashed')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
