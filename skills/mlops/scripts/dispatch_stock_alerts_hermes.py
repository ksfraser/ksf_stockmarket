#!/usr/bin/env python3
"""Dispatch pending stock alerts to a Discord channel via the `hermes send` CLI.

This is the working equivalent of the protocol's `send_message` tool, which is absent
from cron agent toolsets in this deployment. `hermes send` reuses the Discord bot token
from `.env` and needs no running gateway.

Usage:
  python3 dispatch_stock_alerts_hermes.py [--channel #stock-sell-alerts] \
        [--consumer /root/.hermes/scripts/sqlite_alert_consumer.py] [--skip ID1 ID2 ...]

Prints successfully-delivered alert IDs (one per line) on stdout; diagnostics on stderr.
Pipe stdout straight into the consumer's --commit step, e.g.:
  IDS=$(python3 dispatch_stock_alerts_hermes.py)
  python3 /root/.hermes/scripts/sqlite_alert_consumer.py --commit $IDS
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile

CONSUMER = "/root/.hermes/scripts/sqlite_alert_consumer.py"
CHANNEL = "#stock-sell-alerts"
BLOCK_RE = re.compile(r"@@ALERT@@\s+id=([^\n]+)\n(.*?)\n@@END@@", re.DOTALL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", default=CHANNEL)
    ap.add_argument("--consumer", default=CONSUMER)
    ap.add_argument("--skip", nargs="*", default=[],
                    help="Alert IDs already delivered; skip them (still counted as done).")
    args = ap.parse_args()

    res = subprocess.run([sys.executable, args.consumer, "--format"],
                         capture_output=True, text=True)
    if "[NO ALERTS]" in res.stdout:
        print("[NO ALERTS]", file=sys.stderr)
        return
    blocks = [(m.group(1).strip(), m.group(2).strip())
              for m in BLOCK_RE.finditer(res.stdout)]
    print("Parsed %d alert block(s)." % len(blocks), file=sys.stderr)

    skip = set(args.skip)
    delivered = []
    for aid, msg in blocks:
        if aid in skip:
            print("SKIP(already sent) %s" % aid, file=sys.stderr)
            delivered.append(aid)
            continue
        tf = os.path.join(tempfile.gettempdir(), "alert_%s.txt" % aid)
        with open(tf, "w") as fh:
            fh.write(msg)
        r = subprocess.run(
            ["hermes", "send", "--to", "discord:%s" % args.channel,
             "--file", tf, "--json"],
            capture_output=True, text=True)
        ok = (r.returncode == 0) and ('"success": true' in r.stdout)
        if ok:
            delivered.append(aid)
            print("OK   %s" % aid, file=sys.stderr)
        else:
            print("FAIL %s rc=%s %s" % (aid, r.returncode,
                  (r.stderr or r.stdout)[:200]), file=sys.stderr)
    for i in delivered:
        print(i)


if __name__ == "__main__":
    main()
