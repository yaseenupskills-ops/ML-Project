"""Shared FastAPI dependencies: DB session, current user, RBAC, CSRF,
login rate limiting (PRD §4, §7.1, §8.1)."""

import time
import uuid
from collections import defaultdict
from collections.abc import Generator

import jwt
from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.middleware import REQUEST_ID_HEADER
from app.config.settings import get_settings
from app.database.models import Device, User
from app.database.session import SessionLocal
from app.security.device_keys import hash_device_key
from app.security.tokens import decode_access_token

ACCESS_TOKEN_COOKIE = "access_token"
REFRESH_TOKEN_COOKIE = "refresh_token"
CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"
DEVICE_KEY_HEADER = "X-Device-Key"


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    db: Session = Depends(get_db),
    access_token: str | None = Cookie(default=None, alias=ACCESS_TOKEN_COOKIE),
) -> User:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")
    try:
        payload = decode_access_token(access_token, get_settings().jwt_secret)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")

    user = db.get(User, user_id)
    if user is None or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")
    return user


def require_role(*roles: str):
    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return current_user

    return _check


def get_current_device(
    db: Session = Depends(get_db),
    x_device_key: str | None = Header(default=None, alias=DEVICE_KEY_HEADER),
) -> Device:
    if not x_device_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")
    device = db.query(Device).filter(Device.api_key_hash == hash_device_key(x_device_key)).first()
    if device is None or device.status == "revoked":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_device_key")
    return device


def csrf_protect(
    request: Request,
    csrf_token: str | None = Cookie(default=None, alias=CSRF_COOKIE),
) -> None:
    header_token = request.headers.get(CSRF_HEADER)
    if not csrf_token or not header_token or csrf_token != header_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="csrf_failed")


# ponytail: in-memory sliding window, per API process. Fine for the single
# `api` replica in the MVP compose stack; move to a shared store (DB/Redis)
# if the API is ever scaled to multiple instances.
_RATE_LIMIT_ATTEMPTS: dict[str, list[float]] = defaultdict(list)
LOGIN_RATE_LIMIT = 5
LOGIN_RATE_WINDOW_SECONDS = 60
DEVICE_RATE_LIMIT = 120
DEVICE_RATE_WINDOW_SECONDS = 60

# kept for backwards-compatible imports (tests, auth.py)
_LOGIN_ATTEMPTS = _RATE_LIMIT_ATTEMPTS


def _check_rate_limit(bucket: str, key: str, limit: int, window_seconds: int) -> None:
    full_key = f"{bucket}:{key}"
    now = time.monotonic()
    attempts = [t for t in _RATE_LIMIT_ATTEMPTS[full_key] if now - t < window_seconds]
    if len(attempts) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="rate_limited",
            headers={"Retry-After": str(window_seconds)},
        )
    attempts.append(now)
    _RATE_LIMIT_ATTEMPTS[full_key] = attempts


def enforce_login_rate_limit(request: Request, email: str) -> None:
    key = f"{request.client.host if request.client else 'unknown'}:{email.lower()}"
    _check_rate_limit("login", key, LOGIN_RATE_LIMIT, LOGIN_RATE_WINDOW_SECONDS)


def enforce_device_rate_limit(device_id: uuid.UUID) -> None:
    _check_rate_limit("device", str(device_id), DEVICE_RATE_LIMIT, DEVICE_RATE_WINDOW_SECONDS)


def request_id_of(request: Request) -> str:
    return getattr(request.state, "request_id", "") or request.headers.get(REQUEST_ID_HEADER, "")
