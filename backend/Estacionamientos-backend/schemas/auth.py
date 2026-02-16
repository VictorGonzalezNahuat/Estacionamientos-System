# schemas/auth.py
from pydantic import BaseModel


class LoginRequest(BaseModel):
    codigo: int
    password: str

class ConfirmPasswordRequest(BaseModel):
    password: str
