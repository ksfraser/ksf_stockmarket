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
from datetime import datetime, date
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


# ─── Advisor Recommendations ──────────────────────────────────────────────────

@app.route('/api/advisor/recommendations', methods=['GET'])
def list_recommendations():
    """List recent advisor recommendations for the current user (header X-User-Id)."""
    user_id = int(request.headers.get('X-User-Id', request.args.get('user_id', 0)))
    if user_id <= 0:
        return jsonify({'error': 'user_id required'}), 400

    from python.db_connector import get_connection
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT r.*, a.display_name AS advisor_name, a.slug AS advisor_slug
        FROM advisor_recommendations r
        JOIN advisor_accounts a ON a.id = r.advisor_id
        WHERE r.user_id = %s
        ORDER BY r.recommended_at DESC
        LIMIT 100
    """, (user_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify({'user_id': user_id, 'recommendations': rows, 'count': len(rows)})


@app.route('/api/advisor/preferences', methods=['GET', 'POST'])
def advisor_preferences():
    """Get/set advisor notification preferences in user_settings."""
    from python.src.database import get_connection
    user_id = int(request.headers.get('X-User-Id', request.args.get('user_id', 0)))
    if user_id <= 0:
        return jsonify({'error': 'user_id required'}), 400

    conn = get_connection()
    try:
        if request.method == 'POST':
            data = request.get_json() or {}
            allowed = {
                'advisor_notify_email', 'advisor_notify_discord_dm',
                'advisor_notify_discord_channel', 'advisor_notify_whatsapp',
                'advisor_discord_user_id', 'advisor_discord_channel_id',
                'advisor_whatsapp_number',
            }
            with conn.cursor() as cur:
                for key, value in data.items():
                    if key not in allowed:
                        continue
                    cur.execute("""
                        INSERT INTO user_settings (user_id, setting_key, setting_value)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)
                    """, (user_id, key, str(value)))
                conn.commit()
            return jsonify({'status': 'saved', 'user_id': user_id})

        with conn.cursor() as cur:
            cur.execute("SELECT setting_key, setting_value FROM user_settings WHERE user_id = %s", (user_id,))
            rows = cur.fetchall()
        prefs = {r['setting_key']: r['setting_value'] for r in rows}
        return jsonify({'user_id': user_id, 'preferences': prefs})
    finally:
        conn.close()


# ─── Advisor Notification: WhatsApp Gateway Framework ──────────
@app.route('/api/advisor/notifications/whatsapp/send', methods=['POST'])
def api_advisor_whatsapp_send():
    """Outbound WhatsApp send via configured gateway provider.

    Expected JSON:
      {
        "to": "+15551234567",
        "text": "message body",
        "provider_message_id": "optional",
        "metadata": {}
      }

    Behavior:
      - Enforces WHATSAPP_ENABLED=true
      - POSTs to WHATSAPP_GATEWAY_URL/v1/send with Authorization header
      - Falls back to WHATSAPP_FROM_NUMBER if provider requires it
      - Returns 202 Accepted with gateway response details

    Creds not required at build time; wire gateway URL + key later.
    """
    from python.src.notifications.advisor_notifier import _send_whatsapp_gateway
    payload = request.get_json() or {}
    to = (payload.get('to') or '').strip()
    text = (payload.get('text') or '').strip()
    if not to or not text:
        return jsonify({'status': 'error', 'message': 'to and text required'}), 400
    result = _send_whatsapp_gateway(to, text, payload.get('provider_message_id'))
    status_code = 202 if result.get('accepted') else 502
    return jsonify(result), status_code


@app.route('/api/advisor/notifications/whatsapp/status', methods=['POST'])
def api_advisor_whatsapp_status():
    """Inbound status callback from WhatsApp gateway provider.

    Provider should POST:
      {
        "provider_message_id": "...",
        "status": "sent|delivered|read|failed",
        "timestamp": "ISO8601",
        "error": "..."
      }

    TODO: connect to advisor_recommendations and user_preferences for audit.
    """
    payload = request.get_json() or {}
    required = ['provider_message_id', 'status']
    missing = [k for k in required if k not in payload]
    if missing:
        return jsonify({'status': 'error', 'message': f'missing fields: {missing}'}), 400
    # Framework stub — credential backfill will wire audit + retry queue.
    logger.info('WhatsApp status webhook received: %s', payload)
    return jsonify({'status': 'accepted', 'stored': False}), 202


# =====================================================================
# REPORTS
# =====================================================================

@app.route('/api/reports/twror', methods=['GET'])
def api_report_twror():
    user_id = int(request.headers.get('X-User-Id', request.args.get('user_id', 0)))
    if user_id <= 0:
        return jsonify({'error': 'user_id required'}), 400
    start = request.args.get('start')
    end = request.args.get('end')
    if not start or not end:
        return jsonify({'error': 'start and end dates required (YYYY-MM-DD)'}), 400
    from python.src.reports.performance import compute_twror
    from python.src.database import get_connection
    conn = get_connection()
    try:
        result = compute_twror(conn, user_id, date.fromisoformat(start), date.fromisoformat(end))
    finally:
        conn.close()
    return jsonify(result)


@app.route('/api/reports/securities', methods=['GET'])
def api_report_securities():
    user_id = int(request.headers.get('X-User-Id', request.args.get('user_id', 0)))
    if user_id <= 0:
        return jsonify({'error': 'user_id required'}), 400
    start = request.args.get('start', '2000-01-01')
    end = request.args.get('end', str(date.today()))
    account = request.args.get('account') or None
    from python.src.reports.performance import securities_performance
    from python.src.database import get_connection
    conn = get_connection()
    try:
        rows = securities_performance(conn, user_id, date.fromisoformat(start), date.fromisoformat(end), account)
    finally:
        conn.close()
    return jsonify({'count': len(rows), 'securities': rows})


@app.route('/api/reports/payments', methods=['GET'])
def api_report_payments():
    user_id = int(request.headers.get('X-User-Id', request.args.get('user_id', 0)))
    if user_id <= 0:
        return jsonify({'error': 'user_id required'}), 400
    start = request.args.get('start', str(date.today().replace(year=date.today().year - 1)))
    end = request.args.get('end', str(date.today()))
    from python.src.reports.performance import payments_summary
    from python.src.database import get_connection
    conn = get_connection()
    try:
        summary = payments_summary(conn, user_id, date.fromisoformat(start), date.fromisoformat(end))
    finally:
        conn.close()
    return jsonify(summary)


@app.route('/api/reports/tax_lots', methods=['GET'])
def api_report_tax_lots():
    user_id = int(request.headers.get('X-User-Id', request.args.get('user_id', 0)))
    if user_id <= 0:
        return jsonify({'error': 'user_id required'}), 400
    symbol = request.args.get('symbol') or None
    from python.src.reports.performance import tax_lot_summary
    from python.src.database import get_connection
    conn = get_connection()
    try:
        rows = tax_lot_summary(conn, user_id, symbol)
    finally:
        conn.close()
    return jsonify({'count': len(rows), 'lots': rows})


@app.route('/api/reports/heatmap', methods=['GET'])
def api_report_heatmap():
    user_id = int(request.headers.get('X-User-Id', request.args.get('user_id', 0)))
    if user_id <= 0:
        return jsonify({'error': 'user_id required'}), 400
    as_of = request.args.get('date') or str(date.today())
    from python.src.reports.performance import heat_map_data
    from python.src.database import get_connection
    conn = get_connection()
    try:
        data = heat_map_data(conn, user_id, date.fromisoformat(as_of))
    finally:
        conn.close()
    return jsonify(data)


@app.route('/api/reports/rebalance', methods=['GET', 'POST'])
def api_report_rebalance():
    user_id = int(request.headers.get('X-User-Id', request.args.get('user_id', 0)))
    if user_id <= 0:
        return jsonify({'error': 'user_id required'}), 400
    from python.src.database import get_connection
    from python.src.reports.rebalancing import compute_rebalance, list_targets, create_target, update_target, toggle_target, delete_target
    conn = get_connection()
    try:
        if request.method == 'POST':
            payload = request.get_json() or {}
            if request.args.get('action') == 'delete' and request.args.get('target_id'):
                delete_target(conn, int(request.args.get('target_id')))
                return jsonify({'status': 'deleted'})
            if request.args.get('action') == 'toggle' and request.args.get('target_id'):
                toggle_target(conn, int(request.args.get('target_id')), bool(payload.get('active', True)))
                return jsonify({'status': 'toggled'})
            name = payload.get('name', 'Unnamed')
            if not name:
                return jsonify({'error': 'name required'}), 400
            target_id = create_target(
                conn,
                user_id=user_id,
                name=name,
                target_type=payload.get('target_type', 'taxonomy'),
                target_allocations=payload.get('target_allocations', {}),
                tolerance_pct=float(payload.get('tolerance_pct', 5) or 5),
                rebalance_frequency=payload.get('rebalance_frequency', 'monthly'),
                strategy_name=payload.get('strategy_name'),
            )
            return jsonify({'target_id': target_id})
        # GET: list or compute
        if request.args.get('action') == 'compute' and request.args.get('target_id'):
            result = compute_rebalance(conn, user_id, int(request.args.get('target_id')))
            return jsonify(result)
        targets = list_targets(conn, user_id, active_only=request.args.get('active') != 'all')
        return jsonify({'count': len(targets), 'targets': [t.to_dict() for t in targets]})
    finally:
        conn.close()


@app.route('/api/reports/taxonomies', methods=['GET', 'POST'])
def api_report_taxonomies():
    user_id = int(request.headers.get('X-User-Id', request.args.get('user_id', 0)))
    if user_id <= 0:
        return jsonify({'error': 'user_id required'}), 400
    from python.src.database import get_connection
    from python.src.reports.taxonomies import (
        list_taxonomies as _list_taxonomies,
        get_assignments_for_user as _get_assignments,
        assign_symbol as _assign_symbol,
        remove_assignment as _remove_assignment,
        create_taxonomy as _create_taxonomy,
        update_taxonomy as _update_taxonomy,
        delete_taxonomy as _delete_taxonomy,
    )
    conn = get_connection()
    try:
        if request.method == 'POST':
            payload = request.get_json() or {}
            action = payload.get('action') or request.args.get('action')
            if action == 'delete':
                _delete_taxonomy(conn, int(payload.get('taxonomy_id')))
                return jsonify({'status': 'deleted'})
            if action == 'unassign':
                _remove_assignment(conn, int(payload.get('assignment_id')))
                return jsonify({'status': 'unassigned'})
            if payload.get('name'):
                tid = _create_taxonomy(
                    conn,
                    user_id=user_id,
                    name=payload['name'],
                    type=payload.get('type', 'custom'),
                    parent_id=payload.get('parent_id'),
                )
                return jsonify({'taxonomy_id': tid})
            if payload.get('taxonomy_id'):
                _update_taxonomy(conn, int(payload['taxonomy_id']), **{k: v for k, v in payload.items() if k not in ('action', 'taxonomy_id', 'name')})
                return jsonify({'status': 'updated'})
            if payload.get('assign'):
                tid = int(payload.get('taxonomy_id', 0))
                sym = str(payload.get('symbol', ''))
                aid = _assign_symbol(conn, user_id, tid, sym, float(payload.get('weight', 0) or 0), payload.get('notes', ''))
                return jsonify({'assignment_id': aid})
        taxonomies = _list_taxonomies(conn, user_id)
        assignments = _get_assignments(conn, user_id)
        return jsonify({'taxonomies': [t.to_dict() for t in taxonomies], 'assignments': [a.to_dict() for a in assignments]})
    finally:
        conn.close()
