"""Health sweeper: OFFLINE-by-absence-of-heartbeat (PRD §9.3, §10).

Run with DATABASE_URL pointing at a real Postgres with the be2 migration
applied; skipped automatically (see conftest.py) if unreachable.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select

from app.database.models import (
    Alert,
    AlertAction,
    AuditLog,
    CaregiverFeedback,
    Device,
    DeviceHealthSnapshot,
    Event,
    Notification,
)
from app.database.session import SessionLocal
from app.worker import sweep_offline_devices

STALE_SECONDS = 91  # > 3 * DEFAULT_EXPECTED_INTERVAL_S (30)


@pytest.fixture(autouse=True)
def clean_db():
    db = SessionLocal()
    for model in (
        CaregiverFeedback, AlertAction, Notification, Alert, Event,
        AuditLog, DeviceHealthSnapshot, Device,
    ):
        db.execute(delete(model))
    db.commit()
    db.close()
    yield


def _make_device(name: str, health_state: str, last_seen_at: datetime | None) -> Device:
    db = SessionLocal()
    device = Device(device_name=name, status="active", health_state=health_state,
                     last_seen_at=last_seen_at)
    db.add(device)
    db.commit()
    db.refresh(device)
    db.close()
    return device


def test_stale_healthy_device_flips_to_offline_with_snapshot_and_audit():
    stale_at = datetime.now(timezone.utc) - timedelta(seconds=STALE_SECONDS)
    device = _make_device("dev-stale", "HEALTHY", stale_at)

    db = SessionLocal()
    flipped = sweep_offline_devices(db)
    db.close()
    assert flipped == 1

    db = SessionLocal()
    refreshed = db.get(Device, device.id)
    assert refreshed.health_state == "OFFLINE"

    snapshots = db.execute(
        select(DeviceHealthSnapshot).where(DeviceHealthSnapshot.device_id == device.id)
    ).scalars().all()
    assert len(snapshots) == 1
    assert snapshots[0].computed_state == "OFFLINE"

    audits = db.execute(
        select(AuditLog).where(
            AuditLog.device_id == device.id, AuditLog.action == "device_health_offline"
        )
    ).scalars().all()
    assert len(audits) == 1
    db.close()


def test_recently_seen_device_is_untouched():
    recent_at = datetime.now(timezone.utc) - timedelta(seconds=5)
    device = _make_device("dev-fresh", "HEALTHY", recent_at)

    db = SessionLocal()
    flipped = sweep_offline_devices(db)
    db.close()
    assert flipped == 0

    db = SessionLocal()
    refreshed = db.get(Device, device.id)
    assert refreshed.health_state == "HEALTHY"
    snapshots = db.execute(
        select(DeviceHealthSnapshot).where(DeviceHealthSnapshot.device_id == device.id)
    ).scalars().all()
    assert len(snapshots) == 0
    db.close()


def test_already_offline_device_is_idempotent():
    stale_at = datetime.now(timezone.utc) - timedelta(seconds=STALE_SECONDS)
    device = _make_device("dev-already-offline", "OFFLINE", stale_at)

    db = SessionLocal()
    flipped_first = sweep_offline_devices(db)
    flipped_second = sweep_offline_devices(db)
    db.close()

    assert flipped_first == 0  # already OFFLINE before either sweep ran
    assert flipped_second == 0

    db = SessionLocal()
    snapshots = db.execute(
        select(DeviceHealthSnapshot).where(DeviceHealthSnapshot.device_id == device.id)
    ).scalars().all()
    assert len(snapshots) == 0
    audits = db.execute(
        select(AuditLog).where(AuditLog.device_id == device.id)
    ).scalars().all()
    assert len(audits) == 0
    db.close()
