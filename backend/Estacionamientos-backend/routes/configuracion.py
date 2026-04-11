from fastapi import APIRouter, Depends, HTTPException

from core import config as app_config
from core.config import (
    get_public_config_values,
    update_public_config_values,
    update_database_config,
    update_other_config,
)
from core.cortes_config import (
    get_public_cortes_config_values,
    update_cortes_config_values,
)
from core.sync_scheduler import start_sync_scheduler, stop_sync_scheduler
from core.security import get_user_admin
from models.usuario import Usuario
from printer.print import get_printer_config_values, update_printer_config_values
from schemas.configuracion import (
    ConfiguracionResponse,
    ConfiguracionUpdate,
    DatabaseConfigUpdate,
    OtherConfigUpdate,
    CortesConfiguracionResponse,
    CortesConfiguracionUpdate,
    PrinterConfigResponse,
    PrinterConfigUpdate,
)


router = APIRouter()


@router.get("/", response_model=ConfiguracionResponse)
def obtener_configuracion(current_user: Usuario = Depends(get_user_admin)):
    """Obtiene toda la configuracion del sistema"""
    return get_public_config_values()


@router.get("/printer", response_model=PrinterConfigResponse)
def obtener_configuracion_printer(current_user: Usuario = Depends(get_user_admin)):
    """Obtiene la configuracion de impresion desde config_printer.json."""
    return get_printer_config_values()


@router.patch("/printer", response_model=PrinterConfigResponse)
def editar_configuracion_printer(
    cambios: PrinterConfigUpdate,
    current_user: Usuario = Depends(get_user_admin),
):
    """Actualiza parcialmente la configuracion de impresion en config_printer.json."""
    payload = cambios.model_dump(exclude_unset=True)
    try:
        return update_printer_config_values(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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


@router.get("/cortes", response_model=CortesConfiguracionResponse)
def obtener_configuracion_cortes(current_user: Usuario = Depends(get_user_admin)):
    """Obtiene la configuracion de envios de cortes por email."""
    return get_public_cortes_config_values()


@router.patch("/cortes", response_model=CortesConfiguracionResponse)
def editar_configuracion_cortes(
    cambios: CortesConfiguracionUpdate,
    current_user: Usuario = Depends(get_user_admin),
):
    """Actualiza parcialmente la configuracion de envios de cortes por email."""
    payload = cambios.model_dump(exclude_unset=True)
    try:
        updated = update_cortes_config_values(payload)
        return {
            key: value
            for key, value in updated.items()
            if key != "SMTP_PASSWORD"
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
