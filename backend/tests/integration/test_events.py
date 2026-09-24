"""Event ingestion/lifecycle HTTP tests (PRD §7.2, §7.3, §5.1, §3.2, §15)."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.alerts.lifecycle import confirm_event
from app.api.deps import _LOGIN_ATTEMPTS
from app.api.main import app
from app.database.models import (
    Alert,
    AuditLog,
    CaregiverAssignment,
    CaregiverFeedback,
    Device,
    Event,
    EventEvidence,
    Notification,
    RefreshToken,
    Subject,
    User,
)
from app.database.session import SessionLocal
from app.security.device_keys import generate_device_key, hash_device_key, key_prefix
from app.security.passwords import hash_password

client = TestClient(app)

ADMIN_EMAIL = "admin@example.com"
CAREGIVER_EMAIL = "caregiver@example.com"
PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def clean_db():
    _LOGIN_ATTEMPTS.clear()
    client.cookies.clear()
    db = SessionLocal()
    for model in (
        CaregiverFeedback, Notification, Alert, EventEvidence, Event,
        AuditLog, RefreshToken, CaregiverAssignment, Device, Subject, User,
    ):
        db.execute(delete(model))
    db.commit()
    db.close()
    yield
    _LOGIN_ATTEMPTS.clear()


def _make_user(email: str, role: str) -> User:
    db = SessionLocal()
    user = User(email=email, name=role.title(), role=role, password_hash=hash_password(PASSWORD))
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def _login(email: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert resp.status_code == 200
    return resp.cookies["csrf_token"]


def _make_device(subject_id=None) -> tuple[Device, str]:
    db = SessionLocal()
    key = generate_device_key()
    device = Device(
        device_name=f"dev-{uuid.uuid4().hex[:8]}", api_key_hash=hash_device_key(key),
        api_key_prefix=key_prefix(key), status="active", subject_id=subject_id,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    db.close()
    return device, key


def _make_subject() -> Subject:
    db = SessionLocal()
    subject = Subject(display_name="Grandma")
    db.add(subject)
    db.commit()
    db.refresh(subject)
    db.close()
    return subject


def _assign_caregiver(caregiver_id, subject_id) -> None:
    db = SessionLocal()
    db.add(CaregiverAssignment(user_id=caregiver_id, subject_id=subject_id))
    db.commit()
    db.close()


def _event_payload(**overrides) -> dict:
    payload = {
        "client_event_id": str(uuid.uuid4()),
        "track_id": 2,
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "confidence": 0.87,
        "tier": "high",
        "grace_seconds": 20,
        "evidence": {"rapid_downward_motion": True, "orientation_change": 0.71, "summary": "fall-like"},
    }
    payload.update(overrides)
    return payload


def test_post_events_creates_pending_event_with_grace_deadline():
    device, key = _make_device()
    resp = client.post("/api/v1/events", json=_event_payload(), headers={"X-Device-Key": key})
    assert resp.status_code == 201
    body = resp.json()
    assert body["state"] == "PENDING"
    assert body["grace_deadline"]


def test_post_events_is_idempotent_on_client_event_id():
    device, key = _make_device()
    payload = _event_payload()
    first = client.post("/api/v1/events", json=payload, headers={"X-Device-Key": key})
    assert first.status_code == 201

    second = client.post("/api/v1/events", json=payload, headers={"X-Device-Key": key})
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]

    db = SessionLocal()
    count = db.query(Event).filter(Event.client_event_id == payload["client_event_id"]).count()
    assert count == 1
    db.close()


def test_post_events_rejects_oversized_string_field():
    device, key = _make_device()
    payload = _event_payload(evidence={"summary": "x" * 5000})
    resp = client.post("/api/v1/events", json=payload, headers={"X-Device-Key": key})
    assert resp.status_code == 422


def test_post_events_rejects_unknown_top_level_field():
    device, key = _make_device()
    payload = _event_payload()
    payload["not_a_real_field"] = "whatever"
    resp = client.post("/api/v1/events", json=payload, headers={"X-Device-Key": key})
    assert resp.status_code == 422


def test_post_events_ignores_device_id_and_subject_id_in_body():
    device, key = _make_device()
    other_device, _ = _make_device()
    payload = _event_payload(device_id=str(other_device.id), subject_id=str(uuid.uuid4()))
    resp = client.post("/api/v1/events", json=payload, headers={"X-Device-Key": key})
    # extra=forbid on the schema rejects unexpected fields outright
    assert resp.status_code == 422


def test_get_event_as_owning_device_and_not_other_device():
    device, key = _make_device()
    other_device, other_key = _make_device()
    created = client.post("/api/v1/events", json=_event_payload(), headers={"X-Device-Key": key}).json()

    resp = client.get(f"/api/v1/events/{created['id']}", headers={"X-Device-Key": key})
    assert resp.status_code == 200

    resp = client.get(f"/api/v1/events/{created['id']}", headers={"X-Device-Key": other_key})
    assert resp.status_code == 404


def test_get_event_scoped_caregiver_assigned_vs_unassigned():
    subject = _make_subject()
    device, key = _make_device(subject_id=subject.id)
    created = client.post("/api/v1/events", json=_event_payload(), headers={"X-Device-Key": key}).json()

    caregiver = _make_user(CAREGIVER_EMAIL, "caregiver")
    _assign_caregiver(caregiver.id, subject.id)
    _login(CAREGIVER_EMAIL)

    resp = client.get(f"/api/v1/events/{created['id']}")
    assert resp.status_code == 200

    other_subject = _make_subject()
    other_device, other_key = _make_device(subject_id=other_subject.id)
    other_event = client.post(
        "/api/v1/events", json=_event_payload(), headers={"X-Device-Key": other_key}
    ).json()

    resp = client.get(f"/api/v1/events/{other_event['id']}")
    assert resp.status_code == 404


def test_patch_event_confirmed_creates_alert_then_conflicts_on_repeat():
    device, key = _make_device()
    created = client.post("/api/v1/events", json=_event_payload(), headers={"X-Device-Key": key}).json()

    resp = client.patch(
        f"/api/v1/events/{created['id']}",
        json={"state": "CONFIRMED", "occurred_at": datetime.now(timezone.utc).isoformat()},
        headers={"X-Device-Key": key},
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "CONFIRMED"

    db = SessionLocal()
    alert = db.query(Alert).filter(Alert.event_id == uuid.UUID(created["id"])).one_or_none()
    assert alert is not None
    db.close()

    resp = client.patch(
        f"/api/v1/events/{created['id']}",
        json={"state": "CONFIRMED", "occurred_at": datetime.now(timezone.utc).isoformat()},
        headers={"X-Device-Key": key},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "invalid_transition"


def test_cancel_event_while_pending_then_conflict_after_confirmed():
    subject = _make_subject()
    device, key = _make_device(subject_id=subject.id)
    created = client.post("/api/v1/events", json=_event_payload(), headers={"X-Device-Key": key}).json()

    caregiver = _make_user(CAREGIVER_EMAIL, "caregiver")
    _assign_caregiver(caregiver.id, subject.id)
    csrf = _login(CAREGIVER_EMAIL)

    resp = client.post(f"/api/v1/events/{created['id']}/cancel", headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 200
    assert resp.json()["state"] == "CANCELLED"

    # New event: confirm it directly, then attempt a caregiver cancel -> conflict
    created2 = client.post("/api/v1/events", json=_event_payload(), headers={"X-Device-Key": key}).json()
    db = SessionLocal()
    event2 = db.get(Event, uuid.UUID(created2["id"]))
    confirm_event(db, event2, resolved_by="backend_timeout")
    db.close()

    resp = client.post(f"/api/v1/events/{created2['id']}/cancel", headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "event_already_confirmed"


def test_list_events_filters_by_state_and_subject_with_caregiver_scoping():
    subject = _make_subject()
    other_subject = _make_subject()
    device, key = _make_device(subject_id=subject.id)
    other_device, other_key = _make_device(subject_id=other_subject.id)

    client.post("/api/v1/events", json=_event_payload(), headers={"X-Device-Key": key})
    client.post("/api/v1/events", json=_event_payload(), headers={"X-Device-Key": other_key})

    caregiver = _make_user(CAREGIVER_EMAIL, "caregiver")
    _assign_caregiver(caregiver.id, subject.id)
    _login(CAREGIVER_EMAIL)

    resp = client.get("/api/v1/events", params={"state": "PENDING"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["subject_id"] == str(subject.id)
