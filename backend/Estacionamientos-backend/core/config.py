import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"


def _load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(BASE_DIR / ".env")


def _load_json_config(config_path: Path) -> dict:
    if not config_path.exists():
        return {}

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"config.json invalido: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError("config.json debe contener un objeto JSON")

    return raw


def _save_json_config(config_path: Path, data: dict) -> None:
    config_path.write_text(
        json.dumps(data, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _sanitize_entry_ticket_code_type(value: Any) -> str:
    mode = str(value).strip().upper()
    return mode if mode in {"BARCODE", "QR"} else "BARCODE"


def _extract_cloud_db_parts(database_url: str) -> dict:
    raw_url = (database_url or "").strip()
    if not raw_url:
        raise ValueError("DATABASE_CLOUD_URL es obligatoria")

    # urlparse maneja mejor el esquema mysql:// para extraer componentes.
    parse_url = raw_url.replace("mysql+pymysql://", "mysql://", 1)
    parsed = urlparse(parse_url)

    user = unquote(parsed.username or "").strip()
    password = unquote(parsed.password or "")
    host = (parsed.hostname or "").strip()
    port = int(parsed.port or 3306)
    database = parsed.path.lstrip("/").strip()

    if not user or not host or not database:
        raise ValueError("DATABASE_CLOUD_URL no tiene el formato esperado")

    return {
        "DATABASE_CLOUD_USER": user,
        "DATABASE_CLOUD_PASSWORD": password,
        "DATABASE_CLOUD_HOST": host,
        "DATABASE_CLOUD_PORT": port,
        "DATABASE_CLOUD_NAME": database,
    }


def _build_cloud_db_url(
    user: str,
    password: str,
    host: str,
    port: int,
    database: str,
) -> str:
    user_q = quote(user, safe="")
    password_q = quote(password, safe="")
    db_q = quote(database, safe="")
    return f"mysql://{user_q}:{password_q}@{host}:{port}/{db_q}"


def _normalize_mysql_url(database_url: str) -> str:
    # SQLAlchemy with PyMySQL needs mysql+pymysql:// instead of mysql://
    if database_url.startswith("mysql://"):
        return database_url.replace("mysql://", "mysql+pymysql://", 1)
    return database_url

DATABASE_URL = os.getenv("DATABASE_URL")
APP_CONFIG = _load_json_config(BASE_DIR / "config.json")

DATABASE_CLOUD_URL = str(
    APP_CONFIG.get("DATABASE_CLOUD_URL") or os.getenv("DATABASE_CLOUD_URL", "")
).strip()
SYNC_INTERVAL_MINUTES = int(
    APP_CONFIG.get("SYNC_INTERVAL_MINUTES", os.getenv("SYNC_INTERVAL_MINUTES", "4"))
)
SYNC_AUTO_ENABLED = _to_bool(
    APP_CONFIG.get("SYNC_AUTO_ENABLED", os.getenv("SYNC_AUTO_ENABLED", "true"))
)
MOBILE_PRINT = _to_bool(
    APP_CONFIG.get("MOBILE_PRINT", os.getenv("MOBILE_PRINT", "true"))
)
ENTRY_TICKET_CODE_TYPE = str(
    APP_CONFIG.get("ENTRY_TICKET_CODE_TYPE", os.getenv("ENTRY_TICKET_CODE_TYPE", "BARCODE"))
).strip().upper()
if ENTRY_TICKET_CODE_TYPE not in {"BARCODE", "QR"}:
    ENTRY_TICKET_CODE_TYPE = "BARCODE"

PUBLIC_STATUS_BASE_URL = str(
    APP_CONFIG.get("PUBLIC_STATUS_BASE_URL", os.getenv("PUBLIC_STATUS_BASE_URL", "http://localhost:8100"))
).strip()
if not PUBLIC_STATUS_BASE_URL:
    PUBLIC_STATUS_BASE_URL = "http://localhost:8100"

if not DATABASE_URL:
    raise ValueError("DATABASE_URL no esta configurada en variables de entorno")

if not DATABASE_CLOUD_URL:
    raise ValueError("DATABASE_CLOUD_URL no esta configurada en config.json")

DATABASE_URL = _normalize_mysql_url(DATABASE_URL)
DATABASE_CLOUD_URL = _normalize_mysql_url(DATABASE_CLOUD_URL)


def get_public_config_values() -> dict:
    cloud_parts = _extract_cloud_db_parts(DATABASE_CLOUD_URL)
    return {
        "DATABASE_CLOUD_USER": cloud_parts["DATABASE_CLOUD_USER"],
        "DATABASE_CLOUD_HOST": cloud_parts["DATABASE_CLOUD_HOST"],
        "DATABASE_CLOUD_PORT": cloud_parts["DATABASE_CLOUD_PORT"],
        "DATABASE_CLOUD_NAME": cloud_parts["DATABASE_CLOUD_NAME"],
        "SYNC_AUTO_ENABLED": SYNC_AUTO_ENABLED,
        "SYNC_INTERVAL_MINUTES": SYNC_INTERVAL_MINUTES,
        "MOBILE_PRINT": MOBILE_PRINT,
        "ENTRY_TICKET_CODE_TYPE": ENTRY_TICKET_CODE_TYPE,
        "PUBLIC_STATUS_BASE_URL": PUBLIC_STATUS_BASE_URL,
    }


def update_public_config_values(updates: dict) -> dict:
    global DATABASE_CLOUD_URL, SYNC_AUTO_ENABLED, SYNC_INTERVAL_MINUTES, MOBILE_PRINT, ENTRY_TICKET_CODE_TYPE, PUBLIC_STATUS_BASE_URL, APP_CONFIG

    if not isinstance(updates, dict):
        raise ValueError("Payload de configuracion invalido")

    if "DATABASE_CLOUD_PASSWORD" not in updates:
        raise ValueError("DATABASE_CLOUD_PASSWORD es obligatoria")

    cloud_user = str(updates.get("DATABASE_CLOUD_USER", "")).strip()
    cloud_password = str(updates.get("DATABASE_CLOUD_PASSWORD", ""))
    cloud_host = str(updates.get("DATABASE_CLOUD_HOST", "")).strip()
    cloud_port = int(updates.get("DATABASE_CLOUD_PORT", 3306))
    cloud_name = str(updates.get("DATABASE_CLOUD_NAME", "")).strip()

    if not cloud_password.strip():
        raise ValueError("DATABASE_CLOUD_PASSWORD no puede estar vacia")
    if not cloud_user or not cloud_host or not cloud_name:
        raise ValueError("Los datos de DATABASE_CLOUD son obligatorios")

    cloud_url = _build_cloud_db_url(
        user=cloud_user,
        password=cloud_password,
        host=cloud_host,
        port=cloud_port,
        database=cloud_name,
    )

    interval = int(updates.get("SYNC_INTERVAL_MINUTES", SYNC_INTERVAL_MINUTES))
    if interval < 1:
        raise ValueError("SYNC_INTERVAL_MINUTES debe ser mayor o igual a 1")

    auto_enabled = _to_bool(updates.get("SYNC_AUTO_ENABLED", SYNC_AUTO_ENABLED))
    mobile_print = _to_bool(updates.get("MOBILE_PRINT", MOBILE_PRINT))
    code_type = _sanitize_entry_ticket_code_type(updates.get("ENTRY_TICKET_CODE_TYPE", ENTRY_TICKET_CODE_TYPE))
    status_url = str(updates.get("PUBLIC_STATUS_BASE_URL", PUBLIC_STATUS_BASE_URL)).strip()
    if not status_url:
        raise ValueError("PUBLIC_STATUS_BASE_URL no puede estar vacia")

    normalized_cloud_url = _normalize_mysql_url(cloud_url)

    new_data = {
        "DATABASE_CLOUD_URL": normalized_cloud_url,
        "SYNC_AUTO_ENABLED": auto_enabled,
        "SYNC_INTERVAL_MINUTES": interval,
        "MOBILE_PRINT": mobile_print,
        "ENTRY_TICKET_CODE_TYPE": code_type,
        "PUBLIC_STATUS_BASE_URL": status_url,
    }
    _save_json_config(CONFIG_PATH, new_data)

    APP_CONFIG = new_data
    DATABASE_CLOUD_URL = normalized_cloud_url
    SYNC_AUTO_ENABLED = auto_enabled
    SYNC_INTERVAL_MINUTES = interval
    MOBILE_PRINT = mobile_print
    ENTRY_TICKET_CODE_TYPE = code_type
    PUBLIC_STATUS_BASE_URL = status_url

    return get_public_config_values()
