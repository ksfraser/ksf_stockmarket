# CFI DCF Valuation Methodology

> Aligned with **Corporate Finance Institute (CFI)** 8-Step Discounted Cash Flow (DCF) process.
> Reference: https://corporatefinanceinstitute.com/resources/valuation/dcf-model-guide/

---

## Overview

A Discounted Cash Flow (DCF) model is a financial model used to value a business by
forecasting its future cash flows and discounting them back to present value using the
time value of money. The DCF is widely considered the most theoretically sound valuation
method because it relies on the fundamental principle that an asset is worth the present
value of its expected future benefits.

---

## The 8-Step DCF Process (CFI)

### Step 1 — Project Unlevered Free Cash Flows (UFCFs)

Unlevered Free Cash Flow = EBIT × (1 − t) + D&A − CapEx − Change in NWC

- **EBIT**: Earnings before interest and taxes
- **t**: Corporate tax rate
- **D&A**: Depreciation & amortization (non-cash add-back)
- **CapEx**: Capital expenditures required to maintain operations
- **NWC**: Net working capital changes

Forecast UFCFs for a **5-year explicit period** (sometimes 4–10 years depending on
industry stability), then compute a terminal value.

---

### Step 2 — Calculate the Discount Rate (WACC)

Weighted Average Cost of Capital (WACC) is the required return on the firm's capital
structure.

WACC = (E/V × Re) + (D/V × Rd × (1 − t))

- **E**: Market value of equity
- **D**: Market value of debt
- **V**: E + D (total capital)
- **Re**: Cost of equity (via CAPM: Rf + β × (Rm − Rf))
- **Rd**: Cost of debt (yield to maturity or coupon rate)
- **t**: Marginal tax rate

Use 10–15% for most public equities as rough guidance; always compute from first principles.

---

### Step 3 — Determine the Terminal Value

Two approaches:

| Approach | Formula | Notes |
|---|---|---|
| **Exit Multiple (TEV/EBITDA)** | TV = TEV/EBITDA multiple × Year-5 EBITDA | Market-based; use comparable multiples |
| **Perpetuity Growth (Gordon)** | TV = FCFn / (WACC − g) | g = long-term growth rate (≤ GDP growth ~2–3%) |

Always compute both and reconcile to ensure reasonableness.

---

### Step 4 — Discount Cash Flows to Present Value

PV = ∑(FCFt / (1 + WACC)^t) + TV / (1 + WACC)^n

Where:
- t indexes each forecast year (1–n)
- n = length of explicit forecast period

Each year's UFCF and the terminal value are discounted separately.

---

### Step 5 — Compute Enterprise Value

**Enterprise Value (EV)** = ∑(Discounted UFCFs) + Discounted TV

Subtract net debt to arrive at equity value:
**Equity Value** = EV − Net Debt

Divide by diluted shares outstanding to get **Intrinsic Value Per Share**.

---

### Step 6 — Perform Sensitivity and Scenario Analysis

Key sensitivities:
- **WACC ± 200 bps** vs. **Terminal Growth ± 100 bps**
- Best-case / base-case / worst-case FCF paths
- Sensitivity table (heat map) showing implied share price under each combination

Scenario ramps (e.g., optimistic vs. conservative revenue CAGR) validate the range.

---

### Step 7 — Validate Assumptions (Sanity-Check)

Compare DCF result to:
- **Comparable companies (comps)** — public multiples
- **Precedent transactions** — recent M&A multiples
- **Trading multiples** — current market price vs. intrinsic value

Derive implied FCF growth or multiple from current price to see which assumption must
be true. A DCF should never produce a wildly outlier result without clear justification.

---

### Step 8 — Document the Model

Final deliverables:
- **DCF model file** with assumptions clearly separated from formulas
- **Cover page** with modeler name, date, purpose
- **Assumptions table**: revenue growth, margins, WACC components, terminal inputs
- **Sensitivity analysis** chart
- **Executive summary**: intrinsic value range, recommendation, key risks

---

## Financial Dictionary (DCF Terms)

| Term | Definition |
|---|---|
| **CapEx (Capital Expenditures)** | Funds used to acquire or upgrade physical assets (equipment, property). Reducing FCF. |
| **Change in NWC** | Increase in accounts receivable + inventory minus accounts payable. Reduces FCF. |
| **Depreciation & Amortization (D&A)** | Non-cash accounting charge added back to EBIT to compute FCF. |
| **DCF (Discounted Cash Flow)** | Valuation method discounting expected future cash flows to present value. |
| **EBIT (Earnings Before Interest and Taxes)** | Operating profit figure used as starting point for UFCF. |
| **Enterprise Value (EV)** | Total value of a business (equity + net debt). |
| **FCF (Free Cash Flow)** | Cash available to all capital providers after reinvestment needs. |
| **Gordon Growth Model** | Terminal value formula using a constant perpetual growth rate. |
| **Marginal Tax Rate (t)** | Tax rate applied to incremental taxable income. |
| **NOPAT (Net Operating Profit After Tax)** | EBIT × (1 − t), the after-tax operating profit. |
| **Perpetuity Growth Rate (g)** | Long-run growth rate at which FCF is expected to grow into perpetuity. |
| **Risk-Free Rate (Rf)** | Return on default-free government bond (e.g., 10Y Treasury). |
| **Terminal Value (TV)** | Value of all cash flows beyond the explicit forecast period. |
| **UFCF (Unlevered Free Cash Flow)** | FCF before interest payments; flows to both debt and equity holders. |
| **WACC (Weighted Average Cost of Capital)** | Blended required return across equity and debt capital. |

---

## Integration Notes

- Store DCF models under `ksfii_app/CODE/docs/financial-modeling/cfi-reference.md`.
- Link from each stock detail page to a per-symbol DCF model using the extension stub
  defined in user-story **US-DCF-001**.
- Rebase terminal growth assumptions annually based on updated GDP/consensus forecasts.

---
## Sources

- Corporate Finance Institute — Valuation: https://corporatefinanceinstitute.com/resources/valuation/
- Corporate Finance Institute — DCF Model Template: https://corporatefinanceinstitute.com/resources/templates/excel-models/dcf-model-template/

---
*Document control: versioned with KSF documentation. Last updated 2026-07-28.*
