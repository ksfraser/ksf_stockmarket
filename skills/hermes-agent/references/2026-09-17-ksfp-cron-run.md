# 2026-09-17 Cron Run — KSFP (K.S. Fraser Piping) — Pipeline Execution Notes

Business: K.S. Fraser Piping (bagpipe instruction, pipe band performance, recruitment, highland dress services) — Alberta.
Pipeline: SCAN → DEDUP → SCORE → REPORT (CRM/CONTENT/APPROVAL/POST implied; delivery via final response body).

## Execution Path Confirmed

- Primary scanner (`reddit_scanner.py`) and fallback (`workflow.py`) both skipped — expected timeout path under cron (exit 124).
- Effective primary: `web_search` multi-source fallback (as designed in skill).
- Sources queried: Reddit (5), General web (5), Forums/directories (2), Facebook (2).
- Results: 5 candidates; 4 new unique leads; 1 duplicate excluded by dedup DB.

## Leads Produced (new, score ≥3)

| ID | Source | Intent | Score | Age / Freshness |
|---|---|---|---|---|
| ksfp-lead-001 | Facebook (AskCalgarians group) | seeking_lessons (7-year-old beginner) | 5 | 2 days — fresh |
| ksfp-lead-003 | Facebook (CDPB Society) | recruitment_opportunity (band recruiting + beginner classes) | 4 | 0 days — fresh |
| ksfp-lead-004 | Web (BagpipeEvents Alberta calendar) | event_opportunity (Canmore, Calgary Celtic, Red Deer, Edmonton events) | 4 | 0 days — fresh |
| ksfp-lead-002 | Reddit (r/Calgary) | hiring_performer (curling event hire, older) | 3 | 382 days — older signal |

Excluded (duplicate, below threshold):
- `ksfp-lead-005` — Reddit `r/bagpipes` "Considering joining a pipeband" (duplicate URL in DB, score 2).

## Dedup DB Handling Confirmed

- DB: `/root/.hermes/cache/scan_dedup.db`
- Live schema inspected before insert (`sqlite3 .schema scan_dedup`) — key columns: `url` (UNIQUE), `author`, `source`, `subreddit`, `title`, `date_scanned`, `lead_score`, `intent`, `products_interest`, `location`, `notes`.
- Insert matched live schema; no `OperationalError`.
- Dedup check: exact URL first; duplicate skipped; others inserted successfully.

## Key Workarounds Applied (from skill documentation)

- Scanner timeout: did NOT retry; went straight to web_search.
- `execute_code` blocked: used `write_file` + `terminal` (wrote scan JSON, executed Python insert via terminal).
- Discord delivery: did NOT use raw curl/webhook; final response delivered via cron auto-delivery; `hermes send` skipped intentionally (auto-delivery conflict).
- SMTP: not attempted (no delivery failure conditions); file saved to `/tmp/ksfii_email.txt` as combined report.

## Business Variant Confirmation

This run validates the "Business variant — non-financial lead response" section of the skill. KSFP (instruction/performance/recruitment) uses:
- Generic intent signals ("looking to learn", "beginner", "recruiting") instead of financial ones ("renewal shock", "advisor").
- Recruitment/band-specific content templates rather than insurance/broker templates.
- Event-opportunity scoring applied to Alberta highland events.

## Pipeline Artifacts

- `/tmp/ksfp_scan_posts.json` — 5 entries (scanned posts with scores and notes).
- `/tmp/ksfii_email.txt` — final combined report (reused filename per pipeline convention; content KSFP-specific).
- `/root/.hermes/cache/scan_dedup.db` — 4 new rows inserted.

## Lesson for Skill Maintenance

- Web_search multi-source approach reliably produces leads when single API scanners time out.
- Dedup DB schema must be inspected live before insert — never assume column names from JSON format.
- Business-variant execution works with minimal adjustment to query templates and intent categories; keep the pipeline stage structure unchanged.
