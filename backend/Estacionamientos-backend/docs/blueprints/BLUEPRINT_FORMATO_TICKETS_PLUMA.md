# Blueprint de Formato de Tickets para Pluma Terminal
**Proyecto:** Estacionamientos Backend
**Fecha:** 2026-04-10
**Estado:** Documento tecnico de formato

---

## 1. Objetivo

Documentar el formato de impresion que debe reproducir el programita de terminal para que el ticket de entrada quede igual al que hoy genera el backend en `printer/print.py`.

Tambien se incluye un diseño tecnico para el ticket de cambio de turno / aviso de estado de pluma:

1. Pluma activa.
2. Pluma desactivada.
3. Pluma bloqueada por turnos ambiguos.

---

## 2. Fuente de verdad actual en backend

El comportamiento vigente esta implementado en:

1. `printer/print.py`

En particular:

1. `generar_ticket_entrada_prueba(...)` define el contenido ESC/POS del ticket de entrada.
2. `imprimir_ticket_red(...)` imprime primero el encabezado PNG y luego los bytes del ticket.
3. `_obtener_encabezado_ticket("entrada")` selecciona `printer/encabezado_entrada.png`.
4. El programita de terminal debe replicar ese orden si quiere el mismo resultado visual final.

Nota clave:

1. El PNG de encabezado no forma parte de `ticket_bytes`.
2. El encabezado se imprime por separado antes del cuerpo ESC/POS.

---

## 3. Formato exacto del Ticket de Entrada

## 3.1 Orden de impresion actual

Cuando el backend imprime un ticket de entrada en red, hace esto:

1. Centra el encabezado.
2. Imprime `printer/encabezado_entrada.png`.
3. Agrega un salto de linea.
4. Imprime el cuerpo ESC/POS generado por `generar_ticket_entrada_prueba(...)`.

Ese mismo orden es el que debe seguir el programita.

---

## 3.2 Estructura del cuerpo del ticket

El cuerpo actual del ticket de entrada se arma en este orden:

1. Inicializacion ESC/POS.
2. Separador superior.
3. Placa.
4. Entrada.
5. Tarifa.
6. Encargado.
7. Aviso de entrada configurable si existe.
8. Salto de linea.
9. Texto `CODIGO QR` o `CODIGO DE BARRA` segun configuracion.
10. QR o Code39 de la placa.
11. Bloque informativo para consulta de estado si `MOBILE_PRINT` esta activo.
12. Separador inferior.
13. Mensaje de resguardo del ticket.
14. Saltos de linea.
15. Corte de papel.

---

## 3.3 Formato visual linea por linea

La salida actual queda conceptualmente asi:

```text
--------------------------------
Placa        : {placa}
Entrada      : {dd/mm/yyyy} {hh:mm:ss AM/PM}
Tarifa       : {tarifa_nombre}
Encargado       : {cajero}

[aviso de entrada si existe]

CODIGO QR
[QR de la placa]
```

O, si la configuracion no usa QR:

```text
--------------------------------
Placa        : {placa}
Entrada      : {dd/mm/yyyy} {hh:mm:ss AM/PM}
Tarifa       : {tarifa_nombre}
Encargado       : {cajero}

CODIGO DE BARRA
[Code39 de la placa]
```

Luego, si `MOBILE_PRINT` esta habilitado:

```text
Consulta el estado de tu vehiculo
escaneando abajo
[QR con URL publica de estado]
```

Y al final:

```text
--------------------------------
Conserve este ticket
para realizar su salida
--------------------------------


```

---

## 3.4 Reglas exactas de formato detectadas en codigo

1. La fecha se formatea como `dd/mm/yyyy`.
2. La hora se formatea en formato de 12 horas con segundos y sufijo `AM/PM`.
3. El QR o barcode se imprime centrado.
4. El texto `Encargado       :` tiene espaciado manual tal como esta hoy en el codigo.
5. El texto `Conserve este ticket` y `para realizar su salida` va centrado al final.
6. El ticket termina con corte de papel ESC/POS.

---

## 3.5 Elementos controlados por configuracion

### 3.5.1 `ENTRY_TICKET_CODE_TYPE`

Define si el ticket imprime:

1. `QR`
2. `BARCODE`

Si el valor es invalido, el backend usa `BARCODE`.

### 3.5.2 `MOBILE_PRINT`

Si esta activo:

1. Se imprime el texto de consulta de estado.
2. Se imprime un QR adicional con la URL publica del vehiculo.

### 3.5.3 `AVISO_ENTRADA`

Si existe texto configurado:

1. Se agrega dentro del cuerpo del ticket.
2. Se envuelve a ancho aproximado de 42 caracteres.
3. Se respetan saltos de linea logicos.

---

## 4. Formato tecnico recomendado para Ticket de Cambio de Turno / Estado de Pluma

Este ticket sirve para avisar al operador cuando la pluma cambia de estado.

## 4.1 Objetivo visual

Debe ser breve y legible. El programa de terminal lo imprimira cuando:

1. Se detecte un turno activo y la pluma quede habilitada.
2. Se detecte que ya no hay turno abierto y la pluma se desactive.
3. Se detecte ambiguedad por multiples turnos activos y la pluma se bloquee.
4. El programita reinicie y deba reimprimir el estado actual.

---

## 4.2 Encabezado visual recomendado

Para iniciar, no es obligatorio crear PNG nuevo.

Recomendacion:

1. Para `active`, puede reutilizarse `printer/encabezado_entrada.png` o un encabezado neutro existente.
2. Para `inactive`, puede reutilizarse el mismo encabezado neutro.
3. Para `ambiguous`, tambien puede reutilizarse el mismo encabezado neutro.

Si despues quieres una identidad visual propia para avisos, entonces si convendria crear un PNG nuevo.

---

## 4.3 Formato visual recomendado

El ticket de aviso operativo puede seguir esta estructura:

```text
--------------------------------
AVISO OPERATIVO
--------------------------------
Turno        : {turno_id o N/A}
Encargado    : {encargado o N/A}
Estado       : {active|inactive|ambiguous}
Mensaje      : {texto corto de estado}
--------------------------------
```

---

## 4.4 Texto por estado

### Estado `active`

Texto sugerido:

```text
Se ha configurado el turno {turno_id} del encargado {encargado}.
Pluma lista para recibir carros.
```

Formato esperado:

```text
--------------------------------
AVISO OPERATIVO
--------------------------------
Turno        : 152
Encargado    : Juan Perez
Estado       : active
Mensaje      : Pluma lista para recibir carros.
--------------------------------
```

### Estado `inactive`

Texto sugerido:

```text
Es todo por ahora, no hay turnos abiertos.
Pluma desactivada.
```

Formato esperado:

```text
--------------------------------
AVISO OPERATIVO
--------------------------------
Turno        : N/A
Encargado    : N/A
Estado       : inactive
Mensaje      : Es todo por ahora, no hay turnos abiertos.
               Pluma desactivada.
--------------------------------
```

### Estado `ambiguous`

Texto sugerido:

```text
Atencion: hay multiples turnos abiertos.
Pluma bloqueada hasta corregir la configuracion.
```

Formato esperado:

```text
--------------------------------
AVISO OPERATIVO
--------------------------------
Turno        : MULTIPLE
Encargado    : MULTIPLE
Estado       : ambiguous
Mensaje      : Atencion: hay multiples turnos abiertos.
               Pluma bloqueada hasta corregir la configuracion.
--------------------------------
```

---

## 4.5 Comportamiento esperado del programita

El programita debe seguir este flujo:

1. Al iniciar:
   1. Consultar el estado actual del backend.
   2. Imprimir el aviso operativo correspondiente.
2. Durante operacion:
   1. Consultar estado cada 3 segundos.
   2. Si el estado cambia, reimprimir el aviso.
3. Al presionar Enter:
   1. Si el estado no es `active`, bloquear la entrada y mostrar el motivo.
   2. Si el estado es `active`, solicitar el ticket de entrada al backend.
   3. Imprimir el ticket de entrada en la impresora USB local.

---

## 5. PNG requeridos o deseables

Para implementar este flujo no se necesitan PNG nuevos de inmediato.

Ya existen en el backend:

1. `printer/encabezado_entrada.png`
2. `printer/encabezado_salida.png`
3. `printer/encabezado_printer.png`

Para copiar el comportamiento actual del ticket de entrada, el PNG principal es:

1. `printer/encabezado_entrada.png`

Si deseas un encabezado exclusivo para el ticket de aviso operativo, entonces si seria util crear un PNG adicional mas adelante.

---

## 6. Resumen tecnico para el programita

1. El ticket de entrada actual imprime encabezado PNG + cuerpo ESC/POS.
2. El formato de datos debe mantenerse igual para que el ticket visual quede consistente.
3. El aviso operativo de pluma debe ser corto, centrado y con campos clave.
4. Para arrancar, no hace falta un PNG nuevo.
5. Si quieres un branding especifico para el aviso, ahi si conviene generar un encabezado adicional.
