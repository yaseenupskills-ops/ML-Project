"""Skip the whole integration/ directory if no Postgres is reachable
(same pattern as the BE-0 MediaPipe-model skip)."""

import os
import socket
from urllib.parse import urlparse

import pytest

_DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://fallguard:fallguard@localhost:5432/fallguard"
)


def _db_reachable() -> bool:
    parsed = urlparse(_DATABASE_URL.replace("+psycopg", ""))
    try:
        with socket.create_connection((parsed.hostname, parsed.port or 5432), timeout=1):
            return True
    except OSError:
        return False


def pytest_collection_modifyitems(config, items):
    if not _db_reachable():
        skip = pytest.mark.skip(reason=f"Postgres not reachable at {_DATABASE_URL}")
        for item in items:
            item.add_marker(skip)
