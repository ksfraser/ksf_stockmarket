#!/usr/bin/env python3
"""Deliver `sqlite_alert_consumer.py --format` blocks to the #stock-sell-alerts
Discord webhook from a bare cron/agent context (no Hermes CLI or send_message).

Preference order:
  1. `hermes send --to discord:#stock-sell-alerts --file <msg>` (simplest).
  2. Agent `send_message` tool (`target: discord:#stock-sell-alerts`).
  3. This script — webhook direct with browser User-Agent (Cloudflare 1010 fix).

Why this exists: the default `Python-urllib/X.Y` User-Agent is rejected by
Cloudflare's WAF (error 1010) in front of Discord, so a naive urllib POST 403s.
A non-default (browser-like) UA passes. Webhook POSTs return 204 with NO body,
so you can NOT get the message id back to delete it -- never POST a 'test'
message to verify; GET the webhook URL instead (returns the webhook JSON).

Usage:
  python3 deliver_alert_blocks.py blocks.json
  # blocks.json = JSON array of {"id": "...", "message": "..."}

The blocks file is normally produced by parsing --format output, e.g.:
  python3 sqlite_alert_consumer.py --format | python3 -c '
import sys,json,re
out=sys.stdin.read(); blocks=[]
for c in out.split("@@ALERT@@"):
    c=c.strip()
    if "@@END@@" in c:
        m=re.match(r"id=(\\S+)\\s*(.*?)\\s*@@END@@", c, re.DOTALL)
        if m: blocks.append({"id":m.group(1),"message":m.group(2).strip()})
json.dump(blocks, open("blocks.json","w"), ensure_ascii=False)'

Prints one line per block:  <id> -> HTTP <status>
Exits non-zero if any POST did not return a 2xx status.
"""
import os
import sys
import json
import urllib.request
import urllib.error

ENV_FILES = ('/root/.hermes/alert_webhooks.env', '/root/.hermes/.env')
# Browser-like UA -- confirmed to pass Cloudflare's 1010 WAF block this session.
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def load_env():
    data = {}
    for p in ENV_FILES:
        try:
            with open(p) as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    k, _, v = line.partition('=')
                    data.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        except Exception:
            continue
    return data


def main():
    if len(sys.argv) < 2:
        print("Usage: deliver_alert_blocks.py blocks.json", file=sys.stderr)
        sys.exit(2)

    env = dict(os.environ)
    env.update(load_env())
    url = (env.get('DISCORD_SELL_WEBHOOK')
           or env.get('DISCORD_ALERT_WEBHOOK'))
    if not url:
        print("ERROR: DISCORD_SELL_WEBHOOK / DISCORD_ALERT_WEBHOOK not set",
              file=sys.stderr)
        sys.exit(2)

    with open(sys.argv[1]) as fh:
        blocks = json.load(fh)

    ok = True
    for b in blocks:
        aid = b['id']
        msg = b['message']
        payload = json.dumps({"content": msg}).encode('utf-8')
        req = urllib.request.Request(
            url, data=payload,
            headers={'Content-Type': 'application/json', 'User-Agent': UA},
            method='POST')
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                status = r.status
        except urllib.error.HTTPError as e:
            status = e.code
            ok = False
        except Exception as e:
            status = f"ERR:{e}"
            ok = False
        print(f"{aid} -> HTTP {status}")
        if not str(status).startswith('2'):
            ok = False

    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
