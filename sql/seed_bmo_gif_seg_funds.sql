-- Seed: BMO Insurance GIF segregated funds -> stockmarket app seg_funds table
-- Source: digital.lipperweb.com/bmoinsurance/list (Lipper / LSEG), as of July 31, 2026.
-- First verified fund family (BMO Aggregate Bond Index ETF GIF) across its guarantee
-- series and classes. The full 292-fund BMO lineup is populated by the Lipper scraper
-- (scripts/refresh_rbc_seg_funds.php extended for BMO + the monthly cron).
-- Requires migrate_rbc_seg_fund_columns.sql to have been applied (adds
-- asset_type, asset_class, launch_date, mer_pct). Idempotent: guarded with
-- NOT EXISTS on (fund_name, carrier).

INSERT INTO `seg_funds` (fund_name, carrier, asset_type, asset_class, launch_date, mer_pct, is_active)
SELECT 'BMO Aggregate Bond Index ETF GIF 100/100 Class A', 'BMO', 'Fixed Income', 'Canadian Fixed Income', '2023-11-01', 2.56, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='BMO Aggregate Bond Index ETF GIF 100/100 Class A' AND carrier='BMO');

INSERT INTO `seg_funds` (fund_name, carrier, asset_type, asset_class, launch_date, mer_pct, is_active)
SELECT 'BMO Aggregate Bond Index ETF GIF 100/100 Class A Prestige', 'BMO', 'Fixed Income', 'Canadian Fixed Income', '2023-11-01', 2.16, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='BMO Aggregate Bond Index ETF GIF 100/100 Class A Prestige' AND carrier='BMO');

INSERT INTO `seg_funds` (fund_name, carrier, asset_type, asset_class, launch_date, mer_pct, is_active)
SELECT 'BMO Aggregate Bond Index ETF GIF 100/100 Class F', 'BMO', 'Fixed Income', 'Canadian Fixed Income', '2023-11-01', 1.42, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='BMO Aggregate Bond Index ETF GIF 100/100 Class F' AND carrier='BMO');

INSERT INTO `seg_funds` (fund_name, carrier, asset_type, asset_class, launch_date, mer_pct, is_active)
SELECT 'BMO Aggregate Bond Index ETF GIF 75/100 Class A', 'BMO', 'Fixed Income', 'Canadian Fixed Income', '2023-11-01', 2.14, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='BMO Aggregate Bond Index ETF GIF 75/100 Class A' AND carrier='BMO');

INSERT INTO `seg_funds` (fund_name, carrier, asset_type, asset_class, launch_date, mer_pct, is_active)
SELECT 'BMO Aggregate Bond Index ETF GIF 75/100 Class A Prestige', 'BMO', 'Fixed Income', 'Canadian Fixed Income', '2023-11-01', 1.96, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='BMO Aggregate Bond Index ETF GIF 75/100 Class A Prestige' AND carrier='BMO');

INSERT INTO `seg_funds` (fund_name, carrier, asset_type, asset_class, launch_date, mer_pct, is_active)
SELECT 'BMO Aggregate Bond Index ETF GIF 75/100 Class F', 'BMO', 'Fixed Income', 'Canadian Fixed Income', '2023-11-01', 1.01, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='BMO Aggregate Bond Index ETF GIF 75/100 Class F' AND carrier='BMO');

INSERT INTO `seg_funds` (fund_name, carrier, asset_type, asset_class, launch_date, mer_pct, is_active)
SELECT 'BMO Aggregate Bond Index ETF GIF 75/100 Class F Prestige', 'BMO', 'Fixed Income', 'Canadian Fixed Income', '2026-06-01', 0.89, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='BMO Aggregate Bond Index ETF GIF 75/100 Class F Prestige' AND carrier='BMO');

INSERT INTO `seg_funds` (fund_name, carrier, asset_type, asset_class, launch_date, mer_pct, is_active)
SELECT 'BMO Aggregate Bond Index ETF GIF 75/100 Plus Class A', 'BMO', 'Fixed Income', 'Canadian Fixed Income', '2023-11-01', 2.14, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='BMO Aggregate Bond Index ETF GIF 75/100 Plus Class A' AND carrier='BMO');

INSERT INTO `seg_funds` (fund_name, carrier, asset_type, asset_class, launch_date, mer_pct, is_active)
SELECT 'BMO Aggregate Bond Index ETF GIF 75/100 Plus Class A Prestige', 'BMO', 'Fixed Income', 'Canadian Fixed Income', '2023-11-01', 1.96, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='BMO Aggregate Bond Index ETF GIF 75/100 Plus Class A Prestige' AND carrier='BMO');
