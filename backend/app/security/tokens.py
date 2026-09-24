"""JWT access tokens + opaque refresh tokens (PRD §8.1).

Access token: JWT, 15 min, carried in an httpOnly cookie.
Refresh token: opaque random string, 7 days, stored hashed (SHA-256),
rotated on every use; reuse of an already-rotated token revokes the family.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt

ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=7)
JWT_ALGORITHM = "HS256"


def create_access_token(user_id: uuid.UUID, role: str, secret: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + ACCESS_TOKEN_TTL,
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str, secret: str) -> dict:
    return jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def refresh_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + REFRESH_TOKEN_TTL
