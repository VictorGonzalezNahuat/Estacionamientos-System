# Blueprint Tecnico: Pluma Terminal con Turno Activo y Ticket Binario
**Proyecto:** Estacionamientos Backend
**Fecha:** 2026-04-09
**Version:** 1.0
**Estado:** Diseno sin implementacion

---

## 1. Objetivo

Habilitar un flujo de entrada automatica para una pluma/terminal fisica que:

1. Espere eventos de `Enter` en un programa de terminal.
2. Solicite al backend la creacion de entrada de vehiculo.
3. Reciba el ticket en binario ESC/POS (sin imprimir desde backend).
4. Imprima localmente desde USB en el programa externo.
5. Se sincronice con el estado de turnos del sistema para activar, desactivar o bloquear la pluma.

Este blueprint separa explicitamente:

1. Implementacion en backend actual.
2. Implementacion del programita en otro proyecto.

---

## 2. Decisiones Cerradas de Operacion

1. Si hay 2 o mas turnos activos, la pluma se bloquea y se imprime aviso.
2. Polling de estado de turnos: cada 3 segundos.
3. Al reiniciar el programita, se reimprime aviso de estado actual para confirmar recuperacion operativa.

---

## 3. Alcance

Incluye:

1. Endpoint tecnico para estado operativo de pluma.
2. Endpoint tecnico para crear entrada automatica y devolver ticket binario.
3. Regla de placa automatica `SYS-{id_consecutivo}`.
4. Bloqueo por ambiguedad de turnos.
5. Contrato de integracion backend-programita.

No incluye:

1. Implementacion fisica de impresion USB en backend.
2. WebSocket en primera fase (solo polling).
3. Pantalla UI nueva en frontend para esta funcionalidad.

---

## 4. Maquina de Estados Operativa de Pluma

El backend define el estado operativo en tiempo real.

Estados:

1. `active`:
   1. Existe exactamente un turno `activo`.
   2. La pluma puede registrar entradas automaticas.
2. `inactive`:
   1. No existe turno `activo`.
   2. La pluma no debe registrar entradas.
3. `ambiguous`:
   1. Existen 2 o mas turnos `activos`.
   2. La pluma se bloquea por seguridad operativa.

Reglas:

1. Solo `active` permite crear entradas automaticas.
2. `inactive` y `ambiguous` retornan error de negocio al intentar entrada.

---

## 5. Arquitectura General

## 5.1 Backend (este repositorio)

Responsabilidades:

1. Resolver estado operativo de pluma en base a turnos activos.
2. Crear entrada automatica en `current_estacionamiento` con placa `SYS-{consecutivo}`.
3. Asignar entrada al turno/encargado del turno activo detectado.
4. Devolver ticket ESC/POS binario en HTTP para impresion local externa.
5. Asegurar autenticacion tecnica (API key), sin JWT de usuario para este flujo.

## 5.2 Programita Terminal (otro proyecto)

Responsabilidades:

1. Polling de estado cada 3 segundos.
2. Detectar `Enter` continuamente.
3. Llamar endpoint de entrada automatica cuando estado sea `active`.
4. Imprimir binario recibido en impresora USB local.
5. Imprimir ticket de aviso en cambios de estado y al arrancar.
6. Reportar en consola estatus de impresion y errores.

---

## 6. Blueprint Backend (Implementacion en este proyecto)

## 6.1 Nuevos Endpoints Tecnicos

Base path sugerido: `/terminal/pluma`

Seguridad tecnica comun:

1. Header requerido: `X-Terminal-Api-Key`.
2. Validacion contra variable de entorno (por ejemplo `TERMINAL_API_KEY`).
3. Rechazo con `401` en caso de clave invalida o ausente.

### 6.1.1 GET `/terminal/pluma/status`

Descripcion:

1. Devuelve estado operativo actual (`active`, `inactive`, `ambiguous`).
2. Incluye metadatos para ticket de aviso y para UI consola del programita.

Response 200 ejemplo:

```json
{
  "mode": "active",
  "status_version": "turno:152|updated_at:2026-04-09T09:22:10",
  "turno": {
    "id": 152,
    "encargado_id": 7,
    "encargado_nombre": "Juan Perez",
    "estado": "activo"
  },
  "message": "Se ha configurado el turno 152 del encargado Juan Perez. Pluma lista para recibir carros"
}
```

Notas:

1. `status_version` debe cambiar cuando cambie el estado para facilitar deteccion de cambios.
2. Si `inactive` o `ambiguous`, `turno` puede ser `null` o arreglo de turnos segun diseno final.

### 6.1.2 POST `/terminal/pluma/entry-ticket`

Descripcion:

1. Crea entrada automatica de vehiculo.
2. Determina placa automaticamente con patron `SYS-{id_consecutivo}`.
3. Asigna entrada al unico turno activo.
4. Retorna ticket binario ESC/POS.
5. No imprime en backend.

Response exito:

1. HTTP `201`.
2. Body binario (`application/octet-stream`).
3. Headers sugeridos:
   1. `X-Action-Status: created`
   2. `X-Entry-Plate: SYS-000123`
   3. `X-Entry-Id: 9876`
   4. `X-Turno-Id: 152`
   5. `Content-Disposition: attachment; filename=ticket_SYS-000123.bin`

Errores de negocio:

1. `409` sin espacios disponibles.
2. `423` modo `inactive` o `ambiguous`.
3. `500` error interno de generacion.

---

## 6.2 Regla de Placa `SYS-{id_consecutivo}`

Objetivo:

1. Evitar conflictos con placas manuales.
2. Mantener trazabilidad y alta velocidad de captura.

Recomendacion tecnica:

1. Crear mecanismo atomico de consecutivo (tabla de secuencia o secuencia nativa SQL).
2. Formato sugerido: `SYS-{numero_con_padding}` (ejemplo `SYS-000123`).
3. Validar unicidad en DB con indice unico por `placa` en `current_estacionamiento`.
4. Si hay colision por concurrencia, reintentar en la misma operacion.

Decisiones a fijar en implementacion:

1. Longitud de padding (6 recomendado).
2. Consecutivo global monotono (recomendado).

---

## 6.3 Asignacion de Turno y Encargado

Regla funcional:

1. Si hay exactamente 1 turno activo, ese turno se usa para `turno_id` y su `encargado_id`.
2. Si hay 0 turnos activos, no se permite entrada automatica.
3. Si hay 2 o mas turnos activos, se bloquea la pluma y no se permite entrada automatica.

Ventaja:

1. No se requiere usuario tecnico adicional.
2. El corte de caja y trazabilidad permanecen alineados con operacion real.

---

## 6.4 Impresion y Ticket Binario

Regla:

1. Backend genera bytes ESC/POS.
2. Backend devuelve bytes en respuesta HTTP.
3. Backend no invoca impresora de red para este flujo.

Opcional backend:

1. Guardar copia de auditoria en `printer/tickets` para soporte tecnico.

---

## 6.5 Cambios de Codigo (Mapa de Impacto)

Archivos objetivo sugeridos:

1. `routes/current_estacionamientos.py` (si se integra aqui) o nuevo `routes/terminal_pluma.py`.
2. `core/parking_ticket_service.py` (reuso de construccion de ticket).
3. Nuevo servicio en `core/` para resolver estado de pluma y entrada automatica.
4. `main.py` para registrar nuevo router.
5. Nueva migracion SQL para secuencia/indice unico, segun motor usado.

Nota de orden:

1. Es preferible crear router separado para mantener desacoplado el flujo tecnico de terminal.

---

## 6.6 Observabilidad y Auditoria

Minimo recomendado:

1. Log de cada consulta de status (muestreo opcional para no saturar).
2. Log de cada entrada automatica exitosa/fallida.
3. Campos clave en log: timestamp, ip, turno_id, encargado_id, placa_sys, resultado.

---

## 6.7 Pruebas Backend

Casos minimos:

1. `status` con 0 turnos activos -> `inactive`.
2. `status` con 1 turno activo -> `active`.
3. `status` con 2 turnos activos -> `ambiguous`.
4. `entry-ticket` en `active` -> 201 + binario + headers esperados.
5. `entry-ticket` en `inactive` -> 423.
6. `entry-ticket` en `ambiguous` -> 423.
7. `entry-ticket` sin cupo -> 409.
8. concurrencia en 20+ solicitudes -> placas SYS unicas.

---

## 7. Blueprint Programita Terminal (Proyecto Externo)

## 7.1 Objetivo del Programita

Crear un daemon/CLI ligero que opere la pluma local:

1. Detectar `Enter`.
2. Consultar estado de backend cada 3 segundos.
3. En estado `active`, registrar entrada y mandar ticket a impresora USB.
4. En cambios de estado, imprimir ticket de aviso.
5. En arranque, imprimir aviso del estado actual (siempre).

---

## 7.2 Flujo Operativo del Programita

Ciclo principal:

1. Arranque:
   1. Cargar config (URL backend, API key, impresora, timeout).
   2. Consultar `GET /terminal/pluma/status`.
   3. Imprimir ticket de aviso del estado actual (siempre en inicio).
2. Runtime:
   1. Polling cada 3 segundos.
   2. Si cambia `status_version`, imprimir nuevo ticket de aviso.
   3. Escuchar `Enter` en paralelo.
3. Evento `Enter`:
   1. Si estado actual no es `active`, no llamar entry-ticket; mostrar bloqueo y opcional aviso breve.
   2. Si estado `active`, llamar `POST /terminal/pluma/entry-ticket`.
   3. Si 201, imprimir bytes recibidos por USB.
   4. Mostrar resultado en consola (placa SYS, turno, impresion ok/error).

---

## 7.3 Mensajes de Aviso (Texto Referencia)

Activacion (`active`):

1. `Se ha configurado el turno {turno_id} del encargado {encargado}. Pluma lista para recibir carros.`

Sin turno (`inactive`):

1. `Es todo por ahora, no hay turnos abiertos. Pluma desactivada.`

Ambiguedad (`ambiguous`):

1. `Atencion: hay multiples turnos abiertos. Pluma bloqueada hasta corregir la configuracion.`

---

## 7.4 Manejo de Errores en Programita

1. Error de red backend: reintento con backoff corto y aviso en consola.
2. `401`: API key invalida, marcar estado critico.
3. `423`: pluma no habilitada por backend.
4. Falla de impresion USB:
   1. log de error,
   2. mantener bytes en carpeta local de reintento opcional,
   3. continuar operativo.

---

## 7.5 Estructura Sugerida del Proyecto Externo

1. `main.py` (orquestacion y ciclo de eventos).
2. `backend_client.py` (HTTP a status y entry-ticket).
3. `printer_usb.py` (adaptador de impresion local).
4. `status_notifier.py` (generacion de ticket de avisos).
5. `config.py` (`.env` + validaciones).
6. `logging_setup.py`.

---

## 8. Seguridad Tecnica Recomendada

1. API key dedicada para terminal.
2. Rotacion de API key planificada.
3. Restriccion de red por IP cuando sea posible.
4. No exponer endpoint tecnico a internet publica sin gateway.

---

## 9. Plan de Implementacion por Fases

Fase 1 (Backend base):

1. Endpoint `status`.
2. Endpoint `entry-ticket` con binario.
3. API key tecnica.
4. Secuencia SYS atomica.

Fase 2 (Programita MVP):

1. Polling cada 3 segundos.
2. Escucha de `Enter`.
3. Impresion USB de ticket de entrada.
4. Avisos de estado y reinicio.

Fase 3 (Hardening):

1. Logs estructurados y metricas.
2. Reintentos/cola local de impresion fallida.
3. Pruebas de estres y recuperacion.

---

## 10. Criterios de Aceptacion

1. Con 1 turno activo, `Enter` registra entrada y emite ticket impreso localmente.
2. Con 0 turnos activos, pluma no registra entradas e imprime aviso de desactivacion.
3. Con 2+ turnos activos, pluma no registra entradas e imprime aviso de bloqueo.
4. Reinicio del programita imprime aviso de estado actual siempre.
5. No hay impresion de entrada desde backend para este flujo.
6. Placas SYS no se duplican bajo concurrencia.

---

## 11. Riesgos y Mitigaciones

1. Riesgo: turnos duplicados por error humano.
   1. Mitigacion: estado `ambiguous` bloqueante + aviso inmediato.
2. Riesgo: colision de placas SYS bajo concurrencia.
   1. Mitigacion: secuencia atomica + indice unico + retry.
3. Riesgo: backend caido y pluma sin feedback.
   1. Mitigacion: aviso en consola y ticket de error operativo opcional.

---

## 12. Pendientes para Arranque de Implementacion

1. Confirmar nombre final de rutas (`/terminal/pluma/...`).
2. Confirmar esquema de `status_version` (hash o version incremental).
3. Confirmar padding final de placa SYS.
4. Confirmar tecnologia exacta del programita externo (Python recomendado).

Con estos pendientes cerrados, se puede iniciar implementacion inmediatamente.
