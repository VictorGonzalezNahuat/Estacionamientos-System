from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.security import get_current_admin, get_current_user, hash_password
from database import get_db
from models.current_estacionamiento import CurrentEstacionamiento
from models.history_estacionamiento import HistoryEstacionamiento
from models.usuario import Usuario
from schemas.usuario import UsuarioCreate, UsuarioResponse, UsuarioUpdate

router = APIRouter()


@router.post("/", response_model=UsuarioResponse)
def crear_usuario(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    existe = db.query(Usuario).filter(Usuario.codigo == usuario.codigo).first()
    if existe:
        raise HTTPException(status_code=400, detail="El código ya existe")

    rol_json = usuario.rol.model_dump_json() if usuario.rol else None

    nuevo_usuario = Usuario(
        codigo=usuario.codigo,
        nombre=usuario.nombre,
        password_hash=hash_password(usuario.password),
        comision=usuario.comision,
        rol=rol_json,
        observaciones=usuario.observaciones,
        email=usuario.email,
    )

    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    return nuevo_usuario


@router.get("/", response_model=list[UsuarioResponse])
def listar_usuarios(db: Session = Depends(get_db)):
    return db.query(Usuario).all()


@router.put("/{codigo}", response_model=UsuarioResponse)
def editar_usuario(codigo: int, usuario: UsuarioUpdate, current_user: Usuario = Depends(get_current_user),  db: Session = Depends(get_db)):
    usuario_db = db.query(Usuario).filter(Usuario.codigo == codigo).first()
    if not usuario_db:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    cambios = usuario.model_dump(exclude_unset=True)

    if "rol" in cambios:
        cambios["rol"] = usuario.rol.model_dump_json() if usuario.rol else None

    for campo, valor in cambios.items():
        setattr(usuario_db, campo, valor)

    db.commit()
    db.refresh(usuario_db)

    return usuario_db


@router.delete("/{codigo}")
def eliminar_usuario(codigo: int, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    usuario_db = db.query(Usuario).filter(Usuario.codigo == codigo).first()
    if not usuario_db:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    tiene_vehiculos_current = (
        db.query(CurrentEstacionamiento)
        .filter(CurrentEstacionamiento.encargado_id == usuario_db.id)
        .first()
    )

    if tiene_vehiculos_current:
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar el usuario: tiene vehículos en current_estacionamiento",
        )

    tiene_vehiculos_history = (
        db.query(HistoryEstacionamiento)
        .filter(HistoryEstacionamiento.encargado_id == usuario_db.id)
        .first()
    )

    if tiene_vehiculos_history:
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar el usuario: tiene vehículos en history_estacionamiento",
        )

    db.delete(usuario_db)
    db.commit()

    return {"mensaje": "Usuario eliminado correctamente"}


@router.patch("/{usuario_id}/reset-password")
def reset_password(
    codigo_usuario: int,
    nueva_pass: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_admin),
):
    user = db.query(Usuario).filter(Usuario.codigo == codigo_usuario).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.password_hash = hash_password(nueva_pass)
    db.commit()
    return {"msg": "Contraseña actualizada por el administrador"}
