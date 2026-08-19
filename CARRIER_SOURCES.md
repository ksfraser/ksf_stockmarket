# Seg-Fund Carrier Sources & Ingestion Status

Live DB: `seg_funds` on 192.168.1.102. Carrier column values used below.
Counts as of 2026-08-18.

## Status
| Carrier | Rows | Source | Status |
|---------|------|--------|--------|
| BMO | 292 | (prior) | done |
| Beneva | 15 | Brokerage-Beneva-rates.pdf | done |
| Canada Life | 2,474 | FundPerformance.pdf (Jul 31 2026) | done |
| Manulife | 142 | (prior) | done |
| RBC | 34 | Lipper SPA — blocked | pending export from Kevin |
| Sun Life | 94 | (prior) | done |
| Empire Life | 0 | class-segs (JS) + Fund Facts PDFs | pending |
| Equitable | 119 | Fundata EGIF (https://equitablelife.fundata.com/?product=EGIF&language=en) | done (2026-08-18) |
| iA (Industrial Alliance) | 0 | ia.ca/funds-performance | pending [LATER] |

## Source URLs
### Empire Life
- Class seg funds (landing, JS): https://www.empire.ca/funds/discontinued/class-segs
- Discontinued products index: https://www.empire.ca/advisor/investment-products/discontinued-products
  - Fund Codes for Closed Products (PDF): https://www.empire.ca/docs/pdf/FS-FundSERVCodesClosed-EN-web.pdf
  - Portfolio Funds Investor Profile Questionnaire (PDF): https://www.empire.ca/docs/pdf/PortfolioFundsInvestorProfileQuestionnaire-EN-web.pdf
- Per-product Fund Facts: elite, class, CP21, CP2, CP (under /funds/discontinued/)
- Fund pages: https://funds.empire.ca/seg-funds/en-US/DSEG-a etc.

### Equitable
- Product page: https://www.equitable.ca/products/investments/segregated-funds
- Fundata fund search (EGIF): https://equitablelife.fundata.com/?product=EGIF&language=en
  - "Download Performance Report" export available on page
  - Fund Facts PDFs: https://equitablelife.fundata.com/PDFReports/FundFacts/<id>?FF=2&language=en

### iA (LATER — add to KB/processes)
- Seg fund product: https://ia.ca/individuals/investment-products/segregated-funds
- Seg fund performance: https://ia.ca/funds-performance
- Retirement calculator (incorporate if not already): https://ia.ca/retirement-calculator
- Financial Compass (KYC/FNA-like): https://ia.ca/financial-compass

## Carrier calculators / questionnaires to fold into KYC/FNA
### Empire Life (8)
- Investor Profile Questionnaire: https://www.empire.ca/forms-tools/investor-profile-questionnaire
- RRSP Calculator: https://www.empire.ca/forms-tools/rrsp-calculator
- RRSP vs Mortgage Calculator: https://www.empire.ca/forms-tools/rrsp-vs-mortgage-calculator
- RRIF Calculator: https://www.empire.ca/forms-tools/rrif-calculator
- LIF Calculator: https://www.empire.ca/forms-tools/lif-calculator
- Investment Growth Calculator: https://www.empire.ca/forms-and-tools/investment-growth-calculator
- Budget Calculator: https://www.empire.ca/forms-and-tools/budget-calculator
- How Long Will My Money Last: https://www.empire.ca/forms-and-tools/how-long-will-my-money-last

### iA (LATER)
- Retirement Calculator: https://ia.ca/retirement-calculator
- Financial Compass: https://ia.ca/financial-compass

## Notes
- Fundata portals (Canada Life, Equitable, iA) are SPAs; prefer the "Download Performance Report"
  / Fund Facts PDF export over scraping the rendered table.
- Empire Life class-segs is closed to new policies (Oct 31 2014) — only existing clients; still
  ingest for historical/holdings reference.
- KYC/FNA infra already exists in ksfii_app: FNACalculationService, RetirementCalculator
  (ksf_retirement), BudgetCalculatorService. Empire/iA tools should map onto these, not be
  re-implemented from scratch.
