# Especificacion de Flujo: Gestion de Cliente Fiscal por RFC

Fecha: 2026-04-04
Contexto: Complemento al BLUEPRINT_FACTURACION_AGNOSTICA.md
Alcance: Operacion local únicamente. Base de datos nube sin cambios.

## 1) Introduccion

El flujo de facturacion comienza con la identificacion del cliente receptor. En lugar de asumir datos precargados, el sistema permite que el usuario (cliente del estacionamiento) ingrese su RFC en el momento de solicitar factura, y el sistema gestiona su perfil fiscal de forma incremental:
- Búsqueda por RFC.
- Autocarga de datos si existe.
- Captura de datos si es nuevo.
- Reutilización en futuras solicitudes.

## 2) Actores

1. Cliente del estacionamiento (usuario final que se estaciona).
2. Sistema de estacionamiento (backend + frontend).
3. Proveedor de facturacion (Facturapi u otro).

## 3) Flujo de usuario (alto nivel)

Momento: Cliente desea obtener factura por su estacionamiento pagado.

Paso 1. Cliente ingresa RFC
- Endpoint PUT/POST: /facturacion/clientes fiscales/buscar-o-crear

Paso 2. Sistema busca RFC en tabla de clientes fiscales
- Si existe -> retorna datos precargados (nombre, rfc, regimen, codigo postal)
- Si NO existe -> retorna HTTP 404 para que frontend abra formulario de captura

Paso 3. Cliente completa formulario (si es nuevo) o confirma datos (si existe)
- RFC (readonly si ya existe)
- Nombre / Razon Social
- Codigo Postal
- Regimen Fiscal (ej: 601 Personas fisicas sin actividad empresarial)
- Uso CFDI receptor (ej: G03 Gastos en general) [opcional o default]

Paso 4. Sistema guarda cliente fiscal
- Endpoint POST: /facturacion/clientes-fiscales
- Valida RFC, codigo postal, regimen.
- Devuelve cliente_fiscal_id o actualiza existente.

Paso 5. Cliente solicita factura para una transaccion pagada
- Endpoint POST: /facturacion/emitir
- Input: cliente_fiscal_id, payment_transaction_id (o history_estacionamiento_id)
- Sistema crea invoice_request, delega a InvoiceProvider.

Paso 6. Sistema retorna estado de factura
- UUID fiscal, folio, URLs de XML/PDF si estan listos.
- Status: pending, emitida, fallida.

## 4) Diseño de datos para cliente fiscal

### Tabla: fiscal_customers (o invoice_customers)

```
id: int (PK)
rfc: string(13) NOT NULL UNIQUE INDEX
razon_social: string(255) NOT NULL
codigo_postal: string(5) NOT NULL
regimen_fiscal: string(50) NOT NULL
  formato: tabla SAT, ej "601" "603" "605"
uso_cfdi_receptor: string(3) DEFAULT "G03"
  uso CFDI segun SAT, ej "G03", "I01", etc.
nombre_contacto: string(255) NULLABLE
email: string(255) NULLABLE
telefono: string(20) NULLABLE
notas: text NULLABLE
is_active: bool DEFAULT True
created_at: datetime
updated_at: datetime
last_invoiced_at: datetime NULLABLE
```

Notas:
- RFC como UNIQUE para búsqueda directa.
- No guardar datos sensibles de banco (serán parte del método de pago en Facturapi, no aquí).
- email/telefono permiten envio automatico de factura (futuro).

### Tabla: invoice_customer_revisions (auditoria, opcional)

```
id: int (PK)
fiscal_customer_id: int (FK)
change_type: enum ['create', 'update']
changed_fields: json (ej: {"razon_social": {"old": "X", "new": "Y"}})
changed_by: string (usuario/sistema)
changed_at: datetime
```

Permite ver historico de cambios (importante para auditoria fiscal).

## 5) Endpoints de API (especificacion contractual)

### 5.1 Buscar cliente fiscal por RFC

**Endpoint:** `GET /facturacion/clientes-fiscales/por-rfc/{rfc}`

**Respuesta 200:**
```json
{
  "id": 123,
  "rfc": "AAA010101ABC",
  "razon_social": "Acme SA DE CV",
  "codigo_postal": "28001",
  "regimen_fiscal": "601",
  "uso_cfdi_receptor": "G03",
  "nombre_contacto": "Juan Perez",
  "email": "juan@empresa.com",
  "is_active": true,
  "created_at": "2026-03-15T10:30:00Z",
  "updated_at": "2026-04-01T14:20:00Z"
}
```

**Respuesta 404:**
```json
{
  "detail": "Cliente fiscal con RFC AAA010101XYZ no encontrado",
  "code": "FISCAL_CUSTOMER_NOT_FOUND"
}
```

**Autenticacion:** Ninguna (el usuario puede ingresar cualquier RFC).
**Rate limiting:** Sí (max 100 req/min por IP para evitar scraping).

---

### 5.2 Crear o actualizar cliente fiscal

**Endpoint:** `POST /facturacion/clientes-fiscales`

**Request:**
```json
{
  "rfc": "AAA010101ABC",
  "razon_social": "Acme SA DE CV",
  "codigo_postal": "28001",
  "regimen_fiscal": "601",
  "uso_cfdi_receptor": "G03",
  "nombre_contacto": "Juan Perez",
  "email": "juan@empresa.com",
  "telefono": "+34 911 234 567"
}
```

**Respuesta 201 (creado):**
```json
{
  "id": 123,
  "rfc": "AAA010101ABC",
  "razon_social": "Acme SA DE CV",
  "codigo_postal": "28001",
  "regimen_fiscal": "601",
  "uso_cfdi_receptor": "G03",
  "nombre_contacto": "Juan Perez",
  "email": "juan@empresa.com",
  "is_active": true,
  "created_at": "2026-04-04T10:30:00Z",
  "updated_at": "2026-04-04T10:30:00Z",
  "message": "Cliente fiscal creado correctamente"
}
```

**Respuesta 200 (actualizado si RFC ya existe):**
```json
{
  "id": 123,
  "rfc": "AAA010101ABC",
  ...
  "message": "Cliente fiscal actualizado correctamente"
}
```

**Respuesta 400 (RFC invalido):**
```json
{
  "detail": "RFC invalido. Debe tener 13 caracteres",
  "code": "INVALID_RFC_FORMAT"
}
```

**Respuesta 400 (Codigo postal invalido):**
```json
{
  "detail": "Codigo postal debe ser de 5 digitos",
  "code": "INVALID_POSTAL_CODE"
}
```

**Respuesta 400 (Regimen fiscal invalido):**
```json
{
  "detail": "Regimen fiscal debe ser uno de: 601, 603, 605, ...",
  "code": "INVALID_TAX_REGIME"
}
```

**Autenticacion:** Ninguna (publico para clientes internos del estacionamiento).
**Validaciones en backend:**
- RFC: formato 13 caracteres (3 letras + 6 numeros + 4 caracteres alfanumericos).
- Codigo postal: exactamente 5 digitos.
- Razon social: max 255 caracteres, no vacio.
- Regimen fiscal: validar contra catalogo SAT.
- Uso CFDI: validar contra catalogo SAT (opcional, default "G03").

---

### 5.3 Solicitar emision de factura

**Endpoint:** `POST /facturacion/emitir`

**Request:**
```json
{
  "fiscal_customer_id": 123,
  "payment_transaction_id": 456,
  "send_email": true,
  "notes": "Factura por estacionamiento Zona A - Dia completo"
}
```

O alternativa (si queremos usar history_estacionamiento):
```json
{
  "fiscal_customer_id": 123,
  "history_estacionamiento_id": 789,
  "send_email": true
}
```

**Respuesta 201 (solicitud creada, inicio de procesamiento):**
```json
{
  "invoice_request_id": "INV-2026-04-04-001",
  "status": "pending",
  "fiscal_customer_id": 123,
  "idempotency_key": "AAA010101ABC-456-...hash",
  "created_at": "2026-04-04T15:30:00Z",
  "message": "Solicitud de factura creada. Se procesara en breve."
}
```

**Respuesta 400 (Cliente fiscal inexistente):**
```json
{
  "detail": "Cliente fiscal ID 123 no encontrado",
  "code": "FISCAL_CUSTOMER_NOT_FOUND"
}
```

**Respuesta 400 (Transaccion no pagada):**
```json
{
  "detail": "La transaccion 456 no tiene estado completado",
  "code": "TRANSACTION_NOT_PAID"
}
```

**Respuesta 409 (Duplicada por idempotencia):**
```json
{
  "detail": "Ya existe factura para esta combinacion. Ver invoice_request_id ...",
  "code": "INVOICE_ALREADY_EXISTS",
  "existing_invoice_request_id": "INV-2026-04-04-001"
}
```

**Autenticacion:** Opcional (sin usuario logueado) o token simple si es cliente registrado.

---

### 5.4 Consultar estado de factura

**Endpoint:** `GET /facturacion/solicitudes/{invoice_request_id}`

**Respuesta 200:**
```json
{
  "invoice_request_id": "INV-2026-04-04-001",
  "status": "issued",
  "fiscal_customer_id": 123,
  "payment_transaction_id": 456,
  "provider_name": "facturapi",
  "provider_invoice_id": "6282e3d5ba4e2e00015c5c1a",
  "uuid_fiscal": "12345678-90AB-CDEF-1234-567890ABCDEF",
  "serie": "F",
  "folio": "1",
  "issued_at": "2026-04-04T15:35:22Z",
  "subtotal": 150.00,
  "taxes": 24.00,
  "total": 174.00,
  "currency": "MXN",
  "xml_url": "https://drive.google.com/..../factura.xml",
  "pdf_url": "https://drive.google.com/..../factura.pdf",
  "verification_url": "https://verificador.sat.gob.mx/...",
  "attempts": 1,
  "last_error": null,
  "created_at": "2026-04-04T15:30:00Z",
  "updated_at": "2026-04-04T15:35:22Z"
}
```

**Respuesta 200 (aun procesando):**
```json
{
  "invoice_request_id": "INV-2026-04-04-001",
  "status": "processing",
  "attempts": 2,
  "next_retry_at": "2026-04-04T15:45:00Z",
  "last_error": null,
  "created_at": "2026-04-04T15:30:00Z"
}
```

**Respuesta 200 (fallida):**
```json
{
  "invoice_request_id": "INV-2026-04-04-001",
  "status": "failed",
  "attempts": 3,
  "last_error": "CFDI.Atributos.Expedido.RFC: El RFC debe estar registrado en el SAT",
  "created_at": "2026-04-04T15:30:00Z",
  "updated_at": "2026-04-04T15:40:00Z"
}
```

**Respuesta 404:**
```json
{
  "detail": "Solicitud INV-2026-04-04-999 no encontrada",
  "code": "INVOICE_REQUEST_NOT_FOUND"
}
```

---

### 5.5 Cancelar factura emitida

**Endpoint:** `POST /facturacion/solicitudes/{invoice_request_id}/cancelar`

**Request:**
```json
{
  "motivo": "01",
  "comentario": "Error en datos del cliente"
}
```

**Respuesta 200:**
```json
{
  "invoice_request_id": "INV-2026-04-04-001",
  "status": "cancelled",
  "cancelled_at": "2026-04-04T16:00:00Z",
  "uuid_sustitucion": null,
  "message": "Factura cancelada correctamente"
}
```

**Respuesta 400 (Factura no puede cancelarse):**
```json
{
  "detail": "Solo se pueden cancelar facturas con status 'issued'. Status actual: 'processing'",
  "code": "INVALID_STATUS_FOR_CANCELLATION"
}
```

---

## 6) Flujo de datos con secuencia UML (simplificada)

```
Cliente        Frontend       Backend API      InvoiceProvider
  |                |              |                    |
  | RFC ingresado  |              |                    |
  |-----GET RFC----|---GET /clientes/{rfc}----------->|
  |                |              |                    |
  |                |<---404 no existe----             |
  |                | muestra formulario               |
  | completa datos |              |                    |
  |-----POST datos-|---POST /clientes----->|          |
  |                |<---201 guardado---   |          |
  |                |                       |          |
  | solicita fact  |-----POST /emitir---->|          |
  |                |                       | crea req |
  |                | <---201 pending----              |
  |                |                       | async: |
  |                |                       | consulta provider
  | [polling]      |-----GET estado---    | emite CFDI
  |                |<---status: issued    |          |
  |                | uuid, XML, PDF URL              |
  |                |                                  |
  |        [usuario descarga PDF]                    |
```

## 7) Validaciones de negocio por campo

### RFC
- Formato: 3 letras + 6 numeros + 4 caracteres alfanumericos (13 total).
- Contra SAT: validar especificamente si es necesario, o asumir que el cliente es responsable.
- Caso: insensible a mayusculas, normalizar a uppercase en BD.
- Unicidad: un RFC = un cliente fiscal en el sistema (incluso si hay variaciones de nombre).

### Razon Social / Nombre
- Max 255 caracteres.
- No vacio.
- Permite caracteres especiales (acentos, ñ, simbolos).

### Codigo Postal
- Exactamente 5 digitos numericos.
- Validar contra INEGI si es critico (opcional para MVP).

### Regimen Fiscal
- Valores predefinidos segun SAT:
  - 601 Personas fisicas sin actividad empresarial.
  - 603 Personas fisicas con actividad empresarial.
  - 605 Personas fisicas arrendadora de inmuebles.
  - 606 Personas fisicas ejericio de profesión.
  - Empresas: 601, 603, 605, etc.
- Depende del tipo de cliente.
- Para MVP: puede ser dropdown fijo o campo abierto que se resguarde en BD.

### Uso CFDI Receptor
- Valores SAT:
  - G01 Adquisicion de mercancias.
  - G02 Devoluciones, descuentos o bonificaciones.
  - G03 Gastos en general.
  - I01 Construcciones.
  - I02 Mobilario y equipo de oficina.
  - I03 Equipo de transporte.
  - I04 Equipo de computo y accesorios.
  - I05 Dados, troqueles, moldes, matrices y herramental.
  - I06 Activos intangibles.
  - I07 Bienes inmuebles.
  - ... (mas)
- Default: "G03 Gastos en general" para uso genérico.

## 8) Integracion con tablas de transacciones existentes

Relaciones:
- fiscal_customers -> puede tener muchos invoices (1:N).
- invoice_requests -> apunta a una fiscal_customer_id.
- invoice_requests -> apunta a un payment_transaction_id (pago completado).
- invoice_documents -> representa el CFDI ya emitido (mismo invoice_request_id).

FK a agregar en invoice_requests:
```
fiscal_customer_id: int (FK a fiscal_customers)
```

Esto permite trazar: pago -> cliente fiscal -> factura.

## 9) Flujo de datos en el tiempo (estado)

Cliente fiscal:
1. **No existe** -> Se crea en estado ACTIVE.
2. **Existe** -> Se puede actualizar (nombre, regimen, etc.) sin afectar facturación anterior.

Invoice request (solicitud de factura):
1. **pending** -> Just creada, aguardando procesamiento asincrono.
2. **processing** -> Worker intenta emitir.
3. **issued** -> CFDI emitido exitosamente.
4. **failed** -> Error definitivo (RFC invalido, datos incompletos, etc.).
5. **cancelled** -> Cancelada por usuario o sistema.

## 10) Indicadores/Metricas

Para monitored:
- Clientes fiscales creados por dia.
- Solicitudes de factura por dia.
- Tasa de éxito (issued / total).
- Tiempo promedio desde pending -> issued.
- Errores más frecuentes por tipo.

## 11) Seguridad y privacidad

1. RFC: No es dato sensible per se, es publico para identificacion fiscal. Pero no debe exponerse en listados globales.
2. Email/Telefono: Si se usa para envios, cifrar en BD o usar columna separada.
3. No guardar datos bancarios en fiscal_customers. Facturapi los maneja en su BD.
4. Logs: Guardar intentos fallidos pero no errores detallados del SAT (puede filtrar RFC/datos sensibles).

## 12) Plan de implementacion (sin coding aun)

### Milestone 1: Estructura de datos y validaciones
- Definir tabla fiscal_customers con indices.
- Definir tabla invoice_requests y invoice_documents.
- Definir catalogo de regimenes/usos CFDI.

### Milestone 2: APIs de gestión de cliente fiscal
- Endpoint GET /clientes-fiscales/por-rfc/{rfc}.
- Endpoint POST /clientes-fiscales (crear/actualizar).
- Validaciones de RFC, código postal, regimen.

### Milestone 3: API de emision de factura
- Endpoint POST /facturacion/emitir.
- Endpoint GET /facturacion/solicitudes/{id}.
- Logica asincrona de emision (puede ser sincro en MVP).

### Milestone 4: Integracion con InvoiceProvider
- Implementar contrato InvoiceProvider.
- Implementar FacturapiInvoiceService.

## 13) Checklist pre-implementacion

- [ ] Catálogo de regímenes fiscales cerrado.
- [ ] Política de cancelación / sustitución definida.
- [ ] Decidir si se emite siempre o solo a demanda.
- [ ] Decidir si se envía email automático o el cliente descarga PDF.
- [ ] Plan de reintentos (delays, max intentos, estrategia de backoff).
- [ ] Plan de monitoreo y alertas de errores fiscales.
- [ ] Modelo de Facturapi validado en sandbox.
- [ ] Politica de retencion de XMLs/PDFs.
- [ ] Autenticacion definida para endpoints de facturacion (publico, token, login).
