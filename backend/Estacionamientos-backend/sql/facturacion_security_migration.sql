-- Migracion de seguridad para facturacion publica
-- Agrega columnas para token de acceso por solicitud.

ALTER TABLE invoice_requests
  ADD COLUMN IF NOT EXISTS access_token_hash VARCHAR(64) NULL AFTER provider_invoice_id,
  ADD COLUMN IF NOT EXISTS access_token_expires_at DATETIME NULL AFTER access_token_hash;

ALTER TABLE invoice_requests
  ADD INDEX IF NOT EXISTS ix_invoice_requests_access_token_expires_at (access_token_expires_at);
