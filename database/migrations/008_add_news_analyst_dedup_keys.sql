-- ============================================================================
-- Migration 008: add dedup constraints for news + analyst ratings
-- ============================================================================
--
-- Problem:
--   symbol_news had 50 empty rows per symbol because upsert_news inserted
--   every article without dedup and without a unique key.
--   analyst_ratings had duplicate incomplete rows (empty firm / NULL price_target).
--
-- Fix:
--   Add unique keys so INSERT IGNORE actually prevents duplicates on re-runs.
--   yahoo_enrichment.py now skips articles with empty title + url.
--
-- Run manually if needed:
--   mysql -h ksfraser.ca -u ksfraser_stockmarket -p ksfraser_stock_market < migrations/008_add_news_analyst_dedup_keys.sql
-- ============================================================================

-- deduplicate symbol_news by (symbol, url, date)
ALTER TABLE symbol_news
  ADD UNIQUE KEY uk_symbol_news (symbol, url(255), date);

-- deduplicate analyst_ratings by full row contents
ALTER TABLE analyst_ratings
  ADD UNIQUE KEY uk_analyst_ratings (symbol, date, firm, action, rating, price_target);
