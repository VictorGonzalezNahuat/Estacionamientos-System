from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.security import hash_password
from database import get_db
from models.usuario import Usuario
from schemas.usuario import UsuarioCreate, UsuarioResponse

router = APIRouter()


@router.post("/", response_model=UsuarioResponse)
def crear_usuario(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    existe = db.query(Usuario).filter(Usuario.codigo == usuario.codigo).first()
    if existe:
        raise HTTPException(status_code=400, detail="El código ya existe")

    nuevo_usuario = Usuario(
        codigo=usuario.codigo,
        nombre=usuario.nombre,
        password_hash=hash_password(usuario.password),
        comision=usuario.comision,
        rol=usuario.rol,
        observaciones=usuario.observaciones,
    )

    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    return nuevo_usuario


@router.get("/", response_model=list[UsuarioResponse])
def listar_usuarios(db: Session = Depends(get_db)):
    return db.query(Usuario).all()
