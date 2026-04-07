# Blueprint Técnico: Seguridad en Facturación
**Proyecto:** Estacionamientos Backend  
**Fecha:** 2026-04-06  
**Versión:** 1.0  
**Estado:** Diseño sin implementación

---

## 1. Visión General

Hardening de endpoints públicos de facturación mediante:
1. **reCAPTCHA v3** para detección de bots (threshold: 0.5).
2. **Rate limiting** por IP con límites diferenciados por endpoint.
3. **Flujo de elegibilidad de ticket** para validar y autorizar operaciones de RFC.

**Impacto esperado:** Subir de 4.8/10 a 8/10 en resistencia a abuso.

---

## 2. Etapas de Implementación (Por Metas)

### **Etapa 0: Preparación e Integración de reCAPTCHA v3**
**Meta:** Tener configurada la verificación servidor-side de reCAPTCHA v3.

**Deliverables:**
- Configuración de Google reCAPTCHA v3 en Console.
- Variables de entorno (.env) con `RECAPTCHA_SECRET_KEY`.
- Middleware/utilidad de verificación server-side (core/recaptcha_service.py).
- Test manual de captcha válido/inválido.

**Detalles Técnicos:**

#### Configuración Google
1. Ir a: https://www.google.com/recaptcha/admin
2. Crear sitio nuevo:
   - Nombre: "Estacionamientos Facturación"
   - reCAPTCHA v3
   - Dominios: `localhost:3000`, `localhost:8000`, `tu-dominio.com` (frontend y backend)
3. Copiar:
   - `RECAPTCHA_SITE_KEY` → frontend (variable pública)
   - `RECAPTCHA_SECRET_KEY` → backend (variable privada, .env)

#### Servicio de Verificación (core/recaptcha_service.py)
```
Clase: RecaptchaService

Métodos:
- verify_token(token: str) -> RecaptchaVerificationResult
  Input:  token del cliente (capturado por JS)
  Output: {
    "success": bool,
    "score": float (0.0-1.0),
    "action": str,
    "challenge_ts": str,
    "hostname": str,
    "error_codes": [str] | None
  }
  Timeout: 3 segundos
  Retry: No (fail fast)

Config:
- Se llama a endpoint POST https://www.google.com/recaptcha/api/siteverify
- Timeout configurable vía env (default 3s)
```

#### Validación de Score
```
Política:
- Score 0.0-0.3: bot muy probable   → RECHAZAR inmediatamente
- Score 0.3-0.5: sospecha media     → RECHAZAR (threshold del proyecto)
- Score 0.5-0.8: probablemente OK   → ACEPTAR con auditoría
- Score 0.8-1.0: muy probable humano → ACEPTAR

Criteria de aceptación:
- Si score >= 0.5 → permitir operación
- Si score < 0.5  → retornar HTTP 403 con mensaje "Verificación fallida, intenta de nuevo"
- Si error o timeout → retornar HTTP 402 "Servicio temporal no disponible"
```

#### Auditoría Mínima (para detección de patrones)
```
Bitácora captura:
- timestamp
- acción (registro_fiscal, emitir_factura)
- ip
- score recaptcha
- token válido (true/false)

Consultas iniciales útiles:
- Promedio de score por acción/día
- Spike de score bajo
- IPs con múltiples intentos fallidos en corta ventana
```

**Criterios de Aceptación Etapa 0:**
- [ ] Google reCAPTCHA v3 creado y keys en .env
- [ ] Servicio de verificación implementado en core/
- [ ] Pruebas manuales de score: bot simulado (score ~0.1) vs usuario real (score ~0.9)
- [ ] Documentación de keys en setup README
- [ ] Auditoría mínima en logs (no requiere tabla nueva, solo logs)

---

### **Etapa 1: Rate Limiting en Endpoints Públicos**
**Meta:** Implementar límites de tasa por IP en rutas de facturación.

**Deliverables:**
- Middleware/dependencia de rate limiting.
- Configuración diferenciada por endpoint/ruta.
- Respuestas 429 consistentes con Retry-After.
- Monitoreo básico de hits/límites.

**Números Recomendados (Rate Limits por IP):**

| Endpoint | Método | Límite | Ventana | Justificación |
|----------|--------|--------|---------|---------------|
| `/facturacion/clientes-fiscales/por-rfc/{rfc}` | GET | 30 req | 1 min | Búsqueda; evita scraping |
| `/facturacion/clientes-fiscales` | POST | 5 req | 1 min | Alta fiscal; es operación pesada |
| `/facturacion/emitir` | POST | 3 req | 1 min | Emisión de factura; muy costosa |
| `/facturacion/solicitudes/{id}` | GET | 20 req | 1 min | Consulta de estado; puede ser frecuente |
| `/facturacion/solicitudes/{id}/cancelar` | POST | 2 req | 1 min | Cancelación fiscal; muy restrictiva |

**Estrategia de Rate Limiting:**

#### Implementación Propuesta
```
Opción A (Recomendada): Redis + Middleware
- Usar Redis para contador distribuido (escalable)
- Middleware FastAPI que intercepta todas las rutas de /facturacion
- Clave: ip + endpoint
- TTL del contador: duración de ventana (1 min)

Opción B: In-memory (MVP simple)
- Dict con expiry basado en timestamp
- Válido si es single-instance
- No escalable pero rápido de implementar

Elegir Opción A si ya hay Redis en proyecto, B si no.
```

#### Estructura de Respuesta 429
```json
HTTP/1.1 429 Too Many Requests
Retry-After: 45
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1712430300

{
  "detail": "Demasiadas solicitudes. Intenta de nuevo en 45 segundos",
  "error_code": "RATE_LIMITED",
  "retry_after_seconds": 45
}
```

#### Configuración (en .env)
```
# Rate limiting
RATELIMIT_ENABLED=true
RATELIMIT_STORAGE=redis  # o 'memory'
RATELIMIT_REDIS_URL=redis://localhost:6379/1

# Límites por endpoint (segundos y requests)
RATELIMIT_FISCAL_CUSTOMER_GET_PER_MIN=30
RATELIMIT_FISCAL_CUSTOMER_POST_PER_MIN=5
RATELIMIT_EMITIR_POST_PER_MIN=3
RATELIMIT_SOLICITUD_GET_PER_MIN=20
RATELIMIT_SOLICITUD_CANCEL_POST_PER_MIN=2

# Whitelist (para CI/tests locales; vacío en prod)
RATELIMIT_WHITELIST_IPS=127.0.0.1,::1
```

#### Comportamiento por Escenario
```
Escenario 1: Usuario legítimo dentro de límite
- Request 1: 200 OK, X-RateLimit-Remaining: 4
- Request 2: 200 OK, X-RateLimit-Remaining: 3
- Request 3: 200 OK, X-RateLimit-Remaining: 2

Escenario 2: Usuario excede límite en ventana
- Request 1-5: 200 OK (dentro de límite)
- Request 6: 429 Too Many Requests, Retry-After: 45
- (espera 45s)
- Request 7: 200 OK, reset del contador

Escenario 3: Bot intenta fuerza bruta
- Requests 1-5: 429 Too Many Requests inmediatamente
- Cliente legítimo retrocede (Retry-After)
- Bot sin backoff inteligente -> spam inútil
```

**Criterios de Aceptación Etapa 1:**
- [ ] Middleware de rate limiting implementado
- [ ] Configuración diferenciada por endpoint en .env
- [ ] Respuesta 429 con headers y formato según spec
- [ ] Redis (o memory) operando y limpiando expirados
- [ ] Test manual: exceder límite, validar 429 y Retry-After
- [ ] Auditoría de rate limits en logs (IP, endpoint, hit count)
- [ ] Whitelisting de IPs test/desarrollo funciona

---

### **Etapa 2: Validación de Elegibilidad de Ticket**
**Meta:** Crear flujo de validación previa que un ticket es elegible para facturación.

**Deliverables:**
- Endpoint privado de validación de tickets (POST /facturacion/validar-ticket-eligibilidad).
- Token efímero firmado que autoriza operaciones de RFC asociadas.
- Pruebas de elegibilidad en BD.
- Invalidación de tokens tras uso (one-time).

**Definición de "Ticket Elegible":**

Un ticket (HistoryEstacionamiento) es elegible para facturación si:

```
1. Existe en BD (history_id válido)
2. Estado = pagado (history.pagado == True)
3. Monto >= umbral mínimo (default: $10 MXN)
4. NO está facturado ya:
   - No existe invoice_request exitoso con source_id = history.id
5. NO está cancelado/revocado en operación
6. Dentro de ventana temporal:
   - Salida fue dentro de últimas 72 horas
   - (policy: no facturar tickets muy antiguos)
7. Datos completos y válidos:
   - Placa existe y tiene formato válido
   - Fecha/hora de salida coherentes
   - Método pago registrado (efectivo o tarjeta)
```

#### Endpoint de Validación de Ticket

```
POST /facturacion/validar-ticket-eligibilidad

Request:
{
  "history_id": 12345
}

Response 200 (elegible):
{
  "eligible": true,
  "ticket_proof_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_expires_at": "2026-04-06T15:45:00Z",
  "ticket_summary": {
    "placa": "ABC1234",
    "importe": 150.50,
    "fecha_salida": "2026-04-06",
    "hora_salida": "10:30:00",
    "metodo_pago": "efectivo"
  },
  "message": "Ticket elegible para facturación"
}

Response 400 (no elegible):
{
  "eligible": false,
  "reason": "ALREADY_INVOICED",
  "detail": "Este ticket ya tiene una factura emitida",
  "code": "TICKET_NOT_ELIGIBLE"
}

Response 404:
{
  "detail": "Ticket con ID 12345 no encontrado",
  "code": "TICKET_NOT_FOUND"
}
```

#### Estructura de ticket_proof_token

```
JWT Firmado con HS256 (FACTURACION_ACCESS_TOKEN_PEPPER del .env)

Payload:
{
  "sub": "ticket_proof",
  "ticket_id": 12345,
  "importe": 150.50,
  "placa_hash": "sha256(placa)", // Hash para validar luego
  "iat": 1712425200,
  "exp": 1712425500,  // 5 minutos de duración
  "nonce": "random_string"
}

Características:
- TTL: 5 minutos (ventana estrecha, user debe usar rápido)
- Una sola dirección de uso
- Vinculado a ticket_id específico
- No reutilizable (se invalida tras primer uso)
- Hash de placa para detección de tampering
```

#### Reglas de Negocio en Validación

```
Regla 1: Tickets pagados hace más de 72 horas NO son elegibles
  → Mensaje: "Ticket muy antiguo para facturación"

Regla 2: Si el ticket ya está en invoice_requests con status='issued'
  → NO elegible
  → Mensaje: "Ya existe una factura válida para este ticket"

Regla 3: Si monto < $10 MXN
  → NO elegible
  → Mensaje: "Monto insuficiente para facturación"

Regla 4: Si falta algún dato (placa, hora, etc)
  → NO elegible
  → Mensaje: "Datos de ticket incompletos"

Regla 5: Validación de consistencia
  → Si hay invoice_request con status='cancelled' pero mismo ticket_id
  → SÍ es elegible de nuevo (política: se puede reemitir tras cancelación)
```

#### Validación de Token Proof en Endpoints Posteriores

Cuando cliente llame a POST /facturacion/clientes-fiscales o POST /facturacion/emitir:

```
1. Cliente incluye el ticket_proof_token en headers o payload
2. Backend valida token:
   - Firma correcta
   - No expirado
   - Nonce no usado antes (check en tabla de nonces consumidos)
   - ticket_id está en el payload
3. Si válido:
   - Procede con la operación
   - Marca token como consumido (invalidar para futuro)
4. Si inválido:
   - HTTP 401 "Token de validación de ticket inválido o expirado"
   - Cliente debe solicitar nuevo proof token
```

#### Tabla Nueva: ticket_proof_tokens (Auditoría)

```
id INT PK
ticket_id INT (FK a history_estacionamiento)
token_hash VARCHAR(64) (SHA256 del token original)
nonce VARCHAR(100)
status ENUM('valid', 'consumed', 'expired', 'revoked')
created_at DATETIME
consumed_at DATETIME NULL
expires_at DATETIME
ip VARCHAR(45)
user_agent_hash VARCHAR(64)
```

Sirve para:
- Garantizar one-time use
- Auditoría de quién validó qué ticket
- Detección de intentos de replay

**Criterios de Aceptación Etapa 2:**
- [ ] Endpoint POST /facturacion/validar-ticket-eligibilidad implementado
- [ ] Lógica de elegibilidad según 7 criterios arriba
- [ ] JWT proof token generado, firmado y con TTL de 5 min
- [ ] Tabla ticket_proof_tokens creada
- [ ] Validación de token en endpoints de registro/emisión
- [ ] Test: ticket elegible genera token válido
- [ ] Test: ticket facturado no genera token
- [ ] Test: token expirado es rechazado
- [ ] Test: token reutilizado es rechazado (one-time)

---

### **Etapa 3: Ligadura RFC ↔ Ticket Válido en Registro Fiscal**
**Meta:** Restringir creación/actualización de cliente fiscal solo si hay prueba de posesión de ticket válido.

**Deliverables:**
- Modificación de POST /facturacion/clientes-fiscales para requerir ticket_proof_token + reCAPTCHA.
- Validación de que RFC no existe para ese usuario/IP en ventana corta.
- Auditoría de cambios de datos fiscales (quién, cuándo, desde qué IP).
- Bloqueo de updates que cambien RFC (una vez creado, es inmutable).

#### Nuevo Flujo de Registro Fiscal

```
Paso 1: Usuario tiene un ticket válido sin facturar
  GET /history/{ticket_id} → confirma elegibilidad

Paso 2: Usuario solicita validación de ticket
  POST /facturacion/validar-ticket-eligibilidad
  + history_id: 12345
  → Retorna ticket_proof_token (TTL 5 min)

Paso 3: Frontend resuelve reCAPTCHA v3
  (JavaScript captura recaptcha_token)

Paso 4: Usuario completa datos fiscales y envía
  POST /facturacion/clientes-fiscales
  {
    "rfc": "AAA010101ABC",
    "razon_social": "Acme SA",
    "codigo_postal": "28001",
    "regimen_fiscal": "601",
    "email": "contacto@acme.com",
    "ticket_proof_token": "<JWT>",
    "recaptcha_token": "<token_google>"
  }

Paso 5: Backend valida
  1. reCAPTCHA: score >= 0.5
  2. Rate limit: < 5 req/min desde esta IP
  3. Ticket proof token: válido, no expirado, no consumido
  4. RFC: formato válido (regex SAT), 12-13 caracteres
  5. RFC duplicado en últimas 24h desde diferente IP: ALERTA (posible ataque)

Paso 6: Crea/actualiza fiscal_customer
  - Si nuevo: INSERT con created_ip, created_user_agent_hash
  - Si existe y mismo RFC: UPDATE con updated_ip, razón del update
  - Si existe pero RFC diferente: RECHAZAR (RFC inmutable)

Paso 7: Marca ticket_proof_token como consumido
  UPDATE ticket_proof_tokens SET status='consumed', consumed_at=NOW()
```

#### Modificaciones a FiscalCustomerUpsertRequest

```
Actual:
{
  "rfc": str,
  "razon_social": str,
  ...(otros campos)
}

Nuevo:
{
  "rfc": str,
  "razon_social": str,
  ...(otros campos),
  
  # Campos nuevos de seguridad
  "ticket_proof_token": str,           ← JWT validado en Etapa 2
  "recaptcha_token": str,              ← Token de Google reCAPTCHA v3
}
```

#### Tabla de Auditoría: fiscal_customer_audit

```
id INT PK
fiscal_customer_id INT (FK)
change_type ENUM('create', 'update')
changed_fields JSON (ej: {"razon_social": {"old": "X", "new": "Y"}})
changed_by VARCHAR(50) (sistema/usuario/api)
created_at DATETIME
ip VARCHAR(45)
ua_hash VARCHAR(64) (SHA256 de User-Agent)
ticket_id INT (FK a history_estacionamiento, si aplica)
```

Permite:
- Auditoría fiscal de quién cambió qué
- Trazabilidad IP + UA
- Correlación con ticket que autorizó el cambio

#### Validaciones de RFC

```
Validación de Formato RFC:
- Longitud: exactamente 12 o 13 caracteres
- Estructura: 3 letras + 6 números + 4 alfanuméricos (o persona física: 12 caracteres)
- Regex: ^[A-ZÑ&]{3,4}[0-9]{6}[A-Z0-9]{3}$
- Sin caracteres especiales excepto Ñ

Validación de Duplicación:
- Query: SELECT * FROM fiscal_customers WHERE rfc = ? AND is_active = TRUE
- Si existe y misma IP/UA en últimas 24h: PERMITIR (actualización legítima)
- Si existe y diferente IP/UA en últimas 24h: ALERTA en logs (posible ataque)
- Si existe desde >7 días: NOTAR en auditoría (usuario cambió de red)

Validación de RFC Ajeno:
- Actualmente no hay verificación SAT (costo/complejidad alto)
- Mitigation: 
  - Auditoría completa de intentos
  - Score de riesgo (nuevas IPs, múltiples RFCs desde misma IP, etc)
  - (Futuro: challenge OTP si score alto)
```

#### Bloqueos y Alertas

```
Escenario 1: Mismo RFC, misma IP, < 1 hora
  → UPDATE tranquilo, auditoría nota "cambio de datos"

Escenario 2: Mismo RFC, distinta IP, < 24h
  → UPDATE permitido, auditoría ALERTA "RFC desde IP diferente"
  → Log: "Posible cambio legítimo (usuario cambió red)"

Escenario 3: RFC nuevo, IP nuca vista
  → CREATE normal, auditoría standard

Escenario 4: RFC nuevo, misma IP registró 5 RFCs en 1 hora
  → CREATE pero LOG CRÍTICO: "Posible ataque de creación masiva"
  → Métrica de alerta

Escenario 5: RFC ajeno (detectado por cliente después)
  → Cliente reporta
  → Admin puede desactivar y auditar
  → (Futuro: reverse lookup por correo verificado)
```

#### Respuesta 200 en POST /facturacion/clientes-fiscales

```json
{
  "id": 123,
  "rfc": "AAA010101ABC",
  "razon_social": "Acme SA DE CV",
  "codigo_postal": "28001",
  "regimen_fiscal": "601",
  "email": "contacto@acme.com",
  "is_active": true,
  "created_at": "2026-04-06T15:30:00Z",
  "updated_at": "2026-04-06T15:30:00Z",
  "message": "Cliente fiscal registrado correctamente",
  "ticket_linked": 12345,
  "ticket_proof_consumed": true
}
```

#### Respuestas de Error

```
HTTP 403 (reCAPTCHA fallido):
{
  "detail": "Verificación de humano fallida (score < 0.5)",
  "code": "RECAPTCHA_FAILED",
  "score": 0.35
}

HTTP 401 (Ticket proof inválido):
{
  "detail": "Token de validación de ticket inválido o expirado",
  "code": "INVALID_TICKET_PROOF",
  "hint": "Solicita nuevamente validación-ticket-elegibilidad"
}

HTTP 429 (Rate limit):
{
  "detail": "Demasiadas solicitudes desde tu IP",
  "code": "RATE_LIMITED",
  "retry_after_seconds": 35
}

HTTP 400 (RFC inválido):
{
  "detail": "RFC no válido. Debe tener 12-13 caracteres",
  "code": "INVALID_RFC"
}

HTTP 400 (RFC inmutable):
{
  "detail": "No puedes cambiar el RFC de un cliente fiscal existente",
  "code": "RFC_IMMUTABLE",
  "existing_rfc": "AAA010101ABC"
}
```

**Criterios de Aceptación Etapa 3:**
- [ ] POST /facturacion/clientes-fiscales requiere ticket_proof_token + recaptcha_token
- [ ] Validación de reCAPTCHA score >= 0.5
- [ ] Validación de rate limit 5 req/min
- [ ] RFC validado con regex SAT
- [ ] Tabla fiscal_customer_audit creada
- [ ] Auditoría registra IP, UA hash, ticket_id, change_type
- [ ] RFC marcado como inmutable tras primer creación
- [ ] Test: crear fiscal con ticket valid → OK
- [ ] Test: crear fiscal sin ticket_proof_token → 401
- [ ] Test: crear fiscal con reCAPTCHA fallido → 403
- [ ] Test: exceder 5 requests en 1 min → 429

---

### **Etapa 4: Restricción de Emisión a Tickets Elegibles**
**Meta:** Garantizar que solo se emiten facturas para tickets que cumplan criterios de elegibilidad y tengan prueba de autorización.

**Deliverables:**
- Modificación de POST /facturacion/emitir para requerir ticket_proof_token.
- Validación de que fiscal_customer fue creado a partir de ese ticket.
- Bloqueo de emisión para tickets ya facturados.
- Auditoría de intentos fallidos.

#### Nuevo Flujo de Emisión de Factura

```
Paso 1: Usuario tiene un ticket validado y RFC registrado
  (precedentes: Etapa 3 completada)

Paso 2: Usuario solicita validación de ticket nuevamente
  POST /facturacion/validar-ticket-elegibilidad
  + history_id: 12345
  → Retorna nuevo ticket_proof_token (TTL 5 min, different nonce)

Paso 3: Frontend resuelve reCAPTCHA v3 para emisión
  (nuevo token, acción: "emitir_factura")

Paso 4: Usuario envía solicitud de emisión
  POST /facturacion/emitir
  {
    "fiscal_customer_id": 123,
    "history_estacionamiento_id": 12345,
    "placa": "ABC1234",
    "fecha_salida": "2026-04-06",
    "hora_salida": "10:30:00",
    "importe": 150.50,
    "send_email": true,
    "ticket_proof_token": "<JWT>",
    "recaptcha_token": "<token_google>"
  }

Paso 5: Backend valida
  1. reCAPTCHA: score >= 0.5
  2. Rate limit: < 3 req/min desde esta IP
  3. Ticket proof token: válido, no expirado, no consumido, ticket_id = history_id
  4. HistoryEstacionamiento: existe, pagado, dentro de 72h, monto >= $10
  5. FiscalCustomer: existe, activo, mismo RFC que al registrar
  6. Consistencia: placa, fecha, hora, importe coinciden exactamente
  7. No duplicado: no existe invoice_request exitoso para este ticket

Paso 6: Crea Invoice Request
  - Genera access_token (para download/status/cancel later)
  - Status: 'processing'

Paso 7: Marca ticket_proof_token como consumido
  UPDATE ticket_proof_tokens SET status='consumed', consumed_at=NOW()

Paso 8: Auditoría de emisión
  INSERT INTO invoice_events (invoice_request_id, event_type, ...)
  WITH invoice_request_id, ticket_id, fiscal_customer_id, ip, ua_hash
```

#### Modificaciones a InvoiceEmitRequest

```
Actual:
{
  "fiscal_customer_id": int,
  "history_estacionamiento_id": int,
  "placa": str,
  "fecha_salida": date,
  "hora_salida": time,
  "importe": float,
  "send_email": bool,
  "notes": str | None
}

Nuevo:
{
  "fiscal_customer_id": int,
  "history_estacionamiento_id": int,
  "placa": str,
  "fecha_salida": date,
  "hora_salida": time,
  "importe": float,
  "send_email": bool,
  "notes": str | None,
  
  # Campos nuevos de seguridad
  "ticket_proof_token": str,           ← Same JWT de validación
  "recaptcha_token": str               ← Token Google reCAPTCHA v3
}
```

#### Validaciones de Consistencia Estricta

```
Cuando se emite factura, validar que datos de request = datos de ticket:

1. Placa: request.placa.upper().strip() == history.placa.upper()
2. Fecha salida: request.fecha_salida == history.fecha_salida
3. Hora salida: request.hora_salida == history.hora_salida
4. Importe: abs(float(request.importe) - float(history.importe)) <= 0.01 (MXN)
5. Estado pagado: history.pagado == True
6. Dentro de ventana: (NOW() - history.fecha_salida) <= 72 horas
7. No facturado:
   - SELECT COUNT(*) FROM invoice_requests
     WHERE source_id = history.id AND status IN ('issued', 'processing')
   - Counter debe ser 0

Si alguna falla:
- Retornar HTTP 400 con código específico
- NO crear invoice_request
- Auditoría registra el fallo (para detección de tampering)
```

#### Auditoría de Intentos Fallidos

```
Nueva tabla: invoice_emit_failures

id INT PK
history_id INT (FK)
fiscal_customer_id INT (FK)
failure_reason VARCHAR(100) (ej: MISMATCH_PLACA, ALREADY_ISSUED, RATE_LIMITED, etc)
ip VARCHAR(45)
ua_hash VARCHAR(64)
created_at DATETIME

Queries útiles:
- SELECT ip, COUNT(*) FROM invoice_emit_failures 
  WHERE created_at > NOW() - INTERVAL 1 HOUR
  GROUP BY ip
  ORDER BY COUNT(*) DESC
  → Detección de IPs intentando break/attack

- SELECT history_id, COUNT(*) FROM invoice_emit_failures
  WHERE created_at > NOW() - INTERVAL 24 HOUR
  GROUP BY history_id
  → Tickets atacados frecuentemente (posible shared link?)
```

#### Respuesta 200 en POST /facturacion/emitir

```json
{
  "invoice_request_id": 456,
  "status": "processing",
  "fiscal_customer_id": 123,
  "source_type": "history_exit",
  "source_id": "12345",
  "idempotency_key": "history_exit-12345-a1b2c3d4",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "access_token_expires_at": "2026-04-13T15:30:00Z",
  "created_at": "2026-04-06T15:30:00Z",
  "message": "Factura en proceso de emisión",
  "ticket_proof_consumed": true
}
```

**Criterios de Aceptación Etapa 4:**
- [ ] POST /facturacion/emitir requiere ticket_proof_token + recaptcha_token
- [ ] Validación de reCAPTCHA score >= 0.5
- [ ] Validación de rate limit 3 req/min
- [ ] Validación de consistencia placa, fecha, hora, importe
- [ ] Bloqueo si ya existe invoice_request exitoso
- [ ] Tabla invoice_emit_failures creada
- [ ] Auditoría registra attempt, failure_reason, ip, ua_hash
- [ ] Test: emitir con ticket valid y RFC matching → OK
- [ ] Test: emitir con placa incorrecta → 400 MISMATCH
- [ ] Test: emitir con ticket ya facturado → 400 ALREADY_ISSUED
- [ ] Test: emitir sin ticket_proof_token → 401
- [ ] Test: emitir con reCAPTCHA fallido → 403
- [ ] Test: exceder 3 requests en 1 min → 429

---

### **Etapa 5: Hardening Adicional (Opcional, Post-MVP)**
**Meta:** Capas defensivas avanzadas para mitigación de riesgos residuales.

**Deliverables (no críticos para MVP, pero recomendados para producción):**
1. Challenge OTP a correo registrado si score de riesgo alto.
2. Validación de RFC contra SAT (si es viable).
3. Detección de patrones de fraude (ML o heurísticas).
4. Rate limiting por RFC (no solo IP).
5. Reversión de cambios de RFC por admin si se reporta suplantación.

#### Sub-etapa 5.1: Risk Scoring

```
Variables de riesgo:
- RFC nunca visto desde esta IP
- IP registró >3 RFCs en 24h
- IP registró RFCs en múltiples países/ciudades
- UA (User-Agent) nunca vista
- Patrón de captcha scores bajos reciente
- Intentos fallidos repetidos desde misma IP

Score = suma ponderada de variables

Si score >= 7 (de 10):
  → Requerir OTP a correo del RFC para confirmar
  → Añadir delay antes de permitir emisión
  → Log crítico en auditoría
```

#### Sub-etapa 5.2: Validación SAT (Future)

```
Si viable contractualmente:
- Consultar API SAT para verificar RFC válido
- Verificar rfc existe y está activo
- (Cost: ~1-10 centavos por consulta)
- Cache por 24h para no repetir
```

---

## 3. Dependencias Externas

### **Requerimientos Python**

```
google-auth>=2.0.0       # Para reCAPTCHA server-side (requests)
redis>=4.0.0             # Para rate limiting distribuido (opcional)
slowapi>=0.1.5           # Librería Rate limiting FastAPI (alternativa a Redis manual)
pydantic>=1.10           # Validación (ya existe)
python-jose>=3.3.0       # JWT (ya existe)
```

### **Configuración Google reCAPTCHA**

- API key: https://www.google.com/recaptcha/admin
- Documentación: https://developers.google.com/recaptcha/docs/v3
- Sandbox testing: https://developers.google.com/recaptcha/docs/domain_validation#domain_validation

### **Almacenamiento de Datos**

Tablas nuevas/modificadas:
1. `ticket_proof_tokens` (nueva) - Auditoría de validaciones de tickets
2. `fiscal_customer_audit` (nueva) - Auditoría de cambios fiscales
3. `invoice_emit_failures` (nueva) - Auditoría de fallos en emisión

---

## 4. Configuración .env (Completa)

```
# reCAPTCHA v3
RECAPTCHA_SECRET_KEY=6Lc...your_secret...
RECAPTCHA_SITE_KEY=6Lc...your_public...
RECAPTCHA_SCORE_THRESHOLD=0.5
RECAPTCHA_TIMEOUT_SECONDS=3

# Rate Limiting
RATELIMIT_ENABLED=true
RATELIMIT_STORAGE=redis  # o 'memory'
RATELIMIT_REDIS_URL=redis://localhost:6379/1
RATELIMIT_FISCAL_CUSTOMER_GET_PER_MIN=30
RATELIMIT_FISCAL_CUSTOMER_POST_PER_MIN=5
RATELIMIT_EMITIR_POST_PER_MIN=3
RATELIMIT_SOLICITUD_GET_PER_MIN=20
RATELIMIT_SOLICITUD_CANCEL_POST_PER_MIN=2
RATELIMIT_WHITELIST_IPS=127.0.0.1,::1

# Ticket Elegibility
TICKET_ELEGIBILITY_MIN_AMOUNT=10.0
TICKET_ELEGIBILITY_MAX_AGE_HOURS=72
TICKET_PROOF_TOKEN_TTL_MINUTES=5
TICKET_PROOF_TOKEN_SECRET=your_pepper_key_here
TICKET_PROOF_ONE_TIME_ENFORCE=true

# Auditoría
AUDIT_LOG_FISCAL_CHANGES=true
AUDIT_LOG_EMIT_FAILURES=true
```

---

## 5. Flujo End-to-End Integrado

```
┌─── Usuario Estacionamiento ────────────────┐
│ Tiene ticket pagado sin facturar           │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ Frontend obtiene URL │
        │ de ticket en BD      │
        └──────────────┬───────┘
                       │
                       ▼
        ┌──────────────────────────────────┐
        │ POST validar-ticket-elegibilidad │
        │ + history_id: 12345              │
        └──────────────┬───────────────────┘
                       │
                       ▼ (Backend valida elegibilidad)
        ┌──────────────────────────────────┐
        │ Retorna:                         │
        │ + ticket_proof_token (JWT, 5min) │
        │ + ticket_summary                 │
        └──────────────┬───────────────────┘
                       │
                       ▼
        ┌──────────────────────────────────┐
        │ Frontend + reCAPTCHA v3           │
        │ (usuario completa form)          │
        │ + ticket_proof_token             │
        │ + recaptcha_token                │
        │ + datos fiscales (RFC, etc)      │
        └──────────────┬───────────────────┘
                       │
                       ▼ (Google reCAPTCHA API)
                 (score >= 0.5?)
                       │
            ┌──────────┴──────────┐
            │                     │
      Score < 0.5          Score >= 0.5
            │                     │
            ▼                     ▼
       403 REJECTED         ┌──────────────────────────┐
                            │ POST clientes-fiscales   │
                            │ + ticket_proof_token     │
                            │ + recaptcha_token        │
                            └──────────────┬───────────┘
                                           │
                                   (Rate limit? IP < 5 req/min)
                                           │
                            ┌──────────────┴──────────────┐
                            │                             │
                      Dentro de límite            Excedido límite
                            │                             │
                            ▼                             ▼
                  (Validar, crear)            429 Too Many Requests
                            │
                            ▼
                  ┌──────────────────────────────┐
                  │ fiscal_customer creado       │
                  │ + auditoría registrada       │
                  │ + token marcado consumido    │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │ Usuario quiere emitir        │
                  │ POST validar-ticket-elegib.. │
                  │ (nuevo token, mismo flow)    │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │ Nuevo ticket_proof_token     │
                  │ reCAPTCHA nuevamente         │
                  │ POST /facturacion/emitir     │
                  └──────────────┬───────────────┘
                                 │
                          (Validaciones)
                    (reCAPTCHA, rate limit,
                     token, consistencia, etc)
                                 │
                            ┌────┴────┐
                      ✓ OK           ✗ Error
                            │           │
                            ▼           ▼
                  ┌────────────────┐  400-429
                  │ Invoice creado │  (auditoría)
                  │ status=proces. │
                  │ token acceso   │
                  │ para status/   │
                  │ download/canc. │
                  └────────────────┘
```

---

## 6. Matriz de Riesgos Residuales (Post-Implementación)

| Riesgo | Severidad | Mitigación Actual | Gaps | Fase Futura |
|--------|-----------|-------------------|------|-------------|
| Bot masivo en registro | Alta | reCAPTCHA v3 + rate limit | Score spoofing (improbable) | Monitoreo continuo |
| Scraping de RFCs | Media | Rate limit 30 req/min GET | IP distribuida | OTP por IP nueva |
| RFC ajeno registrado | Alta | Ticket válido requerido | Usuario legítimo fraudulento | Auditoría + reporte |
| Spam de emisión | Media | Rate limit 3 req/min + ticket | VPN/proxy | Risk scoring avanzado |
| Suplantación fiscal | Muy alta | Auditoría completa + trazabilidad | SAT no validado | Validación SAT (fase 5.2) |
| Token proof reutilizado | Baja | One-time + TTL + nonce | Colisión (nonce random) | Criptografía robusta |

---

## 7. Plan de Testing (Sin Código)

### **Testing Manual**

```
Caso 1: Flujo Happy Path
- Usuario con ticket válido se registra con RFC
- Emite factura exitosamente
- Descarga XML/PDF con token

Caso 2: reCAPTCHA Falla
- Simular score < 0.5
- Verificar HTTP 403 y mensaje

Caso 3: Rate Limiting Activado
- 6ta solicitud POST en 1 min → 429
- Retry-After header presente

Caso 4: Ticket No Elegible
- Ticket sin pagar → validación falla
- Ticket > 72h → validación falla
- Ticket ya facturado → validación falla

Caso 5: Inconsistencia de Datos
- Placa diferente en emisión → 400 MISMATCH
- Importe diferente > 0.01 → 400 MISMATCH

Caso 6: RFC Inmutable
- Crear con RFC AAA010101ABC
- Intentar update a BBB020202XYZ → 400 RFC_IMMUTABLE
```

### **Testing Automatizado (Unit/Integration)**

```
- Mocks de Google reCAPTCHA (score variable)
- Fixtures de HistoryEstacionamiento (pagado, no pagado, viejo, etc)
- Pruebas de JWT: firma, expiración, reuso
- Pruebas de rate limit: contador reset, TTL
- Pruebas de auditoría: registros creados correctamente
```

---

## 8. Roadmap de Implementación

```
Etapa 0
├─ reCAPTCHA v3 setup
├─ RecaptchaService en core/
└─ Auditoría mínima

    ↓ (A partir de aquí, endpoints comienzan a usar reCAPTCHA)

Etapa 1
├─ Rate limiting middleware
├─ Configuración por endpoint
└─ Respuestas 429 consistency

    ↓ (A partir de aquí, endpoints públicos tienen defensa anti-bot/abuso)

Etapa 2
├─ POST validar-ticket-elegibilidad
├─ JWT proof token (5 min TTL)
├─ ticket_proof_tokens table
└─ One-time use enforcement

    ↓ (A partir de aquí, se requiere prueba de ticket para operaciones)

Etapa 3
├─ POST clientes-fiscales requiere ticket_proof_token
├─ RFC inmutable tras creación
├─ fiscal_customer_audit table
└─ Validaciones de RFC y duplicación

    ↓ (A partir de aquí, no se puede registrar RFC arbitrario)

Etapa 4
├─ POST emitir requiere ticket_proof_token
├─ Validaciones de consistencia
├─ invoice_emit_failures table
└─ Auditoría de intentos

    ↓ (Producción "endurecida")

Etapa 5 (Opcional)
├─ Risk scoring
├─ OTP challenge
├─ Validación SAT
└─ Detección avanzada de fraude
```

---

## 9. Criterios de Aceptación Global

**MVP Seguro (Etapas 0-4 completadas):**
- ✓ reCAPTCHA v3 operativo en endpoints públicos
- ✓ Rate limits activos sin falsos positivos
- ✓ Registro fiscal ligado a ticket válido y no reutilizable
- ✓ Emisión de factura con autorización de ticket
- ✓ Auditoría completa de intentos (OK y fallidos)
- ✓ Resultados: Puntuación de 8/10 esperada

**Testing OK:**
- ✓ 100% de casos happy path pasan
- ✓ 100% de casos de error retornan códigos correctos
- ✓ Auditoría registra IP, UA hash, correlaciones

**Documentación:**
- ✓ Blueprint actualizado con implementación real
- ✓ README con flow de usuario
- ✓ Guía de troubleshooting para soportes

---

**Próximos Pasos:**
1. Aprobar este blueprint (conforme a tu estrategia).
2. Preparar tareas de desarrollo por etapa.
3. Iniciar Etapa 0 (reCAPTCHA setup).
