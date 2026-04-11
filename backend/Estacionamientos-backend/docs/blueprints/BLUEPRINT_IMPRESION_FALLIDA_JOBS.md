# Blueprint Tecnico: Modulo de Impresion Fallida con Jobs y Auditoria
**Proyecto:** Estacionamientos Backend  
**Fecha:** 2026-04-08  
**Version:** 1.0  
**Estado:** Diseno sin implementacion

---

## 1. Objetivo

Crear un modulo separado de reimpresion de tickets erroneos con:
1. Persistencia de tickets fallidos en BD.
2. Reintentos manuales protegidos por current_user.
3. Auditoria completa de intentos y resoluciones.
4. Trazabilidad por origen (entrada, salida, corte, webhook).

Este modulo **no sustituye** reimpresion normal existente; es una cola operativa para fallos de impresora.

---

## 2. Que es un Job de impresion

Un **job** es una tarea de impresion persistida con ciclo de vida.

Estados del job:
1. `pending`: pendiente de reintento.
2. `retrying`: en intento activo (bloqueo logico).
3. `printed`: resuelto por impresion exitosa.
4. `discarded`: cerrado manualmente sin imprimir.

Diferencia contra "solo guardar ticket fallido":
1. El job permite auditar intentos multiples.
2. El job permite control de concurrencia.
3. El job permite metricas y SLA operativos.

---

## 3. Alcance Funcional

Incluye:
1. Captura automatica de fallo de impresion.
2. Lista de jobs fallidos con filtros.
3. Reintento manual por job.
4. Reintento en lote opcional.
5. Cierre manual (descartar) opcional.
6. Historial de intentos por job.

No incluye:
1. Reimpresion historica general (modulo distinto).
2. Confirmacion fisica de papel impreso (limitacion de impresora ESC/POS por red).

---

## 4. Modelo de Datos (Contrato BD)

## 4.1 Tabla principal: `print_jobs`

Campos obligatorios:

1. `id` BIGINT PK autoincrement.
2. `source_type` VARCHAR(40) NOT NULL.
3. `source_id` BIGINT NULL.
4. `placa` VARCHAR(100) NULL.
5. `tipo_ticket` VARCHAR(20) NOT NULL.
6. `copias` INT NOT NULL DEFAULT 1.
7. `ticket_payload` BLOB/BYTEA NOT NULL.
8. `payload_sha256` CHAR(64) NOT NULL.
9. `estado` VARCHAR(20) NOT NULL DEFAULT 'pending'.
10. `error_category` VARCHAR(30) NOT NULL DEFAULT 'unknown'.
11. `error_message` VARCHAR(1000) NOT NULL.
12. `attempts` INT NOT NULL DEFAULT 0.
13. `max_attempts` INT NOT NULL DEFAULT 10.
14. `created_by_user_id` BIGINT NULL.
15. `last_attempt_by_user_id` BIGINT NULL.
16. `resolved_by_user_id` BIGINT NULL.
17. `created_at` DATETIME/TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP.
18. `updated_at` DATETIME/TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP.
19. `last_attempt_at` DATETIME/TIMESTAMP NULL.
20. `printed_at` DATETIME/TIMESTAMP NULL.
21. `resolution_note` VARCHAR(500) NULL.

Restricciones:
1. CHECK `estado IN ('pending','retrying','printed','discarded')`.
2. CHECK `source_type IN ('entrada','salida_efectivo','salida_tarjeta','corte')`.
3. CHECK `tipo_ticket IN ('entrada','salida','corte')`.
4. CHECK `copias >= 1`.
5. CHECK `attempts >= 0`.
6. CHECK `max_attempts >= 1`.

Indices:
1. `idx_print_jobs_estado_created_at (estado, created_at)`.
2. `idx_print_jobs_source (source_type, source_id)`.
3. `idx_print_jobs_placa (placa)`.
4. `idx_print_jobs_payload_hash (payload_sha256)`.

## 4.2 Tabla de auditoria: `print_job_attempts`

Campos:
1. `id` BIGINT PK autoincrement.
2. `print_job_id` BIGINT NOT NULL FK -> print_jobs(id).
3. `attempt_number` INT NOT NULL.
4. `trigger_type` VARCHAR(20) NOT NULL. (`automatic`|`manual`)
5. `triggered_by_user_id` BIGINT NULL.
6. `started_at` DATETIME/TIMESTAMP NOT NULL.
7. `finished_at` DATETIME/TIMESTAMP NOT NULL.
8. `duration_ms` INT NULL.
9. `success` BOOLEAN NOT NULL.
10. `error_category` VARCHAR(30) NULL.
11. `error_message` VARCHAR(1000) NULL.
12. `printer_host_snapshot` VARCHAR(100) NULL.
13. `printer_port_snapshot` INT NULL.

Restricciones:
1. CHECK `attempt_number >= 1`.
2. CHECK `trigger_type IN ('automatic','manual')`.

Indices:
1. `idx_print_job_attempts_job_id (print_job_id)`.
2. `idx_print_job_attempts_started_at (started_at)`.

## 4.3 SQL de referencia (adaptar a motor final)

```sql
CREATE TABLE print_jobs (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  source_type VARCHAR(40) NOT NULL,
  source_id BIGINT NULL,
  placa VARCHAR(100) NULL,
  tipo_ticket VARCHAR(20) NOT NULL,
  copias INT NOT NULL DEFAULT 1,
  ticket_payload BYTEA NOT NULL,
  payload_sha256 CHAR(64) NOT NULL,
  estado VARCHAR(20) NOT NULL DEFAULT 'pending',
  error_category VARCHAR(30) NOT NULL DEFAULT 'unknown',
  error_message VARCHAR(1000) NOT NULL,
  attempts INT NOT NULL DEFAULT 0,
  max_attempts INT NOT NULL DEFAULT 10,
  created_by_user_id BIGINT NULL,
  last_attempt_by_user_id BIGINT NULL,
  resolved_by_user_id BIGINT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_attempt_at TIMESTAMP NULL,
  printed_at TIMESTAMP NULL,
  resolution_note VARCHAR(500) NULL,
  CONSTRAINT ck_print_jobs_estado CHECK (estado IN ('pending','retrying','printed','discarded')),
  CONSTRAINT ck_print_jobs_source_type CHECK (source_type IN ('entrada','salida_efectivo','salida_tarjeta','corte')),
  CONSTRAINT ck_print_jobs_tipo_ticket CHECK (tipo_ticket IN ('entrada','salida','corte')),
  CONSTRAINT ck_print_jobs_copias CHECK (copias >= 1),
  CONSTRAINT ck_print_jobs_attempts CHECK (attempts >= 0),
  CONSTRAINT ck_print_jobs_max_attempts CHECK (max_attempts >= 1)
);

CREATE INDEX idx_print_jobs_estado_created_at ON print_jobs (estado, created_at);
CREATE INDEX idx_print_jobs_source ON print_jobs (source_type, source_id);
CREATE INDEX idx_print_jobs_placa ON print_jobs (placa);
CREATE INDEX idx_print_jobs_payload_hash ON print_jobs (payload_sha256);

CREATE TABLE print_job_attempts (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  print_job_id BIGINT NOT NULL,
  attempt_number INT NOT NULL,
  trigger_type VARCHAR(20) NOT NULL,
  triggered_by_user_id BIGINT NULL,
  started_at TIMESTAMP NOT NULL,
  finished_at TIMESTAMP NOT NULL,
  duration_ms INT NULL,
  success BOOLEAN NOT NULL,
  error_category VARCHAR(30) NULL,
  error_message VARCHAR(1000) NULL,
  printer_host_snapshot VARCHAR(100) NULL,
  printer_port_snapshot INT NULL,
  CONSTRAINT fk_print_job_attempts_job FOREIGN KEY (print_job_id) REFERENCES print_jobs (id),
  CONSTRAINT ck_print_job_attempt_number CHECK (attempt_number >= 1),
  CONSTRAINT ck_print_job_attempt_trigger_type CHECK (trigger_type IN ('automatic','manual'))
);

CREATE INDEX idx_print_job_attempts_job_id ON print_job_attempts (print_job_id);
CREATE INDEX idx_print_job_attempts_started_at ON print_job_attempts (started_at);
```

---

## 5. Contrato API Exacto

Base path sugerido: `/impresion-fallida`

Seguridad:
1. Todos los endpoints requieren `current_user`.
2. Permisos sugeridos: admin y cajero.

Formato de error estandar:
```json
{
  "detail": {
    "code": "PRINT_JOB_NOT_FOUND",
    "message": "No existe job de impresion",
    "meta": {}
  }
}
```

## 5.1 GET /impresion-fallida/jobs

Descripcion:
Lista jobs con filtros y paginacion.

Query params:
1. `estado` opcional (`pending|retrying|printed|discarded`)
2. `source_type` opcional (`entrada|salida_efectivo|salida_tarjeta|corte`)
3. `placa` opcional
4. `from` opcional datetime ISO
5. `to` opcional datetime ISO
6. `limit` opcional int (default 50, max 200)
7. `offset` opcional int (default 0)

Response 200:
```json
{
  "items": [
    {
      "id": 101,
      "source_type": "salida_efectivo",
      "source_id": 5872,
      "placa": "ABC123",
      "tipo_ticket": "salida",
      "copias": 2,
      "estado": "pending",
      "error_category": "network",
      "error_message": "No se pudo conectar a la impresora",
      "attempts": 1,
      "max_attempts": 10,
      "last_attempt_at": "2026-04-08T09:10:11",
      "created_at": "2026-04-08T09:10:11",
      "printed_at": null
    }
  ],
  "paging": {
    "limit": 50,
    "offset": 0,
    "total": 1
  }
}
```

Errores:
1. `400 BAD_REQUEST` (filtro invalido)

## 5.2 GET /impresion-fallida/jobs/{job_id}

Descripcion:
Devuelve detalle de un job y su auditoria de intentos.

Response 200:
```json
{
  "job": {
    "id": 101,
    "source_type": "salida_efectivo",
    "source_id": 5872,
    "placa": "ABC123",
    "tipo_ticket": "salida",
    "copias": 2,
    "estado": "pending",
    "error_category": "network",
    "error_message": "No se pudo conectar a la impresora",
    "attempts": 1,
    "max_attempts": 10,
    "created_by_user_id": 8,
    "last_attempt_by_user_id": 8,
    "resolved_by_user_id": null,
    "created_at": "2026-04-08T09:10:11",
    "updated_at": "2026-04-08T09:10:11",
    "last_attempt_at": "2026-04-08T09:10:11",
    "printed_at": null,
    "resolution_note": null
  },
  "attempts": [
    {
      "id": 9001,
      "attempt_number": 1,
      "trigger_type": "automatic",
      "triggered_by_user_id": 8,
      "started_at": "2026-04-08T09:10:11",
      "finished_at": "2026-04-08T09:10:12",
      "duration_ms": 415,
      "success": false,
      "error_category": "network",
      "error_message": "No se pudo conectar a la impresora"
    }
  ]
}
```

Errores:
1. `404 PRINT_JOB_NOT_FOUND`

## 5.3 POST /impresion-fallida/jobs/{job_id}/reintentar

Descripcion:
Reintento manual de impresion por id.

Request body:
```json
{
  "copias_override": null,
  "force": false
}
```

Reglas:
1. Si `estado` es `printed` o `discarded` y `force=false` => 409.
2. Si `attempts >= max_attempts` y `force=false` => 409.
3. Usa lock logico: pasar a `retrying` al iniciar.
4. Registra fila en `print_job_attempts` siempre.

Response 200 (exito):
```json
{
  "job_id": 101,
  "status": "printed",
  "attempt_number": 2,
  "printed": true,
  "message": "Ticket impreso correctamente",
  "printed_at": "2026-04-08T10:00:01"
}
```

Response 200 (falla de nuevo):
```json
{
  "job_id": 101,
  "status": "pending",
  "attempt_number": 2,
  "printed": false,
  "message": "No se pudo imprimir en red: timeout",
  "error_category": "timeout"
}
```

Errores:
1. `404 PRINT_JOB_NOT_FOUND`
2. `409 PRINT_JOB_ALREADY_RESOLVED`
3. `409 PRINT_JOB_MAX_ATTEMPTS_REACHED`
4. `423 PRINT_JOB_LOCKED` (si ya esta retrying en otro proceso)

## 5.4 POST /impresion-fallida/jobs/reintentar-lote (opcional)

Request:
```json
{
  "job_ids": [101, 102, 103],
  "force": false
}
```

Response 200:
```json
{
  "results": [
    {"job_id": 101, "printed": true, "status": "printed"},
    {"job_id": 102, "printed": false, "status": "pending", "message": "timeout"},
    {"job_id": 103, "printed": false, "status": "discarded", "message": "max attempts"}
  ],
  "summary": {
    "total": 3,
    "printed": 1,
    "failed": 2
  }
}
```

## 5.5 POST /impresion-fallida/jobs/{job_id}/descartar (opcional)

Request:
```json
{
  "reason": "Ticket ya no aplica por ajuste manual"
}
```

Response 200:
```json
{
  "job_id": 101,
  "status": "discarded",
  "discarded": true,
  "discarded_at": "2026-04-08T10:30:00"
}
```

Errores:
1. `404 PRINT_JOB_NOT_FOUND`
2. `409 PRINT_JOB_ALREADY_RESOLVED`

---

## 6. Flujos de Negocio

## 6.1 Flujo A: Falla en impresion original

1. Se construye ticket ESC/POS.
2. Se intenta imprimir por red.
3. Si falla:
   1. Se clasifica error (`network|timeout|config|unknown`).
   2. Se crea `print_jobs` en `pending`.
   3. Se crea `print_job_attempts` intento #1 con `trigger_type=automatic`.
4. Se responde al frontend con `ticket_impreso=false` y mensaje.

## 6.2 Flujo B: Reintento manual

1. Frontend lista jobs `pending`.
2. Usuario selecciona job y dispara reintento.
3. Backend valida estado/limites/lock.
4. Backend intenta imprimir con `ticket_payload`.
5. Si exito:
   1. `estado=printed`
   2. `printed_at` y `resolved_by_user_id`
   3. intento `success=true`
6. Si falla:
   1. `estado=pending`
   2. `attempts += 1`
   3. actualiza `error_category/error_message`
   4. intento `success=false`

## 6.3 Flujo C: Cierre manual

1. Usuario descarta job.
2. `estado=discarded`, `resolved_by_user_id`, `resolution_note`.
3. Job no vuelve a salir en pendientes.

---

## 7. Integracion por Capa

Puntos de integracion actuales (cuando `impreso_ok == False`):
1. Entrada de vehiculo.
2. Salida efectivo (original + copia).
3. Salida tarjeta al confirmar webhook.
4. Ticket de corte de caja.

Capa sugerida nueva:
1. `core/print_job_service.py`
   - `register_failed_print_job(...)`
   - `retry_print_job(...)`
   - `discard_print_job(...)`
   - `list_print_jobs(...)`
   - `get_print_job_detail(...)`
2. `routes/impresion_fallida.py`
3. `models/print_job.py`
4. `models/print_job_attempt.py`
5. `schemas/impresion_fallida.py`

---

## 8. Contrato de Clasificacion de Errores

Mapa de clasificacion (si llega exception o mensaje de error):
1. contiene `timeout` -> `timeout`
2. contiene `connection`, `no route`, `network`, `socket` -> `network`
3. contiene `config`, `invalid`, `valueerror`, `typeerror` -> `config`
4. otro caso -> `unknown`

Mensajes canonicos sugeridos:
1. `No se pudo conectar a la impresora`
2. `Timeout al imprimir ticket`
3. `Configuracion invalida de impresion`
4. `Error no clasificado de impresion`

---

## 9. Reglas de Auditoria y Retencion

1. No hard-delete al imprimir bien.
2. Conservar `printed/discarded` por al menos 90 dias.
3. Limpieza programada (job diario) de historicos antiguos.
4. Toda accion manual debe guardar `user_id`.
5. Toda mutacion de estado debe tener timestamp.

---

## 10. Observabilidad

Metricas minimas:
1. `print_jobs_created_total{source_type,error_category}`
2. `print_jobs_retried_total{result}`
3. `print_jobs_pending_current`
4. `print_job_attempt_duration_ms`

Logs estructurados:
1. `event=print_job_created job_id=... source_type=...`
2. `event=print_job_retry job_id=... attempt=... result=...`
3. `event=print_job_resolved job_id=... status=printed|discarded`

---

## 11. Criterios de Aceptacion

1. Falla de impresion crea job + intento automatico.
2. Endpoint listado devuelve pendientes con filtros.
3. Reintento manual registra intento y cambia estado correcto.
4. Cierre manual deja auditoria.
5. No hay doble reintento concurrente del mismo job.
6. Historial de intentos visible desde endpoint de detalle.

---

## 12. Plan de Implementacion (orden sugerido)

1. Crear tablas y modelos (`print_jobs`, `print_job_attempts`).
2. Crear schemas de request/response.
3. Crear servicio `print_job_service`.
4. Integrar captura de fallo en 4 flujos de impresion.
5. Crear router `/impresion-fallida` protegido.
6. Pruebas unitarias de estados y reintentos.
7. Pruebas manuales end-to-end con impresora desconectada.
8. Activar limpieza de retencion.

---

## 13. Compatibilidad y Decisiones

1. El endpoint de reintento usa el payload binario persistido, no regenera ticket.
2. El modulo es independiente de facturacion y de reimpresion historica normal.
3. El estado `printed` significa "enviado a impresora sin error de transporte".
4. Si en el futuro se requiere confirmacion fisica, se necesitara hardware/protocolo adicional.
