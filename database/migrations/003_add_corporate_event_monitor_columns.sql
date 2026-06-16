-- migrate_corporate_events_from_sqlite.sql
--
-- Adds the SQLite corporate_event_monitor columns missing from MariaDB.
-- This migration is additive; it does not drop or rename existing columns.
--
-- CONTRACT
-- Target table: corporate_events
--
.source <path_to_this_file>  -- optional if using mysql CLI migration runner

-- 1. Schema expansion
ALTER TABLE corporate_events
    ADD COLUMN IF NOT EXISTS url TEXT NULL AFTER source,
    ADD COLUMN IF NOT EXISTS price_at_event DECIMAL(12,4) NULL AFTER url,
    ADD COLUMN IF NOT EXISTS price_5d_after DECIMAL(12,4) NULL AFTER price_at_event,
    ADD COLUMN IF NOT EXISTS price_21d_after DECIMAL(12,4) NULL AFTER price_5d_after,
    ADD COLUMN IF NOT EXISTS eps_expected DECIMAL(10,4) NULL AFTER price_21d_after,
    ADD COLUMN IF NOT EXISTS eps_actual DECIMAL(10,4) NULL AFTER eps_expected,
    ADD COLUMN IF NOT EXISTS div_previous DECIMAL(10,4) NULL AFTER eps_actual,
    ADD COLUMN IF NOT EXISTS div_new DECIMAL(10,4) NULL AFTER div_previous,
    ADD COLUMN IF NOT EXISTS insider_name VARCHAR(120) NULL AFTER div_new,
    ADD COLUMN IF NOT EXISTS insider_title VARCHAR(120) NULL AFTER insider_name,
    ADD COLUMN IF NOT EXISTS insider_shares DECIMAL(14,4) NULL AFTER insider_title,
    ADD COLUMN IF NOT EXISTS insider_value DECIMAL(14,4) NULL AFTER insider_shares,
    ADD COLUMN IF NOT EXISTS is_acknowledged TINYINT(1) NOT NULL DEFAULT 0 AFTER insider_value;

-- 2. Index additions for added columns
CREATE INDEX IF NOT EXISTS idx_events_unread
    ON corporate_events(is_read);

CREATE INDEX IF NOT EXISTS idx_events_ack
    ON corporate_events(is_acknowledged);

-- 3. Optional subsequent tables required by monitor reports
--    earnings_calendar, dividend_history, insider_trades, monitor_state
--    are NOT present in schema_v2_partitioned.sql and need separate migration.

-- 4. Data migration hint (run only if SQLite backup still exists):
--    - Map existing corporate_events rows into the extended schema.
--    - Leave missing monitor-specific columns NULL.
--    - Preserve owner='kevin' as the default where needed.
--
-- NOTE: This file is intentionally safe to re-run.
-- TODO: Add credentials-driven runner file once secrets are loaded from Ansible Vault.
