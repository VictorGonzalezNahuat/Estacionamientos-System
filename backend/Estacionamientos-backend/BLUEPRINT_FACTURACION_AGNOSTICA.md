# Blueprint de Integracion de Facturacion Electronica (Agnostica de Proveedor)

Fecha: 2026-04-04
Estado: Planeacion (sin implementacion)
Contexto: Se prioriza Facturapi como primer proveedor, pero la arquitectura no debe depender de un proveedor unico.

## 1) Objetivo

Disenar una capacidad de facturacion electronica para el sistema de estacionamiento que:
- Funcione con un primer adaptador para Facturapi.
- Permita cambiar o sumar proveedores sin reescribir la logica de negocio.
- Mantenga trazabilidad fiscal y operativa (pago, emision, cancelacion, reintentos, auditoria).
- No bloquee el flujo critico de salida de vehiculos.

## 2) Hallazgos del sistema actual

Fortalezas:
- Existe separacion por capas (routes, core, models, schemas).
- Existe patron de proveedor en pagos (PaymentProvider) reutilizable conceptualmente.
- El flujo de salida y pago concentra el dominio donde conviene enganchar facturacion.
- Se persiste metadata de transacciones, util para correlacion fiscal.

Riesgos/Gaps:
- No hay capa de facturacion desacoplada de proveedor.
- No hay modelo de datos fiscal para CFDI/documentos emitidos.
- No hay modelo de datos para clientes fiscales (receptor de factura).
- No se identifica estrategia formal de migraciones para cambios de esquema.
- La configuracion actual no expone datos/flags de facturacion en su API administrativa.

Notas sobre scope:
- Sincronizacion local-nube: NO aplica en esta fase (todo local, BD nube sin cambios).
- Datos fiscales son capturados y almacenados en local en el momento de solicitar factura.
- Frontend expone rutas de facturacion solo en despliegue final.

## 3) Principios de arquitectura recomendados

1. Proveedor agnostico por contrato
- Definir una interfaz InvoiceProvider con operaciones de alto nivel.
- Facturapi sera solo un adaptador inicial (FacturapiInvoiceProvider).

2. Dominio primero, proveedor despues
- El sistema decide que facturar y cuando.
- El adaptador solo traduce el dominio al API externo.

3. Flujo asincrono para resiliencia
- El evento de pago/salida crea una solicitud de factura.
- Un worker/proceso de reintento emite factura fuera del request del usuario.

4. Idempotencia obligatoria
- Cada solicitud fiscal debe tener idempotency_key estable.
- Evitar doble timbrado por reintentos/webhooks duplicados.

5. Evidencia y auditoria
- Guardar request/respuesta resumida, estatus, errores y referencias externas.
- Mantener ligas a XML/PDF/acuse cuando aplique.

## 4) Arquitectura objetivo (sin implementar)

## 4.1 Contrato agnostico

Interfaz conceptual InvoiceProvider:
- upsert_customer(customer_data) -> customer_ref
- issue_invoice(invoice_request) -> invoice_result
- get_invoice(external_invoice_id) -> invoice_status
- cancel_invoice(external_invoice_id, reason) -> cancel_result
- download_artifacts(external_invoice_id) -> artifacts (xml_url, pdf_url)
- healthcheck() -> provider_status

## 4.2 Modelos de dominio sugeridos

A) fiscal_customers (Clientes fiscales / Receptores)
- id (PK)
- rfc (string 13, UNIQUE INDEX)
- razon_social (string 255)
- codigo_postal (string 5)
- regimen_fiscal (string 50, ej: "601")
- uso_cfdi_receptor (string 3, default "G03")
- nombre_contacto (string 255, nullable)
- email (string 255, nullable)
- telefono (string 20, nullable)
- is_active (bool, default True)
- created_at / updated_at
- last_invoiced_at (nullable)

B) invoice_requests
- id
- fiscal_customer_id (FK a fiscal_customers)
- source_type: payment_transaction | history_exit | manual
- source_id (PK de source_type)
- idempotency_key (RFC + source_id + hash para evitar duplicados)
- status: pending | processing | issued | failed | cancelled
- total
- currency
- invoice_payload_json
- provider_name (ej: "facturapi")
- provider_customer_id
- provider_invoice_id
- provider_last_error
- attempts
- next_retry_at
- created_at / updated_at

C) invoice_documents
- id
- invoice_request_id (FK)
- uuid_fiscal (FIEL SAT)
- serie (string, ej "F")
- folio (int, ej 1)
- issued_at
- xml_url
- pdf_url
- verification_url (consultarle.sat.gob.mx)
- subtotal
- taxes
- total
- status (emitida | cancelada)
- cancelled_at (nullable)

D) invoice_events (auditoria)
- id
- invoice_request_id (FK)
- event_type (ej: "created", "issued", "failed", "cancelled")
- payload_summary_json
- success (bool)
- error_message (nullable, sin exponer detalles SAT)
- created_at

Notas:
- fiscal_customers: tabla central para identidad fiscal del receptor.
- invoice_requests: vincula cliente fiscal con transaccion de pago/salida.
- invoice_documents: persiste CFDI una vez emitido.
- Evitar guardar RFC/datos sensibles en texto plano en campos de error.

## 4.3 Flujo recomendado

**Flujo de Cliente Fiscal (RFC):**
1. Cliente ingresa RFC en frontend.
2. Sistema consulta GET /facturacion/clientes-fiscales/por-rfc/{rfc}.
3. Si existe: retorna datos precargados (nombre, regimen, codigo postal).
4. Si NO existe: frontend abre formulario para capturar datos minimos.
5. Sistema persiste cliente fiscal en BD local con POST /facturacion/clientes-fiscales.
6. Cliente confirma y procede a solicitar factura.

**Flujo de Emision de Factura:**
1. Cliente pagado solicita factura: POST /facturacion/emitir.
   - Input: fiscal_customer_id, payment_transaction_id, send_email.
2. Sistema crea invoice_request en estado pending con idempotency_key.
3. [Sincronico en MVP o Asincrono en prod] Worker/background task:
   - Valida que pago esta completado.
   - Construye payload CFDI segun dominio.
   - Llama InvoiceProvider.issue_invoice().
4. Si proveedor retorna UUID:
   - Guardar invoice_document con uuid_fiscal, xml_url, pdf_url.
   - Marcar invoice_request como issued.
5. Si falla transitorio (timeout, rate limit):
   - Incrementar attempts.
   - Programar retry en next_retry_at (exponencial backoff).
6. Si falla definitivo (RFC invalido, datos incompletos):
   - Marcar failed y registrar error sin exponer detalles SAT.
7. Cliente consulta GET /facturacion/solicitudes/{invoice_request_id}:
   - Obtiene status, uuid, xml/pdf URLs si esta lista.
   - Puede cancelar POST /facturacion/solicitudes/{id}/cancelar si es necesario.

## 5) Politicas funcionales a definir antes de construir

1. Cuando se factura:
- Manual: Cliente solicita factura cuando lo desea (inicio recomendado).
- Automatico: (Fase futura) Al pago completado, se auto-emite.
- Ventana: Decidir si se pueden facturar operaciones historicas (retroactivas).

2. Que metodos de pago aplican:
- Tarjeta: Sí, requiere factura para comprobante.
- Efectivo: Por definir (regimes fiscales pueden variar).
- Ambos: Evaluar necesidad vs complejidad.

3. Datos minimos de receptor (cliente fiscal):
- RFC: Obligatorio, validado contra formato (13 caracteres).
- Razon Social: Obligatorio.
- Codigo Postal: Obligatorio, validado (5 digitos).
- Regimen Fiscal: Obligatorio, listado SAT (601, 603, 605, etc.).
- Uso CFDI: Obligatorio, default "G03" (Gastos generales).
- Email/Telefono: Opcional (para futuro envio de factura).

4. Datos minimos del comprobante CFDI:
- Tipo: Ingreso.
- Moneda: MXN.
- Metodo de pago: TDD (Transferencia bancaria) para tarjeta, EFE (Efectivo) para cash.
- Forma de pago: Por definir segun regulacion.

5. Politica de cancelacion/sustitucion:
- Permitir cancelacion si esta emitida pero sin pago vinculado (retro).
- Sustitucion: Evaluar si es necesario en MVP.
- Fecha limite para cancelar: Por definir (ej: mismo dia, 7 dias, etc.).

6. Reintento en caso de fallo:
- Maximo 3-5 intentos antes de marcar definitivamente como fallido.
- Backoff exponencial: 5 min, 15 min, 30 min, etc.
- No reintentar si error es definitivo (RFC invalido, datos incompletos).

7. Conciliacion:
- Reporte diario de facturas emitidas vs pagos confirmados.
- Alertar si pago existe pero no hay factura (e.g., timeout en emision).

## 6) Integracion con arquitectura actual

Puntos de extension naturales:
- core/parking_exit_service.py: origen de evento de salida/pago.
- routes/pagos.py: vincular estado de transaccion con estado de factura.
- core/payment_provider.py: referencia conceptual para contrato de proveedor (reutilizar patron).
- routes/configuracion.py + core/config.py + schemas/configuracion.py: habilitar flags de facturacion en BD local (no credenciales sensibles en respuestas publicas).

Nuevos modulos a crear:
- core/invoice_provider.py: Contrato agnostico de proveedor (similar a payment_provider.py).
- core/facturapi_service.py: Adaptador concreto para Facturapi.
- core/fiscal_customer_service.py: Logica de busqueda/creacion de clientes fiscales.
- routes/facturacion.py: Endpoints de emision, consulta, cancelacion.
- models/fiscal_customer.py: Modelo de cliente fiscal.
- models/invoice_request.py: Modelo de solicitud de factura.
- models/invoice_document.py: Modelo de CFDI emitido.
- models/invoice_event.py: Modelo de auditoria de eventos fiscales.
- schemas/fiscal_customer.py: Esquemas Pydantic para validacion.
- schemas/invoice_*.py: Esquemas de solicitud/respuesta de facturacion.

Compatibilidad:
- Alta: por modularidad y patron de proveedor ya presente.
- Riesgo bajo: no afecta sync (todo local) ni cambios a tablas criticas actuales.
- Migracion: Evaluar si usar script manual de creacion de tablas o Alembic para futuro.

## 7) Estrategia de proveedor (Facturapi primero, sin lock-in)

1. Crear abstraccion InvoiceProvider independiente de PaymentProvider.
2. Implementar FacturapiInvoiceProvider como adaptador inicial.
3. Definir normalizacion interna de estados:
- draft | issued | cancelled | failed
4. Mantener mapeo de errores por proveedor a errores de dominio.
5. Evitar exponer estructuras nativas de Facturapi al resto del sistema.

## 8) Plan por fases (roadmap)

Fase 0: Discovery funcional-fiscal (2 a 4 dias)
- Cerrar decisiones de negocio y cumplimiento.
- Definir catalogo de casos de uso y excepciones.

Fase 1: Diseño tecnico (3 a 5 dias)
- Esquema de datos final.
- Contratos de servicio.
- Estrategia de retries/idempotencia.
- Plan de migracion de datos.

Fase 2: MVP controlado (1 a 2 semanas)
- Emision manual desde una operacion pagada.
- Persistencia de estado documental.
- Consulta de factura y descarga de artefactos.

Fase 3: Automatizacion robusta (1 a 2 semanas)
- Disparo automatico asincrono.
- Reintentos y monitoreo.
- Cancelacion y sustitucion.

Fase 4: Operacion y escalado (3 a 5 dias)
- Conciliacion diaria.
- Dashboards de errores.
- Hardening de seguridad y observabilidad.

## 9) Riesgos tecnicos y mitigacion

1. Doble timbrado por retries/webhooks duplicados
- Mitigacion: idempotency_key unica (RFC + source_id + hash) + validacion de estado antes de emitir.

2. Caidas del proveedor externo (Facturapi)
- Mitigacion: reintentos exponenciales (5-30-60 min), max 3-5 intentos, registro de cada intento.

3. RFC invalido o datos incompletos detectados tardíamente
- Mitigacion: validar formato RFC en captura, validar codigo postal, regimen contra catalogos.
- Fallar rápido si datos criticos faltan.

4. Cambios de reglas fiscales SAT
- Mitigacion: encapsular validaciones en fiscal_customer_service.py + versionamiento de catalogo CFDI en BD.

5. Exposicion de credenciales Facturapi
- Mitigacion: secretos por entorno (.env), no retornarlos en APIs de configuracion.
- No guardar tokens de respuesta en BD.

6. Inconsistencias entre datos locales y respuesta de SAT
- Mitigacion: sincronizar UUID desde respuesta de Facturapi, guardar xml_url oficial.
- Reportes de conciliacion diarios.

## 10) Checklist de readiness para iniciar implementacion

Producto/Operacion:
- [ ] Politica oficial de cuando facturar aprobada (manual en MVP).
- [ ] Responsables de cancelacion/sustitucion definidos.
- [ ] Decidir si se facturas retroactivas (historicas) en MVP o fase 2.

Fiscal/Cumplimiento:
- [ ] Matriz de datos obligatorios por tipo de receptor cerrada.
- [ ] Catalogos CFDI (Regimen, Uso CFDI, Forma de Pago) validados.
- [ ] Politica de publico en general (RFC generico) definida si aplica.
- [ ] Validacion RFC contra SAT: decidir si es necesario en MVP o asumir cliente es responsable.

Tecnico:
- [ ] Contrato InvoiceProvider aprobado (ver ESPECIFICACION_FLUJO_CLIENTE_FISCAL.md).
- [ ] Modelos de datos (fiscal_customers, invoice_requests, invoice_documents) aprobados.
- [ ] Endpoints API de cliente fiscal y facturacion especificados (ver doc complementario).
- [ ] Estrategia de creacion de tablas acordada (script manual o Alembic).
- [ ] Definicion de reintentos e idempotencia aprobada.
- [ ] Prioridad: trabajar TODO en BD local, nube sin cambios.

Seguridad:
- [ ] Politica de secretos Facturapi por entorno (.env).
- [ ] Politica de retencion de XMLs/PDFs (almacenamiento externo vs URL de proveedor).
- [ ] Rate limiting en endpoints publicos de facturacion.
- [ ] Validacion de inputs (RFC, email, etc.) contra inyeccion.

Integracion:
- [ ] Modelo Facturapi validado en sandbox.
- [ ] Respuesta JSON de emision y cancelacion entendida.

QA:
- [ ] Casos criticos documentados:
  - RFC nuevo -> creacion cliente -> emision factura.
  - RFC existente -> reutilizacion -> emision.
  - RFC invalido -> error captura.
  - Timeout en emision -> reintento.
  - Duplicado -> idempotencia.
  - Cancelacion -> sustitucion o nulificacion.
- [ ] Plan de pruebas locales + sandbox Facturapi.

## 11) Entregables de analisis producidos

**Documentos generados (como base para implementacion):**

1. BLUEPRINT_FACTURACION_AGNOSTICA.md (este archivo)
   - Arquitectura objective, principios, riesgos, plan por fases.
   - Agnóstico de proveedor de facturacion.

2. ESPECIFICACION_FLUJO_CLIENTE_FISCAL.md (complementario)
   - Flujo detallado de captura RFC y datos del cliente fiscal.
   - Endpoints API de cliente fiscal (buscar, crear, actualizar).
   - Endpoints API de emision y consulta de factura.
   - Modelos de datos (fiscal_customers, invoice_requests, invoice_documents, invoice_events).
   - Validaciones, reglas SAT, checklist pre-implementacion.

**Entregables faltantes (siguiente fase):**

3. ADR (Architecture Decision Record)
   - Justificar decisiones de agnóstico vs proveedor, asincronia, idempotencia.

4. Contrato de InvoiceProvider
   - Definicion formal de interfaz / protocolo de proveedor.
   - Mapeo de errores de Facturapi a errores de dominio.

5. Schema de migracion de BD
   - Script SQL (o alembic) para crear tablas:
     - fiscal_customers
     - invoice_requests
     - invoice_documents
     - invoice_events
   - Decidir si usar script manual o integrar con Alembic.

6. Matriz de errores de negocio vs Facturapi
   - RFC invalido SAT -> INVALID_RFC_FORMAT (usuario).
   - Timeout Facturapi -> PROVIDER_TIMEOUT (retry).
   - CFDI.Atributos invalido -> RFC_NOT_IN_SAT (usuario, reintento no).
   - etc.

7. Plan de pruebas (QA) y criterios de aceptacion
   - Casos criticos cubiertos.
   - Sandboxing de Facturapi.
   - Validaciones de RFC/CP/Regimen.

## 12) Recomendacion final

**Recomendacion de implementacion:**

1. Arquitectura agnóstica confirmada.
   - Facturapi como primer adaptador, sin lock-in a este proveedor.
   - Contrato InvoiceProvider permite sumar/cambiar proveedores sin reescribir dominio.

2. Flujo de cliente fiscal validado como elemento central.
   - RFC es entrada clave del usuario final.
   - Autocarga de datos existentes minimiza fricccion en UX.
   - Captura incremental vs precarga evita asumir datos que no tenemos.

3. TODO en BD local (no nube).
   - Simplifica operacion inicial, sin complejidad de sincronizacion.
   - Datos fiscales almacenados solo localmente hasta nuevo aviso.
   - Facilita testing y iteración sin afectar entorno productivo.

4. Priority antes de coding:
   - Cerrar catalogo SAT (regimenes, usos CFDI, formas de pago).
   - Definir politica de cuando se factura (manual en MVP).
   - Validar datos minimos del receptor en Facturapi sandbox.
   - Aprobar contratos API (ESPECIFICACION_FLUJO_CLIENTE_FISCAL.md como base).

5. Riesgos mitigados:
   - Doble timbrado: idempotency_key unica por (rfc, source_id).
   - Falla de proveedor: reintentos exponenciales, no bloquea salida de auto.
   - RFC invalido: validacion en captura, error temprano.
   - Cambios SAT: encapsular validaciones, versionamiento de catalogos.

**Siguiente paso:** Llevar estos dos documentos a sesión de product/fiscal/tech para marcar checkboxes de readiness y aprobar timeline de Fase 1 (MVP controlado).
