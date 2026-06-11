#!/usr/bin/env python3
"""
seg_fund_nav_fetcher.py — Fetch daily NAV prices for segregated funds.

Supports multiple providers:
  - Canada Life (canadalife.com)
  - Manulife (manulife.ca)
  - Sun Life (sunlife.ca)

Each provider has its own scraper class. Add new providers by subclassing
SegFundProvider and implementing fetch_navs().

Usage:
    python3 seg_fund_nav_fetcher.py --provider all          # Fetch all providers
    python3 seg_fund_nav_fetcher.py --provider canada_life  # Just Canada Life
    python3 seg_fund_nav_fetcher.py --dry-run               # Don't write to DB
    python3 seg_fund_nav_fetcher.py --status                # Show last fetch status

Database:
    Reads seg_funds table for fund list, writes to seg_fund_prices.
    Uses MariaDB (ksfraser_stock_market) via db/mysql_adapter.py.
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

# ── Path setup ──────────────────────────────────────────────────────────────
_PYTHON_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _PYTHON_DIR)

from config_loader import Config
from db import Database

log = logging.getLogger(__name__)

# ── Provider base class ─────────────────────────────────────────────────────

class SegFundProvider(ABC):
    """Base class for seg fund NAV providers."""

    name: str = ""
    base_url: str = ""

    def __init__(self, db: Database):
        self.db = db
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })

    @abstractmethod
    def fetch_navs(self, funds: List[dict]) -> List[dict]:
        """Fetch NAVs for the given funds. Returns list of {fund_id, date, nav}."""
        pass

    def get_funds_from_db(self) -> List[dict]:
        """Get funds for this provider from seg_funds table."""
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, fund_name, carrier, series FROM seg_funds WHERE carrier LIKE %s AND is_active = 1",
            (f'%{self.name}%',)
        )
        funds = cur.fetchall()
        conn.close()
        return funds


# ── Canada Life ─────────────────────────────────────────────────────────────

class CanadaLifeProvider(SegFundProvider):
    """Canada Life seg fund NAV fetcher.

    Canada Life publishes daily fund prices at:
    https://www.canadalife.com/investments/segregated-funds/fund-prices.html

    The page contains a table with fund names and NAV values.
    Fund names in our DB follow the pattern: "CAN <Fund Name> (PS2)"
    which maps to the naming on their website.
    """

    name = "Canada Life"
    base_url = "https://www.canadalife.com"

    def fetch_navs(self, funds: List[dict]) -> List[dict]:
        """Fetch NAVs from Canada Life fund prices page."""
        url = f"{self.base_url}/investments/segregated-funds/fund-prices.html"
        log.info(f"Fetching Canada Life NAVs from {url}")

        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            log.error(f"Failed to fetch Canada Life prices: {e}")
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')

        # Try to find the fund prices table
        # Canada Life typically has a table with columns: Fund Name, NAV, Date
        results = []
        today = date.today()

        # Strategy 1: Look for a table with fund data
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:  # skip header
                cells = row.find_all(['td', 'th'])
                if len(cells) < 2:
                    continue

                fund_name = cells[0].get_text(strip=True)
                nav_text = cells[1].get_text(strip=True) if len(cells) > 1 else ''

                # Clean NAV value
                nav_val = self._parse_nav(nav_text)
                if nav_val is None:
                    continue

                # Match fund name to our DB
                fund_id = self._match_fund(funds, fund_name)
                if fund_id:
                    results.append({
                        'fund_id': fund_id,
                        'price_date': today.isoformat(),
                        'nav': nav_val,
                    })

        if not results:
            log.warning("Canada Life: No fund prices parsed from table. Page structure may have changed.")
            # Log the page structure for debugging
            log.debug(f"Page title: {soup.title.string if soup.title else 'N/A'}")
            log.debug(f"Found {len(tables)} tables")

        log.info(f"Canada Life: Found {len(results)} NAVs")
        return results

    def _parse_nav(self, text: str) -> Optional[float]:
        """Parse NAV value from text like '$12.34' or '12.34'."""
        text = text.strip().replace('$', '').replace(',', '')
        try:
            val = float(text)
            return val if val > 0 else None
        except (ValueError, TypeError):
            return None

    def _match_fund(self, funds: List[dict], page_name: str) -> Optional[int]:
        """Match a fund name from the page to our DB funds."""
        page_name_lower = page_name.lower().strip()

        for fund in funds:
            db_name = fund['fund_name'].lower().strip()
            # Exact match
            if db_name == page_name_lower:
                return fund['id']
            # Partial match — page name contains DB name or vice versa
            if len(db_name) > 10 and (db_name in page_name_lower or page_name_lower in db_name):
                return fund['id']
            # Match without series suffix
            db_base = re.sub(r'\s*\([^)]*\)\s*', '', db_name).strip()
            page_base = re.sub(r'\s*\([^)]*\)\s*', '', page_name_lower).strip()
            if len(db_base) > 10 and db_base == page_base:
                return fund['id']

        return None


# ── Manulife ────────────────────────────────────────────────────────────────

class ManulifeProvider(SegFundProvider):
    """Manulife seg fund NAV fetcher.

    Manulife publishes fund prices at:
    https://www.manulife.ca/investments/segregated-funds/fund-prices.html
    """

    name = "Manulife"
    base_url = "https://www.manulife.ca"

    def fetch_navs(self, funds: List[dict]) -> List[dict]:
        """Fetch NAVs from Manulife fund prices page."""
        url = f"{self.base_url}/investments/segregated-funds/fund-prices.html"
        log.info(f"Fetching Manulife NAVs from {url}")

        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            log.error(f"Failed to fetch Manulife prices: {e}")
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')
        results = []
        today = date.today()

        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 2:
                    continue

                fund_name = cells[0].get_text(strip=True)
                nav_text = cells[1].get_text(strip=True) if len(cells) > 1 else ''

                nav_val = self._parse_nav(nav_text)
                if nav_val is None:
                    continue

                fund_id = self._match_fund(funds, fund_name)
                if fund_id:
                    results.append({
                        'fund_id': fund_id,
                        'price_date': today.isoformat(),
                        'nav': nav_val,
                    })

        log.info(f"Manulife: Found {len(results)} NAVs")
        return results

    def _parse_nav(self, text: str) -> Optional[float]:
        text = text.strip().replace('$', '').replace(',', '')
        try:
            val = float(text)
            return val if val > 0 else None
        except (ValueError, TypeError):
            return None

    def _match_fund(self, funds: List[dict], page_name: str) -> Optional[int]:
        page_name_lower = page_name.lower().strip()
        for fund in funds:
            db_name = fund['fund_name'].lower().strip()
            if db_name == page_name_lower:
                return fund['id']
            if len(db_name) > 10 and (db_name in page_name_lower or page_name_lower in db_name):
                return fund['id']
            db_base = re.sub(r'\s*\([^)]*\)\s*', '', db_name).strip()
            page_base = re.sub(r'\s*\([^)]*\)\s*', '', page_name_lower).strip()
            if len(db_base) > 10 and db_base == page_base:
                return fund['id']
        return None


# ── Sun Life ────────────────────────────────────────────────────────────────

class SunLifeProvider(SegFundProvider):
    """Sun Life seg fund NAV fetcher.

    Sun Life publishes fund prices at:
    https://www.sunlife.ca/en/investments/segregated-funds/fund-prices/
    """

    name = "Sun Life"
    base_url = "https://www.sunlife.ca"

    def fetch_navs(self, funds: List[dict]) -> List[dict]:
        """Fetch NAVs from Sun Life fund prices page."""
        url = f"{self.base_url}/en/investments/segregated-funds/fund-prices/"
        log.info(f"Fetching Sun Life NAVs from {url}")

        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            log.error(f"Failed to fetch Sun Life prices: {e}")
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')
        results = []
        today = date.today()

        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 2:
                    continue

                fund_name = cells[0].get_text(strip=True)
                nav_text = cells[1].get_text(strip=True) if len(cells) > 1 else ''

                nav_val = self._parse_nav(nav_text)
                if nav_val is None:
                    continue

                fund_id = self._match_fund(funds, fund_name)
                if fund_id:
                    results.append({
                        'fund_id': fund_id,
                        'price_date': today.isoformat(),
                        'nav': nav_val,
                    })

        log.info(f"Sun Life: Found {len(results)} NAVs")
        return results

    def _parse_nav(self, text: str) -> Optional[float]:
        text = text.strip().replace('$', '').replace(',', '')
        try:
            val = float(text)
            return val if val > 0 else None
        except (ValueError, TypeError):
            return None

    def _match_fund(self, funds: List[dict], page_name: str) -> Optional[int]:
        page_name_lower = page_name.lower().strip()
        for fund in funds:
            db_name = fund['fund_name'].lower().strip()
            if db_name == page_name_lower:
                return fund['id']
            if len(db_name) > 10 and (db_name in page_name_lower or page_name_lower in db_name):
                return fund['id']
            db_base = re.sub(r'\s*\([^)]*\)\s*', '', db_name).strip()
            page_base = re.sub(r'\s*\([^)]*\)\s*', '', page_name_lower).strip()
            if len(db_base) > 10 and db_base == page_base:
                return fund['id']
        return None


# ── NAV storage ─────────────────────────────────────────────────────────────

class NavStorage:
    """Store fetched NAVs to the database."""

    def __init__(self, db: Database):
        self.db = db

    def save_navs(self, navs: List[dict]) -> Tuple[int, int]:
        """Save NAVs to seg_fund_prices. Returns (inserted, skipped)."""
        if not navs:
            return 0, 0

        conn = self.db.get_connection()
        cur = conn.cursor()
        inserted = 0
        skipped = 0

        for nav in navs:
            try:
                cur.execute("""
                    INSERT IGNORE INTO seg_fund_prices (fund_id, price_date, nav)
                    VALUES (%s, %s, %s)
                """, (nav['fund_id'], nav['price_date'], nav['nav']))
                if cur.rowcount > 0:
                    inserted += 1
                else:
                    skipped += 1
            except Exception as e:
                log.error(f"Error saving NAV for fund {nav.get('fund_id')}: {e}")
                skipped += 1

        conn.commit()
        conn.close()
        return inserted, skipped

    def get_status(self) -> dict:
        """Get last fetch status."""
        conn = self.db.get_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM seg_fund_prices")
        total = cur.fetchone()[0]

        cur.execute("SELECT MAX(price_date) FROM seg_fund_prices")
        last_date = cur.fetchone()[0]

        cur.execute("""
            SELECT carrier, COUNT(DISTINCT sp.fund_id) as cnt
            FROM seg_fund_prices sp
            JOIN seg_funds sf ON sp.fund_id = sf.id
            GROUP BY sf.carrier
        """)
        by_carrier = {r[0]: r[1] for r in cur.fetchall()}

        conn.close()
        return {
            'total_navs': total,
            'last_date': str(last_date) if last_date else 'never',
            'by_carrier': by_carrier,
        }


# ── Main ────────────────────────────────────────────────────────────────────

PROVIDERS = {
    'canada_life': CanadaLifeProvider,
    'manulife': ManulifeProvider,
    'sun_life': SunLifeProvider,
}


def main():
    parser = argparse.ArgumentParser(description='Fetch seg fund NAVs')
    parser.add_argument('--provider', default='all',
                        choices=['all'] + list(PROVIDERS.keys()),
                        help='Provider to fetch (default: all)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Fetch but do not write to DB')
    parser.add_argument('--status', action='store_true',
                        help='Show last fetch status and exit')
    parser.add_argument('--verbose', '-v', action='store_true')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s'
    )

    # Init DB
    db = Database()

    storage = NavStorage(db)

    if args.status:
        status = storage.get_status()
        print(json.dumps(status, indent=2))
        return

    # Select providers
    if args.provider == 'all':
        provider_classes = list(PROVIDERS.values())
    else:
        provider_classes = [PROVIDERS[args.provider]]

    total_inserted = 0
    total_skipped = 0

    for cls in provider_classes:
        provider = cls(db)
        funds = provider.get_funds_from_db()
        log.info(f"{cls.name}: {len(funds)} funds in DB")

        if not funds:
            continue

        navs = provider.fetch_navs(funds)
        log.info(f"{cls.name}: Fetched {len(navs)} NAVs")

        if not args.dry_run:
            inserted, skipped = storage.save_navs(navs)
            total_inserted += inserted
            total_skipped += skipped
            log.info(f"{cls.name}: Inserted {inserted}, skipped {skipped}")
        else:
            log.info(f"{cls.name}: DRY RUN — {len(navs)} NAVs not saved")
            for nav in navs[:5]:
                log.debug(f"  Sample: fund_id={nav['fund_id']} nav={nav['nav']} date={nav['price_date']}")

    log.info(f"\nTotal: Inserted {total_inserted}, skipped {total_skipped}")


if __name__ == '__main__':
    main()
