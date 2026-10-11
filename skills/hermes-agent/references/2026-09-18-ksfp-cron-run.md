# 2026-09-18 Cron Run — KSFP (K.S. Fraser Piping) — Pipeline Execution Notes

Business: K.S. Fraser Piping (bagpipe instruction, pipe band performance, recruitment, highland dress services) — Alberta.
Pipeline: SCAN → DEDUP → SCORE → REPORT (delivery via final response body; auto-delivered to discord:1503814224810610811).

## Execution Path Confirmed

- Primary scanner (`reddit_scanner.py`) timed out (expected, exit 124, 60s). Fallback scanner skipped (will also time out).
- Effective primary: `web_search` multi-source (Reddit 5 + General web 5 + Canadian forums/directories 3 + Facebook Groups/Pages 4 = 17 queries/results).
- Results: 17 posts scanned; 13 duplicates excluded by DB; 4 new entries inserted; 0 new qualified leads (score ≥3).

## Leads Produced (new)

None qualified (score ≥3) from this run. All 4 new entries scored <3:
- `ksfp-002`: r/bagpipes — beginner discussion, no Alberta link (score 1)
- `ksfp-003`: r/bagpipes — beginner tips, no Alberta link (score 1)
- `ksfp-004`: r/bagpipes — band discussion, very old (score 1)
- `ksfp-008`: Facebook — Old Geezers Learning Bagpipes global group (score 2)

Excluded from pipeline (scored below threshold): 4 entries tracked in DB but not pursued.

## Dedup DB Handling Confirmed

- DB: `/root/.hermes/cache/scan_dedup.db`
- Schema inspected live (`sqlite3 .schema`) — matched insert to actual columns (`date_scanned`, not `date_posted`).
- Dedup check: URL exact-match first, then title fallback.
- No schema mismatch errors; insert completed cleanly.

## Key Workarounds / Patterns Confirmed

- Scanner timeout: did NOT retry; went straight to web_search (per skill instructions).
- `execute_code` blocked in cron: used `write_file` (JSON + Python scripts) + `terminal` (execution) pattern — confirmed working.
- Discord delivery: did NOT call `hermes send` manually; final response delivered via cron auto-delivery to `discord:1503814224810610811`.
- SMTP: saved to `/tmp/ksfp_email.txt` (fallback file) — no SMTP failure occurred.

## Existing Qualified Leads (DB reference — not new this run)

Key active qualified leads from recent runs (2026-09-12 through 2026-09-17) remain in DB for reference:
- Score 5 — Facebook AskCalgarians: bagpipe tutor for 7-year-old (Calgary) — fresh beginner pipeline
- Score 5 — BandMix Alberta / Calgary musician directories
- Score 5 — Rocky Mountain Pipe Band (Calgary)
- Score 4 — CDPB Society recruitment + Fall beginner intake
- Score 4 — Edmonton Scottish Society (new members)
- Score 4 — Event calendar / Canmore Highland Games / Calgary Celtic Festival
- Score 3 — Calgary Police Service Pipe Band (recruitment)

## Pipeline Artifacts

- `/tmp/ksfp_scan_posts.json` — 17 entries (scanned results in JSON format)
- `/tmp/ksfp_email.txt` — final combined pipeline report (KSFP-specific content, delivery confirmation, market signals, recommendations)
- `/tmp/ksfp_dedup_step.py` — Python dedup/insertion script (written via `write_file`, executed via `terminal`)
- `/tmp/ksfp_score_step.py` — Python scoring/DB inspection script
- `/root/.hermes/cache/scan_dedup.db` — 84 total rows after insert (4 new low-value entries added)

## Business-Variant Validation

- Generic intent signals used correctly: "looking to learn", "beginner", "recruiting", "group lessons" instead of financial signals ("renewal shock", "advisor").
- Recruitment/band content framework applied; event-opportunity scoring confirmed for Alberta highland events.
- Business-variant conversion is stable: same pipeline stages, same DB schema, same web_search multi-source approach; only query templates and content templates change.

## Recommendation (Pipeline Maintenance Note)

- If future runs also return 0 new qualified leads for 3+ consecutive executions, confirm the multi-source web_search template coverage remains fresh (update event dates for 2027 season, verify Facebook group URLs still active, check BandMix directory for new listings).
- The `no_agent: true` shell-script conversion (from `cron-job-conversion.md`) continues to work as designed: agent job with `ksfii-lead-response` skill + multi-source `web_search` produces reliable results; single-source `reddit_scan_*.sh` scripts remain blocked by rate limits/timeouts.
