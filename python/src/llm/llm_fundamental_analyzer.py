"""
llm_fundamental_analyzer.py — LLM-Enhanced Fundamental Analysis

Reads the four llm_* tables at session start, fetches current data from
external sources, analyzes via LLM (using LlmClient fallback chain),
updates llm_* tables with new findings, and produces conviction scores
and investment thesis summaries.

Usage:
    python3 -m python.src.llm.llm_fundamental_analyzer --symbol RY.TO --advisor llm-fundamental-value
    python3 -m python.src.llm.llm_fundamental_analyzer --symbol RY.TO --all-sources
    python3 -m python.src.llm.llm_fundamental_analyzer --dry-run --top 10
"""

from __future__ import annotations

import argparse
import logging
import os
import hashlib
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from python.src.llm.llm_client import LlmClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

TODAY = date.today()
TABLETYPES = {
    "insider": "llm_insider_trading",
    "news": "llm_news_events",
    "product_dev": "llm_product_dev",
    "regulatory": "llm_regulatory",
}


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def db_query(db, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Execute a query and return list of dict rows."""
    stmt = db.prepare(sql)
    stmt.execute(list(params))
    cols = [c[0] for c in stmt.description] if stmt.description else []
    return [dict(zip(cols, row)) for row in stmt.fetchall()]


def db_execute(db, sql: str, params: tuple = ()) -> int:
    """Execute INSERT/UPDATE/DELETE, return affected row count."""
    stmt = db.prepare(sql)
    stmt.execute(list(params))
    return stmt.rowcount()


def db_get_setting(db, key: str) -> str:
    """Read a single system_settings value."""
    try:
        rows = db_query(db, "SELECT setting_value FROM system_settings WHERE setting_key = :k", (key,))
        return rows[0]["setting_value"] if rows else ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# llm_* table CRUD
# ---------------------------------------------------------------------------

def read_insider_trading(db, symbol: str, days_back: int = 90) -> List[Dict]:
    rows = db_query(
        db,
        f"SELECT * FROM {TABLETYPES['insider']} WHERE symbol = :sym AND event_date >= :since ORDER BY event_date DESC",
        (symbol, TODAY - timedelta(days=days_back)),
    )
    return rows


def read_news_events(db, symbol: str, days_back: int = 90) -> List[Dict]:
    rows = db_query(
        db,
        f"SELECT * FROM {TABLETYPES['news']} WHERE symbol = :sym AND event_date >= :since ORDER BY event_date DESC",
        (symbol, TODAY - timedelta(days=days_back)),
    )
    return rows


def read_product_dev(db, symbol: str) -> List[Dict]:
    rows = db_query(
        db,
        f"SELECT * FROM {TABLETYPES['product_dev']} WHERE symbol = :sym ORDER BY event_date DESC",
        (symbol,),
    )
    return rows


def read_regulatory(db, symbol: str) -> List[Dict]:
    rows = db_query(
        db,
        f"SELECT * FROM {TABLETYPES['regulatory']} WHERE symbol = :sym ORDER BY event_date DESC",
        (symbol,),
    )
    return rows


def upsert_insider_event(db, symbol: str, event_date: date, headline: str, details: str,
                         source: str = "", confidence: int = 50, conviction: float = 0.0,
                         is_verified: bool = False) -> int:
    """Insert or update an insider trading event. Returns new row id."""
    hash_key = hashlib.md5(f"{symbol}|{event_date}|{headline}".encode()).hexdigest()[:16]
    existing = db_query(
        db,
        f"SELECT id FROM {TABLETYPES['insider']} WHERE symbol = :sym AND event_date = :dt AND LEFT(headline,100) = :hl",
        (symbol, event_date, headline[:100]),
    )
    if existing:
        rid = existing[0]["id"]
        db_execute(
            db,
            f"UPDATE {TABLETYPES['insider']} SET details = :det, source = :src, "
            f"confidence = :conf, conviction_score = :conv, is_verified = :ver, updated_at = NOW() "
            f"WHERE id = :id",
            (details, source, confidence, conviction, int(is_verified), rid),
        )
        return rid
    db_execute(
        db,
        f"INSERT INTO {TABLETYPES['insider']} (symbol, event_date, headline, details, source, "
        f"confidence, conviction_score, is_verified, as_of) VALUES "
        f"(:sym, :dt, :hl, :det, :src, :conf, :conv, :ver, :asof)",
        (symbol, event_date, headline[:500], details, source, confidence,
         conviction, int(is_verified), TODAY),
    )
    return db_query(db, "SELECT LAST_INSERT_ID() as id")[0]["id"]


def upsert_news_event(db, symbol: str, event_date: date, headline: str, details: str,
                      category: str, source: str = "", confidence: int = 50,
                      sentiment: float = 0.0, conviction: float = 0.0,
                      is_verified: bool = False) -> int:
    hash_key = hashlib.md5(f"{symbol}|{event_date}|{headline}".encode()).hexdigest()[:16]
    existing = db_query(
        db,
        f"SELECT id FROM {TABLETYPES['news']} WHERE symbol = :sym AND event_date = :dt AND LEFT(headline,100) = :hl",
        (symbol, event_date, headline[:100]),
    )
    if existing:
        rid = existing[0]["id"]
        db_execute(
            db,
            f"UPDATE {TABLETYPES['news']} SET details = :det, source = :src, category = :cat, "
            f"confidence = :conf, sentiment_score = :sent, conviction_score = :conv, "
            f"is_verified = :ver, updated_at = NOW() WHERE id = :id",
            (details, source, category, confidence, sentiment, conviction, int(is_verified), rid),
        )
        return rid
    db_execute(
        db,
        f"INSERT INTO {TABLETYPES['news']} (symbol, event_date, headline, details, source, category, "
        f"confidence, sentiment_score, conviction_score, is_verified, as_of) VALUES "
        f"(:sym, :dt, :hl, :det, :src, :cat, :conf, :sent, :conv, :ver, :asof)",
        (symbol, event_date, headline[:500], details, source, category,
         confidence, sentiment, conviction, int(is_verified), TODAY),
    )
    return db_query(db, "SELECT LAST_INSERT_ID() as id")[0]["id"]


def upsert_product_dev_event(db, symbol: str, product_name: str, lifecycle_stage: str,
                             event_date: date, headline: str, details: str,
                             source: str = "", expected_impact: str = "neutral",
                             confidence: int = 50, conviction: float = 0.0,
                             is_verified: bool = False) -> int:
    existing = db_query(
        db,
        f"SELECT id FROM {TABLETYPES['product_dev']} WHERE symbol = :sym AND product_name = :pn AND lifecycle_stage = :stage",
        (symbol, product_name, lifecycle_stage),
    )
    if existing:
        rid = existing[0]["id"]
        db_execute(
            db,
            f"UPDATE {TABLETYPES['product_dev']} SET event_date = :dt, headline = :hl, details = :det, "
            f"source = :src, expected_impact = :imp, confidence = :conf, conviction_score = :conv, "
            f"is_verified = :ver, updated_at = NOW() WHERE id = :id",
            (event_date, headline[:500], details, source, expected_impact,
             confidence, conviction, int(is_verified), rid),
        )
        return rid
    db_execute(
        db,
        f"INSERT INTO {TABLETYPES['product_dev']} (symbol, product_name, lifecycle_stage, event_date, "
        f"headline, details, source, expected_impact, confidence, conviction_score, is_verified, as_of) VALUES "
        f"(:sym, :pn, :stage, :dt, :hl, :det, :src, :imp, :conf, :conv, :ver, :asof)",
        (symbol, product_name, lifecycle_stage, event_date, headline[:500], details, source,
         expected_impact, confidence, conviction, int(is_verified), TODAY),
    )
    return db_query(db, "SELECT LAST_INSERT_ID() as id")[0]["id"]


def upsert_regulatory_event(db, symbol: str, event_date: date, headline: str, details: str,
                            regulatory_type: str, jurisdiction: str = "",
                            status: str = "pending", source: str = "",
                            confidence: int = 50, conviction: float = 0.0,
                            is_verified: bool = False) -> int:
    existing = db_query(
        db,
        f"SELECT id FROM {TABLETYPES['regulatory']} WHERE symbol = :sym AND event_date = :dt AND LEFT(headline,100) = :hl",
        (symbol, event_date, headline[:100]),
    )
    if existing:
        rid = existing[0]["id"]
        db_execute(
            db,
            f"UPDATE {TABLETYPES['regulatory']} SET details = :det, source = :src, regulatory_type = :rtype, "
            f"jurisdiction = :jur, status = :stat, confidence = :conf, conviction_score = :conv, "
            f"is_verified = :ver, updated_at = NOW() WHERE id = :id",
            (details, source, regulatory_type, jurisdiction, status,
             confidence, conviction, int(is_verified), rid),
        )
        return rid
    db_execute(
        db,
        f"INSERT INTO {TABLETYPES['regulatory']} (symbol, event_date, headline, details, source, "
        f"regulatory_type, jurisdiction, status, confidence, conviction_score, is_verified, as_of) VALUES "
        f"(:sym, :dt, :hl, :det, :src, :rtype, :jur, :stat, :conf, :conv, :ver, :asof)",
        (symbol, event_date, headline[:500], details, source, regulatory_type, jurisdiction,
         status, confidence, conviction, int(is_verified), TODAY),
    )
    return db_query(db, "SELECT LAST_INSERT_ID() as id")[0]["id"]


def flag_old_unverified_low_confidence(db) -> List[Dict]:
    """Find rows older than 90 days with is_verified=0 and confidence < 50."""
    cutoff = TODAY - timedelta(days=90)
    rows = db_query(
        db,
        f"SELECT '{TABLETYPES['insider']}' as table_name, id, symbol, event_date, confidence "
        f"FROM {TABLETYPES['insider']} WHERE is_verified = 0 AND confidence < 50 AND event_date < :cutoff "
        f"UNION ALL "
        f"SELECT '{TABLETYPES['news']}' as table_name, id, symbol, event_date, confidence "
        f"FROM {TABLETYPES['news']} WHERE is_verified = 0 AND confidence < 50 AND event_date < :cutoff2 "
        f"UNION ALL "
        f"SELECT '{TABLETYPES['product_dev']}' as table_name, id, symbol, event_date, confidence "
        f"FROM {TABLETYPES['product_dev']} WHERE is_verified = 0 AND confidence < 50 AND event_date < :cutoff3 "
        f"UNION ALL "
        f"SELECT '{TABLETYPES['regulatory']}' as table_name, id, symbol, event_date, confidence "
        f"FROM {TABLETYPES['regulatory']} WHERE is_verified = 0 AND confidence < 50 AND event_date < :cutoff4",
        (cutoff, cutoff, cutoff, cutoff),
    )
    return rows


# ---------------------------------------------------------------------------
# LLM analysis
# ---------------------------------------------------------------------------

def build_llm_prompt(symbol: str, existing_data: Dict[str, List[Dict]]) -> str:
    """Build a prompt for the LLM containing existing data and analysis instructions."""
    insider = existing_data.get("insider_trading", [])
    news = existing_data.get("news_events", [])
    product_dev = existing_data.get("product_dev", [])
    regulatory = existing_data.get("regulatory", [])

    prompt = f"""You are a senior equity research analyst covering {symbol}.

ANALYSIS CONTEXT (existing tracked events in the last 90 days):
"""
    if insider:
        prompt += f"\n\n1. INSIDER/GUIDANCE EVENTS ({len(insider)} tracked):\n"
        for ev in insider[:10]:
            prompt += f"   - {ev['event_date']}: {ev['headline']} (confidence={ev.get('confidence','?')}/{'100'}, conviction={ev.get('conviction_score','?')}/100)\n"

    if news:
        prompt += f"\n\n2. NEWS EVENTS ({len(news)} tracked):\n"
        for ev in news[:10]:
            prompt += f"   - {ev['event_date']} [{ev.get('category','?')}]: {ev['headline']} (sentiment={ev.get('sentiment_score','?')}, conviction={ev.get('conviction_score','?')}/100)\n"

    if product_dev:
        prompt += f"\n\n3. PRODUCT DEVELOPMENT ({len(product_dev)} tracked):\n"
        for ev in product_dev[:10]:
            prompt += f"   - {ev['event_date']} [{ev['lifecycle_stage']}] {ev['product_name']}: {ev['headline']} (conviction={ev.get('conviction_score','?')}/100)\n"

    if regulatory:
        prompt += f"\n\n4. REGULATORY ({len(regulatory)} tracked):\n"
        for ev in regulatory[:10]:
            prompt += f"   - {ev['event_date']} [{ev.get('regulatory_type','?')}] {ev.get('jurisdiction','?')}: {ev['headline']} (status={ev.get('status','?')}, conviction={ev.get('conviction_score','?')}/100)\n"

    prompt += f"""
TASK:
Analyze {symbol} based on the above tracked events. Provide:

1. A brief investment thesis summary (2-3 sentences)
2. An overall conviction score (-100 to +100, where positive = favorable)
3. Any NEW events you would add to the tracking tables (headline, date, category, conviction)
4. Any EXISTING events whose conviction score should be updated

Respond in JSON format:
{{
  "thesis_summary": "string",
  "conviction_score": number,
  "new_events": [
    {{"table": "news_events", "headline": "string", "date": "YYYY-MM-DD", "category": "earnings|product_launch|regulatory|executive|financial|market|other", "conviction": number}}
  ],
  "updated_events": [
    {{"table": "news_events", "headline_match": "string (first 100 chars of existing headline)", "new_conviction": number}}
  ]
}}

If you have no new events or updates, return empty arrays.
"""
    return prompt


def parse_llm_response(response_text: str) -> Dict[str, Any]:
    """Parse LLM JSON response, falling back to empty result on failure."""
    import json as json_mod
    # Try to extract JSON from the response
    try:
        # Find JSON object boundaries
        start = response_text.find("{")
        end = response_text.rfind("}")
        if start >= 0 and end > start:
            json_str = response_text[start:end+1]
            return json_mod.loads(json_str)
    except (json_mod.JSONDecodeError, ValueError):
        pass

    # Fallback: try whole response as JSON
    try:
        return json_mod.loads(response_text)
    except (json_mod.JSONDecodeError, ValueError):
        logger.warning("Failed to parse LLM response as JSON: %s", response_text[:200])
        return {
            "thesis_summary": response_text[:500],
            "conviction_score": 0.0,
            "new_events": [],
            "updated_events": [],
        }


def apply_llm_findings(db, symbol: str, parsed: Dict[str, Any]) -> Dict[str, int]:
    """Apply LLM findings to the database. Returns counts by action type."""
    counts = {"new_inserted": 0, "updated": 0, "errors": 0}

    # Update evalsummary thesis if we have one
    thesis = parsed.get("thesis_summary", "").strip()
    conviction = parsed.get("conviction_score", 0.0)
    if thesis:
        try:
            db_execute(
                db,
                "UPDATE evalsummary SET llm_recommendation = :thesis, llm_confidence = :conv "
                "WHERE symbol = :sym AND price_date = (SELECT MAX(price_date) FROM stockprices WHERE symbol = :sym2)",
                (thesis[:1000], conviction, symbol, symbol),
            )
            counts["updated"] += 1
        except Exception as exc:
            logger.error("Failed to update evalsummary for %s: %s", symbol, exc)
            counts["errors"] += 1

    # Insert new events
    for ev in parsed.get("new_events", []):
        try:
            table = ev.get("table", "news_events")
            headline = ev.get("headline", "")[:500]
            evt_date = ev.get("date", str(TODAY))
            conviction_ev = ev.get("conviction", 0.0)
            confidence_ev = max(0, min(100, abs(conviction_ev) * 50))  # heuristic

            if table == "news_events" or table == "llm_news_events":
                category = ev.get("category", "other")
                upsert_news_event(
                    db, symbol, date.fromisoformat(evt_date), headline, "",
                    category=category, confidence=confidence_ev, conviction=conviction_ev,
                )
                counts["new_inserted"] += 1
            elif table == "insider_trading" or table == "llm_insider_trading":
                upsert_insider_event(
                    db, symbol, date.fromisoformat(evt_date), headline, "",
                    confidence=confidence_ev, conviction=conviction_ev,
                )
                counts["new_inserted"] += 1
            elif table == "product_dev" or table == "llm_product_dev":
                upsert_product_dev_event(
                    db, symbol, ev.get("product_name", ""), ev.get("lifecycle_stage", "concept"),
                    date.fromisoformat(evt_date), headline, "",
                    confidence=confidence_ev, conviction=conviction_ev,
                )
                counts["new_inserted"] += 1
            elif table == "regulatory" or table == "llm_regulatory":
                upsert_regulatory_event(
                    db, symbol, date.fromisoformat(evt_date), headline, "",
                    ev.get("regulatory_type", "other"), "",
                    confidence=confidence_ev, conviction=conviction_ev,
                )
                counts["new_inserted"] += 1
        except Exception as exc:
            logger.error("Failed to insert new event for %s: %s", symbol, exc)
            counts["errors"] += 1

    # Update existing events' conviction
    for ev in parsed.get("updated_events", []):
        try:
            table = ev.get("table", "news_events")
            headline_match = ev.get("headline_match", "")[:100]
            new_conviction = ev.get("new_conviction", 0.0)
            confidence_ev = max(0, min(100, abs(new_conviction) * 50))

            if table in ("news_events", "llm_news_events"):
                existing = db_query(
                    db,
                    f"SELECT id FROM {TABLETYPES['news']} WHERE symbol = :sym AND LEFT(headline,100) = :hl",
                    (symbol, headline_match),
                )
                if existing:
                    db_execute(
                        db,
                        f"UPDATE {TABLETYPES['news']} SET conviction_score = :conv, "
                        f"confidence = :conf, updated_at = NOW() WHERE id = :id",
                        (new_conviction, confidence_ev, existing[0]["id"]),
                    )
                    counts["updated"] += 1
            elif table in ("insider_trading", "llm_insider_trading"):
                existing = db_query(
                    db,
                    f"SELECT id FROM {TABLETYPES['insider']} WHERE symbol = :sym AND LEFT(headline,100) = :hl",
                    (symbol, headline_match),
                )
                if existing:
                    db_execute(
                        db,
                        f"UPDATE {TABLETYPES['insider']} SET conviction_score = :conv, "
                        f"confidence = :conf, updated_at = NOW() WHERE id = :id",
                        (new_conviction, confidence_ev, existing[0]["id"]),
                    )
                    counts["updated"] += 1
        except Exception as exc:
            logger.error("Failed to update event for %s: %s", symbol, exc)
            counts["errors"] += 1

    return counts


# ---------------------------------------------------------------------------
# Main analysis run
# ---------------------------------------------------------------------------

def analyze_symbol(db, symbol: str, llm_client: LlmClient,
                   advisor_profile: str = "primary") -> Dict[str, Any]:
    """
    Run full LLM fundamental analysis for a single symbol.

    Steps:
    1. Read existing llm_* data for symbol
    2. Build prompt with context
    3. Call LLM via fallback chain
    4. Parse response
    5. Apply findings to DB
    6. Return summary
    """
    logger.info("Analyzing %s (profile=%s)...", symbol, advisor_profile)

    # Step 1: Read existing data
    existing = {
        "insider_trading": read_insider_trading(db, symbol),
        "news_events": read_news_events(db, symbol),
        "product_dev": read_product_dev(db, symbol),
        "regulatory": read_regulatory(db, symbol),
    }
    total_existing = sum(len(v) for v in existing.values())
    logger.info("  Found %d existing tracked events for %s", total_existing, symbol)

    # Step 2: Build prompt
    prompt = build_llm_prompt(symbol, existing)

    # Step 3: Call LLM
    response_text, endpoint_used = llm_client.chat(prompt)
    if response_text is None:
        logger.error("  LLM call failed for %s (all endpoints exhausted)", symbol)
        return {
            "symbol": symbol,
            "success": False,
            "error": "LLM call failed — all endpoints exhausted",
            "endpoint_used": endpoint_used,
        }

    logger.info("  LLM response received via %s endpoint", endpoint_used)

    # Step 4: Parse
    parsed = parse_llm_response(response_text)
    thesis = parsed.get("thesis_summary", "")[:100]
    logger.info("  Thesis: %s... (conviction=%s)", thesis, parsed.get("conviction_score", "N/A"))

    # Step 5: Apply
    counts = apply_llm_findings(db, symbol, parsed)
    logger.info("  Applied: %d new events inserted, %d updated, %d errors",
                counts["new_inserted"], counts["updated"], counts["errors"])

    return {
        "symbol": symbol,
        "success": True,
        "endpoint_used": endpoint_used,
        "conviction_score": parsed.get("conviction_score", 0.0),
        "thesis_summary": parsed.get("thesis_summary", ""),
        "new_events_inserted": counts["new_inserted"],
        "events_updated": counts["updated"],
        "errors": counts["errors"],
    }


def analyze_multiple(db, symbols: List[str], llm_client: LlmClient,
                     advisor_profile: str = "primary", dry_run: bool = False) -> List[Dict]:
    """Analyze multiple symbols sequentially."""
    results = []
    for i, sym in enumerate(symbols, 1):
        logger.info("=== %d/%d: %s ===", i, len(symbols), sym)
        try:
            result = analyze_symbol(db, sym, llm_client, advisor_profile)
            results.append(result)
        except Exception as exc:
            logger.exception("Unexpected error analyzing %s: %s", sym, exc)
            results.append({
                "symbol": sym,
                "success": False,
                "error": str(exc),
                "endpoint_used": None,
            })
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LLM Fundamental Analyzer")
    parser.add_argument("--symbol", "-s", help="Single symbol to analyze (e.g. RY.TO)")
    parser.add_argument("--top", "-n", type=int, help="Analyze top N symbols by market cap")
    parser.add_argument("--all", action="store_true", help="Analyze all active symbols")
    parser.add_argument("--dry-run", action="store_true", help="Build prompts but don't call LLM or write DB")
    parser.add_argument("--profile", default="primary", choices=["primary", "secondary", "fallback"],
                        help="LLM endpoint profile to use")
    parser.add_argument("--review-flagged", action="store_true",
                        help="List old unverified low-confidence events for human review")
    args = parser.parse_args()

    # Import DB connector
    try:
        from python.db_connector import get_connection
        db = get_connection()
    except ImportError:
        # Fallback for standalone runs
        import pymysql
        db = pymysql.connect(
            host=os.environ.get("DB_HOST", "ksfraser.ca"),
            database=os.environ.get("DB_NAME", "ksfraser_stock_market"),
            user=os.environ.get("DB_USER", ""),
            password=os.environ.get("DB_PASS", ""),
            charset="utf8mb4",
            autocommit=True,
        )

    # Initialize LLM client
    llm = LlmClient(db)

    if args.review_flagged:
        flagged = flag_old_unverified_low_confidence(db)
        print(f"\n=== Flagged for Review ({len(flagged)} events) ===")
        for row in flagged:
            print(f"  {row['table_name']} | {row['symbol']} | {row['event_date']} | "
                  f"confidence={row['confidence']}/100 | id={row['id']}")
        return

    # Determine symbol list
    symbols: List[str] = []
    if args.symbol:
        symbols = [args.symbol]
    elif args.top:
        try:
            rows = db_query(db, """
                SELECT sm.symbol FROM symbol_master sm
                LEFT JOIN stockprices sp ON sp.symbol = sm.symbol
                AND sp.price_date = (SELECT MAX(price_date) FROM stockprices WHERE symbol = sm.symbol)
                WHERE sm.is_active = 1
                ORDER BY sm.market_cap DESC
                LIMIT %s
            """, (args.top,))
            symbols = [r["symbol"] for r in rows]
        except Exception as exc:
            logger.error("Failed to fetch top symbols: %s", exc)
            rows = db_query(db, "SELECT symbol FROM symbol_master WHERE is_active = 1 LIMIT %s", (args.top,))
            symbols = [r["symbol"] for r in rows]
    elif args.all:
        rows = db_query(db, "SELECT symbol FROM symbol_master WHERE is_active = 1 ORDER BY symbol")
        symbols = [r["symbol"] for r in rows]
    else:
        parser.error("Specify --symbol, --top, or --all")

    if not symbols:
        logger.warning("No symbols to analyze.")
        return

    logger.info("Analyzing %d symbols with profile='%s' (dry_run=%s)...", len(symbols), args.profile, args.dry_run)

    if args.dry_run:
        for sym in symbols[:5]:
            existing = {
                "insider_trading": read_insider_trading(db, sym),
                "news_events": read_news_events(db, sym),
                "product_dev": read_product_dev(db, sym),
                "regulatory": read_regulatory(db, sym),
            }
            prompt = build_llm_prompt(sym, existing)
            print(f"\n--- Prompt for {sym} ({len(existing['news_events'])} news, {len(existing['insider_trading'])} insider events) ---")
            print(prompt[:500] + "...")
        logger.info("Dry run complete. %d prompts would be sent.", len(symbols))
        return

    results = analyze_multiple(db, symbols, llm, args.profile, dry_run=False)

    # Summary
    success_count = sum(1 for r in results if r.get("success"))
    new_total = sum(r.get("new_events_inserted", 0) for r in results)
    updated_total = sum(r.get("events_updated", 0) for r in results)
    error_count = sum(1 for r in results if not r.get("success"))

    print(f"\n=== Analysis Complete ===")
    print(f"  Symbols analyzed: {len(symbols)}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {error_count}")
    print(f"  New events inserted: {new_total}")
    print(f"  Events updated: {updated_total}")
    if results:
        print(f"\n  First result: {results[0]}")


if __name__ == "__main__":
    main()
