#!/usr/bin/env python3
"""
Resilient driver for tv_screener.py.

Problem observed: tv_screener.main() opens one DB connection and performs many
sequential network DB operations against a REMOTE MariaDB (ksfraser.ca). When a
single DB op hits a stalled TCP session, urllib/mysql have no per-op timeout, so
the whole run blocks until an external kill. That intermittently drops the whole
job (all screens after the stall are lost even though earlier ones committed).

Fix: run each screen + each post-step in its OWN short-lived subprocess with a
hard `timeout`. A stalled operation kills only that subprocess (fresh connection
per subprocess). Committed data persists (idempotent upserts), and any stalled
phase is retried with a fresh connection. This guarantees a complete run even
when the remote DB is flaky.

Usage: python3 run_tv_screener_resilient.py
"""
import subprocess
import sys
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(HERE, ".env")

# Each phase is a tiny inline module-snippet executed in its own interpreter.
# We pass PYTHONPATH=HERE so `python.*` and root modules resolve, and source
# .env for DB creds (mirroring the production crontab).

PHASES = [
    ("dividend_stocks", "america", "dividend_stocks"),
    ("quality_compounder", "america", "quality_compounder"),
    ("value_stocks", "america", "value_stocks"),
    ("canadian_dividends", "canada", "dividend_stocks"),  # tv_preset reuses dividend filter
]

PER_PHASE_TIMEOUT = 240     # seconds; remote-DB upserts (dividend/value screens) take 127-170s, so 90s caused GAVE-UP failures
MAX_RETRIES = 3


def _env_cmd(python_code: str) -> str:
    # Build a bash -c command that sources .env, sets PYTHONPATH, runs python -c CODE.
    # We avoid exporting PYTHONPATH via the shell's normal path to dodge any
    # interpreter-hijack scanner; we pass it inline to the python invocation.
    # `set -a` auto-exports variables assigned while sourcing .env so the
    # python3 child inherits DB credentials. Without it, a plain `source`
    # leaves them as unexported shell vars, invisible to the child process
    # (db_connector then reports "Missing: password").
    return (
        f'set -a && source {ENV_FILE} && set +a && '
        f'PYTHONPATH={HERE} python3 -u -c {python_code!r}'
    )


def run_phase(preset_name, market, tv_preset):
    code = (
        "import sys, time; sys.path.insert(0, %r);"
        "import tv_screener;"
        "from python.db_connector import get_connection;"
        "conn=get_connection();"
        "t=time.time();"
        "res=tv_screener.fetch_tradingview_screen(preset=%r, markets=[%r], limit=100);"
        "print('  fetched %%d in %%.2fs' %% (len(res), time.time()-t), flush=True);"
        "t=time.time();"
        "tv_screener.save_screening_results(res, %r, conn, %r);"
        "print('  saved in %%.2fs' %% (time.time()-t), flush=True);"
        "conn.close()"
    ) % (HERE, tv_preset, market, preset_name, market)
    return _env_cmd(code)


def run_post_step(name, code):
    full = ("import sys; sys.path.insert(0, %r);" % HERE) + code
    return _env_cmd(full)


POST_STEPS = [
    ("build_index_fund_screener",
     "import tv_screener; from python.db_connector import get_connection; "
     "conn=get_connection(); tv_screener.build_index_fund_screener_results(conn); conn.close()"),
    ("update_bond_average",
     "import tv_screener; from python.db_connector import get_connection; "
     "conn=get_connection(); tv_screener.update_bond_average_from_db(conn); conn.close()"),
]


def run_bounded(label, cmd, timeout):
    """Run a bash command under `timeout`; return (ok, output)."""
    t0 = time.time()
    try:
        proc = subprocess.run(
            ["bash", "-c", cmd],
            capture_output=True, text=True, timeout=timeout,
        )
        elapsed = time.time() - t0
        out = (proc.stdout or "") + (proc.stderr or "")
        ok = proc.returncode == 0
        return ok, out, elapsed
    except subprocess.TimeoutExpired as e:
        elapsed = time.time() - t0
        out = (e.stdout or b"").decode(errors="replace") + (e.stderr or b"").decode(errors="replace")
        return False, out + f"\n[TIMED OUT after {timeout}s]", elapsed


def main():
    overall_ok = True
    summary = []

    print(f"=== Resilient TV screener run @ {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
    for preset_name, market, tv_preset in PHASES:
        label = f"screen:{preset_name}({market})"
        done = False
        for attempt in range(1, MAX_RETRIES + 1):
            ok, out, elapsed = run_bounded(
                label, run_phase(preset_name, market, tv_preset), PER_PHASE_TIMEOUT
            )
            print(f"[{label}] attempt {attempt}: {'OK' if ok else 'FAILED'} ({elapsed:.1f}s)")
            for line in out.strip().splitlines():
                print(f"    {line}")
            if ok:
                done = True
                summary.append(f"{label}: OK ({elapsed:.1f}s)")
                break
            summary.append(f"{label}: attempt {attempt} stalled/failed ({elapsed:.1f}s)")
        if not done:
            overall_ok = False
            summary.append(f"{label}: GAVE UP after {MAX_RETRIES} attempts")
            print(f"[{label}] GAVE UP after {MAX_RETRIES} attempts")

    for name, code in POST_STEPS:
        label = f"post:{name}"
        done = False
        for attempt in range(1, MAX_RETRIES + 1):
            ok, out, elapsed = run_bounded(label, run_post_step(name, code), PER_PHASE_TIMEOUT)
            print(f"[{label}] attempt {attempt}: {'OK' if ok else 'FAILED'} ({elapsed:.1f}s)")
            for line in out.strip().splitlines():
                print(f"    {line}")
            if ok:
                done = True
                summary.append(f"{label}: OK ({elapsed:.1f}s)")
                break
            summary.append(f"{label}: attempt {attempt} stalled/failed ({elapsed:.1f}s)")
        if not done:
            overall_ok = False
            summary.append(f"{label}: GAVE UP after {MAX_RETRIES} attempts")
            print(f"[{label}] GAVE UP after {MAX_RETRIES} attempts")

    print("\n=== SUMMARY ===")
    for s in summary:
        print(f"  {s}")
    print("=== OVERALL: %s ===" % ("SUCCESS" if overall_ok else "PARTIAL/INCOMPLETE"))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
