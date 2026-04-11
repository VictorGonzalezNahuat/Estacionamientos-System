-- Soporte para contador atomico de placas SYS para terminal/pluma.
-- MySQL 8+

CREATE TABLE IF NOT EXISTS terminal_counters (
  counter_key VARCHAR(64) PRIMARY KEY,
  current_value BIGINT NOT NULL DEFAULT 0,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO terminal_counters (counter_key, current_value)
VALUES ('sys_plate', 0)
ON DUPLICATE KEY UPDATE counter_key = counter_key;
