import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.security import create_access_token, get_current_user, verify_password
from database import get_db
from models.usuario import Usuario

from fastapi.security import OAuth2PasswordRequestForm


router = APIRouter(prefix="/auth", tags=["Auth"])


def _parse_roles(rol_value):
    if rol_value is None:
        return {}
    if isinstance(rol_value, dict):
        return rol_value
    if isinstance(rol_value, str):
        try:
            parsed = json.loads(rol_value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):

    usuario = db.query(Usuario).filter(Usuario.codigo == int(form_data.username)).first()

    if not usuario or not verify_password(form_data.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    access_token = create_access_token(data={"sub": str(usuario.id)})

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/me")
def me(current_user: Usuario = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "codigo": current_user.codigo,
        "nombre": current_user.nombre,
        "rol": current_user.rol
    }


@router.get("/verify-admin")
def verify_admin_role(current_user: Usuario = Depends(get_current_user)):
    roles = _parse_roles(current_user.rol)
    return {"admin": bool(roles.get("admin", False))}


@router.get("/verify-encargado")
def verify_encargado_role(current_user: Usuario = Depends(get_current_user)):
    roles = _parse_roles(current_user.rol)
    return {"encargado": bool(roles.get("encargado", False))}



