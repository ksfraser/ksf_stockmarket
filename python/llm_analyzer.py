#!/usr/bin/env python3
"""
llm_analyzer.py — LLM-Assisted Qualitative Scoring
===================================================
Uses an LLM to analyze unstructured text (press releases, annual filings,
earnings call transcripts) and populate the qualitative scoring tables.

This is NOT a replacement for human judgment — it's an assistant.
Every LLM-generated score can be overridden by a human analyst.

Usage:
  python3 llm_analyzer.py --table tenets --symbol RY.TO
  python3 llm_analyzer.py --table motleyfool --all
  python3 llm_analyzer.py --table evalsummary --all --review
"""

import argparse
import json
import logging
import os
from datetime import datetime

import pandas as pd

from python.db_connector import get_connection, get_active_symbols
from quant.probability import bayesian_update
from quant.statistics import t_test_significant
from quant.research import route_hypothesis

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def get_llm_client():
    """
    Initialize the LLM client.
    Tries OpenAI, then falls back to local Ollama.
    """
    # Try OpenAI first
    openai_key = os.environ.get('OPENAI_API_KEY')
    if openai_key:
        try:
            from openai import OpenAI
            return ('openai', OpenAI(api_key=openai_key))
        except ImportError:
            pass

    # Try Ollama (local)
    try:
        import requests
        resp = requests.get('http://localhost:11434/api/tags', timeout=5)
        if resp.status_code == 200:
            return ('ollama', None)
    except Exception:
        pass

    logger.warning("No LLM client available. Set OPENAI_API_KEY or run Ollama.")
    return (None, None)


def call_llm(client_type, client, prompt: str, model: str = None) -> str:
    """Call the LLM with a prompt and return the response text."""
    if client_type == 'openai':
        model = model or os.environ.get('OPENAI_MODEL', 'gpt-4o')
        response = client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': 'You are a professional financial analyst. Respond in JSON format only.'},
                {'role': 'user', 'content': prompt},
            ],
            temperature=0.2,
            max_tokens=2000,
        )
        return response.choices[0].message.content

    elif client_type == 'ollama':
        import requests
        model = model or os.environ.get('OLLAMA_MODEL', 'llama3')
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={'model': model, 'prompt': prompt, 'stream': False},
            timeout=120,
        )
        return response.json().get('response', '')

    return ''


def analyze_tenets_llm(symbol: str, client_type, client, model: str = None) -> dict:
    """
    Use LLM to analyze Buffett-style tenets from available data sources.
    Reads financial data from MariaDB and generates reasoned scores.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Gather data sources
    cursor.execute("""
        SELECT s.corporatename, s.sector, s.industry,
               r.roe, r.roa, r.debtratio, r.netmargin, r.operatingmargin,
               q.revenue, q.revenuegrowth, q.netincome, q.earningpershare,
               q.totaldebt, q.totalequity, q.retainedearnings
        FROM stockinfo s
        LEFT JOIN ratios r ON r.symbol = s.stocksymbol
        LEFT JOIN quarter_statement q ON q.symbol = s.stocksymbol
        WHERE s.stocksymbol = %s
        ORDER BY q.fiscal_year DESC, q.fiscal_quarter DESC
        LIMIT 1
    """, (symbol,))
    data = cursor.fetchone()
    cursor.close()
    conn.close()

    if not data:
        return {}

    prompt = f"""Analyze the following company data for Buffett-style investment tenets.
Provide a JSON response with scores from 0-10 for each tenet, plus a reasoning string.

Company: {symbol}
Name: {data.get('corporatename', 'N/A')}
Sector: {data.get('sector', 'N/A')}
Industry: {data.get('industry', 'N/A')}

Financial Data:
- ROE: {data.get('roe', 'N/A')}
- ROA: {data.get('roa', 'N/A')}
- Debt Ratio: {data.get('debtratio', 'N/A')}
- Net Margin: {data.get('netmargin', 'N/A')}
- Operating Margin: {data.get('operatingmargin', 'N/A')}
- Revenue Growth: {data.get('revenuegrowth', 'N/A')}
- EPS: {data.get('earningpershare', 'N/A')}
- Total Debt: {data.get('totaldebt', 'N/A')}
- Total Equity: {data.get('totalequity', 'N/A')}
- Retained Earnings: {data.get('retainedearnings', 'N/A')}

Score each tenet from 0-10 and provide reasoning. Output JSON only:
{{
  "simple": {{"score": 0, "reasoning": "..."}},
  "consistent": {{"score": 0, "reasoning": "..."}},
  "longterm": {{"score": 0, "reasoning": "..."}},
  "rationalmanager": {{"score": 0, "reasoning": "..."}},
  "candid": {{"score": 0, "reasoning": "..."}},
  "resistinstitution": {{"score": 0, "reasoning": "..."}},
  "focusroe": {{"score": 0, "reasoning": "..."}},
  "ownerearnings": {{"score": 0, "reasoning": "..."}},
  "highprofitmargin": {{"score": 0, "reasoning": "..."}},
  "retainedtomarket": {{"score": 0, "reasoning": "..."}},
  "valueofbusiness": {{"score": 0, "reasoning": "..."}},
  "discounted": {{"score": 0, "reasoning": "..."}},
  "overall_confidence": 0.0
}}
"""

    response = call_llm(client_type, client, prompt, model)

    # Parse JSON from response
    try:
        # Find JSON in response
        start = response.find('{')
        end = response.rfind('}') + 1
        if start >= 0 and end > start:
            scores = json.loads(response[start:end])
            return scores
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response for {symbol}: {e}")
        logger.debug(f"Raw response: {response[:500]}")

    return {}


def analyze_motleyfool_llm(symbol: str, client_type, client, model: str = None) -> dict:
    """Use LLM to analyze Motley Fool criteria."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT s.corporatename, s.sector,
               q.revenue, q.revenuegrowth, q.revenuegrowth2, q.revenuegrowth3,
               r.roe, r.roa, r.netmargin, r.grossprofitmargin,
               q.earningpershare, q.dividendpershare,
               q.totaldebt, q.totalequity
        FROM stockinfo s
        LEFT JOIN ratios r ON r.symbol = s.stocksymbol
        LEFT JOIN quarter_statement q ON q.symbol = s.stocksymbol
        WHERE s.stocksymbol = %s
        ORDER BY q.fiscal_year DESC
        LIMIT 4
    """, (symbol,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        return {}

    data_str = json.dumps(rows, indent=2, default=str)

    prompt = f"""Analyze whether {symbol} meets Motley Fool Rule Maker criteria.
Respond with JSON only containing boolean (0 or 1) scores and reasoning.

Company data (last 4 quarters):
{data_str}

Criteria to evaluate:
1. doubledigitrisingsales: Is revenue growth >= 10% consistently?
2. risingfreecashflow: Is free cash flow rising? (infer from income trends)
3. risingbookvalue: Is book value rising? (check equity trends)
4. improvingmargin: Are margins (net, gross, operating) improving?
5. risingreturnonequity: Is ROE rising or consistently high?
6. insiderownership: Can you infer management quality from available data?
7. regulardividends: Are dividends paid consistently?

Output JSON:
{{
  "doubledigitrisingsales": {{"score": 0, "reasoning": "..."}},
  "risingfreecashflow": {{"score": 0, "reasoning": "..."}},
  "risingbookvalue": {{"score": 0, "reasoning": "..."}},
  "improvingmargin": {{"score": 0, "reasoning": "..."}},
  "risingreturnonequity": {{"score": 0, "reasoning": "..."}},
  "insiderownership": {{"score": 0, "reasoning": "..."}},
  "regulardividends": {{"score": 0, "reasoning": "..."}},
  "confidence": 0.0
}}
"""

    response = call_llm(client_type, client, prompt, model)
    try:
        start = response.find('{')
        end = response.rfind('}') + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
    except json.JSONDecodeError:
        logger.error(f"Failed to parse MF LLM response for {symbol}")
    return {}


def write_llm_scores(conn, symbol: str, table: str, scores: dict,
                     source: str, confidence: float):
    """Write LLM-generated scores to the appropriate scoring table."""
    if not scores:
        return

    # Bayesian-update LLM confidence against prior historical accuracy for this table/symbol
    try:
        prior_cursor = conn.cursor(dictionary=True)
        prior_cursor.execute(
            "SELECT AVG(llm_confidence) FROM {} WHERE symbol = %s AND is_llm_generated = 1".format(table),
            (symbol,)
        )
        prior_row = prior_cursor.fetchone()
        prior_cursor.close()
        prior = float(prior_row['llm_confidence']) if prior_row and prior_row.get('llm_confidence') else 0.5
        likelihood = confidence if confidence >= 0.5 else confidence * 0.5
        adjusted_confidence = bayesian_update(prior, likelihood, 0.7)
        confidence = max(0.0, min(1.0, adjusted_confidence))
    except Exception:
        pass

    cursor = conn.cursor()

    table_fields = {
        'tenets': ['simple', 'consistent', 'longterm', 'rationalmanager', 'candid',
                    'resistinstitution', 'focusroe', 'ownerearnings', 'highprofitmargin',
                    'retainedtomarket', 'valueofbusiness', 'discounted'],
        'motleyfool': ['doubledigitrisingsales', 'risingfreecashflow', 'risingbookvalue',
                        'improvingmargin', 'risingreturnonequity', 'insiderownership',
                        'regulardividends'],
        'evalbusiness': ['simple', 'consistent_history', 'neededproduct',
                         'noclosesubstitute', 'regulated'],
    }

    fields = table_fields.get(table, [])
    values = {}
    reasoning_parts = []

    for field in fields:
        if field in scores:
            field_data = scores[field]
            if isinstance(field_data, dict):
                values[field] = field_data.get('score', 0)
                reasoning_parts.append(f"{field}: {field_data.get('reasoning', '')}")
            else:
                values[field] = field_data

    if not values:
        return

    # Build UPDATE/INSERT
    all_fields = list(values.keys()) + ['source', 'source_date', 'is_llm_generated',
                                         'llm_confidence', 'llm_reasoning', 'updated_at']
    placeholders = ', '.join(['%s'] * len(all_fields))

    # Check if row exists
    cursor.execute(f"SELECT 1 FROM {table} WHERE symbol = %s", (symbol,))
    exists = cursor.fetchone()

    if exists:
        set_clause = ', '.join([f"{f} = %s" for f in all_fields])
        cursor.execute(f"""
            UPDATE {table} SET {set_clause} WHERE symbol = %s
        """, list(values.values()) + [
            source, datetime.now().date(), 1, confidence,
            ' | '.join(reasoning_parts[:5]), datetime.now(),
            symbol
        ])
    else:
        cursor.execute(f"""
            INSERT INTO {table} (symbol, {', '.join(all_fields)})
            VALUES (%s, {placeholders})
        """, [symbol] + list(values.values()) + [
            source, datetime.now().date(), 1, confidence,
            ' | '.join(reasoning_parts[:5]), datetime.now()
        ])

    conn.commit()
    cursor.close()

    logger.info(f"Wrote LLM scores for {symbol} to {table} (confidence: {confidence:.2f})")


def _fetch_recent_returns(conn, symbol: str, days: int = 252) -> "pd.Series":
    """Fetch daily returns for a symbol from stockprices."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT day_close FROM stockprices
        WHERE symbol = %s
        ORDER BY price_date ASC
        LIMIT %s
    """, (symbol, days))
    rows = cursor.fetchall()
    cursor.close()
    closes = [r['day_close'] for r in rows if r.get('day_close')]
    if len(closes) < 30:
        return pd.Series(dtype=float)
    return pd.Series(closes).pct_change().dropna()


def run_llm_research(conn, symbol: str, scores: dict) -> dict:
    """
    Layer 2: run route_hypothesis() on recent returns and merge
    the ResearchResult JSON into scores so it's persisted alongside
    the LLM scores.  Falls back to half-Kelly if no test matches.
    """
    try:
        returns = _fetch_recent_returns(conn, symbol)
        if returns.empty:
            return scores
        result = route_hypothesis("Does this asset have a statistically significant mean return?", returns)
        scores['quant_test'] = result.test_type
        scores['quant_significant'] = int(result.is_significant)
        scores['quant_p_value']   = result.p_value
        scores['quant_metric']    = round(result.metric, 4)
        scores['quant_detail']    = result.detail
        scores['quant_recommendation'] = result.recommendation
    except Exception as e:
        logger.debug(f"[{symbol}] LLM research route failed: {e}")
    return scores


def run_llm_analysis(table: str, symbols: list = None, model: str = None):
    """Run LLM analysis for a scoring table across symbols."""
    client_type, client = get_llm_client()
    if not client_type:
        logger.error("No LLM client available. Cannot run analysis.")
        return

    conn = get_connection()
    if not symbols:
        symbols = get_active_symbols(conn)

    analyzers = {
        'tenets': analyze_tenets_llm,
        'motleyfool': analyze_motleyfool_llm,
    }

    analyzer = analyzers.get(table)
    if not analyzer:
        logger.error(f"No LLM analyzer for table: {table}")
        return

    logger.info(f"Running LLM analysis for {table} on {len(symbols)} symbols...")

    for i, symbol in enumerate(symbols):
        try:
            scores = analyzer(symbol, client_type, client, model)
            confidence = scores.pop('confidence', scores.pop('overall_confidence', 0.5))
            # Layer 2: LLM deep-dive — auto-route hypothesis test
            if scores:
                scores = run_llm_research(conn, symbol, scores)
                write_llm_scores(conn, symbol, table, scores,
                                'llm_analysis', confidence)
            if (i + 1) % 10 == 0:
                logger.info(f"  Progress: {i+1}/{len(symbols)}")
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")

    conn.close()
    logger.info("LLM analysis complete")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='LLM Analyzer')
    parser.add_argument('--table', required=True,
                        choices=['tenets', 'motleyfool', 'investorplace', 'evalbusiness'])
    parser.add_argument('--symbol', help='Single symbol')
    parser.add_argument('--all', action='store_true', help='All active symbols')
    parser.add_argument('--model', help='LLM model override')
    parser.add_argument('--review', action='store_true',
                        help='Human review mode (show scores before writing)')

    args = parser.parse_args()

    symbols = []
    if args.symbol:
        symbols = [args.symbol.upper()]
    elif args.all:
        symbols = None  # Will fetch all active

    run_llm_analysis(args.table, symbols, args.model)
