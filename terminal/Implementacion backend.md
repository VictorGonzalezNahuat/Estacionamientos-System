Uso esperado por el programa de terminal
Flujo recomendado del programita externo:

Cada 3 segundos consultar GET /terminal/pluma/status con X-Terminal-Api-Key
Al arrancar, imprimir ticket de aviso con el estado actual (siempre)
Si cambia status_version, imprimir nuevo aviso de estado
Al detectar Enter:
Si mode no es active, no llamar entry-ticket y mostrar bloqueo
Si mode es active, llamar POST /terminal/pluma/entry-ticket
Imprimir por USB los bytes recibidos
Mostrar en consola placa generada (desde X-Entry-Plate) y resultado
