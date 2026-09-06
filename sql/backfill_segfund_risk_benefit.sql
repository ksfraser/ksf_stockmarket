-- Backfill: death_benefit_pct, maturity_benefit_pct from `series` text
-- Patterns handled:
--   "75/75 A", "75/100 F", "100/100 A Prestige"     → (75,75) (75,100) (100,100)
--   "75/100 Plus A"                                  → (75,100) "Plus" tier ignored
--   "Basic 75/75", "Enhanced 75/100", "Optimal 100/100" → (75,75) (75,100) (100,100)
-- Anything else: leave NULL (will need manual backfill).

-- 1) Plain NN/NN series (BMO, Canada Life, Manulife, Empire Life, Equitable, RBC, Sun Life)
UPDATE seg_funds
SET
    death_benefit_pct    = CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(series, '/', 1), ' ', -1) AS UNSIGNED),
    maturity_benefit_pct = CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(SUBSTRING_INDEX(series, '/', 2), ' ', 1), '/', -1) AS UNSIGNED)
WHERE series REGEXP '^[0-9]{2,3}/[0-9]{2,3}'
  AND (death_benefit_pct IS NULL OR maturity_benefit_pct IS NULL);

-- 2) Beneva "Basic 75/75" / "Enhanced 75/100" / "Optimal 100/100"
UPDATE seg_funds
SET
    death_benefit_pct    = CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(series, ' ', -1), '/', 1) AS UNSIGNED),
    maturity_benefit_pct = CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(series, ' ', -1), '/', -1) AS UNSIGNED)
WHERE series REGEXP '^(Basic|Enhanced|Optimal) [0-9]{2,3}/[0-9]{2,3}$'
  AND (death_benefit_pct IS NULL OR maturity_benefit_pct IS NULL);

-- 3) Risk rating backfill (heuristic by category) — only fills rows still NULL.
--    Equity subcategories → 'Med-High'; Balanced → 'Medium'; Fixed Income / Money Market → 'Low'.
--    (Note: column has DEFAULT 'Medium' so existing rows are NOT NULL; this only fires for
--    newly-inserted rows that don't supply a rating. The DEFAULT is fine for the controller.)
--
-- For existing rows, do a one-shot recompute so the distribution is meaningful:
UPDATE seg_funds
SET risk_rating = CASE
    WHEN category LIKE '%Money Market%' OR category LIKE '%Fixed Income%' OR category LIKE '%Bond%' THEN 'Low'
    WHEN category LIKE '%Balanced%' OR category LIKE '%Income%' OR category LIKE '%Tactical%' THEN 'Medium'
    WHEN category LIKE '%Equity%' OR category LIKE '%Real Estate%' THEN 'Med-High'
    ELSE 'Medium'
END
WHERE is_active = 1;
