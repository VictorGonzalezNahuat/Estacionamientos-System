# Blueprint Tecnico: Cancelacion de Tickets con Auditoria
**Proyecto:** Estacionamientos Backend  
**Fecha:** 2026-04-10  
**Version:** 1.0  
**Estado:** Diseno aprobado (pendiente implementacion)

---

## 1. Objetivo

Implementar la cancelacion de tickets de salida con trazabilidad completa, agregando:
1. Un estado de cancelacion en `history_estacionamiento`.
2. Una tabla de auditoria `tickets_cancelados` con motivo obligatorio.
3. Reglas para excluir tickets cancelados de operaciones administrativas.
4. Guardas de negocio para evitar inconsistencias en corte, facturacion y pagos.

---

## 2. Reglas de Negocio Confirmadas

1. Se puede cancelar un ticket pagado en efectivo:
   - Si, solo cuando NO tenga `corte_id` asignado.
2. Se puede cancelar un ticket ya facturado:
   - No.
3. Se puede cancelar un ticket con `corte_id` asignado:
   - No.
4. Motivo de cancelacion:
   - Obligatorio.
5. Quien puede cancelar:
   - Cualquier usuario autenticado, siempre capturando motivo.

Interpretacion operativa:
1. Un ticket cancelado deja de participar en calculos administrativos.
2. El sistema debe conservar evidencia de quien cancelo, cuando y por que.
3. La cancelacion no elimina registros historicos; solo los marca y audita.

---

## 3. Cambios de Datos (BD)

## 3.1 Campo nuevo en history_estacionamiento

Agregar columna:
1. `cancelado` TINYINT/SMALLINT NOT NULL DEFAULT 0.
   - `0`: activo.
   - `1`: cancelado.

Indices recomendados:
1. `(cancelado, corte_id)` para consultas administrativas pendientes de corte.
2. `(cancelado, fecha_salida)` para reportes diarios/rangos.
3. `(payment_transaction_id, cancelado)` para estados de pago.

## 3.2 Nueva tabla tickets_cancelados

Campos propuestos:
1. `id` BIGINT PK autoincrement.
2. `history_estacionamiento_id` BIGINT NOT NULL FK.
3. `payment_transaction_id` BIGINT NULL FK.
4. `motivo` VARCHAR(500) NOT NULL.
5. `cancelado_por` BIGINT NOT NULL FK a `usuarios.id`.
6. `fecha_cancelacion` DATETIME/TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP.
7. `created_at` DATETIME/TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP.
8. `updated_at` DATETIME/TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP.

Restricciones recomendadas:
1. FK `history_estacionamiento_id` -> `history_estacionamiento.id`.
2. FK `payment_transaction_id` -> `payment_transactions.id`.
3. FK `cancelado_por` -> `usuarios.id`.
4. `motivo` no vacio (validar en API y opcionalmente check constraint).
5. Unicidad por ticket cancelado:
   - `UNIQUE(history_estacionamiento_id)` para evitar doble cancelacion.

SQL de referencia (adaptar a motor final):

```sql
ALTER TABLE history_estacionamiento
  ADD COLUMN cancelado TINYINT NOT NULL DEFAULT 0;

CREATE INDEX idx_history_cancelado_corte
  ON history_estacionamiento (cancelado, corte_id);

CREATE INDEX idx_history_cancelado_fecha
  ON history_estacionamiento (cancelado, fecha_salida);

CREATE INDEX idx_history_payment_cancelado
  ON history_estacionamiento (payment_transaction_id, cancelado);

CREATE TABLE tickets_cancelados (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  history_estacionamiento_id BIGINT NOT NULL,
  payment_transaction_id BIGINT NULL,
  motivo VARCHAR(500) NOT NULL,
  cancelado_por BIGINT NOT NULL,
  fecha_cancelacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT uq_tickets_cancelados_hist UNIQUE (history_estacionamiento_id),
  CONSTRAINT fk_tc_history FOREIGN KEY (history_estacionamiento_id) REFERENCES history_estacionamiento(id),
  CONSTRAINT fk_tc_payment FOREIGN KEY (payment_transaction_id) REFERENCES payment_transactions(id),
  CONSTRAINT fk_tc_usuario FOREIGN KEY (cancelado_por) REFERENCES usuarios(id)
);
```

---

## 4. Flujo de Cancelacion (Happy Path)

1. Usuario invoca endpoint de cancelacion de pago/ticket con `preferencia_id` y `motivo`.
2. Sistema valida autenticacion y motivo obligatorio.
3. Sistema busca transaccion y ticket historico asociado.
4. Validaciones de negocio:
   - Ticket existe.
   - Ticket no esta ya cancelado.
   - Ticket no tiene `corte_id`.
   - Ticket no tiene factura emitida.
5. Sistema intenta cancelacion remota con proveedor (si aplica), sin bloquear cancelacion local por fallo remoto.
6. Sistema marca:
   - `payment_transaction.estado = cancelado`.
   - `history_estacionamiento.cancelado = 1`.
7. Sistema inserta registro en `tickets_cancelados` con motivo y usuario.
8. Sistema confirma transaccion de BD atomica.
9. Respuesta API incluye resultado local/remoto y metadatos de cancelacion.

---

## 5. Flujo de Rechazo (Guardas)

Casos que deben rechazar cancelacion:
1. Ticket no encontrado.
2. Ticket ya cancelado.
3. Ticket con `corte_id` asignado.
4. Ticket con factura emitida o solicitud en proceso de emision.
5. Motivo vacio o solo espacios.

Codigos sugeridos:
1. `404` no encontrado.
2. `400` motivo invalido.
3. `409` conflicto de negocio (ya cancelado, con corte, facturado).

---

## 6. Endpoints/Modulos Impactados

## 6.1 Criticos

1. Pagos
   - `POST /pagos/cancelar/{preferencia_id}`:
     - aplicar reglas de cancelacion,
     - actualizar history,
     - registrar auditoria en `tickets_cancelados`.

2. Cortes de caja
   - `POST /corte-caja/`:
     - excluir `cancelado = 1` de totales y asignacion de `corte_id`.
   - `GET /corte-caja/turno/{turno_id}/resumen`:
     - excluir cancelados.
   - `GET /corte-caja/{corte_id}/pdf`:
     - no incluir cancelados en movimientos operativos del reporte.

3. Historial
   - `GET /history/hoy`:
     - excluir cancelados.
   - `GET /history/dia/filtrar`:
     - excluir cancelados.
   - `GET /history/rango`:
     - excluir cancelados.
   - `GET /history/reimpresion/ultimos`:
     - excluir cancelados.
   - `POST /history/reimpresion/{historial_id}`:
     - bloquear si cancelado.

4. Facturacion
   - validaciones de ticket para facturacion:
     - rechazar si `cancelado = 1`.

5. Webhooks de pago
   - no finalizar/confirmar ticket si ya fue cancelado.

## 6.2 Complementarios

1. Schemas de request/response de cancelacion:
   - reforzar motivo obligatorio (min length > 0 tras trim).
2. Modelos ORM:
   - agregar campo `cancelado` y modelo `TicketCancelado`.
3. Sync local-nube (si aplica a este entorno):
   - incluir tabla nueva en estrategia de sincronizacion.

---

## 7. Contrato API de Cancelacion (propuesto)

Request:
```json
{
  "provider": "stripe",
  "motivo": "Cobro duplicado en caja"
}
```

Response exito:
```json
{
  "preferencia_id": "pref_123",
  "estado_transaccion": "cancelado",
  "cancelado_local": true,
  "cancelado_remoto": true,
  "provider": "stripe",
  "motivo": "Cobro duplicado en caja",
  "detalle": "Checkout cancelado en proveedor"
}
```

Errores sugeridos:
1. `MOTIVO_OBLIGATORIO`
2. `TICKET_NO_ENCONTRADO`
3. `TICKET_YA_CANCELADO`
4. `TICKET_EN_CORTE`
5. `TICKET_FACTURADO`

---

## 8. Invariantes del Sistema

1. Si `history_estacionamiento.cancelado = 1`, el ticket no participa en:
   - resumenes de turno,
   - corte de caja,
   - historial administrativo operativo,
   - reimpresion de salida,
   - facturacion.
2. Todo ticket cancelado debe tener exactamente un registro en `tickets_cancelados`.
3. Todo registro en `tickets_cancelados` debe tener motivo no vacio.
4. Nunca cancelar ticket ya facturado.
5. Nunca cancelar ticket incluido en corte.

---

## 9. Casos de Prueba Minimos (criterios de aceptacion)

1. Cancelacion exitosa de ticket efectivo sin corte y sin factura.
2. Rechazo de cancelacion por motivo vacio.
3. Rechazo de cancelacion por ticket ya cancelado.
4. Rechazo de cancelacion por ticket con `corte_id`.
5. Rechazo de cancelacion por ticket facturado.
6. Confirmar que corte excluye cancelados en totales.
7. Confirmar que historial (hoy/dia/rango) excluye cancelados.
8. Confirmar que reimpresion falla para cancelados.
9. Confirmar que validacion de facturacion bloquea cancelados.
10. Confirmar comportamiento webhook cuando el ticket ya esta cancelado.

---

## 10. Plan de Implementacion (orden recomendado)

Fase 1: Esquema de datos
1. Migracion de columna `cancelado`.
2. Migracion de tabla `tickets_cancelados`.
3. Indices y constraints.

Fase 2: Dominio y persistencia
1. Actualizar modelos ORM.
2. Ajustar schemas de cancelacion (motivo obligatorio).
3. Implementar logica transaccional de cancelacion.

Fase 3: Blindaje operativo
1. Excluir cancelados en endpoints de historial.
2. Excluir cancelados en endpoints de corte.
3. Bloquear reimpresion de cancelados.
4. Bloquear facturacion de cancelados.
5. Blindar webhook contra tickets cancelados.

Fase 4: Pruebas y regresion
1. Unit tests de reglas de negocio.
2. Tests integracion de endpoints criticos.
3. Verificacion de reportes y totales.

---

## 11. Riesgos y Mitigaciones

1. Carrera entre webhook y cancelacion:
   - Mitigar con validacion de estado cancelado antes de finalizar pago.
2. Datos legacy sin campo cancelado:
   - Mitigar con default `0` y migracion segura.
3. Inconsistencias por doble cancelacion:
   - Mitigar con `UNIQUE(history_estacionamiento_id)` y control de conflicto 409.
4. Degradacion de consultas administrativas:
   - Mitigar con indices por `cancelado`.

---

## 12. Resultado Esperado

Al finalizar la implementacion:
1. Se podra cancelar tickets bajo reglas claras y auditables.
2. Los tickets cancelados no contaminaran operaciones administrativas.
3. Existira trazabilidad completa de motivo y usuario que cancelo.
4. Se mantendra consistencia entre pagos, historial, corte y facturacion.
