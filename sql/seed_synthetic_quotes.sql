-- Seed: synthetic "MMF" exchange — instruments with no TSX/yfinance quote.
-- These are money-market / private-series funds; quotes are served locally
-- (python/src/synthetic_quotes.py) so the pipeline stops hitting yfinance
-- with "Quote not found". Prices are editable placeholders — set real NAVs.
INSERT INTO `synthetic_quotes` (symbol, name, price, currency, exchange, asset_type, asof_date, is_active)
VALUES
  ('BNS557', 'Scotia Money Market Fund Series 557', 50.00, 'CAD', 'MMF', 'Money Market Fund', CURDATE(), 1),
  ('WVN613', 'Synthetic Money Market Series 613',     10.00, 'CAD', 'MMF', 'Money Market Fund', CURDATE(), 1),
  ('WVN618', 'Synthetic Money Market Series 618',     10.00, 'CAD', 'MMF', 'Money Market Fund', CURDATE(), 1)
ON DUPLICATE KEY UPDATE
  name=VALUES(name), price=VALUES(price), currency=VALUES(currency),
  exchange=VALUES(exchange), asset_type=VALUES(asset_type),
  asof_date=VALUES(asof_date), is_active=1;
