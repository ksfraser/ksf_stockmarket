---
name: ksfii-lead-response
reference_for: 2026-09-19 FHS execution
---

# 2026-09-19 FHS Pipeline Execution — Reference

Business: Fraser Highland Shoppe (FHS) — Scottish gifts, kilts, tartan, highland dress, Alberta.
Execution mode: Scheduled cron agent with `ksfii-lead-response` skill.
Scan: Multi-source `web_search` (scanner skipped — expected cron timeout exit 124).
DB: `/root/.hermes/cache/scan_dedup.db` — schema verified live before insert.

Results: 6 posts scanned; 2 new qualified inserted (`fhs-002` Calgary Games event_opportunity score 4; `fhs-003` Calgary Tartan heritage_reference score 3); 1 duplicate skipped (Edmonton kiltmaker, already 2026-09-15 score 5); 3 excluded (<3). No hot (5-6) leads — consistent with FHS domain (event/vendor opportunities dominate over direct forum buying-intent).

Pipeline protocol validated: scanner timeout path, DB schema inspection before insert, `execute_code` blocked → `write_file` + `terminal()` pattern used, flat-array JSON format maintained (workflow.py nested-format issue avoided by manual sqlite3 processing), cron auto-delivery respected (no webhook/API/manual send), email saved to `/tmp/ksfii_email.txt`.

Reference for future FHS runs — event-focused scanning remains the productive path.
