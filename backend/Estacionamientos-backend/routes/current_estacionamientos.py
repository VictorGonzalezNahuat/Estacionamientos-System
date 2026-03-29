from datetime import date, datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.security import get_current_user
from database import get_db
from models.current_estacionamiento import CurrentEstacionamiento
from models.history_estacionamiento import HistoryEstacionamiento
from models.state_estacionamiento import StateEstacionamiento
from models.tarifa import Tarifa
from models.turno import Turno
from models.usuario import Usuario
from printer.print import generar_ticket_entrada_prueba
from printer.print import generar_ticket_salida_prueba
from printer.print import imprimir_ticket_red
from schemas.current_estacionamiento import CurrentEstacionamientoCreate


router = APIRouter()


def _calcular_importe_por_minutos(total_minutos: int, tarifa: Tarifa):
    importe = 0
    minutos_restantes = total_minutos

    MINUTOS_DIA = 1440
    MINUTOS_MEDIO_DIA = 720
    MINUTOS_HORA = 60
    MINUTOS_FRACCION = 30

    dias = minutos_restantes // MINUTOS_DIA
    if dias > 0:
        importe += dias * tarifa.diario
        minutos_restantes = minutos_restantes % MINUTOS_DIA

    medios_dias = minutos_restantes // MINUTOS_MEDIO_DIA
    if medios_dias > 0:
        importe += medios_dias * tarifa.medio_dia
        minutos_restantes = minutos_restantes % MINUTOS_MEDIO_DIA

    if minutos_restantes > 0:
        if minutos_restantes <= MINUTOS_HORA:
            importe += tarifa.hora
            minutos_restantes = 0
        else:
            importe += tarifa.hora
            minutos_restantes -= MINUTOS_HORA

            horas_completas = minutos_restantes // MINUTOS_HORA
            importe += horas_completas * tarifa.hora
            minutos_restantes = minutos_restantes % MINUTOS_HORA

            if minutos_restantes == 0:
                pass
            elif minutos_restantes <= MINUTOS_FRACCION:
                importe += tarifa.fraccion
            else:
                importe += tarifa.hora

    return importe


def _calcular_minutos_estadia(fecha_entrada, hora_entrada, referencia_dt: datetime) -> int:
    entrada = datetime.combine(fecha_entrada, hora_entrada)
    tiempo_total = referencia_dt - entrada
    total_segundos = tiempo_total.total_seconds()

    if total_segundos < 0:
        raise ValueError("Tiempo invalido")

    return max(1, int(total_segundos / 60))


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

    nuevo_vehiculo = CurrentEstacionamiento(
        placa = auto.placa,
        tarifa_id = tarifa.id,
        encargado_id = current_user.id,
        turno_id = turno.id,
        fecha_entrada = date.today(),
        hora_entrada = datetime.now().time()
    )
    estado_estacionamiento.espacios_ocupados += 1
    db.add(nuevo_vehiculo)
    db.commit()
    db.refresh(nuevo_vehiculo)

    entrada_dt = datetime.combine(nuevo_vehiculo.fecha_entrada, nuevo_vehiculo.hora_entrada)
    placa_ticket = nuevo_vehiculo.placa.strip().upper()
    ticket_bytes = generar_ticket_entrada_prueba(
        folio=f"ENT-{placa_ticket}-{entrada_dt:%Y%m%d%H%M%S}",
        placa=placa_ticket,
        fecha_entrada=entrada_dt,
        tarifa_nombre=getattr(tarifa, "nombre", "Tarifa General"),
        cajero=getattr(current_user, "nombre", "SISTEMA")
    )

    tickets_dir = Path("printer") / "tickets"
    tickets_dir.mkdir(parents=True, exist_ok=True)
    ticket_path = tickets_dir / f"entrada_{placa_ticket}_{entrada_dt:%Y%m%d_%H%M%S}.bin"
    ticket_path.write_bytes(ticket_bytes)
    impreso_ok, impresion_mensaje = imprimir_ticket_red(ticket_bytes)

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

    tarifa = db.query(Tarifa).filter(
        Tarifa.id == vehiculo.tarifa_id
    ).first()

    if not tarifa:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada")

    # Momento real de salida (se usa el mismo valor en todo el flujo)
    salida_dt = datetime.now()
    fecha_salida = salida_dt.date()
    hora_salida = salida_dt.time()

    entrada = datetime.combine(vehiculo.fecha_entrada, vehiculo.hora_entrada)

    try:
        total_minutos = _calcular_minutos_estadia(
            vehiculo.fecha_entrada,
            vehiculo.hora_entrada,
            salida_dt
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Tiempo inválido")

    importe = _calcular_importe_por_minutos(total_minutos, tarifa)
    
    #Como es salida se guarda el turno actual del usuario actual
    turno_usuario = db.query(Turno).filter(Turno.encargado_id == current_user.id, Turno.estado == "activo").first()

    if not turno_usuario:
        raise HTTPException(status_code=404, detail="No existe turno abierto para el usuario actual")


    # 🔹 Crear registro en historial
    historial = HistoryEstacionamiento(
        tarifa_id=vehiculo.tarifa_id,
        encargado_id=vehiculo.encargado_id,
        turno_id=turno_usuario.id,
        fecha_entrada=vehiculo.fecha_entrada,
        hora_entrada=vehiculo.hora_entrada,
        fecha_salida=fecha_salida,
        hora_salida=hora_salida,
        placa=vehiculo.placa,
        importe=importe
    )
    estacionamiento.espacios_ocupados -= 1

    # 🔹 Guardar historial y eliminar de current
    db.add(historial)
    db.delete(vehiculo)
    db.commit()

    ticket_bytes = generar_ticket_salida_prueba(
        folio=f"SAL-{placa}-{salida_dt:%Y%m%d%H%M%S}",
        placa=placa,
        fecha_entrada=entrada,
        fecha_salida=salida_dt,
        minutos_estadia=total_minutos,
        total_pagado=float(importe),
        cajero=getattr(current_user, "nombre", "SISTEMA"),
        etiqueta="ORIGINAL"
    )
    ticket_copia_bytes = generar_ticket_salida_prueba(
        folio=f"SAL-{placa}-{salida_dt:%Y%m%d%H%M%S}",
        placa=placa,
        fecha_entrada=entrada,
        fecha_salida=salida_dt,
        minutos_estadia=total_minutos,
        total_pagado=float(importe),
        cajero=getattr(current_user, "nombre", "SISTEMA"),
        etiqueta="COPIA"
    )

    tickets_dir = Path("printer") / "tickets"
    tickets_dir.mkdir(parents=True, exist_ok=True)
    ticket_path = tickets_dir / f"salida_{placa}_{salida_dt:%Y%m%d_%H%M%S}.bin"
    ticket_path.write_bytes(ticket_bytes)
    impreso_original_ok, impresion_original_mensaje = imprimir_ticket_red(ticket_bytes)
    impreso_copia_ok, impresion_copia_mensaje = imprimir_ticket_red(ticket_copia_bytes)
    impreso_ok = impreso_original_ok and impreso_copia_ok
    impresion_mensaje = (
        f"Original: {impresion_original_mensaje} | "
        f"Copia: {impresion_copia_mensaje}"
    )

    return {
        "mensaje": "Vehiculo retirado correctamente",
        "importe": importe,
        "fecha_salida": fecha_salida,
        "hora_salida": hora_salida,
        "ticket_bin": str(ticket_path),
        "ticket_copias": 2,
        "ticket_impreso": impreso_ok,
        "impresion_mensaje": impresion_mensaje
    }

@router.get("/estacionados")
def obtener_estacionados(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    estacionados = db.query(CurrentEstacionamiento).all()
    if not estacionados:
        return []

    tarifa_ids = {vehiculo.tarifa_id for vehiculo in estacionados}
    tarifas = db.query(Tarifa).filter(Tarifa.id.in_(tarifa_ids)).all()
    tarifas_por_id = {tarifa.id: tarifa for tarifa in tarifas}
    referencia_dt = datetime.now()

    resultado = []
    for vehiculo in estacionados:
        tarifa = tarifas_por_id.get(vehiculo.tarifa_id)
        minutos_estadia = None
        monto_estimado = None

        if tarifa:
            try:
                minutos_estadia = _calcular_minutos_estadia(
                    vehiculo.fecha_entrada,
                    vehiculo.hora_entrada,
                    referencia_dt
                )
                monto_estimado = _calcular_importe_por_minutos(minutos_estadia, tarifa)
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