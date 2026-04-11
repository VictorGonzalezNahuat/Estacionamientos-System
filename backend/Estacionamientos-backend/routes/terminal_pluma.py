import hmac
import os
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.datetime_utils import now_local_naive
from core.parking_ticket_service import construir_ticket_entrada, guardar_ticket_bytes
from database import get_db
from models.current_estacionamiento import CurrentEstacionamiento
from models.state_estacionamiento import StateEstacionamiento
from models.tarifa import Tarifa
from models.turno import Turno
from models.usuario import Usuario


router = APIRouter()

_COUNTER_KEY_SYS_PLATE = "sys_plate"


def _require_terminal_api_key(x_terminal_api_key: str | None = Header(default=None, alias="X-Terminal-Api-Key")) -> None:
    expected_key = os.getenv("TERMINAL_API_KEY", "").strip()
    provided_key = (x_terminal_api_key or "").strip()

    if not expected_key:
        raise HTTPException(status_code=503, detail="TERMINAL_API_KEY no esta configurada en el servidor")

    if not provided_key or not hmac.compare_digest(provided_key, expected_key):
        raise HTTPException(status_code=401, detail="No autorizado para terminal")


def _serialize_dt(value: datetime | None) -> str:
    if not value:
        return "na"
    return value.isoformat(timespec="seconds")


def _obtener_turnos_activos(db: Session) -> list[Turno]:
    return db.query(Turno).filter(Turno.estado == "activo").order_by(Turno.id.asc()).all()


def _resolver_estado_pluma(db: Session) -> dict:
    turnos_activos = _obtener_turnos_activos(db)

    if not turnos_activos:
        return {
            "mode": "inactive",
            "status_version": "inactive:0",
            "turno": None,
            "turnos_activos": [],
            "message": "Es todo por ahora, no hay turnos abiertos. Pluma desactivada",
        }

    if len(turnos_activos) > 1:
        turnos_payload = []
        for turno in turnos_activos:
            encargado = db.query(Usuario).filter(Usuario.id == turno.encargado_id).first()
            turnos_payload.append(
                {
                    "id": turno.id,
                    "encargado_id": turno.encargado_id,
                    "encargado_nombre": getattr(encargado, "nombre", "SISTEMA") if encargado else "SISTEMA",
                    "estado": turno.estado,
                }
            )

        ids = "-".join(str(t["id"]) for t in turnos_payload)
        return {
            "mode": "ambiguous",
            "status_version": f"ambiguous:{ids}",
            "turno": None,
            "turnos_activos": turnos_payload,
            "message": "Atencion: hay multiples turnos abiertos. Pluma bloqueada hasta corregir la configuracion.",
        }

    turno = turnos_activos[0]
    encargado = db.query(Usuario).filter(Usuario.id == turno.encargado_id).first()
    encargado_nombre = getattr(encargado, "nombre", "SISTEMA") if encargado else "SISTEMA"

    return {
        "mode": "active",
        "status_version": f"active:{turno.id}:{_serialize_dt(turno.updated_at)}",
        "turno": {
            "id": turno.id,
            "encargado_id": turno.encargado_id,
            "encargado_nombre": encargado_nombre,
            "estado": turno.estado,
        },
        "turnos_activos": [
            {
                "id": turno.id,
                "encargado_id": turno.encargado_id,
                "encargado_nombre": encargado_nombre,
                "estado": turno.estado,
            }
        ],
        "message": f"Se ha configurado el turno {turno.id} del encargado {encargado_nombre}. Pluma lista para recibir carros",
    }


def _ensure_terminal_counter_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS terminal_counters (
              counter_key VARCHAR(64) PRIMARY KEY,
              current_value BIGINT NOT NULL DEFAULT 0,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
    )


def _next_sys_plate(db: Session, retries: int = 20) -> str:
    _ensure_terminal_counter_table(db)

    db.execute(
        text(
            """
            INSERT INTO terminal_counters (counter_key, current_value)
            VALUES (:counter_key, 0)
            ON DUPLICATE KEY UPDATE counter_key = counter_key
            """
        ),
        {"counter_key": _COUNTER_KEY_SYS_PLATE},
    )

    for _ in range(retries):
        current_value = db.execute(
            text(
                """
                SELECT current_value
                FROM terminal_counters
                WHERE counter_key = :counter_key
                FOR UPDATE
                """
            ),
            {"counter_key": _COUNTER_KEY_SYS_PLATE},
        ).scalar_one()

        next_value = int(current_value) + 1
        db.execute(
            text(
                """
                UPDATE terminal_counters
                SET current_value = :next_value
                WHERE counter_key = :counter_key
                """
            ),
            {"counter_key": _COUNTER_KEY_SYS_PLATE, "next_value": next_value},
        )

        placa_candidate = f"SYS-{next_value:06d}"
        exists = db.query(CurrentEstacionamiento.id).filter(CurrentEstacionamiento.placa == placa_candidate).first()
        if not exists:
            return placa_candidate

    raise HTTPException(status_code=500, detail="No fue posible generar placa SYS unica")


@router.get("/status")
def obtener_estado_pluma(_: None = Depends(_require_terminal_api_key), db: Session = Depends(get_db)):
    return _resolver_estado_pluma(db)


@router.post("/entry-ticket")
def crear_entrada_ticket_binario(_: None = Depends(_require_terminal_api_key), db: Session = Depends(get_db)):
    estado = _resolver_estado_pluma(db)
    mode = estado.get("mode")

    if mode != "active":
        raise HTTPException(
            status_code=423,
            detail={
                "code": "PLUMA_NO_HABILITADA",
                "mode": mode,
                "message": estado.get("message"),
            },
        )

    turno_info = estado.get("turno") or {}
    turno_id = int(turno_info.get("id"))
    encargado_id = int(turno_info.get("encargado_id"))
    encargado_nombre = str(turno_info.get("encargado_nombre") or "SISTEMA")

    estado_estacionamiento = db.query(StateEstacionamiento).first()
    if not estado_estacionamiento:
        raise HTTPException(status_code=500, detail="Estado de estacionamiento no configurado")

    if estado_estacionamiento.total_espacios == estado_estacionamiento.espacios_ocupados:
        raise HTTPException(status_code=409, detail="No hay espacios disponibles en estacionamiento")

    tarifa = db.query(Tarifa).filter(Tarifa.default == 1).first()
    if not tarifa:
        raise HTTPException(status_code=500, detail="No hay tarifa default configurada")

    momento_ingreso = now_local_naive()
    placa_sys = _next_sys_plate(db)

    nuevo_vehiculo = CurrentEstacionamiento(
        placa=placa_sys,
        tarifa_id=tarifa.id,
        encargado_id=encargado_id,
        turno_id=turno_id,
        fecha_entrada=momento_ingreso.date(),
        hora_entrada=momento_ingreso.time(),
    )

    estado_estacionamiento.espacios_ocupados += 1
    estado_estacionamiento.espacios_disponibles = max(
        0,
        int(estado_estacionamiento.total_espacios) - int(estado_estacionamiento.espacios_ocupados),
    )

    db.add(nuevo_vehiculo)
    db.commit()
    db.refresh(nuevo_vehiculo)

    entrada_dt = datetime.combine(nuevo_vehiculo.fecha_entrada, nuevo_vehiculo.hora_entrada)
    ticket_bytes = construir_ticket_entrada(
        folio=f"ENT-{placa_sys}-{entrada_dt:%Y%m%d%H%M%S}",
        placa=placa_sys,
        fecha_entrada=entrada_dt,
        tarifa_nombre=getattr(tarifa, "nombre", "Tarifa General"),
        cajero=encargado_nombre,
    )
    guardar_ticket_bytes("entrada", placa_sys, entrada_dt, ticket_bytes)

    filename = f"ticket_{placa_sys}.bin"
    return Response(
        content=ticket_bytes,
        status_code=201,
        media_type="application/octet-stream",
        headers={
            "X-Action-Status": "created",
            "X-Entry-Plate": placa_sys,
            "X-Entry-Id": str(nuevo_vehiculo.id),
            "X-Turno-Id": str(turno_id),
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )