---
name: office-production
description: >
  Complete office production toolkit — build, audit, QC, and refresh spreadsheets and presentations.
  Covers: producing .xlsx files headlessly, auditing spreadsheets for formula errors, building
  QC'd PowerPoint decks, quality-checking IB presentations for number consistency, creating
  reusable PPT template skills, generating strip profiles, populating pitch deck templates,
  refreshing deck numbers, and building financial data packs.
  Use when creating Excel files, auditing models, building or QC'ing PowerPoint decks, checking
  pitch deck number consistency, creating template skills, or generating company strip profiles.
  Triggers on "build xlsx", "generate Excel", "audit this sheet", "check my formulas",
  "create presentation", "build pptx", "check my deck", "QC presentation", "pitch deck quality",
  "number consistency", "PPT template", "strip profile", "company profile", "data pack",
  "financial data pack", "IC data pack".
---

# Office Production Toolkit

Umbrella skill for all spreadsheet and presentation production — build, audit, QC, and refresh.
Each function has a reference file. Load only the reference file(s) needed for the current task.

## Functions & When to Use Each

| Function | Use When | Reference |
|---|---|---|
| **Build .xlsx Headlessly** | Generating Excel files as artifacts in managed-agent sessions | [xlsx-build](#xlsx-build) below |
| **Audit Spreadsheet** | Checking formulas, finding errors, model integrity | [xlsx-audit](#xlsx-audit) below |
| **Clean Data** | Fixing messy data: whitespace, casing, number-as-text, dates, duplicates | `references/clean-data.md` |
| **Build .pptx Headlessly** | Generating PowerPoint decks as artifacts | [pptx-build](#pptx-build) below |
| **Create Template Skill** | Turning a user-provided PPT template into a reusable skill | [ppt-template-create](#ppt-template-create) below |
| **QC Pitch Deck** | Checking number consistency, data-narrative alignment, language polish, visual QC | [deck-qc](#deck-qc) below |
| **Strip Profile** | Generating 1-4 slide company profiles for pitch books | `references/strip-profiles.md` |
| **Populate Pitch Deck** | Filling an IB pitch deck template with data from source files | `references/pitch-deck-population.md` |
| **Refresh Deck Numbers** | Updating numbers across an existing PowerPoint deck | `references/deck-refresh.md` |
| **Data Pack Builder** | Building IC-ready financial data packs from CIMs, filings, etc. | [datapack-builder](#datapack-builder) below |
| **Manual ODF (.odt) Without LibreOffice** | Building a valid `.odt` file artifact when `soffice`/LibreOffice is not installed in the environment | [references/odf-structure.md](references/odf-structure.md) |

---

## xlsx-build

Use when running **headless** (managed-agent / CMA mode) and need to deliver an Excel workbook as a **file artifact**.

### Output contract
- Write to `./out/<name>.xlsx`. Create `./out/` if it does not exist.
- Return the relative path in your final message.

### How to build
Write a short Python script using `openpyxl`:

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

wb = Workbook()
ws = wb.active; ws.title = "Inputs"
ws["B2"] = "Revenue"; ws["C2"] = 1_250_000_000
ws["C2"].font = Font(color="0000FF")  # blue = hardcoded input
calc = wb.create_sheet("DCF")
calc["C5"] = "=Inputs!C2*(1+Inputs!C3)"  # black = formula
wb.save("./out/model.xlsx")
```

### Conventions
- **Blue / black / green font.** Blue = hardcoded input, black = formula, green = cross-sheet link.
- **No hardcodes in calc cells.** Every calculation cell is a formula; every input lives on an Inputs tab.
- **Named ranges** for any value referenced from a deck or memo.
- **Balance checks.** Include a Checks tab (BS balances, CF ties to cash) with TRUE/FALSE.
- **One model per file.** Do not append to an existing workbook unless explicitly asked.

### Row Reference Tracking
Store row numbers when writing data, reference them in formulas:
```python
revenue_row = row
write_data_row(ws, row, "Revenue", revenue_values)
row += 1
# Use stored row numbers in formulas
margin_formula f"=B{ebitda_row}/B{revenue_row}"
```

**Environment:** If `mcp__office__excel_*` tools are available (Cowork plugin mode), use those instead — they drive the user's live workbook. This section is the file-producing fallback for headless runs.

---

## xlsx-audit

Audit formulas and data for accuracy and mistakes. Scope determines depth.

### Step 1: Determine scope
- **selection** — just the currently selected range
- **sheet** — the current active sheet only
- **model** — the whole workbook, including financial-model integrity checks (BS balance, cash tie-out, roll-forwards, logic sanity)

The **model** scope is the deepest — use it for DCF, LBO, 3-statement, merger, comps, or any integrated financial model before sending to a client or IC.

### Step 2: Formula-level checks (ALL scopes)

| Check | What to look for |
|---|---|
| Formula errors | `#REF!`, `#VALUE!`, `#N/A`, `#DIV/0!`, `#NAME?` |
| Hardcodes inside formulas | `=A1*1.05` — the `1.05` should be a cell reference |
| Inconsistent formulas | A formula that breaks the pattern of its neighbors |
| Off-by-one ranges | `SUM`/`AVERAGE` that misses the first or last row |
| Pasted-over formulas | Cell that looks like a formula but is a hardcoded value |
| Circular references | Intentional or accidental |
| Broken cross-sheet links | References to cells that moved or were deleted |
| Unit/scale mismatches | Thousands mixed with millions, % stored as whole numbers |
| Hidden rows/tabs | Could contain overrides or stale calculations |

### Step 3: Model-integrity checks (MODEL scope only)

Identify model type (DCF / LBO / 3-statement / merger / comps / custom):

- **BS balances**: Total Assets = Total Liabilities + Equity (every period)
- **Cash tie-out**: CF Ending Cash = BS Cash (every period)
- **RE rollforward**: Prior RE + Net Income − Dividends = Current RE
- **CF sums**: CFO + CFI + CFF = Δ Cash
- **Income Statement**: Revenue build ties to segments, tax = pre-tax × rate, share count ties to dilution
- **Logic & reasonableness**: Growth rates, margins, terminal value dominance, hockey-stick projections

### Model-type-specific bugs

**DCF:** Discount rate wrong period, TV not discounted, WACC uses book values, FCF includes interest, tax shield double-counted.

**LBO:** Debt paydown doesn't match cash sweep, PIK interest not accruing, management rollover missing, exit multiple on wrong EBITDA.

**Merger:** Accretion/dilution uses wrong share count, synergies not phased, purchase price allocation doesn't balance, foregone interest missing.

**3-statement:** WC changes wrong sign, D&A doesn't match PP&E, debt maturity doesn't match principal payments.

### Step 4: Report

Output a findings table with Severity (Critical / Warning / Info). **Don't change anything without asking.**

---

## pptx-build

Use when running **headless** and need to deliver a PowerPoint deck as a **file artifact**.

### Output contract
- Write to `./out/<name>.pptx`. Create `./out/` if it does not exist.
- Return the relative path.

### How to build
Write a short Python script using `python-pptx`:

```python
from pptx import Presentation
from pptx.util import Inches, Pt

prs = Presentation("./templates/firm-template.pptx")  # if template provided
# or: prs = Presentation()
slide = prs.slides.add_slide(prs.slide_layouts[5])  # title-only
slide.shapes.title.text = "Valuation Summary"
prs.save("./out/pitch-target.pptx")
```

### Conventions
- **One idea per slide.** Title states the takeaway; body supports it.
- **Every number traces to the model.** Footnote the sheet and cell.
- **Use the firm template** when one is mounted at `./templates/`; otherwise default layouts.
- **Charts**: prefer embedding a PNG rendered from the model over native pptx charts when fidelity matters.
- **No external sends.** This skill writes a file; it never emails or uploads.

**Environment:** If `mcp__office__powerpoint_*` tools are available (Cowork plugin mode), use those instead. This section is the file-producing fallback for headless runs.

---

## ppt-template-create

Use ONLY when a user wants to turn their PowerPoint template into a **reusable skill** that can generate presentations later. If the user just wants to create a presentation, use the pptx-build section above.

### Workflow
1. **User provides template** (.pptx or .potx)
2. **Analyze template** — extract layouts, placeholders, dimensions
3. **Initialize skill** — use the `skill-creator` skill to set up the skill structure
4. **Add template** — copy .pptx to `assets/template.pptx`
5. **Write SKILL.md** — be self-contained with all instructions embedded
6. **Create example** — generate sample presentation to validate
7. **Package** — use the `skill-creator` skill to package into a .skill file

### Analyzing placeholders
```python
from pptx import Presentation
prs = Presentation(template_path)
for idx, layout in enumerate(prs.slide_layouts):
    for ph in layout.placeholders:
        left = ph.left / 914400; top = ph.top / 914400
        width = ph.width / 914400; height = ph.height / 914400
```

**CRITICAL:** Extract the OBJECT placeholder's `y` position from content layouts — this indicates where content actually starts (not the subtitle's end position).

### Generated SKILL.md Requirements
- Self-contained with all instructions embedded
- Document exact placeholder positions (x, y, width, height in inches)
- Content area boundaries for custom shapes/tables/charts
- Include Python examples for cover and content slides
- Template bundled at `assets/template.pptx`

---

## deck-qc

Perform comprehensive QC on a presentation across four dimensions. Read every slide, then report findings.

### Environment check
- **Add-in** — read from the live open deck
- **Chat** — read from the uploaded `.pptx` file

### Workflow

**1. Read the deck.**
Extract text from every slide with slide-level attribution. Write to a file for script processing:
```
## Slide 1
[content]

## Slide 2
[content]
```

**2. Number consistency.**
Run the extraction script:
```bash
python scripts/extract_numbers.py /tmp/deck_content.md --check
```
It normalizes units ($500M vs $500MM → same number), categorizes values, and flags conflicting values across slides.

Also verify: calculations correct, unit style consistent ($M or $MM, not mixed), time periods aligned.

**3. Data-narrative alignment.**
Map claims to supporting data. Check: trend statements match chart direction, market position claims supported by data, plausibility of figures.

**4. Language polish.**
Scan for casual phrasing, contractions, exclamation points, vague quantifiers, inconsistent terminology.
See `references/ib-terminology.md` for replacement patterns.

**5. Visual and formatting QC.**
Check: missing chart sources, missing axis labels, typography inconsistencies, number formatting drift, footnote gaps.

### Output
Use `references/ib-report-format.md` for the report structure. Categorize by severity:
- **Critical** — number mismatches, factual errors, data contradicting narrative
- **Important** — language, missing sources, terminology drift
- **Minor** — font sizes, spacing, date formats

---

## datapack-builder

Build professional, standardized financial data packs for PE, IB, and asset management. Transform data from CIMs, offering memorandums, SEC filings, web search into polished Excel workbooks ready for IC review.

### Critical Success Factors
1. **Data Accuracy (Zero Tolerance):** Trace every number to source. Formula-based calculations only. BS balances. CF ties to BS changes.
2. **Format Rules:**
   - Financial data (money) → Currency format with $
   - Operational data (counts) → Number format, NO $
   - Percentages → Percentage format
   - Years → Text format (prevents comma insertion)
3. **Font colors (mandatory):** Blue = hardcoded input, Black = formula, Green = cross-sheet link

### Standard 8-tab Structure
1. Executive Summary
2. Historical Financials (Income Statement)
3. Balance Sheet
4. Cash Flow Statement
5. Operating Metrics
6. Property/Segment Performance
7. Market Analysis
8. Investment Highlights

### Workflow Phases
1. **Document Processing:** Analyze source, extract financials, operating metrics, market data
2. **Normalization:** Standardize accounting, apply format logic, document adjustments
3. **Build Excel Workbook:** Create tab structure with proper formatting, insert all-formula calculations
4. **Scenario Building (if projections):** Management case, base case (risk-adjusted), downside case
5. **QC & Validation:** Data accuracy, format consistency, structure/completeness, documentation
6. **Delivery:** Final check, proper naming: `CompanyName_DataPack_YYYY-MM-DD.xlsx`

### Common EBITDA Adjustments
- Restructuring charges (add back if non-recurring)
- Stock-based compensation (add back per PE standard)
- Acquisition-related costs
- Legal settlements (assess recurrence risk)
- Asset sales/impairments
- Related party adjustments (normalize to market rates)

## Absorbed skills (consolidated modules)

### PowerPoint (powerpoint)

Standalone PPTX skill absorbed here. Core operations: reading content via `markitdown`, editing from template, creating from scratch with `pptxgenjs`.

**Scripts**: `scripts/add_slide.py`, `scripts/clean.py`, `scripts/thumbnail.py`, `scripts/office/unpack.py`, `scripts/office/pack.py`, `scripts/office/soffice.py`

**Key patterns**
- Read: `python -m markitdown presentation.pptx`
- Edit: unpack → manipulate → pack workflow
- QA: convert to images via `pdftoppm` and inspect visually; ALWAYS use subagents

### PDF editing & OCR (nano-pdf, ocr-and-documents)

Standalone PDF tooling absorbed here: `nano-pdf` CLI for text edits, and `markitdown`/`pymupdf` for scan-to-text extraction.

**Commands**
- `nano-pdf edit <file.pdf> <page> "<instruction>"`
- `python -m markitdown <file.pdf>`

**Pitfalls**
- Page numbers may be 0-based or 1-based depending on version
- `nano-pdf` uses an LLM under the hood and requires an API key
- Complex layouts may need manual adjustment after automated edits

### Rules

1. Always audit .pptx output via subagent after first render
2. Always verify PDF edits by re-reading file size and previewing
3. Prefer .pptx `clean.py` for quick reflow fixes before full rebuilds
EOF
