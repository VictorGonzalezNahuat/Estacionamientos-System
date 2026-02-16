from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.security import create_access_token, verify_password
from database import get_db
from models.usuario import Usuario
from schemas.auth import LoginRequest

from fastapi.security import OAuth2PasswordRequestForm


router = APIRouter(prefix="/auth", tags=["Auth"])


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



