# Cron queue processor — run record (2026-11-09 06:51 UTC)

Processor: `/home/ksf_stockmarket/ksf_stockmarket/cron_queue.py` (MariaDB
`ksfraser_stock_market`.`event_queue`). The user-supplied workdir
`/root/Documents/stockmarket/php/stockmarket-app` does not exist (decoy — extra
`/php` segment); fallback to the canonical dev-tree processor.

## Subcommand results

- `python3 cron_queue.py cancel-dupes`
  - stdout: `No pending jobs.`
  - exit code: 0

- `python3 cron_queue.py run --limit 5`
  - stdout: `Queue empty — nothing to retry.`
  - exit code: 0

## Live `event_queue` tally (independent re-query)

    status tally:
      cancelled: 81452
      completed: 1237
      running: 15
    PENDING=0, FAILED=0

## Conclusion

Both commands exited 0 and printed the exact "nothing pending" message. Zero
jobs were run. The 15 `running` rows are stale abandoned claims (event_type
`prices_loaded`, claimed ~2026-11-08); they are invisible to both subcommands
(`cancel-dupes` only touches `pending`, and `run`'s claim() requires
`status='pending'`), so they are not candidates for this run.

## Operational item (separate from delivered body)

Abandoned `running` backlog: 15 `prices_loaded` rows. Not folded into the
empty-queue verdict; recorded here and to `/tmp/cron_alert.log` for the
scheduled-job context.
