from fastapi import APIRouter, Depends, HTTPException

from core import config as app_config
from core.config import get_public_config_values, update_public_config_values
from core.sync_scheduler import start_sync_scheduler, stop_sync_scheduler
from core.security import get_user_admin
from models.usuario import Usuario
from schemas.configuracion import ConfiguracionResponse, ConfiguracionUpdate


router = APIRouter()


@router.get("/", response_model=ConfiguracionResponse)
def obtener_configuracion(current_user: Usuario = Depends(get_user_admin)):
    return get_public_config_values()


@router.patch("/", response_model=ConfiguracionResponse)
async def editar_configuracion(
    cambios: ConfiguracionUpdate,
    current_user: Usuario = Depends(get_user_admin),
):
    payload = cambios.model_dump(exclude_unset=True)
    try:
        updated = update_public_config_values(payload)

        sync_keys = {"SYNC_AUTO_ENABLED", "SYNC_INTERVAL_MINUTES"}
        if sync_keys.intersection(payload.keys()):
            await stop_sync_scheduler()
            if app_config.SYNC_AUTO_ENABLED:
                start_sync_scheduler()

        return updated
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
