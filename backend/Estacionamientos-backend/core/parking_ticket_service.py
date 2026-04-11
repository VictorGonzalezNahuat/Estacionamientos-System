from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Sequence

from printer.print import (
    generar_ticket_entrada_prueba,
    generar_ticket_salida_prueba,
    imprimir_ticket,
    imprimir_tickets,
)


def construir_ticket_entrada(
    folio: str,
    placa: str,
    fecha_entrada: datetime,
    tarifa_nombre: str,
    cajero: str,
    leyenda_reimpresion: str | None = None,
) -> bytes:
    return generar_ticket_entrada_prueba(
        folio=folio,
        placa=placa,
        fecha_entrada=fecha_entrada,
        tarifa_nombre=tarifa_nombre,
        cajero=cajero,
        leyenda_reimpresion=leyenda_reimpresion,
    )


def construir_ticket_salida(
    folio: str,
    placa: str,
    fecha_entrada: datetime,
    fecha_salida: datetime,
    minutos_estadia: int,
    total_pagado: float,
    cajero: str,
    metodo_pago: str,
    etiqueta: str | None = None,
    leyenda_reimpresion: str | None = None,
) -> bytes:
    return generar_ticket_salida_prueba(
        folio=folio,
        placa=placa,
        fecha_entrada=fecha_entrada,
        fecha_salida=fecha_salida,
        minutos_estadia=minutos_estadia,
        total_pagado=total_pagado,
        cajero=cajero,
        metodo_pago=metodo_pago,
        etiqueta=etiqueta,
        leyenda_reimpresion=leyenda_reimpresion,
    )


def guardar_ticket_bytes(
    prefix: str,
    placa: str,
    timestamp: datetime,
    ticket_bytes: bytes,
    subdir: str = "tickets",
    suffix: str = "",
) -> Path:
    tickets_dir = Path("printer") / subdir
    tickets_dir.mkdir(parents=True, exist_ok=True)

    nombre_archivo = f"{prefix}_{placa}_{timestamp:%Y%m%d_%H%M%S}{suffix}.bin"
    ticket_path = tickets_dir / nombre_archivo
    ticket_path.write_bytes(ticket_bytes)
    return ticket_path


def imprimir_ticket_entrada(ticket_bytes: bytes) -> tuple[bool, str]:
    return imprimir_ticket(ticket_bytes, tipo_ticket="entrada")


def imprimir_ticket_salida(ticket_bytes: bytes, copias: int = 1) -> tuple[bool, str]:
    return imprimir_ticket(ticket_bytes, copias=copias, tipo_ticket="salida")


def imprimir_lote_tickets_salida(ticket_lote: Sequence[bytes]) -> tuple[bool, str]:
    return imprimir_tickets(ticket_lote, tipo_ticket="salida")