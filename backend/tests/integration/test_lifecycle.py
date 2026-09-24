"""Event/alert lifecycle correctness (PRD §5.1, §5.2, §9.1): exactly-once
confirmation under a race, notification recipient selection, cancel rules."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete

from app.alerts.lifecycle import confirm_event, cancel_event
from app.database.models import (
    Alert,
    AuditLog,
    CaregiverAssignment,
    Device,
    Event,
    Notification,
    Subject,
    User,
)
from app.database.session import SessionLocal
from app.security.device_keys import generate_device_key, hash_device_key, key_prefix
from app.security.passwords import hash_password


@pytest.fixture(autouse=True)
def clean_db():
    db = SessionLocal()
    for model in (Notification, Alert, Event, AuditLog, CaregiverAssignment, Device, Subject, User):
        db.execute(delete(model))
    db.commit()
    db.close()
    yield


def _make_device(db, subject_id=None) -> Device:
    key = generate_device_key()
    device = Device(
        device_name=f"dev-{uuid.uuid4().hex[:8]}",
        api_key_hash=hash_device_key(key),
        api_key_prefix=key_prefix(key),
        status="active",
        subject_id=subject_id,
    )
    db.add(device)
    db.commit()
    return device


def _make_subject(db) -> Subject:
    subject = Subject(display_name="Subject")
    db.add(subject)
    db.commit()
    return subject


def _make_caregiver(db, subject_id, notify_email=True) -> User:
    user = User(email=f"c-{uuid.uuid4().hex[:8]}@example.com", name="Caregiver", role="caregiver",
                password_hash=hash_password("x" * 12), notify_email=notify_email)
    db.add(user)
    db.commit()
    db.add(CaregiverAssignment(user_id=user.id, subject_id=subject_id))
    db.commit()
    return user


def _make_event(db, device_id, subject_id=None, grace_seconds=20) -> Event:
    now = datetime.now(timezone.utc)
    event = Event(
        client_event_id=uuid.uuid4(),
        device_id=device_id,
        subject_id=subject_id,
        detected_at=now,
        grace_seconds=grace_seconds,
        grace_deadline=now + timedelta(seconds=grace_seconds),
    )
    db.add(event)
    db.commit()
    return event


def test_confirm_event_creates_alert_and_queues_notifications_to_assigned_caregiver():
    db = SessionLocal()
    subject = _make_subject(db)
    caregiver = _make_caregiver(db, subject.id)
    device = _make_device(db, subject_id=subject.id)
    event = _make_event(db, device.id, subject_id=subject.id)

    alert = confirm_event(db, event, resolved_by="backend_timeout")

    assert alert is not None
    assert alert.status == "OPEN"
    db.refresh(event)
    assert event.state == "CONFIRMED"
    assert event.resolved_by == "backend_timeout"

    notifications = db.query(Notification).filter(Notification.alert_id == alert.id).all()
    assert len(notifications) == 1
    assert notifications[0].recipient_user_id == caregiver.id
    assert notifications[0].status == "QUEUED"
    db.close()


def test_confirm_event_falls_back_to_admins_when_no_assigned_caregiver():
    db = SessionLocal()
    subject = _make_subject(db)
    admin = User(email="admin@example.com", name="Admin", role="admin",
                 password_hash=hash_password("x" * 12))
    db.add(admin)
    db.commit()
    device = _make_device(db, subject_id=subject.id)
    event = _make_event(db, device.id, subject_id=subject.id)

    alert = confirm_event(db, event, resolved_by="backend_timeout")

    notifications = db.query(Notification).filter(Notification.alert_id == alert.id).all()
    assert len(notifications) == 1
    assert notifications[0].recipient_user_id == admin.id
    db.close()


def test_confirm_event_excludes_caregiver_with_notify_email_false():
    db = SessionLocal()
    subject = _make_subject(db)
    _make_caregiver(db, subject.id, notify_email=False)
    admin = User(email="admin2@example.com", name="Admin", role="admin",
                 password_hash=hash_password("x" * 12))
    db.add(admin)
    db.commit()
    device = _make_device(db, subject_id=subject.id)
    event = _make_event(db, device.id, subject_id=subject.id)

    alert = confirm_event(db, event, resolved_by="backend_timeout")
    notifications = db.query(Notification).filter(Notification.alert_id == alert.id).all()
    # notify_email=false caregiver excluded -> falls back to admin
    assert len(notifications) == 1
    assert notifications[0].recipient_user_id == admin.id
    db.close()


def test_confirm_event_is_exactly_once_under_concurrent_claim():
    """Simulates two workers racing on the same PENDING event: only the
    first `confirm_event` call should create an alert."""
    db1 = SessionLocal()
    db2 = SessionLocal()
    device = _make_device(db1)
    event = _make_event(db1, device.id)

    event_for_db2 = db2.get(Event, event.id)

    first = confirm_event(db1, event, resolved_by="backend_timeout")
    second = confirm_event(db2, event_for_db2, resolved_by="edge")

    assert first is not None
    assert second is None  # lost the race, no duplicate alert

    db3 = SessionLocal()
    alerts = db3.query(Alert).filter(Alert.event_id == event.id).all()
    assert len(alerts) == 1
    db1.close()
    db2.close()
    db3.close()


def test_cancel_event_succeeds_while_pending():
    db = SessionLocal()
    device = _make_device(db)
    event = _make_event(db, device.id)

    assert cancel_event(db, event, resolved_by="caregiver") is True
    db.refresh(event)
    assert event.state == "CANCELLED"
    assert event.resolved_by == "caregiver"
    db.close()


def test_cancel_event_fails_once_already_confirmed():
    db = SessionLocal()
    device = _make_device(db)
    event = _make_event(db, device.id)

    confirm_event(db, event, resolved_by="backend_timeout")
    db.refresh(event)
    assert event.state == "CONFIRMED"

    assert cancel_event(db, event, resolved_by="caregiver") is False
    db.refresh(event)
    assert event.state == "CONFIRMED"  # unchanged, late cancel had no effect
    db.close()
