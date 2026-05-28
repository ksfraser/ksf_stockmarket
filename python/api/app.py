"""
KSF Stock Market — Python Analysis Engine API

Flask REST API that PHP calls via PythonBridge.
Runs on localhost:5000, proxied through Apache mod_proxy.

All database access goes through the connector module.
All business logic goes through the engine modules.
This file is just routing + serialization.
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'config', '.env'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger('ksf_stockmarket_api')

app = Flask(__name__)

# API key for PHP ↔ Python bridge authentication
API_KEY = os.environ.get('PYTHON_API_KEY', 'dev_key_change_me')


# ─── Authentication Middleware ────────────────────────────────────────────────

@app.before_request
def check_api_key():
    """Verify API key on all /api/* routes."""
    if request.path.startswith('/api/health'):
        return None
    if request.path.startswith('/api/'):
        key = request.headers.get('X-API-Key', '')
        if key != API_KEY:
            return jsonify({'error': 'Unauthorized'}), 401
    return None


# ─── Error Handlers ───────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f'Internal error: {e}')
    return jsonify({'error': 'Internal server error'}), 500


@app.errorhandler(400)
def bad_request(e):
    return jsonify({'error': str(e)}), 400


# ─── Health Check ─────────────────────────────────────────────────────────────

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    from python.db_connector import get_connection
    db_status = 'unknown'
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        db_status = 'connected'
    except Exception as e:
        db_status = f'error: {e}'

    return jsonify({
        'status': 'ok',
        'service': 'ksf-stockmarket-api',
        'database': db_status,
        'time': datetime.utcnow().isoformat(),
    })


# ─── Technical Analysis ───────────────────────────────────────────────────────

@app.route('/api/ta/analyze', methods=['POST'])
def analyze_ta():
    """
    Run technical analysis on a symbol.
    Reads pre-computed indicators from daily_tier2 + ta_values.
    """
    data = request.get_json()
    symbol = data.get('symbol', '').upper()
    if not symbol:
        return jsonify({'error': 'symbol is required'}), 400

    from python.db_connector import get_connection
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Get latest Tier 2 data
    cursor.execute("""
        SELECT * FROM daily_tier2
        WHERE symbol = %s
        ORDER BY price_date DESC LIMIT 1
    """, (symbol,))
    tier2 = cursor.fetchone()

    # Get latest Tier 3 values
    requested = data.get('indicators', [])
    if requested:
        placeholders = ','.join(['%s'] * len(requested))
        cursor.execute(f"""
            SELECT indicator, value, signal FROM ta_values
            WHERE symbol = %s AND price_date = (
                SELECT MAX(price_date) FROM ta_values WHERE symbol = %s
            ) AND indicator IN ({placeholders})
        """, [symbol, symbol] + requested)
    else:
        cursor.execute("""
            SELECT indicator, value, signal FROM ta_values
            WHERE symbol = %s AND price_date = (
                SELECT MAX(price_date) FROM ta_values WHERE symbol = %s
            )
        """, (symbol, symbol))
    ta_values = cursor.fetchall()

    # Get latest price
    cursor.execute("""
        SELECT * FROM stockprices
        WHERE symbol = %s ORDER BY price_date DESC LIMIT 1
    """, (symbol,))
    latest_price = cursor.fetchone()

    cursor.close()
    conn.close()

    # Build response
    indicators = {row['indicator']: row['value'] for row in ta_values}
    patterns = [
        row['indicator'] for row in ta_values
        if row['indicator'].startswith('CDL_') and row['signal'] in ('BUY', 'SELL')
    ]

    signal = 'HOLD'
    confidence = 0.0
    if tier2:
        signal_strength = tier2.get('signal_strength', 0) or 0
        if signal_strength > 20:
            signal = 'BUY'
            confidence = min(95, 50 + signal_strength / 2)
        elif signal_strength < -20:
            signal = 'SELL'
            confidence = min(95, 50 + abs(signal_strength) / 2)
        else:
            confidence = 50 - abs(signal_strength) / 2

    logger.info(f'TA analysis for {symbol}: {signal} ({confidence:.1f}%)')

    return jsonify({
        'symbol': symbol,
        'signal': signal,
        'confidence': round(confidence, 1),
        'indicators': indicators,
        'tier2': tier2,
        'patterns': patterns,
        'price': latest_price,
        'computed_at': datetime.utcnow().isoformat(),
    })


@app.route('/api/ta/values/<symbol>', methods=['GET'])
def get_ta_values(symbol):
    """Get TA values for a symbol on a specific date."""
    date = request.args.get('date')
    from python.db_connector import get_connection
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if date:
        cursor.execute("""
            SELECT indicator, value, signal, source FROM ta_values
            WHERE symbol = %s AND price_date = %s
            ORDER BY indicator
        """, (symbol.upper(), date))
    else:
        cursor.execute("""
            SELECT indicator, value, signal, source FROM ta_values
            WHERE symbol = %s AND price_date = (
                SELECT MAX(price_date) FROM ta_values WHERE symbol = %s
            )
            ORDER BY indicator
        """, (symbol.upper(), symbol.upper()))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify({
        'symbol': symbol.upper(),
        'values': rows,
        'count': len(rows),
    })


# ─── Screening ────────────────────────────────────────────────────────────────

@app.route('/api/screen/run', methods=['POST'])
def run_screen():
    """
    Run a stock/ETF screen.
    Reads from scoring tables (motleyfool, investorplace, tenets, evalsummary).
    """
    data = request.get_json()
    screen_type = data.get('screen_type', '')
    universe = data.get('universe', 'tsx')
    min_score = data.get('min_score', 0)

    from python.db_connector import get_connection
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Build query based on screen type
    queries = {
        'motley_fool_rule_maker': """
            SELECT s.stocksymbol, m.mf_score,
                   m.doubledigitrisingsales, m.risingfreecashflow,
                   m.risingbookvalue, m.improvingmargin,
                   m.risingreturnonequity, m.insiderownership,
                   m.regulardividends
            FROM motleyfool m
            JOIN stockinfo s ON s.stocksymbol = m.symbol
            WHERE m.mf_score >= %s
            ORDER BY m.mf_score DESC
            LIMIT 100
        """,
        'buffett': """
            SELECT s.stocksymbol, e.totalscore, t.total_score as tenet_score,
                   e.ratioscore, e.managementscore, e.businessscore
            FROM evalsummary e
            JOIN stockinfo s ON s.stocksymbol = e.symbol
            LEFT JOIN tenets t ON t.symbol = e.symbol
            WHERE e.totalscore >= %s
            ORDER BY e.totalscore DESC
            LIMIT 100
        """,
        'combined': """
            SELECT s.stocksymbol,
                   e.totalscore,
                   m.mf_score,
                   i.ip_score,
                   t.total_score as tenet_score
            FROM stockinfo s
            LEFT JOIN evalsummary e ON e.symbol = s.stocksymbol
            LEFT JOIN motleyfool m ON m.symbol = s.stocksymbol
            LEFT JOIN investorplace i ON i.symbol = s.stocksymbol
            LEFT JOIN tenets t ON t.symbol = s.stocksymbol
            WHERE COALESCE(e.totalscore, 0) >= %s
            ORDER BY COALESCE(e.totalscore, 0) DESC
            LIMIT 100
        """,
    }

    query = queries.get(screen_type, queries['combined'])
    cursor.execute(query, (min_score,))
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    logger.info(f'Screen {screen_type}/{universe}: {len(results)} results')

    return jsonify({
        'screen_type': screen_type,
        'universe': universe,
        'min_score': min_score,
        'results': results,
        'count': len(results),
        'computed_at': datetime.utcnow().isoformat(),
    })


# ─── Scoring ──────────────────────────────────────────────────────────────────

@app.route('/api/scoring/run', methods=['POST'])
def run_scoring():
    """Run fundamental scoring for a single symbol."""
    data = request.get_json()
    symbol = data.get('symbol', '').upper()
    if not symbol:
        return jsonify({'error': 'symbol is required'}), 400

    from python.scoring_engine import score_symbol, get_connection
    conn = get_connection()
    try:
        result = score_symbol(conn, symbol)
        return jsonify({
            'symbol': symbol,
            'status': 'complete',
            'scores': result,
            'computed_at': datetime.utcnow().isoformat(),
        })
    except Exception as e:
        logger.error(f'Scoring error for {symbol}: {e}')
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/scoring/run_all', methods=['POST'])
def run_all_scoring():
    """Run fundamental scoring for all active symbols."""
    data = request.get_json() or {}
    limit = data.get('limit')

    from python.scoring_engine import run_scoring
    try:
        result = run_scoring(limit=limit)
        return jsonify({
            'status': 'complete',
            **result,
            'computed_at': datetime.utcnow().isoformat(),
        })
    except Exception as e:
        logger.error(f'Batch scoring error: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/scoring/summary/<symbol>', methods=['GET'])
def get_scoring_summary(symbol):
    """Get composite evaluation summary for a symbol."""
    from python.db_connector import get_connection
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM evalsummary WHERE symbol = %s", (symbol.upper(),))
    summary = cursor.fetchone()

    # Get individual table scores
    tables = ['motleyfool', 'investorplace', 'tenets', 'evalbusiness',
              'ratios', 'quarter_statement', 'evalmanagement', 'evalmarket', 'evalvalue']
    scores = {}
    for table in tables:
        try:
            cursor.execute(f"SELECT * FROM {table} WHERE symbol = %s", (symbol.upper(),))
            row = cursor.fetchone()
            if row:
                scores[table] = row
        except Exception:
            pass

    cursor.close()
    conn.close()

    return jsonify({
        'symbol': symbol.upper(),
        'summary': summary,
        'scores': scores,
    })


# ─── Correlation ──────────────────────────────────────────────────────────────

@app.route('/api/correlation/run', methods=['POST'])
def run_correlation():
    """Run signal correlation analysis for a symbol."""
    data = request.get_json()
    symbol = data.get('symbol', '').upper()
    if not symbol:
        return jsonify({'error': 'symbol is required'}), 400

    from python.correlation_analysis import update_signal_weights, get_connection
    conn = get_connection()
    try:
        result = update_signal_weights(conn, symbol)
        conn.commit()
        return jsonify({
            'symbol': symbol,
            'status': 'complete',
            'signal_weights_updated': result,
            'computed_at': datetime.utcnow().isoformat(),
        })
    except Exception as e:
        conn.rollback()
        logger.error(f'Correlation error for {symbol}: {e}')
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/correlation/run_all', methods=['POST'])
def run_all_correlation():
    """Run correlation analysis for all symbols."""
    from python.correlation_analysis import run_correlation_analysis
    try:
        result = run_correlation_analysis()
        return jsonify({
            'status': 'complete',
            **result,
            'computed_at': datetime.utcnow().isoformat(),
        })
    except Exception as e:
        logger.error(f'Batch correlation error: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/signal_weights/<symbol>', methods=['GET'])
def get_signal_weights(symbol):
    """Get signal weights for a symbol."""
    from python.db_connector import get_connection
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT signal_type, weight, win_rate, avg_lead_days,
               is_pre_indicator, correlation, correlates_with,
               weight_boosted, boost_condition, n_trades
        FROM signal_weights
        WHERE symbol = %s
        ORDER BY weight DESC
    """, (symbol.upper(),))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    # Deserialize JSON fields
    import json
    for row in rows:
        if row.get('correlates_with'):
            try:
                row['correlates_with'] = json.loads(row['correlates_with'])
            except (json.JSONDecodeError, TypeError):
                pass

    return jsonify({
        'symbol': symbol.upper(),
        'signal_weights': rows,
        'count': len(rows),
    })

@app.route('/api/backtest/run', methods=['POST'])
def run_backtest():
    """
    Submit a backtest to the queue.

    Request body:
        strategy: str
        parameters: dict
        start_date: str
        end_date: str
        user_id: int

    Returns:
        run_id and status
    """
    data = request.get_json()

    # TODO: Implement backtest queue submission
    logger.info(f'Backtest requested: {data.get("strategy", "unknown")}')

    return jsonify({
        'run_id': 0,
        'status': 'pending',
        'message': 'Backtest engine not yet implemented',
        'submitted_at': datetime.utcnow().isoformat(),
    })


@app.route('/api/backtest/status/<int:run_id>', methods=['GET'])
def backtest_status(run_id: int):
    """Get backtest run status and metrics."""
    return jsonify({
        'run_id': run_id,
        'status': 'pending',
        'message': 'Backtest engine not yet implemented',
    })


@app.route('/api/backtest/results/<int:run_id>', methods=['GET'])
def backtest_results(run_id: int):
    """Get detailed backtest results including trade log."""
    return jsonify({
        'run_id': run_id,
        'status': 'pending',
        'message': 'Backtest engine not yet implemented',
    })


# ─── Data Import ──────────────────────────────────────────────────────────────

@app.route('/api/data/prices/<symbol>', methods=['GET'])
def get_prices(symbol: str):
    """Get price history for a symbol."""
    from_date = request.args.get('from')
    to_date = request.args.get('to')

    # TODO: Query MariaDB for price data
    return jsonify({
        'symbol': symbol.upper(),
        'prices': [],
        'count': 0,
    })


@app.route('/api/data/import', methods=['POST'])
def import_data():
    """Trigger a data import operation."""
    data = request.get_json()
    symbols = data.get('symbols', [])
    source = data.get('source', 'yfinance')

    logger.info(f'Data import requested: {len(symbols)} symbols from {source}')

    # TODO: Implement data import
    return jsonify({
        'status': 'started',
        'symbols_count': len(symbols),
        'source': source,
        'started_at': datetime.utcnow().isoformat(),
    })


# ─── Error Handlers ───────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(e):
    logger.error(f'Internal error: {e}')
    return jsonify({'error': 'Internal server error'}), 500


# ─── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PYTHON_API_PORT', 5000))
    debug = os.environ.get('APP_ENV', 'production') == 'development'

    logger.info(f'Starting KSF Stock Market API on port {port}')
    app.run(host='127.0.0.1', port=port, debug=debug)
