import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


DEFAULT_APP_TIMEZONE = "America/Mexico_City"


def get_app_timezone_name() -> str:
    return os.getenv("APP_TIMEZONE", DEFAULT_APP_TIMEZONE).strip() or DEFAULT_APP_TIMEZONE


def now_local_naive() -> datetime:
    """
    Retorna datetime naive en zona horaria local de la app.

    Se usa naive para mantener compatibilidad con el esquema actual de BD
    (Date y Time sin timezone) y evitar desfases al combinar fecha/hora.
    """
    tz_name = get_app_timezone_name()
    try:
        aware_now = datetime.now(ZoneInfo(tz_name))
    except Exception:
        aware_now = datetime.now(timezone.utc)

    return aware_now.replace(tzinfo=None)
