# Blueprint Tecnico: Reimpresion de Tickets de Entrada y Salida
**Proyecto:** Estacionamientos Backend  
**Fecha:** 2026-04-10  
**Version:** 1.0  
**Estado:** Diseno sin implementacion

---

## 1. Objetivo

Agregar capacidad de reimpresion manual de tickets ya existentes, sin modificar el estado operativo del estacionamiento ni generar efectos secundarios en BD.

La funcionalidad propuesta debe permitir:
1. Reimprimir ticket de entrada a partir de un registro de `current_estacionamiento`.
2. Reimprimir ticket de salida a partir de un registro de `history_estacionamiento`.
3. Consultar los ultimos 50 registros de cada tabla para que el frontend los muestre como candidatos a reimpresion.
4. Proteger todos los endpoints con `current_user`.

Principio clave:
- La reimpresion solo reconstruye e imprime el ticket.
- No debe actualizar estados, no debe escribir auditoria por ahora y no debe afectar el flujo normal de entrada/salida.

---

## 2. Alcance Funcional

Incluye:
1. Consulta de ultimos 50 tickets de entrada disponibles en `current_estacionamiento`.
2. Consulta de ultimos 50 tickets de salida disponibles en `history_estacionamiento`.
3. Reimpresion de ticket de entrada por `id`.
4. Reimpresion de ticket de salida por `id`.
5. Validaciones basicas de existencia del registro.
6. Reutilizacion de la logica de construccion e impresion ya existente.

No incluye:
1. Auditoria de quien reimprimio.
2. Trazabilidad de intentos de reimpresion.
3. Persistencia de eventos de reimpresion.
4. Modificacion del vehiculo, turno, corte o historial.
5. Reimpresion masiva en lote.

---

## 3. Diagnostico del Sistema Actual

Hallazgos relevantes:
1. El ticket de entrada ya se construye e imprime en `routes/current_estacionamientos.py` mediante `construir_ticket_entrada`, `guardar_ticket_bytes` e `imprimir_ticket_entrada`.
2. El ticket de salida ya se construye desde historial en `core/parking_exit_service.py` usando `_construir_ticket_salida_historial` e `imprimir_lote_tickets_salida`.
3. Ambos flujos ya usan modelos persistidos, por lo que la reimpresion puede reconstruirse desde datos almacenados.
4. Los routers ya usan `get_current_user`, asi que la proteccion por autenticacion ya esta alineada con el objetivo.

Riesgos a considerar:
1. No usar el usuario actual para rellenar datos del ticket reimpreso si eso altera la fidelidad historica.
2. No llamar logica de negocio de entrada/salida que modifique espacios, turnos o historial.
3. No reutilizar el flujo de ingreso o salida completa; solo la parte de construccion e impresion.
4. Evitar depender de informacion calculada en tiempo real cuando el ticket original debe preservar sus datos historicos.

---

## 4. Contrato API Propuesto

Base paths sugeridos segun la estructura actual:
- Entradas: `/estacionamiento`
- Historial de salidas: `/history`

### 4.1 GET /estacionamiento/reimpresion/ultimos

Descripcion:
Devuelve los ultimos 50 registros de `current_estacionamiento` ordenados del mas reciente al mas antiguo.

Seguridad:
- Requiere `current_user`.

Reglas:
1. Limite fijo inicial: 50 registros.
2. Orden descendente por `updated_at` o por `id` si no hay mejor criterio disponible.
3. No debe calcular estados ni modificar campos.

Respuesta sugerida:
```json
{
  "data": [
    {
      "id": 123,
      "placa": "ABC123A",
      "tarifa_id": 1,
      "turno_id": 5,
      "encargado_id": 7,
      "fecha_entrada": "2026-04-10",
      "hora_entrada": "08:10:00",
      "updated_at": "2026-04-10T08:10:05"
    }
  ]
}
```

### 4.2 GET /history/reimpresion/ultimos

Descripcion:
Devuelve los ultimos 50 registros de `history_estacionamiento` ordenados del mas reciente al mas antiguo.

Seguridad:
- Requiere `current_user`.

Reglas:
1. Limite fijo inicial: 50 registros.
2. Orden descendente por `updated_at` o por `id` si no hay mejor criterio disponible.
3. No filtrar por corte en esta fase, salvo que el negocio lo exija despues.

Respuesta sugerida:
```json
{
  "data": [
    {
      "id": 987,
      "placa": "ABC123A",
      "tarifa_id": 1,
      "turno_id": 5,
      "encargado_id": 7,
      "fecha_entrada": "2026-04-10",
      "hora_entrada": "08:10:00",
      "fecha_salida": "2026-04-10",
      "hora_salida": "10:42:00",
      "importe": 45.0,
      "metodo_pago": "efectivo",
      "pagado": true,
      "updated_at": "2026-04-10T10:42:10"
    }
  ]
}
```

### 4.3 POST /estacionamiento/reimpresion/{id}

Descripcion:
Reimprime el ticket de entrada correspondiente al registro de `current_estacionamiento`.

Seguridad:
- Requiere `current_user`.

Reglas:
1. Buscar el registro por `id`.
2. Si no existe, responder `404`.
3. Reconstituir el ticket con los datos persistidos del registro.
4. Imprimir el ticket sin guardar cambios en BD.
5. No tocar espacios ocupados/disponibles, turnos o historial.

Respuesta sugerida:
```json
{
  "mensaje": "Ticket de entrada reimpreso correctamente",
  "ticket_impreso": true,
  "impresion_mensaje": "Ticket enviado a impresora (1 copia(s))"
}
```

### 4.4 POST /history/reimpresion/{id}

Descripcion:
Reimprime el ticket de salida correspondiente al registro de `history_estacionamiento`.

Seguridad:
- Requiere `current_user`.

Reglas:
1. Buscar el registro por `id`.
2. Si no existe, responder `404`.
3. Reconstituir el ticket con los datos persistidos del historial.
4. Imprimir el ticket sin guardar cambios en BD.
5. Mantener el formato de salida ya utilizado por el flujo normal.

Respuesta sugerida:
```json
{
  "mensaje": "Ticket de salida reimpreso correctamente",
  "ticket_impreso": true,
  "impresion_mensaje": "Tickets enviados a impresora (2 ticket(s))"
}
```

---

## 5. Reglas de Negocio

1. La reimpresion debe ser solo operativa.
2. El contenido del ticket debe salir de la informacion historica persistida.
3. El flujo no debe generar un nuevo ticket de entrada ni un nuevo historial de salida.
4. La accion de reimprimir no debe alterar `updated_at` de los registros por via de negocio.
5. Si la impresora falla, se retorna el error de impresion sin reintentos automaticos en esta fase.

---

## 6. Refactorizacion Necesaria Antes de Exponer Endpoints

Para evitar duplicacion de logica, conviene preparar funciones compartidas antes o durante la implementacion:

### 6.1 Para entrada
Crear una funcion de construccion desde modelo persistido, por ejemplo:
- recibe `CurrentEstacionamiento`
- resuelve `Tarifa` asociada
- construye bytes con `construir_ticket_entrada`
- imprime con `imprimir_ticket_entrada`

### 6.2 Para salida
Crear una funcion de reimpresion desde historial, por ejemplo:
- recibe `HistoryEstacionamiento`
- resuelve el nombre de cajero con la logica ya existente o con un fallback estable
- construye original/copia con `_construir_ticket_salida_historial`
- imprime con `imprimir_lote_tickets_salida`

### 6.3 Criterio de fidelidad historica
Definir si el ticket reimpreso debe mostrar:
1. Solo datos originales del registro.
2. O datos originales mas una leyenda de reimpresion.

Recomendacion:
- Mantener el ticket visualmente identico al original por ahora, salvo una marca explicita si el negocio la pide despues.

---

## 7. Ubicacion de Implementacion

### Opcion recomendada
1. `routes/current_estacionamientos.py`
   - Endpoint de ultimos 50 registros de entrada.
   - Endpoint de reimpresion de ticket de entrada.

2. `routes/history_estacionamientos.py`
   - Endpoint de ultimos 50 registros de salida.
   - Endpoint de reimpresion de ticket de salida.

### Apoyo tecnico
1. `core/parking_ticket_service.py`
   - Reutilizar funciones de construccion e impresion.

2. `core/parking_exit_service.py`
   - Reutilizar la construccion de ticket de salida ya existente.

3. `models/current_estacionamiento.py`
   - Fuente de datos para reimpresion de entrada.

4. `models/history_estacionamiento.py`
   - Fuente de datos para reimpresion de salida.

---

## 8. Estrategia de Implementacion por Fases

### Fase 1: Definicion del contrato
1. Confirmar nombres finales de endpoints.
2. Confirmar si la ruta de reimpresion vive en los mismos routers o en un subrouter dedicado.
3. Alinear formato de respuesta para frontend.
4. Alinear criterio de orden para los ultimos 50 registros.

### Fase 2: Extraccion de helpers
1. Extraer helpers de construccion de ticket desde entrada.
2. Reutilizar helper de salida desde historial.
3. Centralizar manejo de errores de impresora.
4. Asegurar que la reimpresion no toque BD.

### Fase 3: Implementacion de lectura
1. Endpoint de ultimos 50 registros de `current_estacionamiento`.
2. Endpoint de ultimos 50 registros de `history_estacionamiento`.
3. Manejo consistente de vacios: devolver arreglo vacio cuando no haya datos.

### Fase 4: Implementacion de reimpresion
1. Buscar registro por `id`.
2. Validar existencia.
3. Reconstruir bytes del ticket.
4. Enviar a impresora.
5. Retornar resultado de impresion sin side effects.

### Fase 5: Validacion tecnica
1. Verificar que los endpoints requieren autenticacion.
2. Verificar que la impresora recibe entrada y salida correctamente.
3. Verificar que la salida imprime ORIGINAL y COPIA si el formato actual lo mantiene.
4. Verificar que no se generan commits a BD en el flujo de reimpresion.

---

## 9. Casos de Error Esperados

1. `404 Not Found` si el `id` no existe.
2. `401 Unauthorized` si no hay `current_user` valido.
3. `500 Internal Server Error` si faltan datos para construir el ticket.
4. Error de impresion si la impresora de red no responde o no esta disponible.
5. `409 Conflict` no deberia aplicar aqui, porque la reimpresion no compite con estados de negocio.

Formato sugerido de errores:
```json
{
  "detail": "No se encontro el ticket solicitado"
}
```

---

## 10. Criterios de Aceptacion

1. Se pueden listar los ultimos 50 registros de entrada y salida.
2. Se puede reimprimir un ticket de entrada por `id`.
3. Se puede reimprimir un ticket de salida por `id`.
4. Los endpoints estan protegidos por `current_user`.
5. La reimpresion no modifica registros ni estados del sistema.
6. La logica reutiliza helpers existentes para evitar duplicacion.
7. Los tickets generados conservan el formato de impresion esperado.

---

## 11. Riesgos y Recomendaciones

Riesgos:
1. Reimpresiones con datos no exactos si se usa informacion calculada dinamicamente en lugar de la persistida.
2. Duplicacion de logica si no se extraen helpers compartidos.
3. Confusion operacional si la reimpresion no distingue ticket original de ticket reimpreso.

Recomendaciones:
1. Reusar siempre datos persistidos del modelo.
2. No invocar el flujo de ingreso/salida completo.
3. Agregar auditoria en una segunda fase para registrar quien reimprimio, cuando y por que.
4. Si el negocio lo pide despues, agregar una marca visual de reimpresion sin cambiar la logica de negocio.

---

## 12. Roadmap Sugerido

Fase 0: Confirmacion de contrato y nombres de endpoints.  
Fase 1: Extraccion de helpers de construccion e impresion.  
Fase 2: Endpoints de listado de ultimos 50 registros.  
Fase 3: Endpoints de reimpresion por `id`.  
Fase 4: Pruebas manuales con impresora de red y validacion de no-impacto.  
Fase 5: Agregar auditoria y trazabilidad.
