-- Seed: Sun Life ETF+ Portfolios -> stockmarket app seg_funds table
-- Source of truth: src/Ksfraser/KnowledgeBase/Data/SunLifeEtfPlusPortfolios.php
--               and ~/.hermes/skills/ksf_stockmarket/references/sun_life_etf_plus.json
-- Run on the stockmarket app DB host (local MySQL is not running on the dev box).
-- Idempotent: guarded with NOT EXISTS on (fund_name, series).
--
-- Columns: fund_name, carrier, category, series, mer, return_1yr, return_3yr,
--          return_5yr, return_10yr, is_active
-- NOTE: `mer` stores the MANAGEMENT FEE (not the full MER incl. expenses).
-- NOTE: returns are PREDECESSOR "Sun Life Tactical ETF Portfolios" Series F total returns
--       (pre-2025-12-08 rebrand). ETF+ returns were not published. 5yr/10yr not available -> NULL.
-- NOTE: only mutual-fund codes (prefix SUN) are published; seg-fund contract codes differ.

INSERT INTO `seg_funds` (fund_name, carrier, category, series, mer, return_1yr, return_3yr, return_5yr, return_10yr, is_active)
SELECT 'Sun Life Fixed Income ETF+ Portfolio (Series A)', 'Sun Life Global Investments', 'Global Core Plus Fixed Income', 'A', 0.875, 2.71, 3.18, NULL, NULL, 1
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='Sun Life Fixed Income ETF+ Portfolio (Series A)' AND series='A');

INSERT INTO `seg_funds` (fund_name, carrier, category, series, mer, return_1yr, return_3yr, return_5yr, return_10yr, is_active)
SELECT 'Sun Life Fixed Income ETF+ Portfolio (Series F)', 'Sun Life Global Investments', 'Global Core Plus Fixed Income', 'F', 0.375, 2.71, 3.18, NULL, NULL, 1
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='Sun Life Fixed Income ETF+ Portfolio (Series F)' AND series='F');

INSERT INTO `seg_funds` (fund_name, carrier, category, series, mer, return_1yr, return_3yr, return_5yr, return_10yr, is_active)
SELECT 'Sun Life Conservative ETF+ Portfolio (Series A)', 'Sun Life Global Investments', 'Global Fixed Income Balanced', 'A', 1.125, 7.61, 7.92, NULL, NULL, 1
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='Sun Life Conservative ETF+ Portfolio (Series A)' AND series='A');

INSERT INTO `seg_funds` (fund_name, carrier, category, series, mer, return_1yr, return_3yr, return_5yr, return_10yr, is_active)
SELECT 'Sun Life Conservative ETF+ Portfolio (Series F)', 'Sun Life Global Investments', 'Global Fixed Income Balanced', 'F', 0.375, 7.61, 7.92, NULL, NULL, 1
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='Sun Life Conservative ETF+ Portfolio (Series F)' AND series='F');

INSERT INTO `seg_funds` (fund_name, carrier, category, series, mer, return_1yr, return_3yr, return_5yr, return_10yr, is_active)
SELECT 'Sun Life Conservative ETF+ Portfolio (Series F5)', 'Sun Life Global Investments', 'Global Fixed Income Balanced', 'F5', 0.375, 7.61, 7.92, NULL, NULL, 1
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='Sun Life Conservative ETF+ Portfolio (Series F5)' AND series='F5');

INSERT INTO `seg_funds` (fund_name, carrier, category, series, mer, return_1yr, return_3yr, return_5yr, return_10yr, is_active)
SELECT 'Sun Life Conservative ETF+ Portfolio (Series T5)', 'Sun Life Global Investments', 'Global Fixed Income Balanced', 'T5', 1.125, 7.61, 7.92, NULL, NULL, 1
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='Sun Life Conservative ETF+ Portfolio (Series T5)' AND series='T5');

INSERT INTO `seg_funds` (fund_name, carrier, category, series, mer, return_1yr, return_3yr, return_5yr, return_10yr, is_active)
SELECT 'Sun Life Balanced ETF+ Portfolio (Series A)', 'Sun Life Global Investments', 'Global Neutral Balanced', 'A', 1.400, 11.69, 11.52, NULL, NULL, 1
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='Sun Life Balanced ETF+ Portfolio (Series A)' AND series='A');

INSERT INTO `seg_funds` (fund_name, carrier, category, series, mer, return_1yr, return_3yr, return_5yr, return_10yr, is_active)
SELECT 'Sun Life Balanced ETF+ Portfolio (Series F)', 'Sun Life Global Investments', 'Global Neutral Balanced', 'F', 0.400, 11.69, 11.52, NULL, NULL, 1
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='Sun Life Balanced ETF+ Portfolio (Series F)' AND series='F');

INSERT INTO `seg_funds` (fund_name, carrier, category, series, mer, return_1yr, return_3yr, return_5yr, return_10yr, is_active)
SELECT 'Sun Life Balanced ETF+ Portfolio (Series F5)', 'Sun Life Global Investments', 'Global Neutral Balanced', 'F5', 0.400, 11.69, 11.52, NULL, NULL, 1
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='Sun Life Balanced ETF+ Portfolio (Series F5)' AND series='F5');

INSERT INTO `seg_funds` (fund_name, carrier, category, series, mer, return_1yr, return_3yr, return_5yr, return_10yr, is_active)
SELECT 'Sun Life Balanced ETF+ Portfolio (Series T5)', 'Sun Life Global Investments', 'Global Neutral Balanced', 'T5', 1.400, 11.69, 11.52, NULL, NULL, 1
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='Sun Life Balanced ETF+ Portfolio (Series T5)' AND series='T5');

INSERT INTO `seg_funds` (fund_name, carrier, category, series, mer, return_1yr, return_3yr, return_5yr, return_10yr, is_active)
SELECT 'Sun Life Growth ETF+ Portfolio (Series A)', 'Sun Life Global Investments', 'Global Equity Balanced', 'A', 1.450, 15.07, 14.42, NULL, NULL, 1
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='Sun Life Growth ETF+ Portfolio (Series A)' AND series='A');

INSERT INTO `seg_funds` (fund_name, carrier, category, series, mer, return_1yr, return_3yr, return_5yr, return_10yr, is_active)
SELECT 'Sun Life Growth ETF+ Portfolio (Series F)', 'Sun Life Global Investments', 'Global Equity Balanced', 'F', 0.450, 15.07, 14.42, NULL, NULL, 1
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='Sun Life Growth ETF+ Portfolio (Series F)' AND series='F');

INSERT INTO `seg_funds` (fund_name, carrier, category, series, mer, return_1yr, return_3yr, return_5yr, return_10yr, is_active)
SELECT 'Sun Life Equity ETF+ Portfolio (Series A)', 'Sun Life Global Investments', 'Global Equity', 'A', 1.450, 18.41, 17.56, NULL, NULL, 1
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='Sun Life Equity ETF+ Portfolio (Series A)' AND series='A');

INSERT INTO `seg_funds` (fund_name, carrier, category, series, mer, return_1yr, return_3yr, return_5yr, return_10yr, is_active)
SELECT 'Sun Life Equity ETF+ Portfolio (Series F)', 'Sun Life Global Investments', 'Global Equity', 'F', 0.450, 18.41, 17.56, NULL, NULL, 1
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='Sun Life Equity ETF+ Portfolio (Series F)' AND series='F');
