"""Device health-state rules (PRD §10).

    OFFLINE  no heartbeat for > 3 * expected_interval_s (default 90s)
    ERROR    model_loaded = false, or camera_status = error
    DEGRADED camera_status != online, or camera_fps < 5, or
             inference_latency_ms > 500, or queue_depth > 50, or
             backend_connectivity != connected, or cpu_pct > 95, or mem_pct > 95
    HEALTHY  none of the above

Pure functions only; callers own persistence (heartbeat handler and sweeper).
"""

from datetime import datetime, timedelta, timezone

DEFAULT_EXPECTED_INTERVAL_S = 30
OFFLINE_MULTIPLIER = 3


def is_offline(last_seen_at: datetime | None, expected_interval_s: int, now: datetime | None = None) -> bool:
    if last_seen_at is None:
        return True
    now = now or datetime.now(timezone.utc)
    return now - last_seen_at > timedelta(seconds=expected_interval_s * OFFLINE_MULTIPLIER)


def compute_state_from_snapshot(
    *,
    camera_status: str | None,
    camera_fps: float | None,
    inference_latency_ms: int | None,
    model_loaded: bool | None,
    queue_depth: int | None,
    backend_connectivity: str | None,
    cpu_pct: float | None,
    mem_pct: float | None,
) -> str:
    """State implied by a single heartbeat snapshot (never OFFLINE — that's
    a sweeper-only concept based on the *absence* of a heartbeat)."""
    if model_loaded is False or camera_status == "error":
        return "ERROR"

    degraded = (
        (camera_status is not None and camera_status != "online")
        or (camera_fps is not None and camera_fps < 5)
        or (inference_latency_ms is not None and inference_latency_ms > 500)
        or (queue_depth is not None and queue_depth > 50)
        or (backend_connectivity is not None and backend_connectivity != "connected")
        or (cpu_pct is not None and cpu_pct > 95)
        or (mem_pct is not None and mem_pct > 95)
    )
    if degraded:
        return "DEGRADED"

    return "HEALTHY"
