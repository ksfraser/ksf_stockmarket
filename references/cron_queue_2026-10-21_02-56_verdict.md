2026-10-21 02:56 UTC — cron-queue-runner (scheduled, no-agent)
Commands: python3 cron_queue.py cancel-dupes && python3 cron_queue.py run --limit 5
cancel-dupes: exit 0 → "No pending jobs."
run --limit 5: exit 0 → "Queue empty — nothing to retry."
Corroborating MariaDB tally (ksfraser.ca / ksfraser_stock_market): cancelled=71796 | completed=1030 | running=27 (abandoned, attempts=0, >2mo old) | pending=0 | total=72853
No pending jobs claimed; 27 running rows are stale abandoned claims (invisible to claim() filter). Queue genuinely idle.
