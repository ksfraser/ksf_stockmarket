CREATE TABLE IF NOT EXISTS event_queue (
  event_id VARCHAR(64) NOT NULL PRIMARY KEY,
  event_type VARCHAR(64) NOT NULL,
  payload JSON NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'pending',
  occurred_at DATETIME NOT NULL,
  processed_at DATETIME NULL,
  attempts INT NOT NULL DEFAULT 0,
  last_error TEXT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
