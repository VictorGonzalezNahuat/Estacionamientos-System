-- Esquema inicial de facturacion (local only)
-- Ejecutar contra la base de datos local de la aplicacion.

CREATE TABLE IF NOT EXISTS fiscal_customers (
  id INT AUTO_INCREMENT PRIMARY KEY,
  rfc VARCHAR(13) NOT NULL,
  razon_social VARCHAR(255) NOT NULL,
  codigo_postal VARCHAR(5) NOT NULL,
  regimen_fiscal VARCHAR(50) NOT NULL,
  uso_cfdi_receptor VARCHAR(3) NOT NULL DEFAULT 'G03',
  nombre_contacto VARCHAR(255) NULL,
  email VARCHAR(255) NULL,
  telefono VARCHAR(20) NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  last_invoiced_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_fiscal_customers_rfc (rfc),
  KEY ix_fiscal_customers_id (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS invoice_requests (
  id INT AUTO_INCREMENT PRIMARY KEY,
  fiscal_customer_id INT NOT NULL,
  source_type VARCHAR(50) NOT NULL,
  source_id VARCHAR(100) NOT NULL,
  idempotency_key VARCHAR(255) NOT NULL,
  status VARCHAR(50) NOT NULL DEFAULT 'pending',
  total DECIMAL(12,2) NOT NULL,
  currency VARCHAR(10) NOT NULL DEFAULT 'MXN',
  invoice_payload_json VARCHAR(8000) NULL,
  provider_name VARCHAR(50) NOT NULL DEFAULT 'facturapi',
  provider_customer_id VARCHAR(255) NULL,
  provider_invoice_id VARCHAR(255) NULL,
  access_token_hash VARCHAR(64) NULL,
  access_token_expires_at DATETIME NULL,
  provider_last_error VARCHAR(1000) NULL,
  attempts INT NOT NULL DEFAULT 0,
  next_retry_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_invoice_requests_idempotency_key (idempotency_key),
  KEY ix_invoice_requests_fiscal_customer_id (fiscal_customer_id),
  KEY ix_invoice_requests_source_type (source_type),
  KEY ix_invoice_requests_source_id (source_id),
  KEY ix_invoice_requests_status (status),
  KEY ix_invoice_requests_provider_invoice_id (provider_invoice_id),
  KEY ix_invoice_requests_access_token_expires_at (access_token_expires_at),
  CONSTRAINT fk_invoice_requests_fiscal_customer
    FOREIGN KEY (fiscal_customer_id) REFERENCES fiscal_customers(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS invoice_documents (
  id INT AUTO_INCREMENT PRIMARY KEY,
  invoice_request_id INT NOT NULL,
  uuid_fiscal VARCHAR(120) NULL,
  serie VARCHAR(20) NULL,
  folio VARCHAR(30) NULL,
  issued_at DATETIME NULL,
  subtotal DECIMAL(12,2) NULL,
  taxes DECIMAL(12,2) NULL,
  total DECIMAL(12,2) NULL,
  currency VARCHAR(10) NOT NULL DEFAULT 'MXN',
  xml_url VARCHAR(1000) NULL,
  pdf_url VARCHAR(1000) NULL,
  verification_url VARCHAR(1000) NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'issued',
  cancelled_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_invoice_documents_invoice_request_id (invoice_request_id),
  KEY ix_invoice_documents_uuid_fiscal (uuid_fiscal),
  CONSTRAINT fk_invoice_documents_invoice_request
    FOREIGN KEY (invoice_request_id) REFERENCES invoice_requests(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS invoice_events (
  id INT AUTO_INCREMENT PRIMARY KEY,
  invoice_request_id INT NOT NULL,
  event_type VARCHAR(50) NOT NULL,
  payload_summary_json VARCHAR(8000) NULL,
  success TINYINT(1) NOT NULL DEFAULT 1,
  error_message VARCHAR(1000) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY ix_invoice_events_invoice_request_id (invoice_request_id),
  KEY ix_invoice_events_event_type (event_type),
  CONSTRAINT fk_invoice_events_invoice_request
    FOREIGN KEY (invoice_request_id) REFERENCES invoice_requests(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
