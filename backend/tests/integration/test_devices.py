"""Devices/cameras/heartbeat integration tests (PRD §7.2, §8.2, §10, §15)."""

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
    Camera,
    Device,
    DeviceHealthSnapshot,
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
PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def clean_db():
    _LOGIN_ATTEMPTS.clear()
    client.cookies.clear()
    db = SessionLocal()
    for model in (
        CaregiverFeedback, AlertAction, Notification, Alert, Event,
        AuditLog, DeviceHealthSnapshot, Camera, Device,
        RefreshToken, CaregiverAssignment, User, Subject,
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


def _login_admin() -> str:
    _make_user(ADMIN_EMAIL, "admin")
    resp = client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD})
    assert resp.status_code == 200
    return resp.cookies["csrf_token"]


def _register_device(csrf: str, name: str = "LivingRoom-Cam-01") -> dict:
    resp = client.post(
        "/api/v1/devices", json={"device_name": name}, headers={"X-CSRF-Token": csrf}
    )
    assert resp.status_code == 201
    return resp.json()


def test_device_key_returned_once_and_not_retrievable_again():
    csrf = _login_admin()
    created = _register_device(csrf)
    assert len(created["api_key"]) > 20

    resp = client.get(f"/api/v1/devices/{created['id']}")
    assert resp.status_code == 200
    assert "api_key" not in resp.json()


def test_heartbeat_healthy_case_updates_state():
    csrf = _login_admin()
    created = _register_device(csrf)

    resp = client.post(
        "/api/v1/devices/me/heartbeat",
        json={"camera_status": "online", "camera_fps": 15, "model_loaded": True,
              "backend_connectivity": "connected", "cpu_pct": 40, "mem_pct": 50},
        headers={"X-Device-Key": created["api_key"]},
    )
    assert resp.status_code == 200
    assert resp.json()["expected_interval_s"] == 30

    device_resp = client.get(f"/api/v1/devices/{created['id']}")
    assert device_resp.json()["health"]["state"] == "HEALTHY"


def test_heartbeat_degraded_case_low_fps():
    csrf = _login_admin()
    created = _register_device(csrf)

    client.post(
        "/api/v1/devices/me/heartbeat",
        json={"camera_status": "online", "camera_fps": 2, "model_loaded": True},
        headers={"X-Device-Key": created["api_key"]},
    )
    device_resp = client.get(f"/api/v1/devices/{created['id']}")
    assert device_resp.json()["health"]["state"] == "DEGRADED"


def test_heartbeat_error_case_model_not_loaded():
    csrf = _login_admin()
    created = _register_device(csrf)

    client.post(
        "/api/v1/devices/me/heartbeat",
        json={"camera_status": "online", "model_loaded": False},
        headers={"X-Device-Key": created["api_key"]},
    )
    device_resp = client.get(f"/api/v1/devices/{created['id']}")
    assert device_resp.json()["health"]["state"] == "ERROR"


def test_heartbeat_wrong_or_missing_key_rejected():
    csrf = _login_admin()
    _register_device(csrf)

    resp = client.post("/api/v1/devices/me/heartbeat", json={}, headers={"X-Device-Key": "bogus"})
    assert resp.status_code == 401

    resp = client.post("/api/v1/devices/me/heartbeat", json={})
    assert resp.status_code == 401


def test_revoked_device_key_rejected():
    csrf = _login_admin()
    created = _register_device(csrf)

    resp = client.post(f"/api/v1/devices/{created['id']}/revoke", headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 200

    resp = client.post(
        "/api/v1/devices/me/heartbeat", json={}, headers={"X-Device-Key": created["api_key"]}
    )
    assert resp.status_code == 401


def test_rotate_key_invalidates_old_key():
    csrf = _login_admin()
    created = _register_device(csrf)
    old_key = created["api_key"]

    resp = client.post(f"/api/v1/devices/{created['id']}/rotate-key", headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 200
    new_key = resp.json()["api_key"]
    assert new_key != old_key

    resp = client.post("/api/v1/devices/me/heartbeat", json={}, headers={"X-Device-Key": old_key})
    assert resp.status_code == 401

    resp = client.post("/api/v1/devices/me/heartbeat", json={}, headers={"X-Device-Key": new_key})
    assert resp.status_code == 200


def test_caregiver_sees_only_devices_for_assigned_subjects():
    admin_csrf = _login_admin()

    db = SessionLocal()
    subject_assigned = Subject(display_name="Assigned")
    subject_other = Subject(display_name="Other")
    db.add_all([subject_assigned, subject_other])
    db.commit()
    db.refresh(subject_assigned)
    db.refresh(subject_other)
    caregiver = _make_user(CAREGIVER_EMAIL, "caregiver")
    db.add(CaregiverAssignment(user_id=caregiver.id, subject_id=subject_assigned.id))
    db.commit()

    dev_assigned = _register_device(admin_csrf, "AssignedCam")
    client.patch(
        f"/api/v1/devices/{dev_assigned['id']}",
        json={"subject_id": str(subject_assigned.id)},
        headers={"X-CSRF-Token": admin_csrf},
    )
    dev_other = _register_device(admin_csrf, "OtherCam")
    client.patch(
        f"/api/v1/devices/{dev_other['id']}",
        json={"subject_id": str(subject_other.id)},
        headers={"X-CSRF-Token": admin_csrf},
    )
    db.close()

    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": admin_csrf})
    login_resp = client.post(
        "/api/v1/auth/login", json={"email": CAREGIVER_EMAIL, "password": PASSWORD}
    )
    assert login_resp.status_code == 200

    resp = client.get("/api/v1/devices")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["device_name"] == "AssignedCam"

    resp = client.get(f"/api/v1/devices/{dev_other['id']}")
    assert resp.status_code == 404


def test_non_admin_forbidden_from_creating_device():
    _make_user(CAREGIVER_EMAIL, "caregiver")
    login_resp = client.post(
        "/api/v1/auth/login", json={"email": CAREGIVER_EMAIL, "password": PASSWORD}
    )
    csrf = login_resp.cookies["csrf_token"]

    resp = client.post(
        "/api/v1/devices", json={"device_name": "X"}, headers={"X-CSRF-Token": csrf}
    )
    assert resp.status_code == 403
