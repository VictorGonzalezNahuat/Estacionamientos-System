from fastapi import APIRouter, Depends, HTTPException

from core import config as app_config
from core.config import (
    get_public_config_values,
    update_public_config_values,
    update_database_config,
    update_other_config,
)
from core.sync_scheduler import start_sync_scheduler, stop_sync_scheduler
from core.security import get_user_admin
from models.usuario import Usuario
from schemas.configuracion import (
    ConfiguracionResponse,
    ConfiguracionUpdate,
    DatabaseConfigUpdate,
    OtherConfigUpdate,
)


router = APIRouter()


@router.get("/", response_model=ConfiguracionResponse)
def obtener_configuracion(current_user: Usuario = Depends(get_user_admin)):
    """Obtiene toda la configuracion del sistema"""
    return get_public_config_values()


@router.patch("/base-datos", response_model=ConfiguracionResponse)
async def editar_configuracion_base_datos(
    cambios: DatabaseConfigUpdate,
    current_user: Usuario = Depends(get_user_admin),
):
    """
    Actualiza la configuracion de la base de datos (DATABASE_CLOUD_URL).
    Requiere la contraseña de la base de datos.
    """
    payload = cambios.model_dump(exclude_unset=True)
    try:
        updated = update_database_config(payload)
        return updated
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/", response_model=ConfiguracionResponse)
async def editar_configuracion(
    cambios: OtherConfigUpdate,
    current_user: Usuario = Depends(get_user_admin),
):
    """
    Actualiza las demas variables de configuracion (sin contraseña de BD).
    No requiere la contraseña de la base de datos.
    """
    payload = cambios.model_dump(exclude_unset=True)
    try:
        updated = update_other_config(payload)

        sync_keys = {"SYNC_AUTO_ENABLED", "SYNC_INTERVAL_MINUTES"}
        if sync_keys.intersection(payload.keys()):
            await stop_sync_scheduler()
            if app_config.SYNC_AUTO_ENABLED:
                start_sync_scheduler()

        return updated
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/all", response_model=ConfiguracionResponse)
async def editar_configuracion_completa(
    cambios: ConfiguracionUpdate,
    current_user: Usuario = Depends(get_user_admin),
):
    """
    Endpoint deprecado - Actualiza toda la configuracion en una sola peticion.
    Mantener por retrocompatibilidad. Use /base-datos y / en su lugar.
    """
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
