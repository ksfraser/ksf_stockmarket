-- Add source tracking columns to transactions table
ALTER TABLE transactions 
  ADD COLUMN source_file VARCHAR(255) DEFAULT '' AFTER notes,
  ADD COLUMN source_line INT DEFAULT 0 AFTER source_file;
