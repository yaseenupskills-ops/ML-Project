"""GET /system/health (PRD §7.2): db up/down, no sensitive data."""

from contextlib import contextmanager
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.main import app
from app.api.routers.system import get_engine


class _FakeResult:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


class _FakeConnection:
    def __init__(self, heartbeat: datetime | None):
        self._heartbeat = heartbeat

    def execute(self, statement, *args, **kwargs):
        if "worker_heartbeat" in str(statement):
            row = (self._heartbeat,) if self._heartbeat is not None else None
            return _FakeResult(row)
        return _FakeResult(None)


class _FakeEngine:
    def __init__(self, heartbeat: datetime | None = None, raise_on_connect: bool = False):
        self._heartbeat = heartbeat
        self._raise_on_connect = raise_on_connect

    @contextmanager
    def connect(self):
        if self._raise_on_connect:
            raise ConnectionError("db unreachable")
        yield _FakeConnection(self._heartbeat)


client = TestClient(app)


def test_health_ok_with_heartbeat():
    now = datetime.now(timezone.utc)
    app.dependency_overrides[get_engine] = lambda: _FakeEngine(heartbeat=now)
    try:
        resp = client.get("/api/v1/system/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["db"] == "up"
        assert body["worker_last_tick"] == now.isoformat()
        assert "password" not in resp.text and "secret" not in resp.text
    finally:
        app.dependency_overrides.clear()


def test_health_reports_db_down():
    app.dependency_overrides[get_engine] = lambda: _FakeEngine(raise_on_connect=True)
    try:
        resp = client.get("/api/v1/system/health")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "down"
        assert body["db"] == "down"
    finally:
        app.dependency_overrides.clear()
