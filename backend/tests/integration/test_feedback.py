"""/caregiver-feedback integration tests (PRD §5.3, §7.2, §15)."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.api.deps import _LOGIN_ATTEMPTS
from app.api.main import app
from app.database.models import (
    Alert,
    AlertAction,
    AuditLog,
    CaregiverAssignment,
    CaregiverFeedback,
    Device,
    Event,
    Notification,
    RefreshToken,
    Subject,
    User,
)
from app.database.session import SessionLocal
from app.security.device_keys import generate_device_key, hash_device_key, key_prefix
from app.security.passwords import hash_password

client = TestClient(app)
PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def clean_db():
    _LOGIN_ATTEMPTS.clear()
    client.cookies.clear()
    db = SessionLocal()
    for model in (
        CaregiverFeedback, AlertAction, Notification, Alert, Event,
        AuditLog, RefreshToken, CaregiverAssignment, Device, Subject, User,
    ):
        db.execute(delete(model))
    db.commit()
    db.close()
    yield
    _LOGIN_ATTEMPTS.clear()


def _make_user(email: str, role: str) -> User:
    db = SessionLocal()
    user = User(email=email, name=role.title(), role=role,
                password_hash=hash_password(PASSWORD), must_change_password=False)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def _login(email: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert resp.status_code == 200
    return resp.cookies["csrf_token"]


def _make_event(subject_id=None) -> uuid.UUID:
    db = SessionLocal()
    key = generate_device_key()
    device = Device(device_name=f"dev-{uuid.uuid4().hex[:8]}", api_key_hash=hash_device_key(key),
                     api_key_prefix=key_prefix(key), status="active", subject_id=subject_id)
    db.add(device)
    db.commit()
    now = datetime.now(timezone.utc)
    event = Event(client_event_id=uuid.uuid4(), device_id=device.id, subject_id=subject_id,
                  detected_at=now, grace_seconds=20, grace_deadline=now + timedelta(seconds=20))
    db.add(event)
    db.commit()
    event_id = event.id
    db.close()
    return event_id


def test_caregiver_create_then_upsert_feedback():
    db = SessionLocal()
    subject = Subject(display_name="Assigned")
    db.add(subject)
    db.commit()
    caregiver = _make_user("caregiver@example.com", "caregiver")
    db.add(CaregiverAssignment(user_id=caregiver.id, subject_id=subject.id))
    db.commit()
    subject_id = subject.id
    db.close()

    event_id = _make_event(subject_id=subject_id)
    csrf = _login("caregiver@example.com")

    resp = client.post(
        "/api/v1/caregiver-feedback",
        json={"event_id": str(event_id), "label": "TRUE_FALL"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    assert resp.json()["label"] == "TRUE_FALL"

    resp = client.post(
        "/api/v1/caregiver-feedback",
        json={"event_id": str(event_id), "label": "FALSE_POSITIVE"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    assert resp.json()["label"] == "FALSE_POSITIVE"

    db = SessionLocal()
    rows = db.query(CaregiverFeedback).filter(CaregiverFeedback.event_id == event_id).all()
    assert len(rows) == 1
    db.close()


def test_caregiver_feedback_on_unassigned_event_404():
    db = SessionLocal()
    subject = Subject(display_name="Other")
    db.add(subject)
    db.commit()
    subject_id = subject.id
    db.close()
    _make_user("caregiver2@example.com", "caregiver")
    event_id = _make_event(subject_id=subject_id)
    csrf = _login("caregiver2@example.com")

    resp = client.post(
        "/api/v1/caregiver-feedback",
        json={"event_id": str(event_id), "label": "TRUE_FALL"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 404


def test_invalid_label_rejected():
    _make_user("admin@example.com", "admin")
    csrf = _login("admin@example.com")
    event_id = _make_event()

    resp = client.post(
        "/api/v1/caregiver-feedback",
        json={"event_id": str(event_id), "label": "NOT_A_LABEL"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 422


def test_list_feedback_access_by_role():
    _make_user("admin2@example.com", "admin")
    csrf = _login("admin2@example.com")
    event_id = _make_event()
    client.post(
        "/api/v1/caregiver-feedback",
        json={"event_id": str(event_id), "label": "UNCERTAIN"},
        headers={"X-CSRF-Token": csrf},
    )

    resp = client.get("/api/v1/caregiver-feedback")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    _make_user("caregiver3@example.com", "caregiver")
    _login("caregiver3@example.com")
    resp = client.get("/api/v1/caregiver-feedback")
    assert resp.status_code == 403

    client.post("/api/v1/auth/logout")
    _make_user("mleng@example.com", "ml_engineer")
    _login("mleng@example.com")
    resp = client.get("/api/v1/caregiver-feedback")
    assert resp.status_code == 200
    assert resp.json()["items"][0]["caregiver_id"] is None
