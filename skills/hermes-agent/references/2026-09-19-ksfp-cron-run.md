---
name: ksfii-lead-response
reference_for: 2026-09-19 KSFP execution
---

# 2026-09-19 Cron Run — KSFP (K.S. Fraser Piping) — Pipeline Execution Notes

Business: K.S. Fraser Piping (bagpipe instruction, pipe band performance, recruitment, highland dress services) — Alberta.
Pipeline: SCAN → DEDUP → SCORE → REPORT (delivery via final response body; auto-delivered to discord:1503814224810610811).
Execution mode: Scheduled cron agent with `ksfii-lead-response` skill. No user interaction.

## Execution Path Confirmed

- Primary scanner (`reddit_scanner.py`) timed out (expected, exit 124, 60s). Fallback `workflow.py` skipped (will also time out per documented behavior).
- Effective primary: `web_search` multi-source (Reddit 5 patterns + Web 5 patterns + Forums 1 + Facebook 1 = 12 queries/results).
- DB inspection (`sqlite3 .schema`) performed before insert — confirmed `scan_dedup` table exists with `url UNIQUE`, `date_scanned`, `lead_score`, `intent`, `products_interest`, `location`, `notes`. Insert matched actual schema.

## Scan Results

- Posts collected: 5
- Duplicates (already in DB from 2026-09-12 / 2026-09-17 runs): 4
  - `https://www.facebook.com/CDPBSociety` (Calgary & District Pipes — recruiting, 2025-11-17) — score 4
  - `https://www.cpspipeband.ca/members.html` (CPS Pipe Band — recruiting, 2025-09-01) — score 3
  - `https://www.reddit.com/r/bagpipes/comments/1cz1pmk/considering_joining_a_pipeband` — score 3
  - `https://fcypb.org/` (Foothills Caledonia Youth — open house Oct 6, 2026, 7d old) — score 5
- New leads inserted: 1 (`ksfp-2026-09-19-002` — bagpipes4u.com Calgary lessons listing, 430d old, score 3 at minimum threshold)
- New qualified (≥3): 1 (at threshold — not active pursuit, logged only)

## Key Finding — Fresh Event Signal (Duplicate but Valuable)

The `fcypb.org` entry (Foothills Caledonia Youth Pipe Band open house, Oct 6 2026) is the highest-value signal this run:
- Freshness: 7 days old → high freshness (+2 in Model A, +3 in Model B)
- Intent: `event_opportunity` — youth band recruitment venue
- Score: 5 (hot tier) — but already in DB from 2026-09-17
- Action recommendation: manual follow-up for KSFP — attend/open house presence, beginner instruction referral partnership, or youth-to-adult pipeline collaboration.

This confirms the event-focused scanning pattern remains the most productive path for KSFP domain (same conclusion as 2026-09-19 FHS event-focused scanning reference).

## Scoring Application

- Model A (1-6) applied to new lead (`bagpipes4u.com`): age 430d (old) + single product reference (competitor/business listing) + Calgary AB location + no budget/shopping signal = score 3 (minimum threshold). Not pursued directly.
- The 4 duplicates were not re-scored; their existing DB scores preserved (5, 4, 3, 3).

## Dedup Handling

- Dedup check order: URL exact-match first (`SELECT url FROM scan_dedup WHERE url = ?`), then skip. No title-fallback needed (all 4 duplicates matched by URL).
- New lead (`bagpipes4u.com`) did not exist in DB — inserted cleanly with all 11 schema columns matched.

## Delivery

- Discord: Auto-delivered by cron system to `discord:1503814224810610811`. Final response = this pipeline report.
- Email (SMTP): Not triggered — no new hot/warm leads requiring direct outreach. No SMTP attempt made.
- Fallback file: `/tmp/ksfii_email.txt` saved (combined pipeline report with delivery confirmation).
- No `hermes send` or webhook call attempted (respects cron auto-delivery conflict rules).

## Pipeline Artifacts

- `/tmp/ksfii_scan_posts.json` — 5 entries (scanned results)
- `/tmp/ksfii_email.txt` — final combined pipeline report (KSFP-specific, event signals, delivery notes)
- `/root/.hermes/cache/scan_dedup.db` — updated (1 new row: bagpipes4u.com, score 3)

## Workarounds / Patterns Confirmed

- `execute_code` blocked → used `write_file` + `terminal()` pattern (JSON creation + Python execution + result read-back) — confirmed reliable for this session.
- Scanner timeout path: did NOT retry primary or fallback; went directly to `web_search` — confirmed correct per skill instructions.
- DB live schema inspection before insert: confirmed working; no `OperationalError`.

## Business-Variant Continuity

- KSFP (bagpipe/recruitment) continues to work correctly with the generic pipeline stages.
- Intent signals adapted correctly: `joining_band`, `seeking_lessons`, `event_opportunity` (instead of financial `seeking_insurance`, `renewal_shock`).
- Recruitment/band content framework applied; event-opportunity scoring remains the dominant qualified-lead type for this domain.

## Maintenance Note

- This is the second consecutive KSFP run (2026-09-18 produced 0 qualified new; 2026-09-19 produced 1 at threshold). The 4 duplicates include a very fresh event signal (`fcypb.org`, 7d old). Recommend tracking event-opportunity duplicates separately — if the same event appears in 3+ consecutive runs, it may warrant a dedicated event-tracking mechanism rather than lead duplication.
