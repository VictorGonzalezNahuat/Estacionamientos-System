from datetime import date, datetime
from pathlib import Path
from fastapi.responses import Response
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import and_
from sqlalchemy.orm import Session
from core.corte_email_service import send_corte_report_email_task
from core.security import get_current_user
from database import get_db

from models.corte_caja import CorteCaja
from models.history_estacionamiento import HistoryEstacionamiento
from models.turno import Turno
from models.usuario import Usuario
from printer.corte_pdf import generar_pdf_corte_caja
from printer.print import generar_ticket_corte_caja, imprimir_ticket
from schemas.corte_caja import CorteCajaCreate, CorteCajaResumenResponse, CorteCajaResponse


router = APIRouter()


def _obtener_historial_para_corte(
    turno_id: int,
    current_user: Usuario,
    db: Session,
):
    turno = db.query(Turno).filter(Turno.id == turno_id).first()

    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    if turno.encargado_id != current_user.id and current_user.rol != "admin":
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para hacer corte de este turno"
        )

    if turno.estado != "pendiente_corte":
        raise HTTPException(
            status_code=400,
            detail=f"El turno debe estar en estado 'pendiente_corte', actualmente está en '{turno.estado}'"
        )

    corte_existente = db.query(CorteCaja).filter(CorteCaja.id_turno == turno_id).first()
    if corte_existente:
        raise HTTPException(
            status_code=400,
            detail="Ya existe un corte para este turno"
        )

    historial_turno = db.query(HistoryEstacionamiento).filter(
        and_(
            HistoryEstacionamiento.turno_id == turno_id,
            HistoryEstacionamiento.corte_id == None,
            HistoryEstacionamiento.cancelado == 0,
        )
    ).all()

    return turno, historial_turno


def _obtener_historial_informativo_turno(
    turno_id: int,
    current_user: Usuario,
    db: Session,
):
    turno = db.query(Turno).filter(Turno.id == turno_id).first()

    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    if turno.encargado_id != current_user.id and current_user.rol != "admin":
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para consultar este turno"
        )

    if turno.estado not in ("activo", "pendiente_corte"):
        raise HTTPException(
            status_code=400,
            detail=f"El turno debe estar en estado 'activo' o 'pendiente_corte', actualmente está en '{turno.estado}'"
        )

    historial_turno = db.query(HistoryEstacionamiento).filter(
        and_(
            HistoryEstacionamiento.turno_id == turno_id,
            HistoryEstacionamiento.corte_id == None,
            HistoryEstacionamiento.cancelado == 0,
        )
    ).all()

    return turno, historial_turno


@router.post("/", response_model=CorteCajaResponse)
def crear_corte_caja(
    request: CorteCajaCreate,
    background_tasks: BackgroundTasks,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Crear un corte de caja para un turno.
    
    Flujo:
    1. Valida que el turno existe y tiene estado "pendiente_corte"
    2. Valida que el turno pertenece al usuario actual (o es admin)
    3. Calcula totales de efectivo, tarjeta e importe total
    4. Crea el registro de corte_caja
    5. Actualiza todos los registros de historial del turno con el corte_id
    6. Cambia el turno a estado "cortado"
    """
    
    turno_id = request.turno_id
    total_declarado = request.total_declarado

    turno, historial_turno = _obtener_historial_para_corte(turno_id, current_user, db)
    
    detalle_movimientos = []
    for movimiento in historial_turno:
        detalle_movimientos.append({
            "placa": movimiento.placa,
            "entrada": datetime.combine(movimiento.fecha_entrada, movimiento.hora_entrada),
            "salida": datetime.combine(movimiento.fecha_salida, movimiento.hora_salida),
            "importe": float(movimiento.importe),
            "metodo_pago": movimiento.metodo_pago,
            "pagado": bool(movimiento.pagado),
        })

    # 2. Calcular totales
    total_calculado = sum(float(h.importe) for h in historial_turno)
    total_efectivo = sum(float(h.importe) for h in historial_turno if h.metodo_pago == "efectivo")
    total_tarjeta = sum(float(h.importe) for h in historial_turno if h.metodo_pago == "tarjeta")
    diferencia = total_declarado - total_calculado
    
    # 3. Crear registro de corte_caja
    nuevo_corte = CorteCaja(
        id_turno=turno_id,
        fecha_inicio=turno.fecha,
        hora_inicio=turno.hora_inicio,
        fecha_fin=turno.fecha_fin,
        hora_fin=turno.hora_fin,
        total_calculado=total_calculado,
        total_declarado=total_declarado,
        diferencia=diferencia,
        total_efectivo=total_efectivo,
        total_tarjeta=total_tarjeta
    )
    
    db.add(nuevo_corte)
    db.flush()  # Para obtener el ID del corte sin hacer commit aún
    corte_id = nuevo_corte.id
    
    # 4. Actualizar registros de historia con el corte_id
    db.query(HistoryEstacionamiento).filter(
        and_(
            HistoryEstacionamiento.turno_id == turno_id,
            HistoryEstacionamiento.corte_id == None,
            HistoryEstacionamiento.cancelado == 0,
        )
    ).update({HistoryEstacionamiento.corte_id: corte_id})
    
    # 5. Cambiar estado del turno a "cortado"
    turno.estado = "cortado"
    
    db.commit()
    db.refresh(nuevo_corte)

    fecha_inicio_turno = datetime.combine(turno.fecha, turno.hora_inicio)
    fecha_fin_turno = datetime.combine(turno.fecha_fin, turno.hora_fin)

    ticket_bytes = generar_ticket_corte_caja(
        folio=f"COR-{turno_id}-{corte_id}",
        turno_id=turno_id,
        fecha_inicio=fecha_inicio_turno,
        fecha_fin=fecha_fin_turno,
        detalle_movimientos=detalle_movimientos,
        total_calculado=total_calculado,
        total_declarado=total_declarado,
        diferencia=diferencia,
        total_efectivo=total_efectivo,
        total_tarjeta=total_tarjeta,
        cajero=getattr(current_user, "nombre", "SISTEMA"),
    )

    tickets_corte_dir = Path("printer") / "tickets_corte"
    tickets_corte_dir.mkdir(parents=True, exist_ok=True)
    ticket_corte_path = tickets_corte_dir / f"corte_{turno_id}_{corte_id}_{datetime.now():%Y%m%d_%H%M%S}.bin"
    ticket_corte_path.write_bytes(ticket_bytes)

    impreso_ok, impresion_mensaje = imprimir_ticket(ticket_bytes, tipo_ticket="corte")
    if not impreso_ok:
        print(f"Error imprimiendo corte de caja | {impresion_mensaje}")

    background_tasks.add_task(
        send_corte_report_email_task,
        corte_id=corte_id,
        turno_id=turno_id,
        cajero=getattr(current_user, "nombre", "SISTEMA"),
        fecha_inicio=fecha_inicio_turno,
        fecha_fin=fecha_fin_turno,
        total_calculado=float(total_calculado),
        total_declarado=float(total_declarado),
        diferencia=float(diferencia),
        total_efectivo=float(total_efectivo),
        total_tarjeta=float(total_tarjeta),
        movimientos=detalle_movimientos,
    )
    
    return nuevo_corte


@router.get("/turno/{turno_id}/resumen", response_model=CorteCajaResumenResponse)
def obtener_resumen_corte_turno(
    turno_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener el resumen informativo de un turno en activo o pendiente_corte."""

    _, historial_turno = _obtener_historial_informativo_turno(turno_id, current_user, db)

    total_efectivo = sum(float(h.importe) for h in historial_turno if h.metodo_pago == "efectivo")
    total_tarjeta = sum(float(h.importe) for h in historial_turno if h.metodo_pago == "tarjeta")

    return {
        "turno_id": turno_id,
        "total_efectivo": total_efectivo,
        "total_tarjeta": total_tarjeta,
        "total_total": total_efectivo + total_tarjeta,
    }


@router.get("/turno/{turno_id}", response_model=CorteCajaResponse)
def obtener_corte_turno(
    turno_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener el corte de caja de un turno específico"""
    
    turno = db.query(Turno).filter(Turno.id == turno_id).first()
    
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    
    # Validar que el usuario tiene permiso
    if turno.encargado_id != current_user.id and current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="No tiene permiso para ver este corte")
    
    corte = db.query(CorteCaja).filter(CorteCaja.id_turno == turno_id).first()
    
    if not corte:
        raise HTTPException(status_code=404, detail="No existe corte para este turno")
    
    return corte


@router.get("/", response_model=list[CorteCajaResponse])
def listar_cortes(
    desde: date | None = None,
    hasta: date | None = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Listar cortes de caja del usuario actual.
    Si es admin, lista todos los cortes.
    Opcionalmente filtrar por rango de fechas.
    """
    
    query = db.query(CorteCaja)
    
    # Si no es admin, filtrar por usuario
    if current_user.rol != "admin":
        query = query.join(Turno).filter(Turno.encargado_id == current_user.id)
    
    # Filtrar por rango de fechas si se proporciona
    if desde:
        query = query.filter(CorteCaja.fecha_inicio >= desde)
    
    if hasta:
        query = query.filter(CorteCaja.fecha_fin <= hasta)
    
    cortes = query.all()
    
    return cortes


@router.get("/{corte_id}/pdf")
def descargar_pdf_corte(
    corte_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    corte = db.query(CorteCaja).filter(CorteCaja.id == corte_id).first()
    if not corte:
        raise HTTPException(status_code=404, detail="Corte no encontrado")

    turno = db.query(Turno).filter(Turno.id == corte.id_turno).first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado para este corte")

    if current_user.rol != "admin" and turno.encargado_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tiene permiso para descargar este reporte")

    historial_corte = db.query(HistoryEstacionamiento).filter(
        HistoryEstacionamiento.corte_id == corte.id,
        HistoryEstacionamiento.cancelado == 0,
    ).all()

    movimientos = []
    for item in historial_corte:
        movimientos.append({
            "placa": item.placa,
            "entrada": datetime.combine(item.fecha_entrada, item.hora_entrada),
            "salida": datetime.combine(item.fecha_salida, item.hora_salida),
            "metodo_pago": item.metodo_pago,
            "pagado": bool(item.pagado),
            "importe": float(item.importe),
        })

    cajero = db.query(Usuario).filter(Usuario.id == turno.encargado_id).first()
    nombre_cajero = getattr(cajero, "nombre", "SISTEMA") if cajero else "SISTEMA"

    pdf_bytes = generar_pdf_corte_caja(
        corte_id=corte.id,
        turno_id=turno.id,
        cajero=nombre_cajero,
        fecha_inicio=datetime.combine(corte.fecha_inicio, corte.hora_inicio),
        fecha_fin=datetime.combine(corte.fecha_fin, corte.hora_fin),
        total_calculado=float(corte.total_calculado),
        total_declarado=float(corte.total_declarado),
        diferencia=float(corte.diferencia),
        total_efectivo=float(corte.total_efectivo),
        total_tarjeta=float(corte.total_tarjeta),
        movimientos=movimientos,
    )

    filename = f"corte_{turno.id}_{corte.id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
