# Clean Data — Reference

## Source Skill: `clean-data-xls`

## Workflow

### Step 1: Scope
Use given range or full used range of active sheet. Profile each column for dominant type and outliers.

### Step 2: Detect Issues
| Issue | What to look for |
|---|---|
| Whitespace | Leading/trailing spaces, double spaces |
| Casing | Inconsistent casing in categorical columns |
| Number-as-text | Numeric values stored as text; stray `$`, `,`, `%` |
| Dates | Mixed formats in same column |
| Duplicates | Exact and near-duplicates |
| Blanks | Empty cells in otherwise-populated columns |
| Mixed types | Column that's 98% numbers but has 3 text entries |
| Encoding | Mojibake, non-printing characters |
| Errors | `#REF!`, `#N/A`, `#VALUE!`, `#DIV/0!` |

### Step 3: Propose Fixes
Show summary table before changing anything: Column, Issue, Count, Proposed Fix.

### Step 4: Apply
- **Prefer formulas over hardcoded cleaned values** — use `=TRIM()`, `=VALUE()`, `=UPPER()`, `=DATEVALUE()` in helper columns
- Only overwrite in place when user explicitly asks or no formula equivalent exists
- Confirm with user after each category of fix
- Report before/after summary
