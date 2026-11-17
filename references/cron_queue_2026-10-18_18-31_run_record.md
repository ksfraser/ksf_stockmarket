# Cron queue processor — run record (2026-10-18 18:31 UTC)

Verified against the remote MariaDB (ksfraser.ca / ksfraser_stock_market) with
vault-decrypted `db_password`. Live tally is independent of the queue processor:

    status tally:
      cancelled: 71708
      completed: 1024
      running: 27
    PENDING=0

The 27 `running` rows are stale abandoned claims (~2026-06-28); they are
invisible to both subcommands and never candidates for cancel-dupes/run.

## Subcommand results

- `python3 cron_queue.py cancel-dupes`
  - stdout: `No pending jobs.`
  - exit code: 0

- `python3 cron_queue.py run --limit 5`
  - stdout: `Queue empty — nothing to retry.`
  - exit code: 0

Both exited 0 and printed the exact "nothing pending" messages — the queue is
genuinely empty. No per-job report applicable.
