"""Password hashing and token helpers (PRD §8.1), no DB required."""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.security.passwords import generate_temporary_password, hash_password, verify_password
from app.security.tokens import (
    ACCESS_TOKEN_TTL,
    JWT_ALGORITHM,
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_refresh_token,
)

SECRET = "unit-test-secret"


def test_hash_and_verify_roundtrip():
    password = "correct-horse-battery"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_hash_password_rejects_short_password():
    with pytest.raises(ValueError):
        hash_password("short")


def test_generate_temporary_password_is_unique_and_long_enough():
    passwords = {generate_temporary_password() for _ in range(20)}
    assert len(passwords) == 20
    assert all(len(p) >= 10 for p in passwords)


def test_access_token_roundtrip():
    user_id = uuid.uuid4()
    token = create_access_token(user_id, "admin", SECRET)
    payload = decode_access_token(token, SECRET)
    assert payload["sub"] == str(user_id)
    assert payload["role"] == "admin"


def test_access_token_rejects_wrong_secret():
    token = create_access_token(uuid.uuid4(), "admin", SECRET)
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(token, "a-different-secret")


def test_access_token_expires():
    # Build an already-expired token directly rather than sleeping in a test.
    iat = datetime.now(timezone.utc) - ACCESS_TOKEN_TTL - timedelta(seconds=1)
    payload = {"sub": str(uuid.uuid4()), "role": "admin", "iat": iat, "exp": iat + ACCESS_TOKEN_TTL}
    token = jwt.encode(payload, SECRET, algorithm=JWT_ALGORITHM)

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token, SECRET)


def test_refresh_token_hash_is_deterministic_and_opaque():
    token = generate_refresh_token()
    assert hash_refresh_token(token) == hash_refresh_token(token)
    assert hash_refresh_token(token) != token
