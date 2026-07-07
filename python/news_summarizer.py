#!/usr/bin/env python3
"""
news_summarizer.py — Process news through LLM for concise summaries,
fact/opinion classification, sentiment, and actionable recommendations.
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python.db_connector import get_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a financial news analyst. Given the headline and summary of a news article about a stock or market, produce a JSON object with:
  - "summary": a one-sentence concise summary (max 20 words).
  - "classification": one of "fact", "opinion", "analysis". Fact reports verifiable data/events. Opinion is editorial/commentary. Analysis is expert interpretation.
  - "sentiment": one of "positive", "negative", "neutral".
  - "recommendation": one of "buy", "sell", "hold", "watch", "none". "none" if no actionable signal.
  - "confidence": one of "high", "medium", "low".
Respond ONLY with the JSON."""

NEWS_PROMPT = """Headline: {title}
Source: {source}
Summary: {summary}"""

def get_llm_client():
    openai_key = os.environ.get('OPENAI_API_KEY')
    provider = None
    model = None
    base_url = None

    # Try DB settings first (matches PHP LLMService)
    try:
        conn = get_connection()
        if conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT setting_key, setting_value FROM system_settings WHERE setting_key IN ('llm_provider', 'llm_model', 'llm_api_key', 'llm_base_url')")
            for row in cur.fetchall():
                k = row['setting_key']
                v = row['setting_value']
                if k == 'llm_provider': provider = v
                elif k == 'llm_model': model = v
                elif k == 'llm_api_key' and v: openai_key = v
                elif k == 'llm_base_url': base_url = v
            cur.close()
            conn.close()
    except Exception:
        pass

    if not provider:
        provider = os.environ.get('LLM_PROVIDER', 'openrouter')
    if not model:
        model = os.environ.get('LLM_MODEL', 'gpt-4o-mini')
    if not openai_key:
        openai_key = os.environ.get('OPENAI_API_KEY', '')
    if not base_url:
        base_url = os.environ.get('LLM_BASE_URL', '')

    if provider == 'openrouter' and openai_key and base_url:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key, base_url=base_url)
            return ('openai', client, model)
        except ImportError:
            pass

    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            return ('openai', client, model)
        except ImportError:
            pass

    # Try Ollama (local)
    try:
        import requests
        resp = requests.get('http://localhost:11434/api/tags', timeout=5)
        if resp.status_code == 200:
            return ('ollama', None, model)
    except Exception:
        pass

    return (None, None, None)

def call_llm(client_type, client, prompt, model=None):
    if client_type == 'openai':
        model = model or os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
        response = client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': prompt},
            ],
            temperature=0.2,
            max_tokens=300,
        )
        return response.choices[0].message.content
    elif client_type == 'ollama':
        import requests
        model = model or os.environ.get('OLLAMA_MODEL', 'llama3')
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={'model': model, 'prompt': SYSTEM_PROMPT + "\n\n" + prompt, 'stream': False},
            timeout=120,
        )
        return response.json().get('response', '')
    return None

def clean_json_text(text):
    if not text:
        return None
    text = text.strip()
    if text.startswith('```'):
        lines = text.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        text = '\n'.join(lines).strip()
    return text

def process_batch(symbol=None, limit=50):
    conn = get_connection()
    if not conn:
        logger.error("DB connection failed")
        return

    cursor = conn.cursor(dictionary=True)

    client_type, client, model = get_llm_client()
    if not client_type:
        logger.warning("No LLM available (configure in admin_settings or set OPENAI_API_KEY / run Ollama). Exiting.")
        cursor.close()
        conn.close()
        return

    # Fetch unprocessed news from symbol_news
    sql = """
        SELECT sn.id, sn.symbol, sn.title, COALESCE(sn.summary, sn.title) as body, sn.source, sn.date
        FROM symbol_news sn
        LEFT JOIN news_processed np ON np.source_table = 'symbol_news' AND np.source_id = sn.id
        WHERE np.id IS NULL
    """
    params = []
    if symbol:
        sql += " AND sn.symbol = %s"
        params.append(symbol)
    sql += " ORDER BY sn.date DESC LIMIT %s"
    params.append(limit)

    cursor.execute(sql, params)
    rows = cursor.fetchall()

    processed = 0
    errors = 0
    for row in rows:
        try:
            prompt = NEWS_PROMPT.format(title=row['title'], source=row.get('source', ''), summary=row['body'])
            raw = call_llm(client_type, client, prompt, model=model)
            data = None
            if raw:
                cleaned = clean_json_text(raw)
                if cleaned:
                    try:
                        data = json.loads(cleaned)
                    except json.JSONDecodeError:
                        data = None
            if not data:
                # Fallback: classify as opinion if source looks like MF/Barrons etc, else fact
                src_lower = (row.get('source') or '').lower()
                classification = 'opinion' if any(x in src_lower for x in ['motley', 'fool', 'barrons', 'seeking alpha']) else 'fact'
                data = {
                    'summary': (row['body'] or '')[:120],
                    'classification': classification,
                    'sentiment': 'neutral',
                    'recommendation': 'none',
                    'confidence': 'low',
                }

            cursor.execute("""
                INSERT INTO news_processed (source_id, source_table, symbol, summary, classification, sentiment, recommendation, confidence)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    summary = VALUES(summary),
                    classification = VALUES(classification),
                    sentiment = VALUES(sentiment),
                    recommendation = VALUES(recommendation),
                    confidence = VALUES(confidence)
            """, (
                row['id'], 'symbol_news', row['symbol'],
                data.get('summary', '')[:500],
                data.get('classification', 'fact'),
                data.get('sentiment', 'neutral'),
                data.get('recommendation', 'none'),
                data.get('confidence', 'medium'),
            ))
            conn.commit()
            processed += 1
        except Exception as e:
            conn.rollback()
            errors += 1
            logger.error(f"Error processing news id {row['id']}: {e}")

    cursor.close()
    conn.close()
    logger.info(f"Processed {processed} news items ({errors} errors)")

def main():
    parser = argparse.ArgumentParser(description='News summarizer')
    parser.add_argument('--symbol', help='Process news for a specific symbol')
    parser.add_argument('--limit', type=int, default=50, help='Max items to process')
    parser.add_argument('--all', action='store_true', help='Process all unprocessed')
    args = parser.parse_args()

    if args.all or args.symbol:
        process_batch(symbol=args.symbol, limit=args.limit)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
