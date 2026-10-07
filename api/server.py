"""
FallGuard Care - FastAPI API Bridge
-----------------------------------
Provides a clean REST API and MJPEG stream proxy for the modern caregiver web application.
"""

from __future__ import annotations

import os
import sys
import time
import json
import hmac
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Literal

from fastapi import FastAPI, HTTPException, Cookie, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from alert_store import AlertStore
from alert import AlertManager
from project_config import load_config, resolve_path
import stream_server as ss
from live_detection import get_live_detector, cancel_active_alert

logger = logging.getLogger("fallguard_api")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="FallGuard Care API",
    description="Caregiver-first REST API for Fall Detection System",
    version="2.0.0",
)

ALERT_LOG = resolve_path("logs/alerts.jsonl", base=PROJECT_ROOT)
store = AlertStore(ALERT_LOG)
config = load_config()


# ─── Authentication ──────────────────────────────────────────────────────────

AUTH_COOKIE = "fg_token"


def get_auth_config() -> dict:
    return config.get("auth", {"enabled": False, "users": []})


def _auth_secret() -> str:
    return (
        os.getenv("FALLGUARD_AUTH_SECRET")
        or get_auth_config().get("jwt_secret")
        or get_auth_config().get("secret_key")
        or "fallback-secret-key-change-me"
    )


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a plaintext password against a bcrypt or PBKDF2-SHA256 hash."""
    try:
        if stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$"):
            import bcrypt
            return bcrypt.checkpw(password.encode(), stored_hash.encode())
        salt, digest = stored_hash.split("$", 1)
        result = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return hmac.compare_digest(result.hex(), digest)
    except Exception:
        return False


def generate_token(username: str, role: str, secret: str) -> str:
    payload = f"{username}:{role}:{int(time.time())}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def validate_token(token: Optional[str]) -> Optional[dict]:
    """Validate an HMAC-signed session token; return the user profile or None."""
    if not token:
        return None
    try:
        payload, sig = token.rsplit(":", 1)
        expected = hmac.new(_auth_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        username, _role, ts = payload.split(":", 2)
        expiry_hours = float(get_auth_config().get("token_expiry_hours", 24) or 24)
        if time.time() - int(ts) > expiry_hours * 3600:
            return None
        for u in get_auth_config().get("users", []):
            if u.get("username") == username:
                return {
                    "username": username,
                    "role": u.get("role", "viewer"),
                    "display_name": u.get("display_name", username),
                    "assigned_subjects": u.get("assigned_subjects", []),
                }
        # User was removed from config → their tokens are no longer valid
        return None
    except Exception:
        return None


def _public_user(user: dict) -> dict:
    return {
        "username": user["username"],
        "role": user.get("role", "viewer"),
        "display_name": user.get("display_name", user["username"]),
        "assigned_subjects": user.get("assigned_subjects", []),
    }


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
def login(req: LoginRequest, response: Response):
    """Verify credentials and set an httpOnly session cookie."""
    username = (req.username or "").strip()
    user = None
    for candidate in get_auth_config().get("users", []):
        if candidate.get("username") == username and verify_password(req.password, candidate.get("password_hash", "")):
            user = candidate
            break
    if user is None:
        # Do not reveal whether the username exists
        raise HTTPException(status_code=401, detail="Invalid username or password")
    expiry_hours = float(get_auth_config().get("token_expiry_hours", 24) or 24)
    token = generate_token(user["username"], user.get("role", "viewer"), _auth_secret())
    response.set_cookie(
        AUTH_COOKIE,
        token,
        max_age=int(expiry_hours * 3600),
        httponly=True,
        samesite="lax",
        path="/",
    )
    return _public_user(user)


@app.post("/api/auth/logout")
def logout(response: Response):
    """Clear the session cookie."""
    response.delete_cookie(AUTH_COOKIE, path="/")
    return {"ok": True}


@app.get("/api/auth/me")
def current_user(fg_token: Optional[str] = Cookie(default=None)):
    """Return the signed-in user profile, a guest profile when auth is disabled, or 401."""
    if not get_auth_config().get("enabled", False):
        return {
            "username": "guest",
            "role": "guest",
            "display_name": "Guest User",
            "assigned_subjects": [],
            "guest": True,
        }
    user = validate_token(fg_token)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@app.get("/health")
def health():
    """Public liveness probe (never requires auth)."""
    return {"status": "ok"}


@app.middleware("http")
async def auth_guard(request: Request, call_next):
    """Reject unauthenticated API calls when auth is enabled."""
    if request.method == "OPTIONS":
        return await call_next(request)
    if request.url.path.startswith("/api/auth/") or request.url.path == "/health":
        return await call_next(request)
    if not get_auth_config().get("enabled", False):
        return await call_next(request)
    user = validate_token(request.cookies.get(AUTH_COOKIE))
    if user is None:
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)
    request.state.user = user
    return await call_next(request)


# Registered last so CORS wraps the auth guard: preflight is handled first and
# every response (including 401s) carries CORS headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure stream server is running
def get_or_start_stream_server():
    server = ss.get_stream_server()
    if server is None:
        stream_cfg = config.get("streaming", {})
        stream_cfg["camera"] = config.get("camera", {})
        server = ss.StreamServer(stream_cfg)
        server.start()
        ss._server_singleton = server
    return server


# ─── Helper Functions ────────────────────────────────────────────────────────

def format_relative_time(timestamp: float | None) -> str:
    if not timestamp:
        return "Unknown"
    dt = datetime.fromtimestamp(timestamp)
    now = datetime.now()
    diff = now - dt

    if diff.total_seconds() < 60:
        return "Just now"
    if diff.total_seconds() < 3600:
        mins = int(diff.total_seconds() // 60)
        return f"{mins}m ago"
    if dt.date() == now.date():
        return f"Today, {dt.strftime('%I:%M %p')}"
    return dt.strftime("%b %d, %I:%M %p")


def map_alert_for_caregiver(alert: dict) -> dict:
    ts = alert.get("timestamp") or alert.get("created_at") or time.time()
    tier = str(alert.get("fall_event_tier") or alert.get("tier") or "medium").lower()
    conf = float(alert.get("fall_event_confidence") or alert.get("confidence") or 0.0)
    status = str(alert.get("status", "pending")).lower()
    subject = str(alert.get("fall_event_subject") or alert.get("subject_id") or "Resident")

    severity = "High Risk" if tier == "high" or conf > 0.75 else "Moderate Risk" if tier == "medium" else "Minor Event"

    plain_status = {
        "pending": "Needs Attention",
        "acknowledged": "Attended",
        "dismissed": "False Alarm",
        "escalated": "Emergency Contacted",
        "cancelled": "Resolved Automatically",
    }.get(status, status.capitalize())

    return {
        "id": str(alert.get("id")),
        "timestamp": ts,
        "time_formatted": format_relative_time(ts),
        "exact_time": datetime.fromtimestamp(ts).strftime("%I:%M:%S %p"),
        "date_formatted": datetime.fromtimestamp(ts).strftime("%b %d, %Y"),
        "subject": "Eleanor Vance" if subject in {"live", "demo", "unknown", "Resident"} else subject,
        "room": "Living Room",
        "status": status,
        "plain_status": plain_status,
        "severity": severity,
        "confidence_pct": round(conf * 100),
        "notes": alert.get("notes", ""),
        "acknowledged_by": alert.get("acknowledged_by"),
        "video_clip": alert.get("video_clip_path") or None,
    }


# ─── API Routes ─────────────────────────────────────────────────────────────

@app.get("/api/status")
def get_system_status():
    """Return high-level status for the peace-of-mind dashboard."""
    server = get_or_start_stream_server()
    detector = get_live_detector()
    det_status = detector.status()

    # Determine current active source
    cam_cfg = server.config.get("camera", {}) if server else {}
    current_src = str(cam_cfg.get("source", 0))
    source_type = "demo" if "demo" in current_src else "webcam"

    # Inspect alerts to see if there is an active pending event
    all_alerts = store.read_all()
    pending_alerts = [a for a in all_alerts if a.get("status") == "pending"]

    resident_status = "safe"
    active_alert = None
    grace_remaining = 0

    if pending_alerts:
        latest_pending = max(pending_alerts, key=lambda a: float(a.get("timestamp") or 0))
        alert_age = time.time() - float(latest_pending.get("timestamp") or time.time())
        grace_timeout = det_status.get("grace_timeout_sec", 20)

        active_alert = map_alert_for_caregiver(latest_pending)

        if alert_age < grace_timeout and det_status.get("active"):
            resident_status = "grace_period"
            grace_remaining = max(1, int(grace_timeout - alert_age))
        else:
            resident_status = "alert"

    return {
        "resident_name": "Eleanor Vance",
        "room": "Living Room",
        "resident_status": resident_status,  # "safe" | "grace_period" | "alert"
        "camera_online": True,
        "active_source": source_type,
        "detection_active": det_status.get("active", False),
        "grace_seconds_remaining": grace_remaining,
        "active_alert": active_alert,
        "last_checked_at": datetime.now().strftime("%I:%M %p"),
    }


@app.get("/api/alerts")
def get_alerts():
    """Return past alerts formatted for caregivers."""
    all_alerts = store.read_all()
    # Sort newest first
    sorted_alerts = sorted(all_alerts, key=lambda a: float(a.get("timestamp") or 0), reverse=True)
    return [map_alert_for_caregiver(a) for a in sorted_alerts[:50]]


class AlertActionRequest(BaseModel):
    action: Literal["acknowledge", "dismiss", "escalate"]
    user: str = "Sarah Miller (Caregiver)"
    notes: Optional[str] = None


@app.post("/api/alerts/{alert_id}/action")
def take_alert_action(alert_id: str, req: AlertActionRequest):
    """Acknowledge, dismiss, or escalate an alert."""
    cancel_active_alert(alert_id)

    target_status = {
        "acknowledge": "acknowledged",
        "dismiss": "dismissed",
        "escalate": "escalated",
    }.get(req.action, "acknowledged")

    try:
        updated = store.update(
            alert_id=alert_id,
            action=target_status,
            user=req.user,
            role="caregiver",
            extra_updates={
                "acknowledged_at": time.time(),
                "notes": req.notes or "",
            },
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        # If escalating, trigger notification
        if req.action == "escalate":
            try:
                alert_rec = store.get(alert_id) or {}
                mgr = AlertManager()
                mgr.send_email_alert(
                    {
                        "subject_id": alert_rec.get("subject_id", "Eleanor Vance"),
                        "timestamp": time.time(),
                        "confidence": float(alert_rec.get("confidence") or 0.9),
                        "tier": "high",
                    },
                    {"outcome": "escalated_by_caregiver", "response_time": 0},
                    log_alert=False,
                )
            except Exception as e:
                logger.warning(f"Escalation notification failed: {e}")

        return {"ok": True, "alert_id": alert_id, "new_status": target_status}
    except Exception as e:
        logger.error(f"Failed to update alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SwitchSourceRequest(BaseModel):
    source: Literal["webcam", "demo"]


@app.post("/api/stream/switch")
def switch_camera_source(req: SwitchSourceRequest):
    """Switch active feed between live webcam and demo fall video."""
    server = get_or_start_stream_server()
    cam_cfg = server.config.get("camera", {})
    webcam_src = cam_cfg.get("webcam_source", 0)
    demo_src = cam_cfg.get("demo_source", "data/demo/demo_fall.mp4")

    want = webcam_src if req.source == "webcam" else demo_src

    try:
        server.switch_source(want)
        detector = get_live_detector()
        detector.run_session(want)
        return {"ok": True, "active_source": req.source}
    except Exception as e:
        logger.error(f"Error switching camera source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stream/feed")
def get_video_stream():
    """Stream MJPEG frames directly from the active camera source."""
    server = get_or_start_stream_server()
    cam = server.ensure_camera()

    def mjpeg_generator():
        import cv2
        interval = 1.0 / 15.0
        while True:
            start = time.time()
            frame = cam.read_frame()
            if frame is not None:
                success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                if success:
                    frame_bytes = buffer.tobytes()
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            elapsed = time.time() - start
            time.sleep(max(0.01, interval - elapsed))

    return StreamingResponse(
        mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.get("/api/stream/snapshot")
def get_snapshot():
    """Single JPEG snapshot for low-bandwidth or preview."""
    server = get_or_start_stream_server()
    cam = server.ensure_camera()
    frame = cam.read_frame()
    if frame is None:
        raise HTTPException(status_code=503, detail="Frame not available")

    import cv2
    success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if not success:
        raise HTTPException(status_code=500, detail="Encoding failed")

    return Response(content=buffer.tobytes(), media_type="image/jpeg")


@app.get("/api/contacts")
def get_emergency_contacts():
    """Return emergency and care team contacts."""
    return [
        {
            "id": "c1",
            "name": "Sarah Miller",
            "role": "Daughter / Primary Caregiver",
            "phone": "(555) 234-5678",
            "email": "sarah.miller@example.com",
            "is_primary": True,
            "badge": "On Duty",
        },
        {
            "id": "c2",
            "name": "Dr. Robert Chen",
            "role": "Primary Care Physician",
            "phone": "(555) 876-5432",
            "email": "dr.chen@oakridgehealth.org",
            "is_primary": False,
            "badge": "Physician",
        },
        {
            "id": "c3",
            "name": "Oakridge Nursing Station",
            "role": "On-Site Nurse Team",
            "phone": "(555) 991-0022",
            "email": "nursing@oakridgecare.com",
            "is_primary": False,
            "badge": "Facility",
        },
        {
            "id": "c4",
            "name": "Emergency Medical Services",
            "role": "Local EMS / 911",
            "phone": "911",
            "email": "",
            "is_primary": False,
            "badge": "Emergency",
        },
    ]


@app.get("/api/summary")
def get_peace_of_mind_summary():
    """Return peaceful summary metrics for the caregiver."""
    all_alerts = store.read_all()
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    
    today_alerts = [a for a in all_alerts if float(a.get("timestamp") or 0) >= today_start]
    falls_today = len([a for a in today_alerts if a.get("status") in {"acknowledged", "escalated"}])
    
    return {
        "streak_days": 18,
        "falls_today": falls_today,
        "routine_checks_today": 4,
        "avg_response_sec": 38,
        "last_routine_check": "15 minutes ago",
        "system_health": "Optimal",
        "privacy_mode": "Secured Local-Only",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.server:app", host="127.0.0.1", port=8000, reload=True)
