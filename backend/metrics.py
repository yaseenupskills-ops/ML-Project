"""
Live Metrics State (Phase 3)
----------------------------
Thread-safe shared metrics store used by camera stream server, the detection
pipeline (simulate_stream.py) and the dashboard. Enables cross-component
visibility of real-time performance without coupling them.
"""

import threading
import time
from collections import deque
from pathlib import Path

_lock = threading.Lock()

_state = {
    "camera_online": False,
    "camera_available": False,
    "fps": 0.0,
    "capture_latency_ms": 0.0,
    "pipeline_latency_ms": 0.0,
    "pipeline_running": False,
    "frames_processed": 0,
    "windows_evaluated": 0,
    "alerts_triggered": 0,
    "fall_candidates": 0,
    "false_positives_cancelled": 0,
    "recorded_segments": 0,
    "recording_active": False,
    "last_frame_ts": None,
    "started_at": time.time(),
    "last_update": 0.0,
}

# Rolling window of alert timestamps (unix seconds) for falls-per-minute
_alert_events: deque = deque(maxlen=2000)


def update(**kwargs):
    """Thread-safe partial update of live metrics."""
    with _lock:
        _state.update(kwargs)
        _state["last_update"] = time.time()


def get() -> dict:
    """Return a copy of the current metrics state."""
    with _lock:
        return dict(_state)


def register_alert(ts: float = None):
    """Record an alert event timestamp for rate computation."""
    ts = ts if ts is not None else time.time()
    with _lock:
        _alert_events.append(ts)
        _state["alerts_triggered"] += 1


def alerts_in_window(window_sec: float) -> list:
    """Return alert timestamps within the last `window_sec` seconds."""
    cutoff = time.time() - window_sec
    with _lock:
        return [ts for ts in _alert_events if ts >= cutoff]


def _rate_fn(events: list, started_at: float, minutes: int) -> float:
    """Lock-free per-minute rate from a timestamps list."""
    if minutes <= 0:
        return 0.0
    window_sec = minutes * 60.0
    cutoff = time.time() - window_sec
    count = len([ts for ts in events if ts >= cutoff])
    elapsed = min(time.time() - started_at, window_sec)
    if elapsed <= 0:
        return 0.0
    return round((count / elapsed) * 60.0, 2)


def falls_per_minute(window_minutes: int = 60) -> float:
    """Alert events per minute over the rolling window."""
    if window_minutes <= 0:
        return 0.0
    with _lock:
        return _rate_fn(list(_alert_events), _state["started_at"], window_minutes)


def format_summary() -> dict:
    """Human-friendly snapshot for JSON endpoints and dashboard metrics."""
    with _lock:
        st = dict(_state)
        st["uptime_sec"] = time.time() - st["started_at"]
        st["falls_per_min"] = _rate_fn(
            list(_alert_events), _state["started_at"], 60
        )
        last = st.get("last_frame_ts")
        st["last_frame_age_sec"] = round(time.time() - last, 2) if last else None
        st["recording_active"] = st.get("recording_active", False)
        return st