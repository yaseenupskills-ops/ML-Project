"""Argon2id password hashing (PRD §8.1): min length 10, admin-initiated reset only."""

import secrets
import string

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

MIN_PASSWORD_LENGTH = 10

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"password must be at least {MIN_PASSWORD_LENGTH} characters")
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


_TEMP_PASSWORD_ALPHABET = string.ascii_letters + string.digits


def generate_temporary_password(length: int = 16) -> str:
    return "".join(secrets.choice(_TEMP_PASSWORD_ALPHABET) for _ in range(length))
