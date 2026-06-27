-- 007_add_symbol_lifecycle.sql
-- Add lifecycle state tracking columns to symbol_master
-- This supports the Python lifecycle state machine in python/src/lifecycle/

ALTER TABLE symbol_master
  ADD COLUMN pipeline_state VARCHAR(30) NOT NULL DEFAULT 'unknown' AFTER deactivated_reason,
  ADD COLUMN last_state_transition TIMESTAMP NULL AFTER pipeline_state;
