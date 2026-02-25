from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine

# Routers
from routes import auth, cortes_caja, current_estacionamientos, history_estacionamientos, state_estacionamientos, tarifas, turnos, usuarios

# from app.routes import usuarios, tarifas, turnos

app = FastAPI(
    title="Sistema de Estacionamiento",
    description="API para gestión de estacionamiento",
    version="0.1.0",
)

# CORS (luego Angular lo va a agradecer)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # luego se restringe
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Endpoint de prueba (health check)
@app.get("/")
def root():
    return {"status": "ok", "message": "API de Estacionamiento funcionando"}


@app.get("/db-test")
def db_test():
    with engine.connect() as conn:
        return {"db": "Conectado :)"}

app.include_router(auth.router)
app.include_router(usuarios.router, prefix="/usuarios", tags=["Usuarios"])
app.include_router(tarifas.router, prefix="/tarifas", tags=["Tarifas"])
app.include_router(turnos.router, prefix="/turnos", tags=["Turnos"])
app.include_router(current_estacionamientos.router, prefix="/estacionamiento", tags=["Estacionamiento"])
app.include_router(state_estacionamientos.router, prefix="/estacion", tags=["Estado_estacionamiento"])
app.include_router(cortes_caja.router, prefix="/corte-caja", tags=["Corte_de_cajas"])
app.include_router(history_estacionamientos.router, prefix="/history", tags=["Historial"])