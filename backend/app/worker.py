"""python -m app.worker (PRD §3.1, §9.3, §14).

BE-1 wires the heartbeat so /system/health has something real to report.
BE-3 adds the health sweeper (offline detection). BE-4 adds the
grace-deadline sweeper; notification/escalation sweepers are added in BE-5.
"""

import logging
import signal
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.alerts.lifecycle import GRACE_SLACK_SECONDS, confirm_event
from app.database.models import Device, DeviceHealthSnapshot, Event
from app.database.session import SessionLocal, engine
from app.monitoring.audit import log_audit
from app.monitoring.health import DEFAULT_EXPECTED_INTERVAL_S, is_offline
from app.monitoring.logging import configure_logging

logger = logging.getLogger(__name__)

TICK_SECONDS = 2
HEALTH_SWEEP_INTERVAL_SECONDS = 15
_shutdown = False


def _handle_shutdown(signum, frame) -> None:
    global _shutdown
    _shutdown = True


def _write_heartbeat() -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO worker_heartbeat (id, last_tick) VALUES (1, :now)
                ON CONFLICT (id) DO UPDATE SET last_tick = :now
                """
            ),
            {"now": datetime.now(timezone.utc)},
        )


def sweep_offline_devices(db: Session) -> int:
    """Mark devices OFFLINE when no heartbeat arrived in time (PRD §10).

    Idempotent: only flips devices not already OFFLINE, so it's safe to run
    from two worker instances at once (PRD §9.3).
    """
    flipped = 0
    devices = db.query(Device).filter(Device.status != "revoked").all()
    for device in devices:
        if device.health_state == "OFFLINE":
            continue
        if not is_offline(device.last_seen_at, DEFAULT_EXPECTED_INTERVAL_S):
            continue

        device.health_state = "OFFLINE"
        db.add(DeviceHealthSnapshot(device_id=device.id, computed_state="OFFLINE"))
        log_audit(
            db,
            action="device_health_offline",
            result="success",
            device_id=device.id,
            resource_type="device",
            resource_id=str(device.id),
        )
        db.commit()
        flipped += 1
    return flipped


def _sweep_offline_devices() -> None:
    db = SessionLocal()
    try:
        sweep_offline_devices(db)
    finally:
        db.close()


def sweep_grace_deadlines(db: Session) -> int:
    """PRD §5.1/§9.3: PENDING events past grace_deadline + GRACE_SLACK become
    CONFIRMED if nothing cancelled them first. `confirm_event` does the
    atomic claim, so this is safe with two worker instances running it."""
    deadline = datetime.now(timezone.utc) - timedelta(seconds=GRACE_SLACK_SECONDS)
    pending = db.execute(
        select(Event).where(Event.state == "PENDING", Event.grace_deadline < deadline)
    ).scalars().all()

    confirmed = 0
    for event in pending:
        if confirm_event(db, event, resolved_by="backend_timeout") is not None:
            confirmed += 1
    return confirmed


def _sweep_grace_deadlines() -> None:
    db = SessionLocal()
    try:
        sweep_grace_deadlines(db)
    finally:
        db.close()


def run() -> None:
    configure_logging()
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)
    logger.info("worker started")

    last_sweep = time.monotonic()
    while not _shutdown:
        try:
            _write_heartbeat()
        except Exception:
            logger.exception("heartbeat write failed")

        try:
            _sweep_grace_deadlines()
        except Exception:
            logger.exception("grace-deadline sweep failed")

        now = time.monotonic()
        if now - last_sweep >= HEALTH_SWEEP_INTERVAL_SECONDS:
            last_sweep = now
            try:
                _sweep_offline_devices()
            except Exception:
                logger.exception("health sweep failed")

        time.sleep(TICK_SECONDS)

    logger.info("worker stopped")


if __name__ == "__main__":
    run()
