from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.security import get_current_user
from database import get_db
from models.tarifa import Tarifa
from models.usuario import Usuario
from schemas.tarifa import TarifaBase, TarifaRespose

router = APIRouter()


@router.get("/default")
def tarifa_default(current_user: Usuario = Depends(get_current_user),db: Session = Depends(get_db)):
    return db.query(Tarifa).filter(Tarifa.default == 1).first()

@router.get("/", response_model=list[TarifaRespose])
def listar_tarifas(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Tarifa).filter(Tarifa.eliminado==0).all()

@router.get("/deleted", response_model=list[TarifaRespose])
def listar_tarifas_eliminadas(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Tarifa).filter(Tarifa.eliminado == 1).all()


@router.post("/", response_model=TarifaRespose)
def crear_tarifa( tarifa: TarifaBase,current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    existe = db.query(Tarifa).filter(Tarifa.numero == tarifa.numero).first()
    if existe:
        raise HTTPException(status_code=400, detail="El número de la tarifa ya existe")

    nueva_tarifa = Tarifa(
        numero=tarifa.numero,
        tipo_vehiculo=tarifa.tipo_vehiculo,
        hora=tarifa.hora,
        fraccion=tarifa.fraccion,
        medio_dia=tarifa.medio_dia,
        diario=tarifa.diario,
        observaciones=tarifa.observaciones
    )

    db.add(nueva_tarifa)
    db.commit()
    db.refresh(nueva_tarifa)

    return nueva_tarifa

@router.put("/{numero}", response_model=TarifaRespose)
def editar_tarifa(numero: int, tarifa: TarifaBase, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    existe_tarifa = db.query(Tarifa).filter(Tarifa.numero == numero, Tarifa.eliminado == 0).first()

    if not existe_tarifa:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada")

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
    
    existe_tarifa.eliminado = 1

    db.commit()
    db.refresh(existe_tarifa)

    return existe_tarifa

@router.patch("/{numero}/restore", response_model=TarifaRespose)
def restaurar_tarifa(numero: int, current_user: Usuario = Depends(get_current_user), db:Session=Depends(get_db)):
    existe_tarifa_eliminada = db.query(Tarifa).filter(Tarifa.numero == numero, Tarifa.eliminado == 1).first()

    if not existe_tarifa_eliminada:
        raise HTTPException(status_code=404, detail="Tarifa eliminada no encontrada o activa")
    
    existe_tarifa_eliminada.eliminado = 0

    db.commit()
    db.refresh(existe_tarifa_eliminada)

    return existe_tarifa_eliminada

