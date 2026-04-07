from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.sync_scheduler import start_sync_scheduler, stop_sync_scheduler
from database import engine

# Routers
from routes import auth, configuracion, cortes_caja, current_estacionamientos, history_estacionamientos, mensajes, state_estacionamientos, sync, tarifas, turnos, usuarios, pagos, facturacion

# from app.routes import usuarios, tarifas, turnos

app = FastAPI(
    title="Sistema de Estacionamiento",
    description="API para gestión de estacionamiento",
    version="0.1.0",
)


@app.on_event("startup")
async def on_startup() -> None:
    start_sync_scheduler()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await stop_sync_scheduler()

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
app.include_router(mensajes.router, prefix="/mensajes", tags=["Mensajes"])
app.include_router(sync.router, prefix="/sync", tags=["Sync"])
app.include_router(configuracion.router, prefix="/config", tags=["Configuracion"])
app.include_router(pagos.router, prefix="/pagos", tags=["Pagos"])
app.include_router(facturacion.router, prefix="/facturacion", tags=["Facturacion"])