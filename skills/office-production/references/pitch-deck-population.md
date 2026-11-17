# Pitch Deck Template Population

Populates investment banking pitch deck templates with data from source files. Use when: user provides a PowerPoint template to fill in, user has source data (Excel/CSV) to populate into slides, user mentions populating or filling a pitch deck template, or user needs to transfer data into existing slide layouts. Not for creating presentations from scratch.

## Reference Files

Read all reference files at task start before beginning any work. These are in the `pitch-deck/` directory.

| File | Purpose |
|------|---------|
| `formatting-standards.md` | Text, bullets, tables, charts, alignment |
| `slide-templates.md` | Content mapping guidance for common slide types |
| `xml-reference.md` | PowerPoint XML patterns for tables, shapes, arrows |
| `calculation-standards.md` | Financial formulas for verification (CAGR, consensus) |

## Workflow Decision Tree

- **Populating empty template with source data** → Follow "Template Population Workflow" below
- **Editing existing populated slides** → Extract current content, modify, revalidate
- **Fixing formatting issues** → See Common Failures table, apply targeted fixes

## Critical Rendering Limitation

LibreOffice is used for validation but DOES NOT render PowerPoint files accurately. It will mangle fonts, gradients, shape positions, text wrapping, and some table formatting.

**Required action:** Always include this statement when delivering output:
> "This file was validated using LibreOffice. Please review in Microsoft PowerPoint before distribution, as rendering differences may exist."

## Template Population Workflow

### Phase 1: Data Extraction
1. Create backup of original template before any modifications
2. Identify all source materials (Excel, CSV, PDF reports, Word documents, databases, web sources)
3. Extract relevant data points from each source
4. Validate all numbers against original sources
5. Standardize units and currency
6. Note any calculations that need verification

### Phase 2: Content Mapping
1. Open and visually review the template — understand its structure, style, and existing content
2. Analyze template structure — identify all placeholder areas and content boxes
3. Map source data to corresponding template sections
4. Identify placeholder guidance boxes (colored instruction boxes from task creator)
5. Note any data gaps or mismatches

### Phase 3: Template Population
1. Remove or reformat placeholder boxes — colored instruction boxes show WHAT to create, not HOW to format
2. Populate each section with mapped content (focus on content first)
3. Apply formatting to match template style
4. Create tables as actual table objects (NEVER use pipe/tab-separated text)
5. Create arrows/shapes as PowerPoint objects
6. Insert company logo if provided

### Phase 4: Validate → Fix → Repeat

```bash
soffice --headless --convert-to pdf presentation.pptx
pdftoppm -jpeg -r 150 presentation.pdf slide
```

Validation checklist:
- Text readable against background?
- Tables are actual objects (NOT pipe/tab-separated text)?
- Charts/tables fill designated areas?
- Bullet formatting consistent?
- Font sizes match across same-level boxes?
- No content beyond slide boundaries?
- No placeholder formatting retained?

Fix cycle: After 3 cycles, if issues remain, document and escalate to user.

### Phase 5: Final Verification
- All figures match original source documents
- Calculated values verified
- Every template section populated
- No [bracket] placeholder text remaining
- Text readable against all backgrounds
- Tables are actual table objects

## Critical Anti-Patterns: NEVER DOSE

### Anti-Pattern 1: Populating Data INTO Placeholder Boxes
The colored box IS the placeholder. Delete the entire shape, then create new content with production formatting.

### Anti-Pattern 2: Text-Based "Tables"
Tabular data MUST be table objects, not tab-separated text. Columns will never align properly with text separators.

### Anti-Pattern 3: Inheriting Placeholder Contrast
Placeholder uses light text on colored background to signal "replace me." Production slides use dark text on light backgrounds for body content.

## Table Structure Guidelines
- Text columns: Left-aligned
- Numeric columns: Right-aligned or center-aligned
- Header row: Bold, shaded background (template's brand color), white text

## Footnote Format
```
Sources: [Source 1] (Year), [Source 2] (Year).
Notes: (1) [First note]; (2) [Second note].
```

All superscript numbers in slide body MUST have corresponding Notes entries.
