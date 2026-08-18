-- Seed: Beneva Insurance GIF segregated funds -> stockmarket app seg_funds table
-- Source: beneva.ca/en/savings-investments/segregated-funds (public). Beneva markets
-- guarantee-tier portfolios (Basic 75/75, Enhanced 75/100, Optimal 100/100), not named
-- funds. Best 5-yr annualized net return (basic) = 13.24% as of Jun 30 2026.
-- Full portfolio-level data is SPA/advisor-portal-gated (see KB/Beneva/Segregated_Funds.md).
-- Requires migrate_rbc_seg_fund_columns.sql. Idempotent: NOT EXISTS on (fund_name, carrier).

INSERT INTO `seg_funds` (fund_name, carrier, asset_type, asset_class, return_5yr, is_active)
SELECT 'Beneva Segregated Fund - Basic (75/75)', 'Beneva', 'Segregated Fund', 'Basic: 75% maturity / 75% death', '13.24', '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='Beneva Segregated Fund - Basic (75/75)' AND carrier='Beneva');

INSERT INTO `seg_funds` (fund_name, carrier, asset_type, asset_class, is_active)
SELECT 'Beneva Segregated Fund - Enhanced (75/100)', 'Beneva', 'Segregated Fund', 'Enhanced: 75% maturity / 100% death', '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='Beneva Segregated Fund - Enhanced (75/100)' AND carrier='Beneva');

INSERT INTO `seg_funds` (fund_name, carrier, asset_type, asset_class, is_active)
SELECT 'Beneva Segregated Fund - Optimal (100/100)', 'Beneva', 'Segregated Fund', 'Optimal: 100% maturity / 100% death', '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='Beneva Segregated Fund - Optimal (100/100)' AND carrier='Beneva');
