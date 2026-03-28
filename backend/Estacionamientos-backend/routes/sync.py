from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.security import get_current_admin, get_current_user
from core.sync_scheduler import get_sync_scheduler_status
from core.sync_service import run_incremental_sync
from database import get_cloud_db, get_db
from models.usuario import Usuario

router = APIRouter()


@router.post("/run")
def run_sync(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
    cloud_db: Session = Depends(get_cloud_db),
):
    return run_incremental_sync(local_db=db, cloud_db=cloud_db)


@router.get("/scheduler-status")
def scheduler_status(current_user: Usuario = Depends(get_current_user)):
    return get_sync_scheduler_status()
