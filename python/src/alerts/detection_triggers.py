"""Stock alert detection triggers — thin CLI shim.

Business logic now lives in the canonical alerts package:

    from python.src.alerts.checks import check_volume_spike, check_oscillator_extremes
    from python.src.alerts.repository import write_alert
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Allow running as: python3 detection_triggers.py from repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "python" / "src"))

from alerts.checks import (  # noqa: E402
    check_gap_opening,
    check_natr_spike,
    check_oscillator_extremes,
    check_volume_spike,
)
from alerts.repository import write_alert  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    import sys
    print('DEBUG: main start', flush=True)
    sys.stdout.flush()
    parser = argparse.ArgumentParser(description="Stock alert detection triggers")
    parser.add_argument("--volume", action="store_true", help="Run volume spike detection")
    parser.add_argument("--natr", action="store_true", help="Run NATR spike detection")
    parser.add_argument("--oscillator", action="store_true", help="Run oscillator extremes detection")
    parser.add_argument("--gap", action="store_true", help="Run gap opening detection")
    parser.add_argument("--all", action="store_true", help="Run all detection triggers")
    parser.add_argument("--symbols", nargs="+", help="Specific symbols to check")
    args = parser.parse_args()

    run_all = args.all or not (args.volume or args.natr or args.oscillator or args.gap)

    # Lazy import to avoid heavy startup if not needed
    from alerts.checks import _conn as _conn_factory

    symbols = args.symbols
    if not symbols:
        print('DEBUG: loading symbols from DB', flush=True)
        conn = _conn_factory()
        try:
            cur = conn.cursor()
            cur.execute("SELECT symbol FROM watchlist_symbols WHERE is_active = 1")
            symbols = [r[0] for r in cur.fetchall()]
            print('DEBUG: loaded symbols', symbols, flush=True)
        finally:
            conn.close()

    print('DEBUG: starting checks', flush=True)
    alerts_found = 0

    for symbol in symbols:
        print('DEBUG: symbol', symbol, flush=True)
        checks = []
        if run_all or args.volume:
            checks.append(("volume_spike", lambda s=symbol: check_volume_spike(s)))
        if run_all or args.natr:
            checks.append(("natr_spike", lambda s=symbol: check_natr_spike(s)))
        if run_all or args.oscillator:
            checks.append(("oscillator_extremes", lambda s=symbol: check_oscillator_extremes(s)))
        if run_all or args.gap:
            checks.append(("gap_up", lambda s=symbol: check_gap_opening(s)))

        print('DEBUG: symbol', symbol, 'checks', [c[0] for c in checks], flush=True)
        for alert_type, check_fn in checks:
            print('DEBUG: running', alert_type, 'for', symbol, flush=True)
            result = check_fn()
            print('DEBUG: result', alert_type, symbol, result, flush=True)
            if result is None:
                print('DEBUG: continuing', alert_type, symbol, flush=True)
                continue
            from alerts.dto import Alert, DetectionResult
            alert = Alert(
                symbol=result["symbol"],
                alert_type=result["alert_type"],
                severity=result["severity"],
                payload=result.get("payload", {}),
                triggered_at=result.get("triggered_at"),
            )
            detection = DetectionResult(alert=alert)
            if write_alert(detection):
                alerts_found += 1
                logger.info("Queued %s for %s", alert_type, symbol)

    logger.info("Alerts queued: %d", alerts_found)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
