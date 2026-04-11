import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


DEFAULT_APP_TIMEZONE = "America/Merida"
MERIDA_FALLBACK_OFFSET = timezone(timedelta(hours=-6), name="America/Merida")


def get_app_timezone_name() -> str:
    return os.getenv("APP_TIMEZONE", DEFAULT_APP_TIMEZONE).strip() or DEFAULT_APP_TIMEZONE


def _resolve_app_tzinfo():
    tz_name = get_app_timezone_name()
    try:
        return ZoneInfo(tz_name)
    except Exception:
        # En Windows, ZoneInfo puede fallar si falta tzdata.
        # Para la operacion del negocio, mantenemos Merida fija (-06:00)
        # y evitamos caer a UTC, que desplaza +6 horas la informacion.
        if tz_name in {"America/Merida", "America/Mexico_City"}:
            return MERIDA_FALLBACK_OFFSET
        return MERIDA_FALLBACK_OFFSET


def now_local_naive() -> datetime:
    """
    Retorna datetime naive en zona horaria local de la app.

    Se usa naive para mantener compatibilidad con el esquema actual de BD
    (Date y Time sin timezone) y evitar desfases al combinar fecha/hora.
    """
    aware_now = datetime.now(_resolve_app_tzinfo())

    return aware_now.replace(tzinfo=None)
