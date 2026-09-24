"""GET /system/health (PRD §7.2): public liveness/readiness, no sensitive data."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.database.session import engine

router = APIRouter(tags=["system"])


def get_engine() -> Engine:
    return engine


@router.get("/system/health")
def health(response: Response, db_engine: Engine = Depends(get_engine)) -> dict:
    db_status = "up"
    worker_last_tick: str | None = None

    try:
        with db_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            row = conn.execute(
                text("SELECT last_tick FROM worker_heartbeat WHERE id = 1")
            ).first()
            if row is not None:
                worker_last_tick = row[0].isoformat()
    except Exception:
        db_status = "down"

    body = {
        "status": "ok" if db_status == "up" else "down",
        "db": db_status,
        "worker_last_tick": worker_last_tick,
        "server_time": datetime.now(timezone.utc).isoformat(),
    }
    response.status_code = (
        status.HTTP_200_OK if db_status == "up" else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return body
