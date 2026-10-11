# Background launch & hang-diagnosis for cron runs

## Problem 1 — fire-and-forget guard blocked
Cron guard commands commonly use `setsid bash -c '... &'` to fire a long job
while returning immediately (creating a lock, then launching a detached refresh).
Hermes blocks shell-level background wrappers (`nohup`/`disown`/`setsid`) in
foreground `terminal` calls:
`Foreground command uses shell-level background wrappers ... Use terminal(background=true) so Hermes can track the process`.

## Pattern A — split guard + tracked launch
```bash
# Step 1 (foreground terminal call): guard + branch stdout
cd /repo && for v in DB_HOST DB_NAME DB_USER DB_PASS DB_PASSWORD DB_CHARSET DB_PORT; do
  val=$(grep "^$v=" .env 2>/dev/null | head -1 | cut -d= -f2-); [ -n "$val" ] && export "$v=$val"; done
ASOF=$(python3 -P -c "..." 2>/dev/null)
if [ -f /tmp/job.lock ]; then echo "SKIP_CONCURRENT (last as_of=$ASOF)";
else touch /tmp/job.lock; echo "LAUNCHED (refreshing; previous as_of=$ASOF)"; fi

# Step 2 (terminal background=true, notify_on_complete=true): the detached half
cd /repo && python3 -P scripts/run_job.py >> /tmp/job.log 2>&1; rm -f /tmp/job.lock
```
Key points:
- The branch `echo` in Step 1 **IS** the command's stdout — capture and report it.
- Hermes keeps the Step-2 process (and its child worker) alive across turns; the
  `rm -f lock` runs on completion, so the lock self-clears and future runs won't
  be stuck `SKIP_CONCURRENT`.
- Never start Step 2 if the lock already exists (would double-run / race).

## Problem 2 — false "hung" read on a background run
The PID returned by `terminal(background=true)` for a `bash -lic 'python ...; rm lock'`
command is the **shell**, not the worker. The shell shows `do_wait` / 0% CPU /
tiny RSS because it's just `wait()`-ing on its child. This looks like a hang but isn't.

## Pattern B — diagnose the real worker child
```bash
# parent = the bash -lic ... PID returned by terminal()
ps -o pid,ppid,pgid,sid,stat,wchan,cmd -p <parent>
# find the real worker child:
CHILD=$(pgrep -P <parent>)
ps -o pid,etime,time,%cpu,rss,stat,wchan,cmd -p $CHILD
# its real output (redirected to a file, NOT the Hermes pipe):
tail -n 20 /tmp/job.log
# session check (worker survives the turn if SID==parent and Hermes tracks parent):
ps -o pid,ppid,pgid,sid -p $CHILD
```
Worker is healthy if: `%CPU` > 0, `TIME` accumulating, `STAT` R/S, RSS
stable/growing, and log lines advancing. The parent's `do_wait`/0% CPU is
expected and NOT a hang. Only if the **child** shows 0% CPU AND no log progress
for minutes is it a real hang (blocked on DB/network) — then kill it and
investigate the script.

## Worked example (lipper scoring cron)
- Guard returned `LAUNCHED (refreshing; previous as_of=2026-08-27)`.
- Worker PID 236938: `STAT=R`, ~60% CPU, `TIME=00:03:22` over 5m+, RSS ~198MB,
  `wchan=wait_w` — genuine progress over 3,426 symbols.
- Parent 236894 (shell) showed `do_wait`/0% CPU — initially misread as a hang;
  resolved by inspecting the child (Pattern B).
- Log `/tmp/lipper_cron.log` carried only the initial
  `as_of: 2026-08-27 | symbols with attributes & prices: 3426` line because the
  script emits a summary only at the end — expected mid-run.
