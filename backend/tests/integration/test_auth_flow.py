"""Auth/RBAC integration tests against real Postgres (PRD §15).

Run with DATABASE_URL pointing at a real Postgres with the be2 migration
applied; skipped automatically (see conftest.py) if unreachable.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.api.deps import LOGIN_RATE_LIMIT, _LOGIN_ATTEMPTS
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
PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def clean_db():
    _LOGIN_ATTEMPTS.clear()
    client.cookies.clear()
    db = SessionLocal()
    # Alert/AlertAction/Notification/CaregiverFeedback/Event FK-reference User
    # (and Event->Device), so they must go before User/Subject/Device or a
    # leftover row from an earlier-run test file breaks this delete.
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


def _login(email: str = ADMIN_EMAIL, password: str = PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_login_success_sets_cookies_and_returns_profile():
    _make_user(ADMIN_EMAIL, "admin")
    resp = _login()
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"
    assert "access_token" in resp.cookies
    assert "refresh_token" in resp.cookies
    assert "csrf_token" in resp.cookies


def test_login_wrong_password_rejected():
    _make_user(ADMIN_EMAIL, "admin")
    resp = client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"})
    assert resp.status_code == 401


def test_login_disabled_user_rejected():
    _make_user(ADMIN_EMAIL, "admin", status="disabled")
    resp = _login()
    assert resp.status_code == 401


def test_login_rate_limited_after_five_attempts():
    _make_user(ADMIN_EMAIL, "admin")
    for _ in range(LOGIN_RATE_LIMIT):
        client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"})
    resp = client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"})
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


def test_refresh_rotates_token_and_old_token_then_fails():
    _make_user(ADMIN_EMAIL, "admin")
    login_resp = _login()
    old_refresh = login_resp.cookies["refresh_token"]
    csrf = login_resp.cookies["csrf_token"]

    resp = client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 200
    new_refresh = client.cookies.get("refresh_token")
    assert new_refresh != old_refresh

    # Using the old (rotated-away) refresh token again must fail.
    client.cookies.set("refresh_token", old_refresh)
    resp = client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "reuse_detected"


def test_refresh_reuse_revokes_whole_family_including_current_token():
    _make_user(ADMIN_EMAIL, "admin")
    login_resp = _login()
    old_refresh = login_resp.cookies["refresh_token"]
    csrf = login_resp.cookies["csrf_token"]

    client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf})
    current_refresh = client.cookies.get("refresh_token")

    # Trigger reuse detection with the stale token.
    client.cookies.set("refresh_token", old_refresh)
    client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf})

    # The token issued by the rotation just before reuse was detected must
    # also be revoked now (whole family killed).
    client.cookies.set("refresh_token", current_refresh)
    resp = client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 401


def test_csrf_required_for_mutating_routes():
    _make_user(ADMIN_EMAIL, "admin")
    _login()
    resp = client.post("/api/v1/auth/logout")  # no X-CSRF-Token header
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "csrf_failed"


def test_change_password_requires_current_password():
    _make_user(ADMIN_EMAIL, "admin")
    login_resp = _login()
    csrf = login_resp.cookies["csrf_token"]

    resp = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "wrong", "new_password": "brand-new-password"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400

    resp = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "brand-new-password"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200


def test_non_admin_forbidden_from_users_endpoint():
    _make_user(CAREGIVER_EMAIL, "caregiver")
    login_resp = client.post(
        "/api/v1/auth/login", json={"email": CAREGIVER_EMAIL, "password": PASSWORD}
    )
    assert login_resp.status_code == 200

    resp = client.get("/api/v1/users")
    assert resp.status_code == 403


def test_admin_can_list_and_create_users():
    _make_user(ADMIN_EMAIL, "admin")
    login_resp = _login()
    csrf = login_resp.cookies["csrf_token"]

    resp = client.get("/api/v1/users")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    resp = client.post(
        "/api/v1/users",
        json={"email": CAREGIVER_EMAIL, "name": "Care Giver", "role": "caregiver"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201
    assert resp.json()["must_change_password"] is True
    assert len(resp.json()["temporary_password"]) > 0
