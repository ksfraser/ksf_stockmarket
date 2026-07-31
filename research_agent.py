#!/usr/bin/env python3
"""
research_agent.py — Strategy Research & Brief Generator
======================================================
Two modes:
  1. Internal brief: uses existing MariaDB data (ATR sweep, eval scores, fundamentals)
  2. External brief: scans Reddit/TradingView/arXiv/YouTube for new strategy ideas,
     LLM-scores them on novelty/feasibility/edge, and writes source-linked briefs.

Outputs:
  - MariaDB table: research_briefs
  - Markdown: memory/institutional/research-brief-YYYY-MM-DD.md
  - JSON: memory/institutional/research-brief-YYYY-MM-DD.json

Usage:
  python3 research_agent.py --mode internal
  python3 research_agent.py --mode external --limit 20
  python3 research_agent.py --mode both
"""

import argparse
import json
import logging
import os
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional

import mysql.connector
from mysql.connector import Error as MySQLError
import requests

from db_connector import get_connection


class _HermesJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (Decimal,)):
            return float(obj)
        return super().default(obj)

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
MEMORY_DIR = BASE_DIR / "memory" / "institutional"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

DB_TABLE = "research_briefs"
TODAY = date.today().isoformat()

# External source defaults
REDDIT_USER_AGENT = "StockResearchAgent/1.0 (by /u/ksfraser)"
TRADINGVIEW_IDEAS_URL = "https://www.tradingview.com/ideas/"
ARXIV_QUANT_URL = "http://export.arxiv.org/api/query?search_query=cat:q-fin&sortBy=lastUpdatedDate&sortOrder=descending&max_results=10"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# ==========================================================================
# DATABASE HELPERS
# ==========================================================================

def _ensure_table(conn: Any) -> None:
    """Create research_briefs table if it does not exist."""
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS `{DB_TABLE}` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `symbol` VARCHAR(32) DEFAULT NULL,
            `brief_date` DATE NOT NULL,
            `mode` ENUM('internal','external','both') NOT NULL,
            `category` VARCHAR(64) DEFAULT 'general',
            `title` VARCHAR(255) NOT NULL,
            `summary` TEXT,
            `source_url` VARCHAR(1024) DEFAULT NULL,
            `scores` JSON DEFAULT NULL,
            `recommendation` VARCHAR(255) DEFAULT NULL,
            `raw_data` JSON DEFAULT NULL,
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY `uniq_brief` (`brief_date`, `mode`, `category`, `title`(191))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    conn.commit()
    cursor.close()


def save_brief(
    conn: Any,
    *,
    mode: str,
    category: str,
    title: str,
    summary: str,
    symbol: Optional[str] = None,
    source_url: Optional[str] = None,
    scores: Optional[Dict[str, Any]] = None,
    recommendation: Optional[str] = None,
    raw_data: Optional[Dict[str, Any]] = None,
) -> None:
    """INSERT ... ON DUPLICATE KEY UPDATE a research brief."""
    sql = f"""
        INSERT INTO `{DB_TABLE}`
          (`brief_date`, `mode`, `category`, `title`, `summary`, `symbol`,
           `source_url`, `scores`, `recommendation`, `raw_data`)
        VALUES (%(brief_date)s, %(mode)s, %(category)s, %(title)s, %(summary)s,
                %(symbol)s, %(source_url)s, %(scores)s, %(recommendation)s, %(raw_data)s)
        ON DUPLICATE KEY UPDATE
          `summary` = VALUES(`summary`),
          `scores` = VALUES(`scores`),
          `recommendation` = VALUES(`recommendation`),
          `raw_data` = VALUES(`raw_data`),
          `source_url` = VALUES(`source_url`)
    """
    params = {
        "brief_date": TODAY,
        "mode": mode,
        "category": category,
        "title": title,
        "summary": summary,
        "symbol": symbol,
        "source_url": source_url,
        "scores": json.dumps(scores, cls=_HermesJSONEncoder) if scores else None,
        "recommendation": recommendation,
        "raw_data": json.dumps(raw_data, cls=_HermesJSONEncoder) if raw_data else None,
    }
    with conn.cursor() as cur:
        cur.execute(sql, params)
    conn.commit()


# ==========================================================================
# INTERNAL BRIEF MODE
# ==========================================================================

def fetch_atr_top_results(conn: Any, limit: int = 10) -> List[Dict[str, Any]]:
    """Best ATR stop-optimization combos by PnL across all symbols."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"""
        SELECT symbol, stop_factor, trailing_pct, pnl_pct, n_trades
        FROM `atr_stop_optimization`
        WHERE pnl_pct IS NOT NULL
        ORDER BY pnl_pct DESC
        LIMIT {int(limit)}
    """)
    rows = cursor.fetchall()
    cursor.close()
    return rows


def fetch_eval_summary(conn: Any, limit: int = 20) -> List[Dict[str, Any]]:
    """Latest evalsummary rows with strategy_json."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT symbol, price_date, close,
               consensus_signal, consensus_strength,
               atr_position_size, portfolio_weight, strategy_json
        FROM `evalsummary`
        WHERE price_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        ORDER BY price_date DESC
        LIMIT %s
    """, (limit,))
    rows = cursor.fetchall()
    cursor.close()
    return rows


def fetch_fundamental_scores(conn: Any, limit: int = 20) -> List[Dict[str, Any]]:
    """Latest motleyfool/tenets scores per symbol."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT m.symbol, m.score AS mf_score, m.lastupdate,
               (SELECT COUNT(*) FROM tenets t WHERE t.symbol=m.symbol AND t.passed=1) AS tenets_passed
        FROM motleyfool m
        WHERE m.lastupdate >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        ORDER BY m.score DESC
        LIMIT %s
    """, (limit,))
    rows = cursor.fetchall()
    cursor.close()
    return rows


def build_internal_brief(conn: Any) -> Dict[str, Any]:
    """Aggregate internal system data into a brief dict."""
    atr_top = fetch_atr_top_results(conn)
    eval_rows = fetch_eval_summary(conn)
    fund_rows = fetch_fundamental_scores(conn)

    sections: List[str] = []
    sections.append("# Internal Strategy Brief — " + TODAY + "\n")

    if atr_top:
        sections.append("## ATR Stop Optimization Leaders\n")
        for r in atr_top[:5]:
            sections.append(
                f"- **{r['symbol']}** stop={r['stop_factor']}× "
                f"trailing={r['trailing_pct']}% → PnL {r['pnl_pct']:.2f}% "
                f"({r['n_trades']} trades)"
            )
        sections.append("")

    if eval_rows:
        sections.append("## Recent Evaluation Signals\n")
        for r in eval_rows[:10]:
            sig = r.get("consensus_signal")
            sig_str = {1: "BUY", 2: "SELL", 3: "HOLD"}.get(sig, str(sig))
            sections.append(
                f"- **{r['symbol']}** {sig_str} "
                f"(strength {r.get('consensus_strength')}) "
                f"ATR size {r.get('atr_position_size')}% "
                f"weight {r.get('portfolio_weight')}%"
            )
        sections.append("")

    if fund_rows:
        sections.append("## Fundamental Score Leaders\n")
        for r in fund_rows[:10]:
            sections.append(
                f"- **{r['symbol']}** MF score {r['mf_score']} "
                f"tenets passed {r['tenets_passed']} "
                f"(as of {r.get('lastupdate')})"
            )
        sections.append("")

    summary = "\n".join(sections)
    return {
        "mode": "internal",
        "category": "internal",
        "title": f"Internal Brief — {TODAY}",
        "summary": summary,
        "source_url": None,
        "scores": {
            "atr_symbols": len(atr_top),
            "eval_signals": len(eval_rows),
            "fundamentals": len(fund_rows),
        },
        "recommendation": "Review ATR leaders and eval signals for candidate trades.",
        "raw_data": {
            "atr_top": atr_top[:10],
            "eval_rows": [
                {k: (v.isoformat() if hasattr(v, "isoformat") else v)
                 for k, v in r.items()}
                for r in eval_rows[:10]
            ],
            "fund_rows": [
                {k: (v.isoformat() if hasattr(v, "isoformat") else v)
                 for k, v in r.items()}
                for r in fund_rows[:10]
            ],
        },
    }


# ==========================================================================
# EXTERNAL BRIEF MODE
# ==========================================================================

def _get_reddit_token(conn: Any) -> Optional[str]:
    """Return a valid Reddit OAuth access token from external_auth_tokens."""
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT access_token, refresh_token, expires_at
            FROM external_auth_tokens
            WHERE provider = 'reddit' AND is_active = 1
            ORDER BY updated_at DESC
            LIMIT 1
        """)
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        access_token, _refresh_token, expires_at = row
        now = datetime.now()
        if expires_at:
            if isinstance(expires_at, datetime):
                if expires_at > now - timedelta(minutes=5):
                    return access_token
            elif isinstance(expires_at, str):
                parsed = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
                if parsed > now - timedelta(minutes=5):
                    return access_token
        return access_token
    except Exception as exc:
        logger.debug(f"No Reddit token available: {exc}")
        return None


def _reddit_search(conn: Any, subreddits: List[str], limit: int = 20) -> List[Dict[str, str]]:
    """Search Reddit for quant/algotrading posts."""
    results: List[Dict[str, str]] = []
    access_token = _get_reddit_token(conn)

    if access_token:
        headers = {
            "Authorization": f"bearer {access_token}",
            "User-Agent": REDDIT_USER_AGENT,
        }
    else:
        headers = {"User-Agent": REDDIT_USER_AGENT}

    for sub in subreddits:
        try:
            if access_token:
                url = f"https://oauth.reddit.com/r/{sub}/hot.json?limit={limit}"
            else:
                url = f"https://www.reddit.com/r/{sub}/hot.json?limit={limit}"
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                logger.warning(f"Reddit {sub} returned {resp.status_code}")
                continue
            data = resp.json().get("data", {}).get("children", [])
            for child in data:
                post = child.get("data", {})
                title = post.get("title", "")
                permalink = post.get("permalink", "")
                if title and permalink:
                    results.append({
                        "source": f"reddit/r/{sub}",
                        "title": title,
                        "url": f"https://reddit.com{permalink}",
                    })
        except Exception as exc:
            logger.warning(f"Reddit {sub} fetch failed: {exc}")
    return results


def _arxiv_quant(limit: int = 20) -> List[Dict[str, str]]:
    """Fetch recent quant finance arXiv papers."""
    results: List[Dict[str, str]] = []
    try:
        resp = requests.get(ARXIV_QUANT_URL, timeout=20)
        if resp.status_code != 200:
            logger.warning(f"arXiv returned {resp.status_code}")
            return results
        # Minimal XML parsing without external deps
        text = resp.text
        import re
        entries = re.findall(r"<entry>(.*?)</entry>", text, re.DOTALL)
        for entry in entries[:limit]:
            title_m = re.search(r"<title>(.*?)</title>", entry, re.DOTALL)
            link_m = re.search(r"<id>(.*?)</id>", entry, re.DOTALL)
            if title_m and link_m:
                results.append({
                    "source": "arxiv/q-fin",
                    "title": title_m.group(1).strip().replace("\n", " "),
                    "url": link_m.group(1).strip(),
                })
    except Exception as exc:
        logger.warning(f"arXiv fetch failed: {exc}")
    return results


def _tradingview_ideas(limit: int = 20) -> List[Dict[str, str]]:
    """
    Placeholder for TradingView ideas.
    TradingView does not offer a public unauthenticated ideas API.
    This stub returns empty; plug in TradingView MCP or authenticated
    endpoint when available.
    """
    logger.info("TradingView ideas scraping skipped — no public API.")
    return []


# ==========================================================================
# YOUTUBE STRATEGY AGENT (from yt-strategy-agent)
# ==========================================================================

_YOUTUBE_EXTRACTION_SYSTEM = """You are a trading-strategy analyst. You read transcripts of trading and investing YouTube videos and extract a structured representation of the host's strategy: what they buy, what they sell, how they manage risk, how they time entries and exits, and any specific trades they describe executing.

You return ONLY valid JSON matching this exact schema:

{
  "strategy_summary": "string — 2-4 sentences describing the host's overall approach in this video",
  "buy_rules":    [{"rule": "string", "confidence": 0.0-1.0, "source_quote": "string"}],
  "sell_rules":   [{"rule": "string", "confidence": 0.0-1.0, "source_quote": "string"}],
  "risk_notes":   [{"note": "string", "confidence": 0.0-1.0, "source_quote": "string"}],
  "timing_notes": [{"note": "string", "confidence": 0.0-1.0, "source_quote": "string"}],
  "executed_trades": [
    {"asset": "string", "direction": "long|short", "entry": "string", "exit": "string", "outcome": "string"}
  ],
  "strategy_shift": {"changed": false, "what_changed": "string", "vs_prior": "string"}
}

Rules:
- Each rule/note must be a concrete, actionable statement, not a vague observation.
- `confidence` reflects how clearly and emphatically the host states the rule (0.9+ for explicit "always do X", 0.5 for offhand suggestions, <0.3 for speculation).
- `source_quote` must be a verbatim snippet from the transcript (≤200 chars).
- If the host mentions changing their mind from a previous position, set strategy_shift.changed = true.
- If a section has no relevant content, return an empty array.
- Return JSON only, no markdown fences, no commentary."""

_IMPACT_SYSTEM = """You are a trading-strategy reviewer. The user runs a paper-trading system that reads a "strategy spec" markdown file and executes signals.

Given (a) the spec, (b) a fresh extraction from a new video by the same host, write a 3-5 sentence brief covering:
1. Whether this video changes the spec's bias (long / flat / short).
2. Whether any explicit invalidation level mentioned in the spec is now closer or further from triggering.
3. Whether tranche size, entry zones, or take-profit levels need adjusting based on what the host said.
4. One concrete action (or "no action — bias intact") for the next 24 hours.

Be plain-spoken, no hedging adverbs. Do not invent numbers the host didn't say."""


def _youtube_transcript_fetch(video_ids: List[str], apify_token: str) -> Dict[str, Optional[str]]:
    """Fetch transcripts via Apify actor karamelo/youtube-transcripts."""
    if not video_ids:
        return {}
    try:
        from apify_client import ApifyClient
    except ImportError:
        logger.warning("apify-client not installed; run: pip install apify-client")
        return {vid: None for vid in video_ids}

    client = ApifyClient(apify_token)
    urls = [f"https://www.youtube.com/watch?v={vid}" for vid in video_ids]
    out: Dict[str, Optional[str]] = {vid: None for vid in video_ids}
    try:
        run = client.actor("karamelo/youtube-transcripts").call(
            run_input={
                "urls": urls,
                "outputFormat": "singleStringText",
                "maxRetries": 8,
                "channelIDBoolean": True,
                "datePublishedBoolean": True,
            }
        )
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            vid = item.get("videoId")
            captions = item.get("captions") or ""
            if vid and captions:
                import html as _html
                out[vid] = _html.unescape(captions).strip()
    except Exception as exc:
        logger.warning("Apify transcript fetch failed: %s", exc)
    return out


def _youtube_extract_transcript(transcript: str, video_title: str) -> Dict[str, Any]:
    """Extract structured strategy JSON from a transcript via the configured LLM."""
    api_key = _get_system_setting(None, "llm_api_key", "")
    if not api_key:
        return {"strategy_summary": "", "buy_rules": [], "sell_rules": [], "risk_notes": [], "timing_notes": [], "executed_trades": [], "strategy_shift": {"changed": False}}

    provider = _get_system_setting(None, "llm_provider", "openrouter").strip().lower()
    model = _get_system_setting(None, "llm_model", "anthropic/claude-sonnet-4").strip()
    base_url = _get_system_setting(None, "llm_base_url", "").strip()
    if not base_url:
        base_url = {
            "openrouter": "https://openrouter.ai/api/v1",
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com",
            "ollama": "http://localhost:11434",
            "google": "https://generativelanguage.googleapis.com/v1beta",
        }.get(provider, "https://openrouter.ai/api/v1")

    user_prompt = (
        f"Video title: {video_title}\n\n"
        f"Transcript:\n{transcript[:60000]}\n\n"
        "Extract the structured strategy JSON now."
    )

    try:
        if provider == "anthropic":
            url = base_url.rstrip("/") + "/v1/messages"
            headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
            payload = {
                "model": model,
                "max_tokens": 1024,
                "system": [{"type": "text", "text": _YOUTUBE_EXTRACTION_SYSTEM, "cache_control": {"type": "ephemeral"}}],
                "messages": [{"role": "user", "content": user_prompt}],
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            body = resp.json()
            text = "".join(block.text for block in body.get("content", []) if hasattr(block, "text"))
        else:
            url = base_url.rstrip("/") + "/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": model,
                "max_tokens": 1024,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": _YOUTUBE_EXTRACTION_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            body = resp.json()
            text = body.get("choices", [{}])[0].get("message", {}).get("content", "")

        text = text.strip()
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip().rstrip("`").strip()
        return json.loads(text)
    except Exception as exc:
        logger.warning("YouTube extraction failed for '%s': %s", video_title, exc)
        return {"strategy_summary": "", "buy_rules": [], "sell_rules": [], "risk_notes": [], "timing_notes": [], "executed_trades": [], "strategy_shift": {"changed": False}, "error": str(exc)[:200]}


def _youtube_impact_summary(extraction: Dict[str, Any], video_title: str, strategy_spec: str) -> str:
    """Summarize the impact of a new video on the current paper-trading spec."""
    api_key = _get_system_setting(None, "llm_api_key", "")
    if not api_key:
        return "(impact summary skipped — no LLM API key)"

    provider = _get_system_setting(None, "llm_provider", "openrouter").strip().lower()
    model = _get_system_setting(None, "llm_model", "anthropic/claude-sonnet-4").strip()
    base_url = _get_system_setting(None, "llm_base_url", "").strip()
    if not base_url:
        base_url = {
            "openrouter": "https://openrouter.ai/api/v1",
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com",
            "ollama": "http://localhost:11434",
            "google": "https://generativelanguage.googleapis.com/v1beta",
        }.get(provider, "https://openrouter.ai/api/v1")

    spec_block = f"Current spec:\n{strategy_spec.strip()}\n\n" if strategy_spec else "(No paper-trading spec exists yet for this channel — return: 'No tradable spec for this channel; this video updates the macro view only.')\n\n"
    user_prompt = spec_block + f"New video: {video_title}\n\nExtracted JSON:\n{json.dumps(extraction, indent=2)}\n\nWrite the brief now."

    try:
        if provider == "anthropic":
            url = base_url.rstrip("/") + "/v1/messages"
            headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
            payload = {
                "model": model,
                "max_tokens": 600,
                "system": [{"type": "text", "text": _IMPACT_SYSTEM, "cache_control": {"type": "ephemeral"}}],
                "messages": [{"role": "user", "content": user_prompt}],
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            body = resp.json()
            return "".join(block.text for block in body.get("content", []) if hasattr(block, "text")).strip()
        else:
            url = base_url.rstrip("/") + "/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": model,
                "max_tokens": 600,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": _IMPACT_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            body = resp.json()
            return body.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    except Exception as exc:
        return f"(impact summary failed: {exc})"


def _youtube_channel_search(channel_handles: List[str], limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search YouTube for latest videos from given channels, fetch transcripts,
    extract structured strategies, and return them as research items.
    """
    youtube_api_key = _get_system_setting(None, "youtube_api_key", "")
    apify_token = _get_system_setting(None, "apify_token", "")
    if not youtube_api_key or not apify_token:
        logger.info("YouTube API key or Apify token not configured — skipping YouTube scan.")
        return []

    results: List[Dict[str, Any]] = []
    try:
        from googleapiclient.discovery import build
    except ImportError:
        logger.warning("google-api-python-client not installed; run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        return results

    try:
        yt = build("youtube", "v3", developerKey=youtube_api_key)
        for handle in channel_handles:
            handle = handle.strip().lstrip("@")
            if not handle:
                continue
            # Resolve channel ID from handle
            try:
                search_resp = yt.search().list(q=handle, type="channel", part="id,snippet", maxResults=1).execute()
                channel_id = search_resp.get("items", [{}])[0].get("id", {}).get("channelId")
                if not channel_id:
                    continue
                channel_title = search_resp.get("items", [{}])[0].get("snippet", {}).get("title", handle)
            except Exception as exc:
                logger.warning("YouTube channel lookup failed for @%s: %s", handle, exc)
                continue

            # Get uploads playlist
            try:
                uploads_resp = yt.channels().list(id=channel_id, part="contentDetails").execute()
                uploads_playlist = uploads_resp.get("items", [{}])[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
                if not uploads_playlist:
                    continue
            except Exception:
                continue

            # Fetch latest videos
            try:
                pl_items = yt.playlistItems().list(part="snippet,contentDetails", playlistId=uploads_playlist, maxResults=limit).execute()
                videos = [
                    {
                        "video_id": item["contentDetails"]["videoId"],
                        "title": item["snippet"]["title"],
                        "published_at": item["contentDetails"].get("videoPublishedAt") or item["snippet"]["publishedAt"],
                    }
                    for item in pl_items.get("items", [])
                ]
            except Exception as exc:
                logger.warning("YouTube playlist fetch failed for @%s: %s", handle, exc)
                continue

            # Fetch transcripts
            transcripts = _youtube_transcript_fetch([v["video_id"] for v in videos], apify_token)

            for video in videos:
                vid = video["video_id"]
                transcript = transcripts.get(vid)
                if not transcript:
                    continue
                extraction = _youtube_extract_transcript(transcript, video["title"])
                # Build a research item compatible with the rest of the pipeline
                item: Dict[str, Any] = {
                    "title": video["title"],
                    "source": "youtube",
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "channel_handle": handle,
                    "channel_title": channel_title,
                    "published_at": video["published_at"],
                    "extraction": extraction,
                }
                results.append(item)
    except Exception as exc:
        logger.warning("YouTube channel scan failed: %s", exc)

    return results


# ==========================================================================
# RECENCY WEIGHTING (from yt-strategy-agent)
# ==========================================================================

_YOUTUBE_WEIGHTS = [1.00, 0.70, 0.50, 0.35, 0.25]
_YOUTUBE_MIN_CONFIDENCE = 0.30
_YOUTUBE_SIMILARITY_THRESHOLD = 0.82


def _recency_weighted_rules(extractions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Merge a rolling window of YouTube extractions using recency weighting
    and cosine-similarity grouping. Returns a unified rules dict.
    """
    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.warning("sentence-transformers or numpy not installed; skipping recency weighting.")
        if extractions:
            return extractions[0]
        return {"strategy_summary": "", "buy_rules": [], "sell_rules": [], "risk_notes": [], "timing_notes": []}

    model = SentenceTransformer("all-MiniLM-L6-v2")

    def _embed(texts: List[str]) -> Any:
        if not texts:
            return np.zeros((0, 384))
        return model.encode(texts, normalize_embeddings=True, show_progress_bar=False)

    def _rebuild_section(section_items_per_video: List[List[Dict]], text_key: str) -> List[Dict]:
        flat: List[Dict] = []
        for video_idx, items in enumerate(section_items_per_video):
            weight = _YOUTUBE_WEIGHTS[video_idx] if video_idx < len(_YOUTUBE_WEIGHTS) else 0.0
            for item in items or []:
                flat.append({
                    "text": item.get(text_key, "").strip(),
                    "raw_confidence": float(item.get("confidence", 0.5)),
                    "weight": weight,
                    "source_quote": item.get("source_quote", ""),
                    "video_idx": video_idx,
                })
        flat = [f for f in flat if f["text"]]
        if not flat:
            return []

        # Group by similarity
        embs = _embed([f["text"] for f in flat])
        groups: List[List[int]] = []
        centroids: List[Any] = []
        for i, emb in enumerate(embs):
            placed = False
            for gi, centroid in enumerate(centroids):
                if float(np.dot(emb, centroid)) >= _YOUTUBE_SIMILARITY_THRESHOLD:
                    groups[gi].append(i)
                    members = np.stack([embs[j] for j in groups[gi]])
                    centroids[gi] = members.mean(axis=0)
                    centroids[gi] /= np.linalg.norm(centroids[gi]) + 1e-9
                    placed = True
                    break
            if not placed:
                groups.append([i])
                centroids.append(emb)

        out = []
        for group in groups:
            weights = [g["weight"] for g in group]
            confs = [g["raw_confidence"] * g["weight"] for g in group]
            eff = sum(confs) / max(sum(weights), 1e-9)
            if eff < _YOUTUBE_MIN_CONFIDENCE:
                continue
            canonical = max(group, key=lambda g: g["raw_confidence"] * g["weight"])
            out.append({
                "text": canonical["text"],
                "effective_confidence": round(eff, 3),
                "source_quote": canonical["source_quote"],
                "appears_in": sorted({g["video_idx"] for g in group}),
            })
        out.sort(key=lambda r: r["effective_confidence"], reverse=True)
        return out

    # Build section lists per extraction
    buy_rules = _rebuild_section([e.get("buy_rules", []) for e in extractions], "rule")
    sell_rules = _rebuild_section([e.get("sell_rules", []) for e in extractions], "rule")
    risk_notes = _rebuild_section([e.get("risk_notes", []) for e in extractions], "note")
    timing_notes = _rebuild_section([e.get("timing_notes", []) for e in extractions], "note")

    summaries = [e.get("strategy_summary", "") for e in extractions if e.get("strategy_summary")]
    return {
        "strategy_summary": summaries[0] if summaries else "",
        "buy_rules": buy_rules,
        "sell_rules": sell_rules,
        "risk_notes": risk_notes,
        "timing_notes": timing_notes,
    }


def _youtube_shift_detect(handle: str, new_extraction: Dict[str, Any], channel_dir_path: str) -> bool:
    """Detect strategy shift using semantic drift + contradiction detection."""
    import numpy as np
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2")
    rules_path = Path(channel_dir_path) / "rules.json"
    prior = json.loads(rules_path.read_text()) if rules_path.exists() else None

    if not prior:
        return False

    triggers: List[str] = []
    prior_summary = prior.get("strategy_summary", "")
    new_summary = new_extraction.get("strategy_summary", "")
    if prior_summary and new_summary:
        embs = model.encode([prior_summary, new_summary], normalize_embeddings=True)
        semantic_distance = 1.0 - float(np.dot(embs[0], embs[1]))
        if semantic_distance > 0.35:
            triggers.append("Strategy summary drifted significantly from prior state.")

    prior_rules = [r["text"] for r in (prior.get("buy_rules", []) + prior.get("sell_rules", [])) if r.get("effective_confidence", 0) >= 0.6]
    new_rules = [r.get("rule", "") for r in (new_extraction.get("buy_rules", []) + new_extraction.get("sell_rules", []))]
    if prior_rules and new_rules:
        embs_prior = model.encode(prior_rules, normalize_embeddings=True)
        embs_new = model.encode(new_rules, normalize_embeddings=True)
        for i, e_new in enumerate(embs_new):
            for j, e_prior in enumerate(embs_prior):
                sim = float(np.dot(e_new, e_prior))
                if 0.55 < sim < 0.78:
                    triggers.append(f'Possible contradiction: new "{new_rules[i]}" vs prior "{prior_rules[j]}"')
                    break

    shift = new_extraction.get("strategy_shift") or {}
    if shift.get("changed"):
        triggers.append(f"Host explicitly noted a shift: {shift.get('what_changed','')} (vs {shift.get('vs_prior','')})")

    if not triggers:
        return False

    changelog_path = Path(channel_dir_path) / "changelog.md"
    header = "" if changelog_path.exists() else "# Strategy changelog\n\n"
    quote = ""
    for src in (new_extraction.get("buy_rules") or []) + (new_extraction.get("sell_rules") or []):
        if src.get("source_quote"):
            quote = src["source_quote"]
            break
    entry = [
        f"## {datetime.now(timezone.utc).date().isoformat()} — {new_extraction.get('title', 'unknown')}",
    ]
    for t in triggers:
        entry.append(f"- {t}")
    if quote:
        entry.append(f'- Triggering quote: "{quote}"')
    with changelog_path.open("a") as fh:
        fh.write(header + "\n".join(entry) + "\n")
    return True


def _get_system_setting(conn: Any, key: str, default: str = "") -> str:
    """Read a value from system_settings via the existing DB connection."""
    try:
        cur = conn.cursor()
        cur.execute("SELECT setting_value FROM system_settings WHERE setting_key = %s", (key,))
        row = cur.fetchone()
        cur.close()
        return row[0] if row else default
    except Exception:
        return default


def score_idea_with_llm(conn: Any, idea: Dict[str, str]) -> Dict[str, Any]:
    """
    Score an external strategy idea via the configured LLM provider.

    Reads provider/model/credentials from system_settings:
      - llm_provider  (e.g. openrouter, openai, anthropic)
      - llm_model
      - llm_api_key
      - llm_base_url

    Falls back to heuristic placeholders when no API key is configured
    or when the provider call fails.
    """
    api_key = _get_system_setting(conn, "llm_api_key", "").strip()
    if not api_key:
        logger.debug("No LLM API key configured — using heuristic scores.")
        return {
            "novelty": 5,
            "feasibility": 5,
            "edge": 5,
            "total": 15,
            "model": "heuristic",
        }

    provider = _get_system_setting(conn, "llm_provider", "openrouter").strip().lower()
    model = _get_system_setting(conn, "llm_model", "anthropic/claude-sonnet-4").strip()
    base_url = _get_system_setting(conn, "llm_base_url", "").strip()

    # Resolve provider base URL if not explicitly set
    if not base_url:
        if provider == "openrouter":
            base_url = "https://openrouter.ai/api/v1"
        elif provider == "openai":
            base_url = "https://api.openai.com/v1"
        elif provider == "anthropic":
            base_url = "https://api.anthropic.com"
        elif provider == "ollama":
            base_url = "http://localhost:11434"
        elif provider == "google":
            base_url = "https://generativelanguage.googleapis.com/v1beta"
        elif provider == "azure":
            base_url = "https://<resource>.openai.azure.com"
        else:
            base_url = "https://openrouter.ai/api/v1"

    prompt = (
        "Score this trading/strategy idea from 1–10 on three axes:\n"
        "  - novelty: how original is the approach?\n"
        "  - feasibility: how implementable is it?\n"
        "  - edge: does it have a plausible alpha edge?\n\n"
        f"Title: {idea.get('title', '')}\n"
        f"Source: {idea.get('source', '')}\n"
        f"URL: {idea.get('url', '')}\n"
    )

    try:
        if provider == "anthropic":
            # Anthropic Messages API
            url = base_url.rstrip("/") + "/v1/messages"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            payload = {
                "model": model,
                "max_tokens": 64,
                "messages": [
                    {"role": "user", "content": prompt + "\nReturn JSON only: {novelty, feasibility, edge, reasoning}."}
                ],
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=20)
            resp.raise_for_status()
            body = resp.json()
            text = body.get("content", [{}])[0].get("text", "")

        elif provider == "ollama":
            # Ollama local chat API
            url = base_url.rstrip("/") + "/api/chat"
            headers = {"content-type": "application/json"}
            payload = {
                "model": model,
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 64},
                "messages": [
                    {"role": "user", "content": prompt + "\nReturn JSON only: {novelty, feasibility, edge, reasoning}."}
                ],
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            body = resp.json()
            text = body.get("message", {}).get("content", "")

        elif provider == "google":
            # Google Generative AI
            url = base_url.rstrip("/") + "/models/" + model + ":generateContent"
            params = {"key": api_key}
            headers = {"content-type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt + "\nReturn JSON only: {novelty, feasibility, edge, reasoning}."}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 64},
            }
            resp = requests.post(url, params=params, json=payload, headers=headers, timeout=20)
            resp.raise_for_status()
            body = resp.json()
            text = (
                body.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )

        else:
            # OpenAI-compatible chat completions (OpenRouter, OpenAI, Azure, etc.)
            if provider == "openrouter":
                url = base_url.rstrip("/") + "/chat/completions"
            elif provider == "azure":
                url = base_url.rstrip("/") + "/openai/deployments/" + model + "/chat/completions?api-version=2024-02-15-preview"
            else:
                url = base_url.rstrip("/") + "/chat/completions"

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "max_tokens": 64,
                "temperature": 0.2,
                "messages": [
                    {"role": "user", "content": prompt + "\nReturn JSON only: {novelty, feasibility, edge, reasoning}."}
                ],
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=20)
            resp.raise_for_status()
            body = resp.json()
            text = body.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Try to parse JSON from model response
        scores: Dict[str, Any] = {}
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                scores = json.loads(text[start : end + 1])
        except Exception:
            scores = {}

        novelty = int(scores.get("novelty", 5))
        feasibility = int(scores.get("feasibility", 5))
        edge = int(scores.get("edge", 5))
        novelty = max(1, min(10, novelty))
        feasibility = max(1, min(10, feasibility))
        edge = max(1, min(10, edge))
        return {
            "novelty": novelty,
            "feasibility": feasibility,
            "edge": edge,
            "total": novelty + feasibility + edge,
            "model": model,
            "provider": provider,
            "reasoning": scores.get("reasoning", ""),
        }

    except Exception as exc:
        logger.warning("LLM scoring failed for idea=%s: %s", idea.get("title", ""), exc)
        return {
            "novelty": 5,
            "feasibility": 5,
            "edge": 5,
            "total": 15,
            "model": "heuristic_fallback",
            "error": str(exc)[:200],
        }


def build_external_brief(conn: Any, limit: int = 20) -> Dict[str, Any]:
    """Scan external sources, score ideas, write brief."""
    reddit_posts = _reddit_search(conn, ["algotrading", "quant", "options", "investing"], limit)
    arxiv_papers = _arxiv_quant(limit // 2)
    tv_ideas = _tradingview_ideas(limit // 2)

    # YouTube strategy channels (from Admin Settings)
    yt_items: List[Dict[str, Any]] = []
    try:
        yt_channels_raw = _get_system_setting(conn, "youtube_watch_channels", "")
        if yt_channels_raw:
            yt_handles = [h.strip() for h in yt_channels_raw.split(",") if h.strip()]
            if yt_handles:
                yt_items = _youtube_channel_search(yt_handles, limit=5)
    except Exception as exc:
        logger.warning("YouTube channel scan failed: %s", exc)

    all_items = reddit_posts + arxiv_papers + tv_ideas + yt_items
    scored: List[Dict[str, Any]] = []
    for item in all_items[:limit]:
        scores = score_idea_with_llm(conn, item)
        scored.append({**item, "scores": scores})

    scored.sort(key=lambda x: x.get("scores", {}).get("total", 0), reverse=True)

    lines = [f"# External Strategy Brief — {TODAY}\n"]
    for s in scored:
        sc = s.get("scores", {})
        source_tag = s.get("source", "external")
        lines.append(
            f"- **{s['title']}** [{source_tag}] "
            f"novelty={sc.get('novelty')} feasibility={sc.get('feasibility')} "
            f"edge={sc.get('edge')} total={sc.get('total')} "
            f"— {s['url']}"
        )
    lines.append("")

    # Append YouTube structured extractions if present
    yt_sections = [i for i in scored if i.get("source") == "youtube" and i.get("extraction")]
    if yt_sections:
        lines.append("## YouTube Strategy Extractions\n")
        for yt in yt_sections:
            ext = yt.get("extraction", {})
            lines.append(f"### {yt['title']} ({yt.get('channel_title', '')}) — {yt.get('published_at', '')}")
            lines.append(f"URL: {yt['url']}")
            lines.append(f"Summary: {ext.get('strategy_summary', '').strip() or '_(none)_'}")
            for section, key in [("Buy rules", "buy_rules"), ("Sell rules", "sell_rules"), ("Risk notes", "risk_notes"), ("Timing notes", "timing_notes")]:
                items = ext.get(key) or []
                lines.append(f"#### {section}")
                if not items:
                    lines.append("_(none)_")
                for it in items:
                    text = it.get("rule") or it.get("note") or ""
                    conf = it.get("confidence", 0.0)
                    quote = (it.get("source_quote") or "").strip()
                    lines.append(f"- ({conf:.2f}) {text}")
                    if quote:
                        lines.append(f"  > {quote}")
                lines.append("")
            trades = ext.get("executed_trades") or []
            lines.append("#### Executed trades")
            if not trades:
                lines.append("_(none)_")
            for t in trades:
                lines.append(
                    f"- {t.get('asset','?')} {t.get('direction','?')} entry {t.get('entry','?')} "
                    f"exit {t.get('exit','?')} → {t.get('outcome','?')}"
                )
            lines.append("")

    summary = "\n".join(lines)
    return {
        "mode": "external",
        "category": "external",
        "title": f"External Brief — {TODAY}",
        "summary": summary,
        "source_url": None,
        "scores": {"items_scored": len(scored), "youtube_extractions": len(yt_sections)},
        "recommendation": "Top-scored ideas should be backtested by the Backtest Agent.",
        "raw_data": scored,
    }


# ==========================================================================
# PERSISTENCE
# ==========================================================================

def write_markdown(brief: Dict[str, Any]) -> Path:
    """Append brief to institutional memory markdown."""
    filepath = MEMORY_DIR / f"research-brief-{TODAY}.md"
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(brief["summary"] + "\n")
    return filepath


def write_json(brief: Dict[str, Any]) -> Path:
    """Write brief as JSON for machine consumption."""
    filepath = MEMORY_DIR / f"research-brief-{TODAY}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(brief, f, indent=2, cls=_HermesJSONEncoder)
    return filepath


# ==========================================================================
# MAIN
# ==========================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="Strategy Research Agent")
    parser.add_argument(
        "--mode",
        choices=["internal", "external", "both"],
        default="internal",
        help="Brief mode",
    )
    parser.add_argument("--limit", type=int, default=20, help="Max external items")
    args = parser.parse_args()

    conn = get_connection()
    if conn is None:
        logger.error("Database connection failed.")
        return 1
    _ensure_table(conn)

    modes = [args.mode] if args.mode != "both" else ["internal", "external"]

    for mode in modes:
        logger.info(f"Building {mode} brief...")
        if mode == "internal":
            brief = build_internal_brief(conn)
        else:
            brief = build_external_brief(conn, limit=args.limit)

        save_brief(conn, **brief)
        md_path = write_markdown(brief)
        json_path = write_json(brief)
        logger.info(f"Saved brief to DB and files: {md_path}, {json_path}")

    conn.close()
    logger.info("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
