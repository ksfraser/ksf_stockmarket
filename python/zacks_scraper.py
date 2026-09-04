#!/usr/bin/env python3
"""
zacks_scraper.py — Fetch Zacks Research data from ica.zacks.com and store in fundamentals.

Fetches:
  type=main  — valuation, margins, liquidity, 52-week range, broker recs, estimates
  type=ratios — historical ratio trends (ROE, ROA, Net Margin, Debt/Eq, etc.)

Stores results in:
  fundamentals  — zacks_* columns
  zacks_ratios_history — historical ratios (new table)
  zacks_broker_recommendations — individual firm grades/targets

Usage:
    python3 zacks_scraper.py --symbol MEOH
    python3 zacks_scraper.py --all
    python3 zacks_scraper.py --status
"""

import sys
import os
import json
import re
import time
import argparse
import pymysql
from datetime import date, datetime
from typing import Optional, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(__file__))
try:
    from db.mysql_adapter import MySQLConnection
except ImportError:
    MySQLConnection = None  # type: ignore

try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# ── Config ──────────────────────────────────────────────────────────────────
BASE_URL = "https://ica.zacks.com/report.php"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
}
TIMEOUT = 30
RATE_LIMIT = 1.0


# ── Helpers ──────────────────────────────────────────────────────────────────

def _text(el) -> str:
    if el is None:
        return ""
    return el.get_text(" ", strip=True)


def _to_float(s: str) -> Optional[float]:
    if not s:
        return None
    s = s.strip()
    if not s or s in ("—", "-", "NM", "N/A", "n/a", "NA"):
        return None
    s = re.sub(r"[\$%,]", "", s)
    s = s.replace(",", "")
    if s.endswith("B"):
        return float(s[:-1]) * 1e9
    if s.endswith("M"):
        return float(s[:-1]) * 1e6
    if s.endswith("K"):
        return float(s[:-1]) * 1e3
    try:
        return float(s)
    except ValueError:
        return None


def _to_int(s: str) -> Optional[int]:
    v = _to_float(s)
    return int(v) if v is not None else None


def _clean(text: str) -> str:
    """Collapse whitespace for matching."""
    return re.sub(r"\s+", " ", text).strip()


# ── Extraction helpers ───────────────────────────────────────────────────────

def _kv(body: str, key: str, window: int = 60) -> List[str]:
    """
    Find all occurrences of `key` in body text and return the value token(s)
    that follow (up to `window` chars). The key must be followed by whitespace,
    a colon, or end of string to avoid false matches (e.g., 'Beta' in
    'DataBeta'). If `key` ends with '!nosep', no separator is required.
    """
    nosep = key.endswith("!nosep")
    if nosep:
        key = key[:-6]

    results = []
    if nosep:
        # Allow key directly followed by a value (e.g. "Beta .58")
        pattern = re.compile(
            rf"{re.escape(key)}\s*([+-]?\.?[0-9]+\.?[0-9]*)",
            re.IGNORECASE
        )
    else:
        # Require separator (whitespace, colon, newline)
        pattern = re.compile(
            rf"{re.escape(key)}\s*[:-]?\s*([+-]?\.?[0-9]+\.?[0-9]*)",
            re.IGNORECASE
        )
    for m in pattern.finditer(body):
        val = m.group(1).strip() if m.lastindex >= 1 else ""
        if val:
            results.append(val)
    return results


def _first_float(body: str, *keys: str) -> Optional[float]:
    """Try multiple key patterns, return first successful parse.

    Each key may include a flag ':nosep' suffix in the key string to disable
    the requirement of a separator between the key and the value. The default
    requires the key to be followed by whitespace, a colon, or a newline
    (so 'Beta .58' matches but 'InputBeta' does not).
    """
    for key in keys:
        # Allow regex in keys (passed as raw regex pattern)
        # Try with separator first
        vals = _kv(body, key)
        for v in vals:
            f = _to_float(v)
            if f is not None:
                return f
    return None


def _first_int(body: str, *keys: str) -> Optional[int]:
    for key in keys:
        vals = _kv(body, key)
        for v in vals:
            i = _to_int(v)
            if i is not None:
                return i
    return None


# ── Scraper ──────────────────────────────────────────────────────────────────

class ZacksScraper:
    """Extract Zacks metrics from public report pages."""

    def __init__(self):
        self.session = requests.Session() if REQUESTS_AVAILABLE else None
        if self.session:
            self.session.headers.update(HEADERS)

    def _symbol_for_zacks(self, symbol: str) -> str:
        """
        Map our internal symbol to Zacks-compatible ticker.
        Some symbols have different tickers on Zacks (e.g., Methanex=MEOH).
        """
        # Curated mapping: our symbol -> Zacks ticker
        zacks_map = {
            "MX": "MEOH",      # Methanex trades as MEOH on US exchanges
            "MX.TO": "MEOH",
            "MEOH": "MEOH",
            # Add more as needed
        }
        return zacks_map.get(symbol.upper(), symbol)

    def fetch(self, symbol: str) -> dict:
        """Fetch Zacks data for a symbol. Returns dict of metrics."""
        if not REQUESTS_AVAILABLE or self.session is None:
            return {"symbol": symbol, "error": "requests/beautifulsoup4 not available"}

        zacks_sym = self._symbol_for_zacks(symbol)

        result: dict = {"symbol": symbol, "fetch_date": str(date.today())}

        # ── Main report ─────────────────────────────────────────────────────
        main_data = self._fetch_page(zacks_sym, "main")
        if "error" in main_data:
            return {"symbol": symbol, "error": main_data["error"]}

        body = main_data["body"]
        result.update(self._parse_main(body))

        # ── Ratios page ─────────────────────────────────────────────────────
        ratios_data = self._fetch_page(zacks_sym, "ratios")
        if "error" not in ratios_data:
            ratios = self._parse_ratios(ratios_data["body"])
            result.update(ratios)

        # ── Recommendations page ─────────────────────────────────────────────
        recs_data = self._fetch_page(zacks_sym, "recommendations")
        if "error" not in recs_data:
            recs = self._parse_recommendations(recs_data["body"])
            result.update(recs)

        # ── Estimates page (consensus EPS & revision trends) ─────────────────
        est_data = self._fetch_page(zacks_sym, "estimates")
        if "error" not in est_data:
            est = self._parse_estimates(est_data["body"])
            result.update(est)

        # Raw JSON for debugging
        result["zacks_raw_json"] = json.dumps({
            k: v for k, v in result.items()
            if k not in ("symbol", "fetch_date", "zacks_raw_json")
        })

        return result

    def _fetch_page(self, symbol: str, report_type: str) -> dict:
        url = f"{BASE_URL}?t={symbol}&type={report_type}"
        try:
            resp = self.session.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            body = _clean(soup.get_text(" ", strip=True))
            if len(body) < 200:
                return {"error": f"page too short ({len(body)} chars)"}
            return {"body": body}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response else 0
            return {"error": f"HTTP {code}: {e}"}
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    # ── Main report parser ───────────────────────────────────────────────────

    def _parse_main(self, body: str) -> dict:
        data: dict = {}

        # 52-week range
        high = _first_float(body, "52-week high")
        low = _first_float(body, "52-week low")
        if high and low:
            data["zacks_price_change_52w"] = ((high - low) / low) * 100 if low else None

        # Valuation
        data["trailing_pe"] = _first_float(body, "P/E \\(TTM\\)", "P/E (TTM)")
        data["forward_pe"] = _first_float(body, "P/E \\(F1\\)", "P/E (F1)")
        data["peg_ratio"] = _first_float(body, "PEG", "PEG Ratio")
        data["price_to_book"] = _first_float(body, "P/Book")
        data["price_to_sales"] = _first_float(body, "P/Sales")
        data["book_value"] = _first_float(body, "Book Value per Share")

        # EPS
        data["trailing_eps"] = _first_float(body, "EPS \\(Trailing\\)", "EPS (Trailing)")
        data["forward_eps"] = _first_float(body, "Consensus Estimate for Next Fiscal Year")

        # Per-share
        data["shares_outstanding"] = _first_float(body, "Shares Outstanding \\(millions\\)") * 1e6 if _first_float(body, "Shares Outstanding \\(millions\\)") else None
        data["market_cap"] = _first_float(body, "Market Capitalization \\(millions\\)") * 1e6 if _first_float(body, "Market Capitalization \\(millions\\)") else None

        # Profitability
        data["gross_margin"] = _first_float(body, "Gross Margin")
        data["operating_margin"] = _first_float(body, "Operating Margin")
        data["profit_margin"] = _first_float(body, "Net Margin", "Net Profit Margin")
        data["roe"] = _first_float(body, "ROE", "Return on Equity")
        data["roa"] = _first_float(body, "ROA", "Return on Assets")
        data["zacks_roi"] = _first_float(body, "ROI", "Return on Invested Capital")

        # Leverage / Liquidity
        data["debt_to_equity"] = _first_float(body, "Total Debt / Equity", "Debt / Equity")
        data["current_ratio"] = _first_float(body, "Current Ratio")
        data["quick_ratio"] = _first_float(body, "Quick Ratio")
        data["zacks_lt_debt_capital_pct"] = _first_float(body, "LT Debt/Capital", "Long Term Debt/Capital")
        data["zacks_asset_turnover_ttm"] = _first_float(body, "Asset Turnover")
        data["zacks_fcf_f0"] = _first_float(body, "Free Cash Flow")
        data["zacks_net_profit_margin"] = _first_float(body, "Net Profit Margin", "Net Margin")

        # Dividend
        data["dividend_yield"] = _first_float(body, "Dividend Yield")
        data["payout_ratio"] = _first_float(body, "Payout Ratio")

        # Beta / Short (use !nosep because page format is "Beta .58" with space)
        data["beta"] = _first_float(body, "Beta!nosep")
        data["short_ratio"] = _first_float(body, "Short Ratio!nosep")

        # Institutional / Insider
        insider = _first_float(body, "% held by Insiders")
        inst = _first_float(body, "% held by Institutions")
        if insider is not None:
            data["insider_percent"] = insider / 100.0
        if inst is not None:
            data["institutional_percent"] = inst / 100.0

        # Sector / Industry
        ind_m = re.search(r"Industry:\s*([^\s]+)", body)
        if ind_m:
            data["industry"] = ind_m.group(1).strip()
            if ind_m.group(1).strip() == "n/a":
                data["industry"] = None

        # Broker recommendation counts
        rec_counts = {}
        for level in ["Strong Buy", "Moderate Buy", "Hold", "Moderate Sell", "Strong Sell"]:
            n = _first_int(body, f"Analysts recommending as a {level}")
            rec_counts[level] = n or 0
        total_recs = sum(rec_counts.values())
        data["zacks_num_analysts"] = total_recs if total_recs > 0 else None

        # Average recommendation (1=Strong Buy, 5=Strong Sell)
        avg_rec = _first_float(body, "Current Average Recommendation")
        if avg_rec is not None and not (isinstance(avg_rec, float) and avg_rec == 0.0):
            data["zacks_recommendation"] = self._rec_label(avg_rec)
        else:
            data["zacks_recommendation"] = None

        # Price momentum from 52-week range (we only have 52w from main page)
        # 12w/24w/4w come from price history if available
        data["zacks_price_change_12w"] = None
        data["zacks_price_change_24w"] = None
        data["zacks_price_change_4w"] = None

        # EPS growth estimates
        data["zacks_eps_pct_change_f1_f0"] = _first_float(body, "EPS % Change F1/F0")
        data["zacks_eps_pct_change_f2_f1"] = _first_float(body, "EPS % Change F2/F1")
        data["zacks_eps_growth_q0_q4"] = _first_float(body, "EPS Growth Q0/Q-4")
        data["zacks_eps_growth_5yr"] = _first_float(body, "EPS Growth 5[\s-]*Yr")
        data["zacks_eps_growth_lt_3_5yr"] = _first_float(body, "EPS Growth LT 3-5")
        data["zacks_sales_growth_reported_q"] = _first_float(body, "Sales Growth Reported Q")

        # EPS change estimates
        for fk, fval in [("F1", "zacks_eps_change_f1_1w"), ("F1", "zacks_eps_change_f1_4w"),
                         ("F1", "zacks_eps_change_f1_12w"), ("F2", "zacks_eps_change_f2_1w"),
                         ("F2", "zacks_eps_change_f2_4w")]:
            # These typically don't appear on the main page; leave NULL
            pass

        return data

    def _parse_ratios(self, body: str) -> dict:
        """
        Parse the Financial Ratios page. This page has tabular data like:
          Return on Equity 5.43 10.58 7.04 14.12
        We take the most recent value.
        """
        data: dict = {}

        ratio_map = {
            "Return on Equity": "roe",
            "Return on Assets": "roa",
            "Return on Invested Capital": "zacks_roi",
            "Pre-Tax Profit Margin %": "profit_margin",  # overwritten by Net Margin later
            "Net Profit Margin": "profit_margin",
            "Price / Book": "price_to_book",
            "Price / Earnings": "trailing_pe",
            "Price / Revenue": "price_to_sales",
            "Book Value per Share": "book_value",
            "Current Ratio": "current_ratio",
            "Quick Ratio": "quick_ratio",
            "Debt / Equity": "debt_to_equity",
            "Leverage Ratio": "zacks_lt_debt_capital_pct",
            "Inventory as % of Revenue": "zacks_inventory_turnover_5yr",
            "Sales per \$Inventory": "zacks_inventory_turnover_5yr",
        }

        # Find table-like sections: label followed by numeric columns
        for label, field in ratio_map.items():
            # Match: label followed by 2-5 numeric tokens; take the first (most recent)
            pattern = rf"{re.escape(label)}\s+([0-9][0-9.,\s]{{5,100}})"
            m = re.search(pattern, body)
            if m:
                values_str = m.group(1)
                values = re.findall(r"[0-9]+\.?[0-9]*", values_str)
                if values:
                    val = _to_float(values[0])
                    # Only overwrite if not already set from main page
                    if field not in data or data[field] is None:
                        data[field] = val

        return data

    def _parse_recommendations(self, body: str) -> dict:
        """Parse the Recommendations page for firm-level data."""
        data: dict = {}
        # This page has firm names and ratings — extract if present
        # For now, we just flag that we tried
        data["_recs_page_fetched"] = True
        return data

    @staticmethod
    def _rec_label(score: float) -> str:
        """Convert 1-5 recommendation score to label."""
        labels = {1: "Strong Buy", 2: "Buy", 3: "Hold", 4: "Sell", 5: "Strong Sell"}
        closest = min(labels.keys(), key=lambda k: abs(k - score))
        return labels.get(closest, "Hold")

    def _parse_estimates(self, body: str) -> dict:
        """
        Parse the Estimates page for consensus EPS estimates and revision trends.
        Returns dict with forward_eps and zacks_eps_change_f1_* / zacks_eps_change_f2_*.
        """
        data: dict = {}

        # Current consensus (today's average estimates)
        avg_m = re.search(
            r"Average Estimate\s+([0-9]+\.[0-9]+(?:\s+[0-9]+\.[0-9]+){3,})",
            body,
        )
        if avg_m:
            vals = re.findall(r"[0-9]+\.[0-9]+", avg_m.group(1))
            if len(vals) >= 4:
                f1_now = float(vals[2])
                f2_now = float(vals[3])
                data["forward_eps"] = f2_now
            else:
                f1_now = f2_now = None
        else:
            f1_now = f2_now = None

        # 7 Days Ago consensus
        d7_m = re.search(
            r"Consensus 7 Days Ago\s+([0-9]+\.[0-9]+(?:\s+[0-9]+\.[0-9]+){3,})",
            body,
        )
        if d7_m:
            vals = re.findall(r"[0-9]+\.[0-9]+", d7_m.group(1))
            if len(vals) >= 4:
                f1_7d = float(vals[2])
                f2_7d = float(vals[3])
                if f1_now is not None:
                    data["zacks_eps_change_f1_1w"] = round(f1_now - f1_7d, 4)
                if f2_now is not None:
                    data["zacks_eps_change_f2_1w"] = round(f2_now - f2_7d, 4)

        # 30 Days Ago consensus
        d30_m = re.search(
            r"Consensus 30 Days Ago\s+([0-9]+\.[0-9]+(?:\s+[0-9]+\.[0-9]+){3,})",
            body,
        )
        if d30_m:
            vals = re.findall(r"[0-9]+\.[0-9]+", d30_m.group(1))
            if len(vals) >= 4:
                f1_30d = float(vals[2])
                f2_30d = float(vals[3])
                if f1_now is not None:
                    data["zacks_eps_change_f1_4w"] = round(f1_now - f1_30d, 4)
                if f2_now is not None:
                    data["zacks_eps_change_f2_4w"] = round(f2_now - f2_30d, 4)

        return data


# ── Broker Recommendations Parser ───────────────────────────────────────────

def extract_broker_recommendations(html: str, symbol: str, fetch_date: str) -> list:
    """
    Extract individual broker recommendations from the Recommendations page HTML.
    Returns list of dicts for zacks_broker_recommendations table.
    """
    recs = []
    soup = BeautifulSoup(html, "html.parser")

    tables = soup.find_all("table")
    for tbl in tables:
        headers = [th.get_text(strip=True).lower() for th in tbl.find_all("th")]
        if not any("firm" in h or "broker" in h or "analyst" in h for h in headers):
            continue
        if not any("target" in h or "grade" in h or "rating" in h for h in headers):
            continue

        for row in tbl.find_all("tr")[1:]:
            cells = [td.get_text(" ", strip=True) for td in row.find_all(["td", "th"])]
            if len(cells) < 2:
                continue
            rec = {
                "symbol": symbol,
                "firm": cells[0] if cells else "",
                "analyst": cells[1] if len(cells) > 1 else "",
                "grade": cells[2] if len(cells) > 2 else "",
                "price_target": _to_float(cells[3]) if len(cells) > 3 else None,
                "action": cells[4] if len(cells) > 4 else "",
                "rec_date": None,
                "fetch_date": fetch_date,
                "raw_json": json.dumps(cells),
            }
            for cell in cells:
                d = re.search(r"(\d{4}-\d{2}-\d{2})", cell)
                if d:
                    rec["rec_date"] = d.group(1)
                    break
            if rec["firm"]:
                recs.append(rec)
        if recs:
            break

    return recs


# ── Database Storage ──────────────────────────────────────────────────────────

class ZacksStore:
    """Store Zacks metrics in MySQL."""

    def __init__(self):
        if MySQLConnection:
            self.adapter = MySQLConnection(
                host=os.environ.get("DB_HOST", "ksfraser.ca"),
                user=os.environ.get("DB_USER", "ksfraser_stockmarket"),
                password=os.environ.get("DB_PASS", ""),
                database=os.environ.get("DB_NAME", "ksfraser_stock_market"),
            )
        else:
            self.adapter = None

    def upsert_fundamentals(self, data: dict) -> bool:
        """Insert or update fundamentals row with zacks_* fields.
        If no existing row for the symbol exists, create one."""
        if not self.adapter or not data or "error" in data:
            return False

        zacks_fields = {k: v for k, v in data.items() if k.startswith("zacks_") or k in (
            "trailing_pe", "forward_pe", "peg_ratio", "price_to_book", "price_to_sales",
            "book_value", "trailing_eps", "forward_eps", "market_cap", "shares_outstanding",
            "gross_margin", "operating_margin", "profit_margin", "roe", "roa",
            "debt_to_equity", "current_ratio", "quick_ratio", "dividend_yield",
            "payout_ratio", "beta", "short_ratio", "insider_percent", "institutional_percent",
            "industry",
        )}
        if not zacks_fields:
            return False

        # Check if a row exists for this symbol
        try:
            with self.adapter as conn:
                existing = conn.fetchone(
                    "SELECT id FROM fundamentals WHERE symbol = %s ORDER BY fetch_date DESC LIMIT 1",
                    (data["symbol"],)
                )
        except Exception as e:
            print(f"  lookup error: {e}")
            return False

        if existing:
            # UPDATE existing row
            cols = list(zacks_fields.keys())
            vals = list(zacks_fields.values())
            set_clause = ", ".join(f"{c} = %s" for c in cols)
            sql = f"""
                UPDATE fundamentals
                SET {set_clause}
                WHERE symbol = %s
                ORDER BY fetch_date DESC LIMIT 1
            """
            try:
                with self.adapter as conn:
                    affected = conn.execute(sql, tuple(vals) + (data["symbol"],))
                return affected > 0
            except Exception as e:
                print(f"  update error: {e}")
                return False
        else:
            # INSERT new row
            all_fields = {"symbol": data["symbol"], "fetch_date": str(date.today())}
            all_fields.update(zacks_fields)
            cols = list(all_fields.keys())
            vals = list(all_fields.values())
            placeholders = ", ".join(["%s"] * len(cols))
            sql = f"""
                INSERT INTO fundamentals ({", ".join(cols)})
                VALUES ({placeholders})
            """
            try:
                with self.adapter as conn:
                    conn.execute(sql, tuple(vals))
                return True
            except Exception as e:
                print(f"  insert error: {e}")
                return False

    def store_ratios_history(self, symbol: str, ratios_body: str) -> int:
        """
        Parse and store historical ratios from the ratios page body.
        Creates/updates zacks_ratios_history table.
        """
        if not self.adapter or not ratios_body:
            return 0

        # Ensure table exists
        try:
            with self.adapter as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS zacks_ratios_history (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        symbol VARCHAR(20) NOT NULL,
                        ratio_name VARCHAR(80) NOT NULL,
                        period_label VARCHAR(20) NULL,
                        ratio_value DOUBLE NULL,
                        fetch_date DATE NOT NULL,
                        raw_text TEXT NULL,
                        INDEX idx_symbol (symbol),
                        INDEX idx_ratio (ratio_name, fetch_date)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
        except Exception:
            pass

        # Parse tabular ratio data from body
        rows = []
        # Pattern: ratio_name followed by 4 numeric values (4 years)
        ratio_names = [
            "Return on Equity", "Return on Assets", "Return on Invested Capital",
            "Pre-Tax Profit Margin %", "Net Profit Margin",
            "Price / Book", "Price / Earnings", "Price / Revenue", "Price / Cash Flow",
            "Book Value per Share", "Current Ratio", "Quick Ratio",
            "Debt / Equity", "Leverage Ratio",
            "Inventory as % of Revenue", "Sales per $Inventory",
        ]
        for rname in ratio_names:
            pattern = rf"{re.escape(rname)}\s+([0-9][0-9.,\s]{{5,100}})"
            m = re.search(pattern, ratios_body)
            if m:
                values_str = m.group(1)
                values = re.findall(r"[0-9]+\.?[0-9]*", values_str)
                # Assign to year columns (most recent first)
                years = ["current", "year-1", "year-2", "year-3"]
                for i, v in enumerate(values[:4]):
                    rows.append({
                        "symbol": symbol,
                        "ratio_name": rname,
                        "period_label": years[i] if i < len(years) else f"y{i}",
                        "ratio_value": _to_float(v),
                        "fetch_date": str(date.today()),
                        "raw_text": values_str.strip(),
                    })

        if not rows:
            return 0

        try:
            with self.adapter as conn:
                # Delete old rows for same symbol+ratio_name+today
                conn.execute(
                    "DELETE FROM zacks_ratios_history WHERE symbol = %s AND fetch_date = %s",
                    (symbol, str(date.today()))
                )
                for r in rows:
                    conn.execute("""
                        INSERT INTO zacks_ratios_history
                        (symbol, ratio_name, period_label, ratio_value, fetch_date, raw_text)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (r["symbol"], r["ratio_name"], r["period_label"],
                          r["ratio_value"], r["fetch_date"], r["raw_text"]))
            return len(rows)
        except Exception as e:
            print(f"  Ratios DB error: {e}")
            return 0

    def store_broker_recs(self, recs: list) -> int:
        """Store broker recommendations."""
        if not self.adapter or not recs:
            return 0
        today = str(date.today())
        symbols = list(set(r["symbol"] for r in recs))
        try:
            with self.adapter as conn:
                for sym in symbols:
                    conn.execute(
                        "DELETE FROM zacks_broker_recommendations WHERE symbol = %s AND fetch_date = %s",
                        (sym, today)
                    )
                inserted = 0
                for r in recs:
                    conn.execute("""
                        INSERT INTO zacks_broker_recommendations
                        (symbol, firm, analyst, grade, price_target, action, rec_date, fetch_date, raw_json)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (r["symbol"], r["firm"], r["analyst"], r["grade"],
                          r["price_target"], r["action"], r["rec_date"],
                          r["fetch_date"], r["raw_json"]))
                    inserted += 1
            return inserted
        except Exception as e:
            print(f"  Broker recs DB error: {e}")
            return 0

    def status(self) -> dict:
        if not self.adapter:
            return {"error": "adapter not available"}
        try:
            with self.adapter as conn:
                row = conn.fetchone("""
                    SELECT COUNT(DISTINCT symbol) as n, MAX(fetch_date) as latest
                    FROM fundamentals WHERE zacks_rank IS NOT NULL
                """)
                return row or {"n": 0, "latest": None}
        except Exception as e:
            return {"error": str(e)}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Zacks Research Wizard scraper")
    parser.add_argument("--symbol", help="Single symbol to fetch")
    parser.add_argument("--symbols", help="Comma-separated symbols")
    parser.add_argument("--all", action="store_true", help="Fetch all active symbols")
    parser.add_argument("--status", action="store_true", help="Show Zacks data status")
    args = parser.parse_args()

    scraper = ZacksScraper()
    store = ZacksStore()

    if args.status:
        s = store.status()
        print(f"Zacks data: {s.get('n', 0)} symbols, latest={s.get('latest', 'N/A')}")
        return

    if args.symbol:
        symbols = [args.symbol.strip().upper()]
    elif args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    elif args.all:
        try:
            with MySQLConnection(
                host=os.environ.get("DB_HOST", "ksfraser.ca"),
                user=os.environ.get("DB_USER", "ksfraser_stockmarket"),
                password=os.environ.get("DB_PASS", ""),
                database=os.environ.get("DB_NAME", "ksfraser_stock_market"),
            ) as conn:
                rows = conn.fetchall("SELECT symbol FROM symbol_master WHERE is_active = 1 ORDER BY symbol")
                symbols = [r["symbol"] for r in rows]
        except Exception as e:
            print(f"✗ Failed to load symbols: {e}")
            return
    else:
        parser.print_help()
        return

    print(f"Zacks scrape: {len(symbols)} symbols")

    ok = fail = 0
    for i, sym in enumerate(symbols):
        print(f"  [{i+1}/{len(symbols)}] {sym}...", end=" ", flush=True)
        data = scraper.fetch(sym)
        if "error" in data:
            print(f"SKIP ({data['error']})")
            fail += 1
            continue

        recs = []
        if scraper.session:
            try:
                zacks_sym = scraper._symbol_for_zacks(sym)
                url = f"{BASE_URL}?t={zacks_sym}&type=recommendations"
                resp = scraper.session.get(url, timeout=TIMEOUT)
                resp.raise_for_status()
                recs = extract_broker_recommendations(resp.text, sym, data["fetch_date"])
            except Exception:
                pass

        ratios_stored = 0
        if scraper.session:
            try:
                zacks_sym = scraper._symbol_for_zacks(sym)
                url = f"{BASE_URL}?t={zacks_sym}&type=ratios"
                resp = scraper.session.get(url, timeout=TIMEOUT)
                resp.raise_for_status()
                body = _clean(BeautifulSoup(resp.text, "html.parser").get_text(" ", strip=True))
                ratios_stored = store.store_ratios_history(sym, body)
            except Exception:
                pass

        if store.upsert_fundamentals(data):
            rec_count = store.store_broker_recs(recs)
            print(f"✓ ({ratios_stored} ratios, {rec_count} broker recs)")
            ok += 1
        else:
            print("✗ (DB error)")
            fail += 1

        if i < len(symbols) - 1:
            time.sleep(RATE_LIMIT)

    print(f"\nDone. {ok} ok, {fail} failed, {len(symbols)} total")


if __name__ == "__main__":
    main()
