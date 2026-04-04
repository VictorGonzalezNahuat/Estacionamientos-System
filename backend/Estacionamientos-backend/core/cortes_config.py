import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_CORTES_PATH = BASE_DIR / "config" / "config_cortes.json"


DEFAULT_CORTES_CONFIG = {
    "AUTOSEND_REPORT": False,
    "SMTP_HOST": "smtp.gmail.com",
    "SMTP_PORT": 587,
    "SMTP_USERNAME": "",
    "SMTP_PASSWORD": "",
    "SMTP_USE_TLS": True,
    "SMTP_TIMEOUT_SECONDS": 20,
    "REPORT_FROM_NAME": "Sistema de Estacionamiento",
    "REPORT_SUBJECT_TEMPLATE": "Corte de caja #{corte_id} - Turno #{turno_id}",
}


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _save_cortes_config(config_path: Path, data: dict) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(data, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )


def load_cortes_config() -> dict:
    if not CONFIG_CORTES_PATH.exists():
        return dict(DEFAULT_CORTES_CONFIG)

    try:
        raw = json.loads(CONFIG_CORTES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_CORTES_CONFIG)

    if not isinstance(raw, dict):
        return dict(DEFAULT_CORTES_CONFIG)

    config = {**DEFAULT_CORTES_CONFIG, **raw}
    config["AUTOSEND_REPORT"] = _to_bool(config.get("AUTOSEND_REPORT"))
    config["SMTP_USE_TLS"] = _to_bool(config.get("SMTP_USE_TLS"))
    config["SMTP_PORT"] = _to_int(config.get("SMTP_PORT"), DEFAULT_CORTES_CONFIG["SMTP_PORT"])
    config["SMTP_TIMEOUT_SECONDS"] = _to_int(
        config.get("SMTP_TIMEOUT_SECONDS"), DEFAULT_CORTES_CONFIG["SMTP_TIMEOUT_SECONDS"]
    )

    config["SMTP_HOST"] = str(config.get("SMTP_HOST", "")).strip()
    config["SMTP_USERNAME"] = str(config.get("SMTP_USERNAME", "")).strip()
    config["SMTP_PASSWORD"] = str(config.get("SMTP_PASSWORD", "")).strip()
    config["REPORT_FROM_NAME"] = str(config.get("REPORT_FROM_NAME", "")).strip() or DEFAULT_CORTES_CONFIG["REPORT_FROM_NAME"]
    config["REPORT_SUBJECT_TEMPLATE"] = str(config.get("REPORT_SUBJECT_TEMPLATE", "")).strip() or DEFAULT_CORTES_CONFIG["REPORT_SUBJECT_TEMPLATE"]

    return config


def get_cortes_config_values() -> dict:
    return load_cortes_config()


def _to_public_cortes_config(config: dict) -> dict:
    return {
        key: value
        for key, value in config.items()
        if key != "SMTP_PASSWORD"
    }


def get_public_cortes_config_values() -> dict:
    return _to_public_cortes_config(load_cortes_config())


def update_cortes_config_values(updates: dict) -> dict:
    if not isinstance(updates, dict):
        raise ValueError("Payload de configuracion de cortes invalido")

    current = load_cortes_config()
    merged = {**current, **updates}

    merged["AUTOSEND_REPORT"] = _to_bool(merged.get("AUTOSEND_REPORT", DEFAULT_CORTES_CONFIG["AUTOSEND_REPORT"]))
    merged["SMTP_USE_TLS"] = _to_bool(merged.get("SMTP_USE_TLS", DEFAULT_CORTES_CONFIG["SMTP_USE_TLS"]))
    merged["SMTP_PORT"] = _to_int(merged.get("SMTP_PORT"), DEFAULT_CORTES_CONFIG["SMTP_PORT"])
    merged["SMTP_TIMEOUT_SECONDS"] = _to_int(
        merged.get("SMTP_TIMEOUT_SECONDS"), DEFAULT_CORTES_CONFIG["SMTP_TIMEOUT_SECONDS"]
    )

    if merged["SMTP_PORT"] < 1 or merged["SMTP_PORT"] > 65535:
        raise ValueError("SMTP_PORT debe estar entre 1 y 65535")
    if merged["SMTP_TIMEOUT_SECONDS"] < 1:
        raise ValueError("SMTP_TIMEOUT_SECONDS debe ser mayor o igual a 1")

    merged["SMTP_HOST"] = str(merged.get("SMTP_HOST", "")).strip()
    merged["SMTP_USERNAME"] = str(merged.get("SMTP_USERNAME", "")).strip()
    merged["SMTP_PASSWORD"] = str(merged.get("SMTP_PASSWORD", "")).strip()
    merged["REPORT_FROM_NAME"] = (
        str(merged.get("REPORT_FROM_NAME", "")).strip() or DEFAULT_CORTES_CONFIG["REPORT_FROM_NAME"]
    )
    merged["REPORT_SUBJECT_TEMPLATE"] = (
        str(merged.get("REPORT_SUBJECT_TEMPLATE", "")).strip()
        or DEFAULT_CORTES_CONFIG["REPORT_SUBJECT_TEMPLATE"]
    )

    _save_cortes_config(CONFIG_CORTES_PATH, merged)
    return merged
