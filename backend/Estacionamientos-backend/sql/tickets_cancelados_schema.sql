-- Soporte para cancelacion de tickets de salida.
-- MySQL 8+

ALTER TABLE history_estacionamiento
  ADD COLUMN IF NOT EXISTS cancelado TINYINT NOT NULL DEFAULT 0;

CREATE INDEX idx_history_cancelado_corte ON history_estacionamiento (cancelado, corte_id);
CREATE INDEX idx_history_cancelado_fecha ON history_estacionamiento (cancelado, fecha_salida);
CREATE INDEX idx_history_payment_cancelado ON history_estacionamiento (payment_transaction_id, cancelado);

CREATE TABLE IF NOT EXISTS tickets_cancelados (
  id INT PRIMARY KEY AUTO_INCREMENT,
  history_estacionamiento_id INT NOT NULL,
  payment_transaction_id INT NULL,
  motivo VARCHAR(500) NOT NULL,
  cancelado_por INT NOT NULL,
  fecha_cancelacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT uq_tickets_cancelados_hist UNIQUE (history_estacionamiento_id),
  CONSTRAINT fk_tc_history FOREIGN KEY (history_estacionamiento_id) REFERENCES history_estacionamiento(id),
  CONSTRAINT fk_tc_payment FOREIGN KEY (payment_transaction_id) REFERENCES payment_transactions(id),
  CONSTRAINT fk_tc_usuario FOREIGN KEY (cancelado_por) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
