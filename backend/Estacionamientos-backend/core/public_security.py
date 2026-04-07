import os
import threading
import time

import requests
from fastapi import HTTPException, Request


_RATE_LIMIT_LOCK = threading.Lock()
_RATE_LIMIT_COUNTERS: dict[str, int] = {}
_RATE_LIMIT_LAST_CLEANUP_TS = 0.0


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, str(default)).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float, min_value: float, max_value: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        parsed = float(raw)
    except ValueError:
        parsed = default
    return max(min_value, min(max_value, parsed))


def _env_int(name: str, default: int, min_value: int, max_value: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        parsed = int(raw)
    except ValueError:
        parsed = default
    return max(min_value, min(max_value, parsed))


def get_client_ip(request: Request) -> str:
    x_forwarded_for = request.headers.get("x-forwarded-for", "")
    if x_forwarded_for:
        first_ip = x_forwarded_for.split(",", 1)[0].strip()
        if first_ip:
            return first_ip

    x_real_ip = request.headers.get("x-real-ip", "").strip()
    if x_real_ip:
        return x_real_ip

    if request.client and request.client.host:
        return request.client.host

    return "unknown"


def enforce_rate_limit_or_raise(request: Request, scope: str, limit_per_window: int, window_seconds: int = 60) -> None:
    if limit_per_window <= 0:
        return

    if not _env_bool("FACTURACION_RATE_LIMIT_ENABLED", True):
        return

    now = int(time.time())
    window_id = now // max(1, window_seconds)
    ip = get_client_ip(request)
    key = f"{scope}:{ip}:{window_id}"

    global _RATE_LIMIT_LAST_CLEANUP_TS
    with _RATE_LIMIT_LOCK:
        _RATE_LIMIT_COUNTERS[key] = _RATE_LIMIT_COUNTERS.get(key, 0) + 1
        current = _RATE_LIMIT_COUNTERS[key]

        # Keep memory usage stable by pruning old windows every ~2 minutes.
        if (now - _RATE_LIMIT_LAST_CLEANUP_TS) >= 120:
            min_window_to_keep = window_id - 2
            old_keys = [k for k in _RATE_LIMIT_COUNTERS if int(k.rsplit(":", 1)[-1]) < min_window_to_keep]
            for old_key in old_keys:
                _RATE_LIMIT_COUNTERS.pop(old_key, None)
            _RATE_LIMIT_LAST_CLEANUP_TS = float(now)

    if current <= limit_per_window:
        return

    retry_after = max(1, window_seconds - (now % window_seconds))
    raise HTTPException(
        status_code=429,
        detail={
            "code": "RATE_LIMITED",
            "message": f"Demasiadas solicitudes. Intenta de nuevo en {retry_after} segundos",
            "retry_after_seconds": retry_after,
        },
        headers={"Retry-After": str(retry_after)},
    )


def verify_recaptcha_or_raise(request: Request, token: str, expected_action: str | None = None) -> None:
    if not _env_bool("FACTURACION_RECAPTCHA_ENABLED", True):
        return

    token_norm = (token or "").strip()
    if not token_norm:
        raise HTTPException(status_code=400, detail="recaptcha_token requerido")

    secret_key = os.getenv("FACTURACION_RECAPTCHA_SECRET_KEY", "").strip()
    if not secret_key:
        raise HTTPException(status_code=503, detail="reCAPTCHA no configurado en el servidor")

    verify_url = os.getenv("FACTURACION_RECAPTCHA_VERIFY_URL", "https://www.google.com/recaptcha/api/siteverify").strip()
    timeout_seconds = _env_int("FACTURACION_RECAPTCHA_TIMEOUT_SECONDS", 3, 1, 10)
    threshold = _env_float("FACTURACION_RECAPTCHA_SCORE_THRESHOLD", 0.5, 0.0, 1.0)
    strict_action = _env_bool("FACTURACION_RECAPTCHA_STRICT_ACTION", False)

    try:
        response = requests.post(
            verify_url,
            data={
                "secret": secret_key,
                "response": token_norm,
                "remoteip": get_client_ip(request),
            },
            timeout=timeout_seconds,
        )
    except Exception:
        raise HTTPException(status_code=503, detail="Servicio de verificacion reCAPTCHA no disponible")

    if response.status_code >= 400:
        raise HTTPException(status_code=503, detail="No fue posible validar reCAPTCHA")

    body = response.json() if response.content else {}
    success = bool(body.get("success"))
    score = float(body.get("score") or 0.0)
    action = str(body.get("action") or "")

    if not success:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "RECAPTCHA_FAILED",
                "message": "Verificacion de humano fallida",
            },
        )

    if strict_action and expected_action and action and action != expected_action:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "RECAPTCHA_ACTION_MISMATCH",
                "message": "Accion de reCAPTCHA invalida",
            },
        )

    if score < threshold:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "RECAPTCHA_LOW_SCORE",
                "message": "Verificacion de humano fallida (score bajo)",
                "score": score,
                "threshold": threshold,
            },
        )
