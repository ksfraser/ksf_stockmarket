# 2026-09-18 KSFII Financial Cron Run

## Execution Summary

- **Date:** 2026-09-18
- **Business:** KSFII Financial (insurance/financial advisory)
- **Pipeline:** SCAN → DEDUP → SCORE → CRM → CONTENT → APPROVAL → POST → KB
- **Scanner:** Both `reddit_scanner.py` and `workflow.py` returned 0 / timed out. Web search used as primary data source.
- **Leads found:** 10 qualified (all scored ≥5/10 on 10-point factored model)
- **Delivery:** Email to fraser.ks@gmail.com ✅ | Discord webhook POST to #ksfii ✅

## Scanner Behavior

| Tool | Result |
|------|--------|
| `reddit_scanner.py --business ksfii --min-score 3 --top 10` | 0 posts (exit 0, but empty) |
| `workflow.py --business ksfii --stage scan --min-score 3 --top 10` | Timeout (exit 124, 120s) |

Both scanner paths failed. Web search is confirmed as the effective primary path for this cron execution context.

## Web Search Results

Two rounds of web search were executed:

**Round 1:** `site:reddit.com Alberta insurance financial advisor need life insurance mortgage` + `Alberta Canada buy life insurance best rate financial planning 2026 Reddit forum`

**Round 2:** `site:reddit.com "looking for" OR "recommend" financial advisor OR insurance Alberta Calgary Edmonton 2026` + `site:reddit.com/r/PersonalFinanceCanada life insurance term coverage need advice 2025 2026`

4 Reddit posts were extracted via web_extract for content details.

## Scoring — 10-Point Factored Model

All 10 leads scored using the 10-point factored model (Model B). Distribution:

| Score | Count | Lead Highlights |
|-------|-------|-----------------|
| 10/10 | 8 | CairnMom (Calgary SW FA), HeadReality (Alberta life insurance), Economy-Ad6234 (Calgary life insurance first-time), archer-review (Calgary hourly FA), r/Edmonton auto broker (FRESH), $75k inheritance Edmonton, Alberta life insurance shopper, Calgary fee-based planner |
| 8/10 | 2 | Ulkurz (Edmonton independent FA), mortgage life insurance Alberta |

All 10 qualified (≥5 threshold). No leads were excluded.

## Delivery

### Email
- **Primary:** fraser.ks@gmail.com — SMTP success on first attempt (ksfraser.ca SMTP)
- **Fallback:** Not needed

### Discord
- **Method:** Direct webhook POST to `$DISCORD_KSFII_WEBHOOK`
- **Result:** HTTP 204 (success)
- **Note:** `hermes send` was not required; webhook path works reliably in this execution context

## Report Template Produced

The report at `/tmp/ksfii_report.md` (also saved to `/var/www/stockmarket-app/ksfii_lead_report_2026-09-18.md`) follows this structure:

1. Pipeline status table (all 8 stages with ✅/⏳ status and notes)
2. Scan summary (method, total leads, qualified, new, very recent)
3. Top leads — detailed (10 leads, each with URL, location, age, need, score reasons)
4. Draft responses — Kaplan framework (10 draft Reddit responses)
5. Pipeline notes (scanner, dedup, CRM, content, timeliness)
6. Delivery log

This template is recommended as the standard format for KSFII lead-response reports going forward.

## Key Observations

1. **Fresh lead found:** r/Edmonton "Recommend an insurance broker" was posted same day — auto insurance broker needed in Edmonton. Worth prioritizing.
2. **Evergreen leads are valuable:** Several leads were 1-5 years old but scored highly due to strong intent + location + product signals. The 10-point factored model correctly captures this.
3. **Fee-only/independent preference is a high-value signal:** Multiple Calgary leads specifically asked for fee-only or independent advisors. This signals educated buyers who are harder to reach but higher lifetime value.
4. **Calgary SW is an affluent submarket:** CairnMom specifically asked for SW Calgary — this is a high-income area worth targeted outreach.
5. **$75k inheritance lead (Edmonton):** High-net-worth indicator with clear pain point (idle money, no TFSA/RRSP). Strong cross-sell potential (investment + insurance + tax planning).
