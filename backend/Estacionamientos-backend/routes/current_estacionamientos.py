from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.datetime_utils import now_local_naive
from core.security import get_current_user
from core.parking_exit_service import registrar_salida_efectivo
from core.parking_pricing import calcular_importe_por_minutos, calcular_minutos_estadia
from core.parking_ticket_service import construir_ticket_entrada, guardar_ticket_bytes, imprimir_ticket_entrada
from database import get_db
from models.current_estacionamiento import CurrentEstacionamiento
from models.state_estacionamiento import StateEstacionamiento
from models.tarifa import Tarifa
from models.turno import Turno
from models.usuario import Usuario
from schemas.current_estacionamiento import CurrentEstacionamientoCreate


router = APIRouter()


@router.post("/ingresar")
def ingresar_auto(auto: CurrentEstacionamientoCreate, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    
    estado_estacionamiento = db.query(StateEstacionamiento).first()
    
    if estado_estacionamiento.total_espacios == estado_estacionamiento.espacios_ocupados:
        raise HTTPException(status_code=409, detail="No hay espacios disponibles en estacionamiento")
    
    turno = db.query(Turno).filter(Turno.encargado_id == current_user.id, Turno.estado == "activo").first()

    if not turno:
        raise HTTPException(status_code=404, detail="No existe turno abierto para el usuario actual")
    
    vehiculo = db.query(CurrentEstacionamiento).filter(CurrentEstacionamiento.placa == auto.placa).first()

    if vehiculo:
        raise HTTPException(status_code=400, detail="Vehiculo ya registrado dentro del estacionamiento")
    
    tarifa = db.query(Tarifa).filter(Tarifa.default == 1).first()

    momento_ingreso = now_local_naive()

    nuevo_vehiculo = CurrentEstacionamiento(
        placa = auto.placa,
        tarifa_id = tarifa.id,
        encargado_id = current_user.id,
        turno_id = turno.id,
        fecha_entrada = momento_ingreso.date(),
        hora_entrada = momento_ingreso.time()
    )
    estado_estacionamiento.espacios_ocupados += 1
    db.add(nuevo_vehiculo)
    db.commit()
    db.refresh(nuevo_vehiculo)

    entrada_dt = datetime.combine(nuevo_vehiculo.fecha_entrada, nuevo_vehiculo.hora_entrada)
    placa_ticket = nuevo_vehiculo.placa.strip().upper()
    ticket_bytes = construir_ticket_entrada(
        folio=f"ENT-{placa_ticket}-{entrada_dt:%Y%m%d%H%M%S}",
        placa=placa_ticket,
        fecha_entrada=entrada_dt,
        tarifa_nombre=getattr(tarifa, "nombre", "Tarifa General"),
        cajero=getattr(current_user, "nombre", "SISTEMA")
    )

    ticket_path = guardar_ticket_bytes("entrada", placa_ticket, entrada_dt, ticket_bytes)
    impreso_ok, impresion_mensaje = imprimir_ticket_entrada(ticket_bytes)

    return {
        "mensaje": "Vehiculo ingresado correctamente",
        "ticket_bin": str(ticket_path),
        "ticket_impreso": impreso_ok,
        "impresion_mensaje": impresion_mensaje
    }

@router.post("/salir")
def sacar_auto(
    auto: CurrentEstacionamientoCreate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    
    placa = auto.placa.strip().upper()

    vehiculo = db.query(CurrentEstacionamiento).filter(
        CurrentEstacionamiento.placa == placa
    ).first()

    estacionamiento = db.query(StateEstacionamiento).first()

    if estacionamiento.espacios_ocupados == 0:
        raise HTTPException(status_code=409, detail="No hay autos estacionados")

    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehiculo no encontrado")
    resultado = registrar_salida_efectivo(db, current_user, placa)
    return resultado.to_dict()

@router.get("/estacionados")
def obtener_estacionados(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    estacionados = db.query(CurrentEstacionamiento).all()
    if not estacionados:
        return []

    tarifa_ids = {vehiculo.tarifa_id for vehiculo in estacionados}
    tarifas = db.query(Tarifa).filter(Tarifa.id.in_(tarifa_ids)).all()
    tarifas_por_id = {tarifa.id: tarifa for tarifa in tarifas}
    referencia_dt = now_local_naive()

    resultado = []
    for vehiculo in estacionados:
        tarifa = tarifas_por_id.get(vehiculo.tarifa_id)
        minutos_estadia = None
        monto_estimado = None

        if tarifa:
            try:
                minutos_estadia = calcular_minutos_estadia(
                    vehiculo.fecha_entrada,
                    vehiculo.hora_entrada,
                    referencia_dt
                )
                monto_estimado = calcular_importe_por_minutos(minutos_estadia, tarifa)
            except ValueError:
                minutos_estadia = None
                monto_estimado = None

        resultado.append({
            "id": vehiculo.id,
            "encargado_id": vehiculo.encargado_id,
            "placa": vehiculo.placa,
            "tarifa_id": vehiculo.tarifa_id,
            "turno_id": vehiculo.turno_id,
            "fecha_entrada": vehiculo.fecha_entrada,
            "hora_entrada": vehiculo.hora_entrada,
            "updated_at": vehiculo.updated_at,
            "minutos_estadia": minutos_estadia,
            "monto_estimado": monto_estimado
        })

    return resultado