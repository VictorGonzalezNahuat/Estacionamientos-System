from datetime import datetime
from threading import Lock

from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session

from models.current_estacionamiento import CurrentEstacionamiento
from models.history_estacionamiento import HistoryEstacionamiento
from models.ticket_cancelado import TicketCancelado
from models.state_estacionamiento import StateEstacionamiento
from models.sync_state import SyncState
from models.tarifa import Tarifa
from models.turno import Turno
from models.usuario import Usuario


# Mensajes queda fuera por regla de negocio actual.
SYNC_MODELS = [
    Usuario,
    Tarifa,
    Turno,
    CurrentEstacionamiento,
    HistoryEstacionamiento,
    TicketCancelado,
    StateEstacionamiento,
]

_SYNC_LOCK = Lock()


def _ensure_sync_state_table(db: Session) -> None:
    SyncState.__table__.create(bind=db.get_bind(), checkfirst=True)


def _row_to_dict(row: object) -> dict:
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def _sync_deleted_rows(local_db: Session, cloud_db: Session, model: type, pk_name: str) -> int:
    local_ids = {row[0] for row in local_db.query(getattr(model, pk_name)).all()}
    cloud_ids = {row[0] for row in cloud_db.query(getattr(model, pk_name)).all()}

    ids_to_delete = cloud_ids - local_ids
    if not ids_to_delete:
        return 0

    deleted = (
        cloud_db.query(model)
        .filter(getattr(model, pk_name).in_(ids_to_delete))
        .delete(synchronize_session=False)
    )
    return int(deleted)


def _upsert_table_incremental(local_db: Session, cloud_db: Session, model: type) -> dict:
    table_name = model.__tablename__
    mapper = inspect(model)
    pk_column = mapper.primary_key[0]
    pk_name = pk_column.name
    has_updated_at = "updated_at" in mapper.columns

    state = local_db.query(SyncState).filter(SyncState.table_name == table_name).first()
    if state is None:
        state = SyncState(table_name=table_name)
        local_db.add(state)
        local_db.commit()

    query = local_db.query(model)
    if has_updated_at and state.last_success_at is not None:
        query = query.filter(getattr(model, "updated_at") > state.last_success_at)

    if has_updated_at:
        query = query.order_by(getattr(model, "updated_at").asc(), getattr(model, pk_name).asc())
    else:
        query = query.order_by(getattr(model, pk_name).asc())

    inserted = 0
    updated = 0
    deleted = 0
    local_rows = query.all()

    for local_row in local_rows:
        row_data = _row_to_dict(local_row)
        pk_value = getattr(local_row, pk_name)

        cloud_row = cloud_db.get(model, pk_value)
        if cloud_row is None:
            cloud_db.add(model(**row_data))
            inserted += 1
            continue

        changed = False
        for field, value in row_data.items():
            if getattr(cloud_row, field) != value:
                setattr(cloud_row, field, value)
                changed = True

        if changed:
            updated += 1

    deleted = _sync_deleted_rows(local_db=local_db, cloud_db=cloud_db, model=model, pk_name=pk_name)
    cloud_db.commit()

    now = datetime.utcnow()
    state.last_sync_at = now
    state.last_success_at = now
    state.last_error = None
    local_db.commit()

    return {
        "table": table_name,
        "records_local": len(local_rows),
        "inserted": inserted,
        "updated": updated,
        "deleted": deleted,
        "synced_at": now.isoformat(),
    }


def run_incremental_sync(local_db: Session, cloud_db: Session, non_blocking: bool = False) -> dict:
    acquired = _SYNC_LOCK.acquire(blocking=not non_blocking)
    if not acquired:
        return {
            "mode": "incremental_upsert_by_updated_at",
            "status": "skipped",
            "reason": "sync_already_running",
            "excluded_tables": ["mensajes"],
            "started_at": datetime.utcnow().isoformat(),
            "results": [],
        }

    try:
        _ensure_sync_state_table(local_db)

        started_at = datetime.utcnow().isoformat()
        results: list[dict] = []

        for model in SYNC_MODELS:
            table_name = model.__tablename__
            try:
                table_result = _upsert_table_incremental(local_db=local_db, cloud_db=cloud_db, model=model)
                table_result["status"] = "ok"
                results.append(table_result)
            except Exception as exc:
                cloud_db.rollback()
                local_db.rollback()

                state = local_db.query(SyncState).filter(SyncState.table_name == table_name).first()
                if state is None:
                    state = SyncState(table_name=table_name)
                    local_db.add(state)

                state.last_error = str(exc)[:500]
                state.last_sync_at = datetime.utcnow()
                local_db.commit()

                results.append(
                    {
                        "table": table_name,
                        "status": "error",
                        "error": str(exc),
                    }
                )

        return {
            "mode": "incremental_upsert_by_updated_at",
            "excluded_tables": ["mensajes"],
            "started_at": started_at,
            "results": results,
        }
    finally:
        _SYNC_LOCK.release()
