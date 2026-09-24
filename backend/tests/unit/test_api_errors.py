"""Error envelope + request-id (PRD §7.1)."""

from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


def test_404_uses_error_envelope():
    resp = client.get("/api/v1/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert "error" in body
    assert set(body["error"].keys()) == {"code", "message", "request_id", "details"}


def test_request_id_is_echoed():
    resp = client.get("/api/v1/system/health", headers={"X-Request-ID": "test-request-123"})
    assert resp.headers["X-Request-ID"] == "test-request-123"


def test_request_id_is_generated_when_missing():
    resp = client.get("/api/v1/system/health")
    assert resp.headers["X-Request-ID"]
