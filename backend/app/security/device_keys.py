"""Per-device API keys (PRD §8.2): 32+ random bytes, shown once, stored as
SHA-256 hash + short prefix for identification."""

import hashlib
import secrets

KEY_PREFIX_LENGTH = 8


def generate_device_key() -> str:
    return secrets.token_urlsafe(32)


def hash_device_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def key_prefix(key: str) -> str:
    return key[:KEY_PREFIX_LENGTH]
