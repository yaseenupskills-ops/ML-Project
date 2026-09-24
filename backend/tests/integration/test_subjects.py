"""Subjects RBAC/masking integration tests (PRD §7.2, §4, §15)."""

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
from app.security.passwords import hash_password

client = TestClient(app)

ADMIN_EMAIL = "admin@example.com"
CAREGIVER_EMAIL = "caregiver@example.com"
ML_EMAIL = "ml@example.com"
OPERATOR_EMAIL = "operator@example.com"
PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def clean_db():
    _LOGIN_ATTEMPTS.clear()
    client.cookies.clear()
    db = SessionLocal()
    # Children before parents: Event/Device reference Subject, Alert/etc
    # reference User, so a leftover row from another test file must not
    # block these deletes.
    for model in (
        CaregiverFeedback, AlertAction, Notification, Alert, Event, Device,
        AuditLog, RefreshToken, CaregiverAssignment, User, Subject,
    ):
        db.execute(delete(model))
    db.commit()
    db.close()
    yield
    _LOGIN_ATTEMPTS.clear()


def _make_user(email: str, role: str, status: str = "active") -> User:
    db = SessionLocal()
    user = User(email=email, name=role.title(), role=role, status=status,
                password_hash=hash_password(PASSWORD), must_change_password=False)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def _make_subject(display_name: str = "Subject A", location_label: str | None = "Living room") -> Subject:
    db = SessionLocal()
    subject = Subject(display_name=display_name, location_label=location_label)
    db.add(subject)
    db.commit()
    db.refresh(subject)
    db.close()
    return subject


def _assign(user_id, subject_id) -> None:
    db = SessionLocal()
    db.add(CaregiverAssignment(user_id=user_id, subject_id=subject_id))
    db.commit()
    db.close()


def _login(email: str) -> None:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert resp.status_code == 200
    return resp


def test_admin_can_create_list_get_update_subject():
    admin = _make_user(ADMIN_EMAIL, "admin")
    login_resp = _login(ADMIN_EMAIL)
    csrf = login_resp.cookies["csrf_token"]

    resp = client.post(
        "/api/v1/subjects",
        json={"display_name": "Subject A", "location_label": "Living room"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201
    subject_id = resp.json()["id"]

    resp = client.get("/api/v1/subjects")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["display_name"] == "Subject A"

    resp = client.get(f"/api/v1/subjects/{subject_id}")
    assert resp.status_code == 200
    assert resp.json()["location_label"] == "Living room"

    resp = client.patch(
        f"/api/v1/subjects/{subject_id}",
        json={"status": "inactive"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "inactive"


def test_caregiver_sees_only_assigned_subjects_and_gets_404_for_others():
    caregiver = _make_user(CAREGIVER_EMAIL, "caregiver")
    assigned = _make_subject("Assigned Subject")
    other = _make_subject("Other Subject")
    _assign(caregiver.id, assigned.id)

    _login(CAREGIVER_EMAIL)

    resp = client.get("/api/v1/subjects")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["id"] == str(assigned.id)

    resp = client.get(f"/api/v1/subjects/{assigned.id}")
    assert resp.status_code == 200

    resp = client.get(f"/api/v1/subjects/{other.id}")
    assert resp.status_code == 404

    # Caregiver cannot create/update (admin-only endpoints).
    resp = client.post("/api/v1/subjects", json={"display_name": "X"})
    assert resp.status_code == 403


def test_ml_engineer_responses_are_masked():
    _make_user(ML_EMAIL, "ml_engineer")
    subject = _make_subject("Secret Name", "Secret Location")

    _login(ML_EMAIL)

    resp = client.get("/api/v1/subjects")
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert "display_name" not in item
    assert "location_label" not in item
    assert set(item.keys()) == {"id", "status"}

    resp = client.get(f"/api/v1/subjects/{subject.id}")
    assert resp.status_code == 200
    assert "display_name" not in resp.json()
    assert "location_label" not in resp.json()


def test_operator_forbidden_from_subjects():
    _make_user(OPERATOR_EMAIL, "operator")
    subject = _make_subject()

    _login(OPERATOR_EMAIL)

    resp = client.get("/api/v1/subjects")
    assert resp.status_code == 403

    resp = client.get(f"/api/v1/subjects/{subject.id}")
    assert resp.status_code == 403
