import asyncio
from datetime import datetime
from typing import Optional

from core import config as app_config
from core.sync_service import run_incremental_sync
from database import SessionCloud, SessionLocal

_scheduler_task: Optional[asyncio.Task] = None
_stop_event: Optional[asyncio.Event] = None
_run_count = 0
_last_run_at: Optional[str] = None
_last_result_status: Optional[str] = None
_last_error: Optional[str] = None
_interval_seconds = 0


def _run_sync_once() -> dict:
    local_db = SessionLocal()
    cloud_db = SessionCloud()
    try:
        result = run_incremental_sync(local_db=local_db, cloud_db=cloud_db, non_blocking=True)
        print(f"[sync-scheduler] result={result.get('status', 'ok')} mode={result.get('mode')}")
        return result
    except Exception as exc:
        print(f"[sync-scheduler] error={exc}")
        return {"status": "error", "error": str(exc)}
    finally:
        cloud_db.close()
        local_db.close()


async def _scheduler_loop(interval_minutes: int, stop_event: asyncio.Event) -> None:
    global _run_count, _last_run_at, _last_result_status, _last_error, _interval_seconds

    interval_seconds = max(interval_minutes, 1) * 60
    _interval_seconds = interval_seconds

    while not stop_event.is_set():
        try:
            result = await asyncio.to_thread(_run_sync_once)
            _run_count += 1
            _last_run_at = datetime.utcnow().isoformat()
            _last_result_status = str(result.get("status", "ok"))
            _last_error = result.get("error")

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
            except asyncio.TimeoutError:
                continue
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            _last_error = str(exc)
            print(f"[sync-scheduler] loop_error={exc}")
            # Evita que el loop muera por errores inesperados y reintenta en el siguiente ciclo.
            await asyncio.sleep(interval_seconds)


def start_sync_scheduler() -> None:
    global _scheduler_task, _stop_event, _last_error

    if not app_config.SYNC_AUTO_ENABLED:
        print("[sync-scheduler] disabled by SYNC_AUTO_ENABLED")
        return

    if _scheduler_task is not None and not _scheduler_task.done():
        return

    _stop_event = asyncio.Event()
    _last_error = None
    _scheduler_task = asyncio.create_task(_scheduler_loop(app_config.SYNC_INTERVAL_MINUTES, _stop_event))
    print(f"[sync-scheduler] started interval={max(app_config.SYNC_INTERVAL_MINUTES, 1)}m")


async def stop_sync_scheduler() -> None:
    global _scheduler_task, _stop_event

    if _scheduler_task is None:
        return

    if _stop_event is not None:
        _stop_event.set()

    await _scheduler_task
    _scheduler_task = None
    _stop_event = None
    print("[sync-scheduler] stopped")


def get_sync_scheduler_status() -> dict:
    active = _scheduler_task is not None and not _scheduler_task.done()
    return {
        "enabled": app_config.SYNC_AUTO_ENABLED,
        "active": active,
        "interval_minutes": max(app_config.SYNC_INTERVAL_MINUTES, 1),
        "interval_seconds": _interval_seconds or max(app_config.SYNC_INTERVAL_MINUTES, 1) * 60,
        "run_count": _run_count,
        "last_run_at": _last_run_at,
        "last_result_status": _last_result_status,
        "last_error": _last_error,
    }
