from __future__ import annotations

from models.tarifa import Tarifa


MINUTOS_DIA = 1440
MINUTOS_MEDIO_DIA = 720
MINUTOS_HORA = 60
MINUTOS_FRACCION = 30


def calcular_minutos_estadia(fecha_entrada, hora_entrada, referencia_dt) -> int:
    """Calcula los minutos de estancia usando la misma regla para todo el sistema."""
    from datetime import datetime as dt

    entrada = dt.combine(fecha_entrada, hora_entrada)
    tiempo_total = referencia_dt - entrada
    total_segundos = tiempo_total.total_seconds()

    if total_segundos < 0:
        raise ValueError("Tiempo invalido")

    return max(1, int(total_segundos / 60))


def calcular_importe_por_minutos(total_minutos: int, tarifa: Tarifa) -> float:
    """Calcula el importe con la misma tabla de tarifas que usa la operacion diaria."""
    importe = 0
    minutos_restantes = total_minutos

    dias = minutos_restantes // MINUTOS_DIA
    if dias > 0:
        importe += dias * tarifa.diario
        minutos_restantes = minutos_restantes % MINUTOS_DIA

    medios_dias = minutos_restantes // MINUTOS_MEDIO_DIA
    if medios_dias > 0:
        importe += medios_dias * tarifa.medio_dia
        minutos_restantes = minutos_restantes % MINUTOS_MEDIO_DIA

    if minutos_restantes > 0:
        if minutos_restantes <= MINUTOS_HORA:
            importe += tarifa.hora
            minutos_restantes = 0
        else:
            importe += tarifa.hora
            minutos_restantes -= MINUTOS_HORA

            horas_completas = minutos_restantes // MINUTOS_HORA
            importe += horas_completas * tarifa.hora
            minutos_restantes = minutos_restantes % MINUTOS_HORA

            if minutos_restantes == 0:
                pass
            elif minutos_restantes <= MINUTOS_FRACCION:
                importe += tarifa.fraccion
            else:
                importe += tarifa.hora

    return importe