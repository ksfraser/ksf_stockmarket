-- Seed: RBC Insurance GIF segregated funds -> stockmarket app seg_funds table
-- Source: rbc_gif_funds_2026-08-17.csv (email-gateway export of lipper.rbcinsurance.com).
-- Only the columns present in the CSV are populated; the remaining RBC Lipper
-- columns (currency, asset_class, launch_date, aum, nav, quartile ranks, MER %, etc.)
-- are filled by the monthly refresh job (scripts/refresh_rbc_seg_funds.php).
-- Idempotent: guarded with NOT EXISTS on (fund_name, carrier).

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC Canadian Money Market GIF', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '1.92', '3.22', '2.65', '1.61', '1.41', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC Canadian Money Market GIF' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC Canadian Short-Term Income GIF', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '1.28', '3.55', '0.75', '0.59', '0.63', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC Canadian Short-Term Income GIF' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC Bond GIF', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '1.25', '3.01', '-1.02', '0.35', '1.07', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC Bond GIF' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC Global Bond GIF', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '-1.65', '0.2', '-3.42', '-1.12', '-0.23', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC Global Bond GIF' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC High Yield Bond GIF', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2.78', '5.02', '1.14', '2.3', '2.42', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC High Yield Bond GIF' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC Balanced GIF', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '15.54', '12.18', '6.53', '6.35', '5.97', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC Balanced GIF' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC Vision Balanced GIF', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '5.71', '9.3', NULL, NULL, '2.76', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC Vision Balanced GIF' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC Conservative Growth & Income GIF', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '8.19', '7.46', '2.8', '3.31', '3.63', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC Conservative Growth & Income GIF' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC Balanced Growth & Income GIF', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '18.2', '13.67', '7.98', '7.08', '6.59', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC Balanced Growth & Income GIF' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC Global Growth & Income GIF', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '10.25', '9.94', '3.68', NULL, '5.85', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC Global Growth & Income GIF' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC PH&N Monthly Income GIF', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '14.98', '12.05', '7.52', '6.41', '5.6', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC PH&N Monthly Income GIF' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC Global Balanced GIF', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '13.48', '11.09', '5.8', '6.27', '6.14', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC Global Balanced GIF' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC Select Conservative GIP', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '10.05', '8.87', '4.13', '4.56', '4.62', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC Select Conservative GIP' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC Select Balanced GIP', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '14.36', '11.89', '6.12', '6.51', '6.39', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC Select Balanced GIP' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC Select Growth GIP', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '17.56', '13.62', '7.24', '7.52', '7.27', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC Select Growth GIP' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC Select Aggressive Growth GIP', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '23.59', '17.64', '10.31', '9.81', '9.29', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC Select Aggressive Growth GIP' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC Global Conservative GIP', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '6.73', '7.35', '2.15', NULL, '3.24', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC Global Conservative GIP' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC Global Balanced GIP', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '9.85', '9.93', '3.95', NULL, '5.59', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC Global Balanced GIP' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC Global Growth GIP', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '12.56', '11.84', '5.22', NULL, '7.01', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC Global Growth GIP' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC Global All-Equity GIP', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '16.66', '15.23', '7.56', NULL, '10.06', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC Global All-Equity GIP' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC Canadian Dividend GIF', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '32.02', '19.61', '13.25', '10.28', '8.86', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC Canadian Dividend GIF' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC Canadian Equity GIF', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '29.38', '19.83', '12.95', '9.72', '8.31', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC Canadian Equity GIF' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC Vision Canadian Equity GIF', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '25.98', '19.02', NULL, NULL, '11.59', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC Vision Canadian Equity GIF' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC PH&N Canadian Income GIF', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '28.02', '18.52', '12.98', '10.09', '8.47', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC PH&N Canadian Income GIF' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC North American Value GIF', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '21.59', '17.36', '12.58', '10.86', '9.83', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC North American Value GIF' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC North American Growth GIF', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '20.8', '18.17', '11.19', '11.0', '9.87', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC North American Growth GIF' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC U.S. Dividend GIF', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '23.12', '19.13', '12.92', '12.04', '11.9', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC U.S. Dividend GIF' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC U.S. Equity GIF', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '20.04', '18.7', '12.11', '12.33', '11.7', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC U.S. Equity GIF' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC QUBE Low Volatility US Equity GIF', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '12.73', '11.74', '8.36', NULL, '9.8', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC QUBE Low Volatility US Equity GIF' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC Emerging Markets Dividend GIF', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '44.42', '22.35', '10.84', '9.51', '8.01', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC Emerging Markets Dividend GIF' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC Global Dividend Growth GIF', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '12.55', '14.13', '7.06', '10.72', '10.36', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC Global Dividend Growth GIF' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC Global Equity GIF', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '9.34', '13.3', '5.2', '9.67', '9.77', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC Global Equity GIF' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC QUBE Low Volatility Global Equity GIF', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '15.66', '12.07', '7.62', NULL, '7.93', NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC QUBE Low Volatility Global Equity GIF' AND carrier='RBC');

INSERT INTO `seg_funds` (fund_name, carrier, fund_code, num_securities, pe, pb, eps_growth, div_yield, return_1mo, return_3mo, ytd_pct, return_1yr, return_3yr, return_5yr, return_10yr, return_inception, volatility, is_active)
SELECT 'RBC GIF Interest Savings Account', 'RBC', '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '1'
WHERE NOT EXISTS (SELECT 1 FROM `seg_funds` WHERE fund_name='RBC GIF Interest Savings Account' AND carrier='RBC');
