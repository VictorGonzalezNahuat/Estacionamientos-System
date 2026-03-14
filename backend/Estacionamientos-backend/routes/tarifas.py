from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.security import get_current_user
from database import get_db
from models.tarifa import Tarifa
from models.usuario import Usuario
from models.current_estacionamiento import CurrentEstacionamiento
from models.history_estacionamiento import HistoryEstacionamiento
from schemas.tarifa import TarifaBase, TarifaRespose

router = APIRouter()


@router.get("/default")
def tarifa_default(current_user: Usuario = Depends(get_current_user),db: Session = Depends(get_db)):
    return db.query(Tarifa).filter(Tarifa.default == 1).first()

@router.get("/next-numero")
def obtener_siguiente_numero(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Devuelve el siguiente número esperado para una nueva tarifa.
    Busca el número más alto actual y suma 1.
    """
    from sqlalchemy import func
    
    max_numero = db.query(func.max(Tarifa.numero)).scalar()
    siguiente_numero = (max_numero or 0) + 1
    
    return {"siguiente_numero": siguiente_numero}

@router.get("/", response_model=list[TarifaRespose])
def listar_tarifas(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Tarifa).filter(Tarifa.eliminado==0).all()

@router.get("/deleted", response_model=list[TarifaRespose])
def listar_tarifas_eliminadas(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Tarifa).filter(Tarifa.eliminado == 1).all()


@router.post("/", response_model=TarifaRespose)
def crear_tarifa( tarifa: TarifaBase,current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    # Verificar que no exista una tarifa ACTIVA con ese número
    existe_activa = db.query(Tarifa).filter(Tarifa.numero == tarifa.numero, Tarifa.eliminado == 0).first()
    if existe_activa:
        raise HTTPException(status_code=400, detail="El número de la tarifa ya existe")

    nueva_tarifa = Tarifa(
        numero=tarifa.numero,
        tipo_vehiculo=tarifa.tipo_vehiculo,
        hora=tarifa.hora,
        fraccion=tarifa.fraccion,
        medio_dia=tarifa.medio_dia,
        diario=tarifa.diario,
        observaciones=tarifa.observaciones,
        eliminado=0
    )

    db.add(nueva_tarifa)
    db.commit()
    db.refresh(nueva_tarifa)

    return nueva_tarifa

@router.put("/{numero}", response_model=TarifaRespose)
def editar_tarifa(numero: int, tarifa: TarifaBase, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    # Solo editar tarifas activas (no eliminadas)
    existe_tarifa = db.query(Tarifa).filter(Tarifa.numero == numero, Tarifa.eliminado == 0).first()

    if not existe_tarifa:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada o eliminada")

    # Validar que la tarifa no esté siendo usada en estacionamientos actuales
    tarifa_en_uso_actual = db.query(CurrentEstacionamiento).filter(
        CurrentEstacionamiento.tarifa_id == existe_tarifa.id
    ).first()
    
    if tarifa_en_uso_actual:
        raise HTTPException(
            status_code=400, 
            detail="No se puede modificar la tarifa porque está siendo utilizada actualmente. Se recomienda crear una nueva tarifa y establecerla como default."
        )
    
    # Validar que la tarifa no esté en el historial
    tarifa_en_historial = db.query(HistoryEstacionamiento).filter(
        HistoryEstacionamiento.tarifa_id == existe_tarifa.id
    ).first()
    
    if tarifa_en_historial:
        raise HTTPException(
            status_code=400, 
            detail="No se puede modificar la tarifa porque ya ha sido utilizada. Se recomienda crear una nueva tarifa y establecerla como default."
        )

    existe_tarifa.tipo_vehiculo = tarifa.tipo_vehiculo
    existe_tarifa.hora = tarifa.hora
    existe_tarifa.fraccion = tarifa.fraccion
    existe_tarifa.medio_dia = tarifa.medio_dia
    existe_tarifa.diario = tarifa.diario
    existe_tarifa.observaciones = tarifa.observaciones

    db.commit()
    db.refresh(existe_tarifa)

    return existe_tarifa

@router.delete("/{numero}/", response_model=TarifaRespose)
def eliminar_tarifa(numero: int, current_user: Usuario = Depends(get_current_user), db:Session = Depends(get_db)):
    existe_tarifa = db.query(Tarifa).filter(Tarifa.numero == numero, Tarifa.eliminado == 0).first()

    if not existe_tarifa:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada o eliminada")
    
    # Validar que la tarifa no esté siendo usada en estacionamientos actuales
    tarifa_en_uso_actual = db.query(CurrentEstacionamiento).filter(
        CurrentEstacionamiento.tarifa_id == existe_tarifa.id
    ).first()
    
    if tarifa_en_uso_actual:
        raise HTTPException(
            status_code=400, 
            detail="No se puede eliminar la tarifa porque está siendo utilizada actualmente."
        )
    
    # Validar que la tarifa no esté en el historial
    tarifa_en_historial = db.query(HistoryEstacionamiento).filter(
        HistoryEstacionamiento.tarifa_id == existe_tarifa.id
    ).first()
    
    if tarifa_en_historial:
        raise HTTPException(
            status_code=400, 
            detail="No se puede eliminar la tarifa porque ya ha sido utilizada."
        )
    
    existe_tarifa.eliminado = 1

    db.commit()
    db.refresh(existe_tarifa)

    return existe_tarifa

@router.patch("/{tarifa_id}/restore", response_model=TarifaRespose)
def restaurar_tarifa(tarifa_id: int, current_user: Usuario = Depends(get_current_user), db:Session=Depends(get_db)):
    # Buscar por ID para ser específico cuando hay múltiples eliminadas con el mismo número
    existe_tarifa_eliminada = db.query(Tarifa).filter(Tarifa.id == tarifa_id, Tarifa.eliminado == 1).first()

    if not existe_tarifa_eliminada:
        raise HTTPException(status_code=404, detail="Tarifa eliminada no encontrada")
    
    # Verificar que no exista una tarifa ACTIVA con el mismo número
    ya_existe_activa = db.query(Tarifa).filter(
        Tarifa.numero == existe_tarifa_eliminada.numero, 
        Tarifa.eliminado == 0
    ).first()
    
    if ya_existe_activa:
        raise HTTPException(status_code=400, detail="Ya existe una tarifa activa con este número")
    
    existe_tarifa_eliminada.eliminado = 0

    db.commit()
    db.refresh(existe_tarifa_eliminada)

    return existe_tarifa_eliminada

@router.patch("/{numero}/set-default", response_model=TarifaRespose)
def establecer_tarifa_default(numero: int, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Establece una tarifa como default. Automáticamente quita el default de las otras tarifas.
    Solo puede haber una tarifa con default = 1.
    """
    existe_tarifa = db.query(Tarifa).filter(Tarifa.numero == numero, Tarifa.eliminado == 0).first()

    if not existe_tarifa:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada o eliminada")
    
    # Quitar default de todas las tarifas
    db.query(Tarifa).filter(Tarifa.default == 1).update({Tarifa.default: 0})
    
    # Establecer esta tarifa como default
    existe_tarifa.default = 1

    db.commit()
    db.refresh(existe_tarifa)

    return existe_tarifa

