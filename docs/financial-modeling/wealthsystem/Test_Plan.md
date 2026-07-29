# Test Plan — WealthSystem Port
BR-081 | WealthSystem Detail + Edit on Symbol Detail Page

## Preconditions
- Migrations 016 executed; tables exist in MySQL
- php-fpm + httpd running
- User authenticated for `?action=detail&symbol=...`

## Test Cases

### TC-01 Load detail with empty WS data
1. Clear `tenets`, `motleyfool`, `evaluation_scores`, `llm_analysis` for a symbol
2. Load detail page
3. **Expected:** All 4 WS cards render with empty/fallback text; no PHP fatal; page loads under 5s

### TC-02 Load detail with full WS data
1. Insert 12 tenets, Motley criteria, 4 eval domains, 1 LLM row
2. Load detail page
3. **Expected:** Card headers visible; checkboxes show correct state; grades/notes visible

### TC-03 Save Buffett tenets
1. Toggle tenets + add notes
2. Submit form
3. **Expected:** Redirect to `?action=detail&symbol=...&msg=Buffett tenets saved.`
4. Reloads: checkboxes and notes match submission

### TC-04 Save Motley Fool
1. Toggle criteria
2. Submit form
3. **Expected:** Redirect with success message; reloads with criteria rechecked

### TC-05 Save evaluations
1. Edit score/max/grade/note for Business, Financial, Management, Market
2. Submit form
3. **Expected:** JSON payload encoded client-side; MySQL rows upsert; reload shows updated values

### TC-06 Save LLM
1. Edit summary + model
2. Submit form
3. **Expected:** Row inserted/updated in `llm_analysis`; reloads with new summary and model

### TC-07 Degrade on missing tables
1. Rename `tenets` table temporarily
2. Load detail page
3. **Expected:** No fatal error; Buffett card shows fallback/empty state

## Automation Notes
- No automated UI tests yet; manual verification via browser is acceptable.
- PHPUnit coverage can be added for `StockController::save*` methods later.
