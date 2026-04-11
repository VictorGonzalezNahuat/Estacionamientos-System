# Programita terminal pluma (simulacion de impresion)

Este cliente de terminal:

1. Consulta `GET /terminal/pluma/status` cada 3 segundos.
2. Imprime un aviso de estado al iniciar y en cada cambio de `status_version`.
3. Espera `Enter` en consola.
4. Si `mode=active`, llama `POST /terminal/pluma/entry-ticket`.
5. En Windows, envia los bytes recibidos a la impresora predeterminada (RAW por spooler).
6. En otros sistemas (o si falla impresora), guarda en `printed/` como fallback.

## Archivo principal

- `programita_terminal.py`

## Configuracion (.env)

Variables soportadas:

- `TERMINAL_API_KEY`
- `BACKEND_BASE_URL` (default: `http://127.0.0.1:8000`)
- `POLL_INTERVAL_SECONDS` (default: `3`)
- `REQUEST_TIMEOUT_SECONDS` (default: `10`)
- `PRINTED_DIR` (default: `printed`)

Notas de rutas (importante para servicio en Windows):

- El programa resuelve `.env`, `assets/` y `PRINTED_DIR` relativo a la carpeta donde esta `Terminal.py`.
- No depende del directorio de trabajo actual (por ejemplo `C:\Windows\System32`).

## Ejecucion

Requiere Python 3.8 o superior.
Para imprimir encabezados PNG en tickets, instalar `Pillow`.

```bash
pip install Pillow
python3 programita_terminal.py
```

## Comportamiento esperado

- Si no hay backend disponible, el programa falla en el arranque mostrando el error.
- Con backend disponible, al presionar Enter:
  - `active`: imprime en la impresora predeterminada de Windows (o guarda fallback en `printed/`).
  - `inactive` o `ambiguous`: bloquea la accion y lo muestra en consola.
