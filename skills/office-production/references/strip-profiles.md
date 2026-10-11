# Strip Profile Creation

Creates professional investment banking strip profiles (company profiles) for pitch books, deal materials, and client presentations. Generates 1-4 information-dense slides with quadrant layouts, charts, and tables.

## When to Use

Use when the user asks to create a company profile slide, strip profile, or company overview slide for a pitch book or deal presentation.

## Workflow

### 1. Clarify Requirements
- **Ask the user**: Single-slide or multi-slide (3-4 slides)?
- **Ask the user**: Any specific focus areas or topics to emphasize?
- **Only after user confirms**, proceed to research

### 2. Research & Planning

**Data Sources:**
- **Primary**: Company filings (SEC EDGAR - "Item 1. Business", MD&A), investor presentations, corporate website
- **Market data**: Bloomberg, FactSet, CapIQ (price, shares, market cap, net debt, EV, ownership)
- **Estimates**: FactSet/CapIQ consensus for NTM revenue, EBITDA, EPS
- **News**: Press releases from last 90 days, M&A activity, guidance changes

**Required Metrics:**
- **Financials**: Revenue, EBITDA, margins (%), EPS, FCF for ±3 years
- **Valuation**: Market Cap, EV, EV/Revenue, EV/EBITDA, P/E multiples
- **Growth**: YoY growth rates (%)
- **Ownership**: Top 5 shareholders with % ownership
- **Segments**: Product mix and/or geographic mix (% breakdown)

**Normalization:**
- Convert all amounts to consistent currency
- Scale consistently ($mm or $bn throughout, not mixed)

**Before Building:**
- Print outline to chat with 4-5 bullet points per item (actual numbers, no placeholders)
- Print style choices: fonts, colors (hex codes), chart types for each data set
- Get user alignment

### 3. Slide-by-Slide Creation

**CRITICAL: Create ONE slide at a time and get user approval before proceeding.**

For EACH slide: create, convert to image, visually review, fix issues, show to user, wait for approval.

## Slide Format Requirements

### Information Density is Critical

Per quadrant targets:
- **Company Overview**: 6-8 bullets minimum
- **Business & Positioning**: 6-8 bullets
- **Key Financials**: Table with 8-10 rows OR chart + 4-5 key metrics
- **Fourth quadrant**: 5-7 bullets

### First Page Layout (4:3 aspect ratio)

| Quadrant | Position | Content |
|----------|----------|---------|
| **1** | x=0.3, y=0.6, w=4.7, h=3.0 | Company Overview |
| **2** | x=5.0, y=0.6, w=4.7, h=3.0 | Business & Positioning |
| **3** | x=0.3, y=3.7, w=4.7, h=3.5 | Key Financials table |
| **4** | x=5.0, y=3.7, w=4.7, h=3.5 | Stock chart + shareholders |

### Font Sizes
| Element | Size |
|---------|------|
| Slide title | 24pt |
| Quadrant headers | 14pt |
| Body/bullet text | 11pt |
| Table text | 10pt |
| Chart labels | 9pt |
| Source/footer | 8pt |

## Quality Checklist
- [ ] Title section with company name, ticker, industry
- [ ] Exactly 4 equal quadrants below title
- [ ] All bullets, no paragraphs
- [ ] Financials in table or chart (not both)
- [ ] No text overflow or cutoff
- [ ] Consistent fonts and colors
- [ ] No placeholder text
- [ ] Consistent scaling
- [ ] Sources cited
