# Resumen Ejecutivo: Plan de Facturacion Electronica

**Fecha:** 2026-04-04 | **Estado:** Planeacion | **Contexto:** RFC-driven local-only

---

## 1) Problema y objetivo

**Problema:** Cliente del estacionamiento necesita factura electronica por su pago de estacionamiento.

**Objetivo:** Capacidad de emitir CFDI a traves de Facturapi, con datos del cliente capturados en el momento (RFC-driven), sin bloquear flujo de salida del auto.

---

## 2) Flujo esperado

```
Cliente pide factura
    ↓
Ingresa RFC
    ↓
¿Existe en BD local?
    ├─ SI → Autocompleta datos (nombre, codigo postal, regimen)
    └─ NO → Abre formulario, cliente captura datos
    ↓
Sistema guarda cliente fiscal para proxima vez
    ↓
Cliente solicita emision de factura
    ↓
Sistema crea solicitud (pending)
    ↓
[Asincrono] Intenta emitir en Facturapi:
    ├─ Exito → UUID + XML/PDF URL
    ├─ Fallo transitorio → Reintenta (5-30-60 min)
    └─ Fallo definitivo → Error al usuario
    ↓
Cliente descarga PDF/XML
```

---

## 3) Decisiones clave

| Aspecto | Decision | Razon |
|--------|----------|-------|
| **Alcance** | TODO local, BD nube sin cambios | Simplifica MVP, sin riesgos de sincronizacion |
| **Captura RFC** | Usuario ingresa RFC, autocarga datos | UX sin friccion, datos inmediatos |
| **Cuando emitir** | Manual (usuario solicita) en MVP | Evita automatizacion prematura |
| **Asincronia** | Si, no bloquea salida de auto | Tolerancia a latencia de Facturapi |
| **Proveedor** | Facturapi como adaptador inicial | Agnóstico, se puede cambiar/sumar proveedor |
| **Idempotencia** | RFC + source_id + hash unico | Evita doble timbrado por reintentos |

---

## 4) Datos del cliente fiscal (ejemplo)

Usuario captura UNA SOLA VEZ por RFC:

```json
{
  "rfc": "AAA010101ABC",
  "razon_social": "Acme SA DE CV",
  "codigo_postal": "28001",
  "regimen_fiscal": "601",
  "uso_cfdi_receptor": "G03"
}
```

Proxima vez que el MISMO RFC ingrese, datos estan listos → autocompleta.

---

## 5) Arquitectura agnóstica

**Contrato InvoiceProvider:**
```
interface InvoiceProvider {
  upsert_customer(customer_data) → customer_ref
  issue_invoice(invoice_request) → invoice_result
  get_invoice(external_invoice_id) → invoice_status
  cancel_invoice(external_invoice_id, reason) → cancel_result
  download_artifacts(external_invoice_id) → {xml_url, pdf_url, ...}
}
```

Permite Facturapi hoy, cualquier otro proveedor mañana sin tocar logica de negocio.

---

## 6) Modelos de datos minimos

**1. fiscal_customers**
- RFC (PK), razon_social, codigo_postal, regimen_fiscal, uso_cfdi, is_active, timestamps

**2. invoice_requests**
- fiscal_customer_id, source_id (payment_tx), status, idempotency_key, attempts, provider response

**3. invoice_documents**
- UUID FIEL, serie, folio, xml_url, pdf_url, issued_at, status

**4. invoice_events**
- Auditoria: created, issued, failed, cancelled, con timestamps y errores (sin exponer SAT)

---

## 7) Endpoints API principales

| Endpoint | Metodo | Proposito |
|----------|--------|-----------|
| `/facturacion/clientes-fiscales/por-rfc/{rfc}` | GET | Buscar cliente por RFC |
| `/facturacion/clientes-fiscales` | POST | Crear/Actualizar cliente |
| `/facturacion/emitir` | POST | Solicitar emision de factura |
| `/facturacion/solicitudes/{id}` | GET | Consultar estado y artefactos |
| `/facturacion/solicitudes/{id}/cancelar` | POST | Cancelar factura emitida |

Todo sin autenticacion requerida (publico para usuarios del estacionamiento).

---

## 8) Riesgos y mitigaciones

| Riesgo | Mitigacion |
|--------|-----------|
| Doble timbrado | idempotency_key unica por operacion |
| Falla de Facturapi | Reintentos exponenciales (no bloquea al usuario) |
| RFC invalido | Validacion en captura (13 char, formato) |
| Timeout largo | Polling asincrono, usuario ve status en tiempo real |
| Cambios SAT | Catalogos versionados en BD, validaciones encapsuladas |

---

## 9) Fases de implementacion

| Fase | Entregable | Tiempo |
|------|-----------|--------|
| **0** | Cierre fiscal/operativo (definiciones SAT, cuando facturar) | 2-4 dias |
| **1** | MVP: Emision manual de factura (cliente fiscal + solicitud) | 1-2 semanas |
| **2** | Automatizacion: Auto-emision al pago, reintentos | 1-2 semanas |
| **3** | Operacion: Conciliacion, dashboards, hardening | 3-5 dias |

---

## 10) Checklist para avanzar (Fase 0)

- [ ] Regimen fiscal cliente: 601, 603, otra?
- [ ] Uso CFDI receptor por defecto: G03 (gastos)?
- [ ] RFC generico (publico en general) si aplica?
- [ ] Metodo de pago: solo tarjeta, tambien efectivo?
- [ ] Politica de cancelacion: mismo dia, 7 dias, indefinida?
- [ ] Facturapi sandbox: credenciales y test de request/response.
- [ ] RFC validacion: solo formato o contra SAT?

---

## 11) Documentacion de referencia

1. **BLUEPRINT_FACTURACION_AGNOSTICA.md** - Arquitectura, principios, riesgos, roadmap.
2. **ESPECIFICACION_FLUJO_CLIENTE_FISCAL.md** - Flujo detallado, endpoints, validaciones, checklist tecnico.

---

## 12) Recomendacion

1. **Revisar y aprobar checklist Fase 0** (producto, fiscal, tech).
2. **Presentar estos docs** a stakeholders para marcar decisiones SAT/operativas.
3. **No iniciar coding** hasta closure de politicas (evita retrabajo).
4. **Target MVP:** 2-3 semanas una vez aprobado Fase 0.
