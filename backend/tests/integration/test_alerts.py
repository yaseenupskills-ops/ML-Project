"""/alerts integration tests (PRD §5.2, §7.2, §15)."""

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


def _make_confirmed_alert(subject_id=None) -> tuple:
    db = SessionLocal()
    key = generate_device_key()
    device = Device(device_name=f"dev-{uuid.uuid4().hex[:8]}", api_key_hash=hash_device_key(key),
                     api_key_prefix=key_prefix(key), status="active", subject_id=subject_id)
    db.add(device)
    db.commit()
    now = datetime.now(timezone.utc)
    event = Event(client_event_id=uuid.uuid4(), device_id=device.id, subject_id=subject_id,
                  detected_at=now, tier="high", grace_seconds=20,
                  grace_deadline=now + timedelta(seconds=20))
    db.add(event)
    db.commit()
    alert = confirm_event(db, event, resolved_by="backend_timeout")
    alert_id, event_id = alert.id, event.id
    db.close()
    return alert_id, event_id


def test_admin_acknowledge_then_dismiss_fails_409():
    _make_user("admin@example.com", "admin")
    csrf = _login("admin@example.com")
    alert_id, _ = _make_confirmed_alert()

    resp = client.post(f"/api/v1/alerts/{alert_id}/acknowledge", json={},
                        headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACKNOWLEDGED"

    resp = client.post(f"/api/v1/alerts/{alert_id}/dismiss", json={},
                        headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 409


def test_escalate_then_acknowledge_succeeds():
    _make_user("admin2@example.com", "admin")
    csrf = _login("admin2@example.com")
    alert_id, _ = _make_confirmed_alert()

    resp = client.post(f"/api/v1/alerts/{alert_id}/escalate", json={},
                        headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ESCALATED"

    resp = client.post(f"/api/v1/alerts/{alert_id}/acknowledge", json={},
                        headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACKNOWLEDGED"


def test_caregiver_can_act_on_assigned_alert_and_404_on_unassigned():
    db = SessionLocal()
    subject_assigned = Subject(display_name="Assigned")
    subject_other = Subject(display_name="Other")
    db.add_all([subject_assigned, subject_other])
    db.commit()
    assigned_id, other_id = subject_assigned.id, subject_other.id
    caregiver = _make_user("caregiver@example.com", "caregiver")
    db.add(CaregiverAssignment(user_id=caregiver.id, subject_id=assigned_id))
    db.commit()
    db.close()

    alert_assigned, _ = _make_confirmed_alert(subject_id=assigned_id)
    alert_other, _ = _make_confirmed_alert(subject_id=other_id)

    csrf = _login("caregiver@example.com")

    resp = client.post(f"/api/v1/alerts/{alert_assigned}/acknowledge", json={},
                        headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 200

    resp = client.get(f"/api/v1/alerts/{alert_other}")
    assert resp.status_code == 404


def test_bulk_alerts_partial_success():
    _make_user("admin3@example.com", "admin")
    csrf = _login("admin3@example.com")
    alert_id, _ = _make_confirmed_alert()
    bogus_id = str(uuid.uuid4())

    resp = client.post(
        "/api/v1/alerts/bulk",
        json={"action": "acknowledge", "alert_ids": [str(alert_id), bogus_id]},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    results = {r["alert_id"]: r["status"] for r in resp.json()["results"]}
    assert results[str(alert_id)] == "ok"
    assert results[bogus_id] == "error"


def test_export_csv_returns_header_and_row():
    _make_user("admin4@example.com", "admin")
    _login("admin4@example.com")
    _make_confirmed_alert()

    resp = client.get("/api/v1/alerts/export.csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    lines = resp.text.strip().splitlines()
    assert lines[0] == "datetime,subject,device,confidence,tier,state,status,acknowledged_by,response_time_s,model_version"
    assert len(lines) >= 2


def test_ml_engineer_list_is_masked():
    _make_user("admin5@example.com", "admin")
    admin_csrf = _login("admin5@example.com")
    subject = Subject(display_name="Should Not Appear")
    db = SessionLocal()
    db.add(subject)
    db.commit()
    subject_id = subject.id
    db.close()
    _make_confirmed_alert(subject_id=subject_id)

    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": admin_csrf})
    _make_user("mleng@example.com", "ml_engineer")
    _login("mleng@example.com")

    resp = client.get("/api/v1/alerts")
    assert resp.status_code == 200
    body_text = resp.text
    assert "Should Not Appear" not in body_text
