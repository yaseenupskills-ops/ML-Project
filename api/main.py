"""FastAPI service exposing the fall-detection backend.

Replaces dashboard/app.py (UI removed, business logic now in services/) and
stream_server.py (routes ported below so the frontend has a single origin;
camera lifecycle now lives in services/camera_service.py, so stream_server.py
itself is no longer imported anywhere and has been deleted).
Run with: uvicorn api.main:app --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import yaml
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel

import camera as camera_module
import metrics
from services import alerts_service, analytics_service, recordings_service
from services.alert_repository import JsonlAlertRepository
from services.camera_service import BOUNDARY, CameraState
from services.roles import get_current_user, get_user_permissions, filter_by_role

CONFIG_PATH = "config.yaml"
_ACTION_TO_STATUS = {"acknowledge": "acknowledged", "dismiss": "dismissed", "escalate": "escalated"}
_ACTION_TO_PERM = {"acknowledge": "can_acknowledge", "dismiss": "can_dismiss", "escalate": "can_escalate"}


def _load_config() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _stream_server_config() -> dict:
    """Same shape dashboard.app._stream_server_config built (lines 685-712)."""
    cfg = _load_config()
    s = cfg.get("streaming", {})
    r = cfg.get("recording", {})
    cam = cfg.get("camera", {})
    allow_remote = s.get("allow_remote", False)
    return {
        "enabled": s.get("enabled", True),
        "host": "0.0.0.0" if allow_remote else s.get("host", "127.0.0.1"),
        "port": int(s.get("port", 8091)),
        "jpeg_quality": int(s.get("jpeg_quality", 80)),
        "max_fps": float(s.get("max_fps", 15)),
        "camera": {
            "source": cam.get("source", cam.get("index", 0)),
            "width": int(cam.get("width", 640)),
            "height": int(cam.get("height", 480)),
            "fps": float(cam.get("fps", 30)),
        },
        "use_synthetic": s.get("use_synthetic", False),
        "record_path": r.get("path", "data/recordings/"),
        "recording_max_days": int(r.get("max_days", 7)),
        "recording_segment_duration": r.get("segment_duration", 300),
    }


def _escalation_config() -> dict:
    return _load_config().get("escalation", {})


def get_alert_repository() -> JsonlAlertRepository:
    return JsonlAlertRepository()


def _df_to_records(df: pd.DataFrame) -> List[dict]:
    d = df.copy()
    if "datetime" in d.columns:
        d["datetime"] = d["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
    d = d.astype(object).where(pd.notnull(d), None)
    return d.to_dict(orient="records")


_stream: Optional[CameraState] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _stream
    cfg = _stream_server_config()
    if cfg.get("enabled", True):
        _stream = CameraState(cfg)
        _stream.ensure_camera()
    yield
    if _stream is not None:
        _stream.stop()


app = FastAPI(title="FallGuard AI API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_stream() -> CameraState:
    if _stream is None:
        raise HTTPException(status_code=503, detail="Streaming disabled (streaming.enabled: false in config.yaml)")
    return _stream


# ─── Pydantic response models ──────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    camera: bool
    time: float


class MetricsResponse(BaseModel):
    camera_online: bool
    camera_available: bool
    fps: float
    capture_latency_ms: float
    pipeline_latency_ms: float
    pipeline_running: bool
    frames_processed: int
    windows_evaluated: int
    alerts_triggered: int
    fall_candidates: int
    false_positives_cancelled: int
    recorded_segments: int
    recording_active: bool
    last_frame_ts: Optional[float] = None
    started_at: float
    last_update: float
    uptime_sec: float
    falls_per_min: float
    last_frame_age_sec: Optional[float] = None


class AlertOut(BaseModel):
    timestamp: float
    subject_id: str
    clip_id: str
    confidence: float
    tier: str
    outcome: str
    response_time: Optional[float] = None
    status: str
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[float] = None
    video_clip_path: Optional[str] = None
    datetime: Optional[str] = None


class AlertsListResponse(BaseModel):
    alerts: List[AlertOut]
    total: int


class AlertActionRequest(BaseModel):
    action: str  # "acknowledge" | "dismiss" | "escalate"


class AlertActionResponse(BaseModel):
    ok: bool
    timestamp: float
    status: str


class BulkActionRequest(BaseModel):
    ids: List[float]
    action: str


class BulkActionResponse(BaseModel):
    ok: bool
    updated: List[float]


class FunnelStage(BaseModel):
    stage: str
    count: int


class EscalationFunnel(BaseModel):
    stages: List[FunnelStage]
    acknowledged_rate_pct: float
    escalated_rate_pct: float


class WeekOverWeek(BaseModel):
    this_week: int
    last_week: int
    delta: int
    pct_change: float
    daily_avg: float


class AnalyticsSummaryResponse(BaseModel):
    total: int
    pending: int
    acknowledged: int
    escalated: int
    dismissed: int
    high_risk: int
    high_confidence: int
    avg_confidence: float
    by_tier: Dict[str, int]
    by_status: Dict[str, int]
    confidence_histogram: List[dict]
    heatmap: List[List[int]]
    week_over_week: WeekOverWeek
    escalation_funnel: EscalationFunnel


class SubjectTrend(BaseModel):
    subject_id: str
    alerts: int
    high_risk: int
    avg_response_min: Optional[float] = None
    escalation_rate_pct: float
    avg_confidence: float
    trend: List[dict]


class ResponseTimesResponse(BaseModel):
    mean_min: Optional[float] = None
    median_min: Optional[float] = None
    p95_min: Optional[float] = None
    n_actioned: int
    histogram: List[dict]


class RecordingOut(BaseModel):
    name: str
    path: str
    size_mb: float
    created: float
    alerts: List[dict] = []


class RecordingInfoResponse(BaseModel):
    name: str
    size_mb: float
    duration_sec: float
    fps: float
    width: int
    height: int
    frame_count: int
    segment_start: Optional[float] = None


class RecordActionResponse(BaseModel):
    ok: bool
    recording: bool
    path: Optional[str] = None
    error: Optional[str] = None


class MeResponse(BaseModel):
    username: str
    role: str
    display_name: str


# ─── Health / metrics ───────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health():
    cam_ok = _stream is not None and _stream.camera is not None
    metrics.update(camera_online=cam_ok)
    return HealthResponse(status="ok" if cam_ok else "degraded", camera=cam_ok, time=time.time())


@app.get("/metrics", response_model=MetricsResponse)
def get_metrics():
    srv = _require_stream()
    fps = getattr(srv.camera, "get_fps", lambda: 0.0)() if srv.camera is not None else 0.0
    metrics.update(
        camera_online=srv.camera is not None,
        camera_available=srv.camera is not None,
        fps=round(fps, 2),
        recording_active=srv.recording_started,
    )
    return metrics.format_summary()


# ─── Alerts ─────────────────────────────────────────────────────────────────

@app.get("/alerts", response_model=AlertsListResponse)
def list_alerts(
    tier: Optional[str] = None,
    status: Optional[str] = None,
    subject_id: Optional[str] = None,
    from_: Optional[str] = Query(default=None, alias="from"),
    to: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    repo = get_alert_repository()
    df = alerts_service.load_alert_history(repo)
    df = filter_by_role(df, user)
    df = alerts_service.filter_alerts(df, tier=tier, status=status, subject_id=subject_id, date_from=from_, date_to=to)
    records = _df_to_records(df)
    return {"alerts": records, "total": len(records)}


@app.patch("/alerts/{id}", response_model=AlertActionResponse)
def update_alert(id: float, body: AlertActionRequest, user: dict = Depends(get_current_user)):
    if body.action not in _ACTION_TO_STATUS:
        raise HTTPException(status_code=400, detail="action must be one of acknowledge|dismiss|escalate")
    perms = get_user_permissions(user)
    if not perms.get(_ACTION_TO_PERM[body.action]):
        raise HTTPException(status_code=403, detail="not permitted for this role")
    repo = get_alert_repository()
    if body.action == "escalate":
        notify = _escalation_config().get("notify_on_escalate", True)
        updated = alerts_service.escalate_with_notify(repo, [id], user["username"], user["role"], notify=notify)
        ok = len(updated) > 0
    else:
        ok = alerts_service.acknowledge_one(repo, id, user["username"], user["role"], _ACTION_TO_STATUS[body.action])
    if not ok:
        raise HTTPException(status_code=404, detail="alert not found")
    return AlertActionResponse(ok=True, timestamp=id, status=_ACTION_TO_STATUS[body.action])


@app.post("/alerts/bulk", response_model=BulkActionResponse)
def bulk_alert_action(body: BulkActionRequest, user: dict = Depends(get_current_user)):
    if body.action not in _ACTION_TO_STATUS:
        raise HTTPException(status_code=400, detail="action must be one of acknowledge|dismiss|escalate")
    perms = get_user_permissions(user)
    if not perms.get(_ACTION_TO_PERM[body.action]):
        raise HTTPException(status_code=403, detail="not permitted for this role")
    repo = get_alert_repository()
    if body.action == "escalate":
        notify = _escalation_config().get("notify_on_escalate", True)
        updated = alerts_service.escalate_with_notify(repo, body.ids, user["username"], user["role"], notify=notify)
    else:
        updated = alerts_service.bulk_update(repo, body.ids, user["username"], user["role"], _ACTION_TO_STATUS[body.action])
    return BulkActionResponse(ok=True, updated=updated)


# ─── Analytics ──────────────────────────────────────────────────────────────

def _role_filtered_history(user: dict) -> pd.DataFrame:
    df = alerts_service.load_alert_history(get_alert_repository())
    return filter_by_role(df, user)


@app.get("/analytics/summary", response_model=AnalyticsSummaryResponse)
def analytics_summary(user: dict = Depends(get_current_user)):
    return analytics_service.summary(_role_filtered_history(user))


@app.get("/analytics/subjects", response_model=List[SubjectTrend])
def analytics_subjects(user: dict = Depends(get_current_user)):
    return analytics_service.subject_trends(_role_filtered_history(user))


@app.get("/analytics/response-times", response_model=ResponseTimesResponse)
def analytics_response_times(user: dict = Depends(get_current_user)):
    return analytics_service.response_times(_role_filtered_history(user))


@app.get("/analytics/export.csv")
def analytics_export_csv(user: dict = Depends(get_current_user)):
    if not get_user_permissions(user).get("can_export"):
        raise HTTPException(status_code=403, detail="not permitted for this role")
    csv_bytes = analytics_service.to_csv_bytes(_role_filtered_history(user))
    filename = f"fall_alerts_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([csv_bytes]), media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── Recordings ─────────────────────────────────────────────────────────────

@app.get("/recordings", response_model=List[RecordingOut])
def get_recordings(user: dict = Depends(get_current_user)):
    srv = _require_stream()
    recs = recordings_service.list_recordings(srv.rec_path)
    df = _role_filtered_history(user)
    mapping = recordings_service.map_alerts_to_recordings(df, recs, srv.segment_duration)
    for r in recs:
        r["alerts"] = mapping.get(r["name"], [])
    return recs


@app.get("/recordings/{name}/info", response_model=RecordingInfoResponse)
def get_recording_info(name: str):
    srv = _require_stream()
    info = recordings_service.recording_info(srv.rec_path, name)
    if info is None:
        raise HTTPException(status_code=404, detail="not found")
    return info


@app.get("/recordings/{name}/video")
def get_recording_video(name: str):
    srv = _require_stream()
    p = recordings_service.safe_recording_path(srv.rec_path, name)
    if p is None:
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(str(p), media_type="video/mp4", filename=p.name)


@app.post("/record/start", response_model=RecordActionResponse)
def record_start():
    """Opt-in recording to disk; ported from stream_server._handle_record_start (353-373)."""
    srv = _require_stream()
    if srv.camera is None:
        return RecordActionResponse(ok=False, recording=False, error="no source")
    try:
        ok = srv.camera.start_recording(
            srv.rec_path, segment_duration=srv.segment_duration, max_days=srv.max_days
        )
        srv.recording_started = ok
        segs = len(srv.camera.list_recordings(srv.rec_path))
        metrics.update(recording_active=ok, recorded_segments=segs)
        return RecordActionResponse(ok=ok, recording=ok, path=str(srv.rec_path))
    except Exception as e:
        return RecordActionResponse(ok=False, recording=False, error=str(e))


@app.post("/record/stop", response_model=RecordActionResponse)
def record_stop():
    srv = _require_stream()
    if srv.camera is not None:
        try:
            srv.camera.stop_recording()
        except Exception:
            pass
    srv.recording_started = False
    metrics.update(recording_active=False)
    return RecordActionResponse(ok=True, recording=False)


# ─── Live video ─────────────────────────────────────────────────────────────

@app.get("/video_feed")
def video_feed():
    """MJPEG stream, ported from stream_server._handle_video_feed (274-291)."""
    srv = _require_stream()

    def gen():
        for chunk in srv.camera.generate_mjpeg_stream(quality=srv.jpeg_quality, max_fps=srv.max_fps):
            metrics.update(last_frame_ts=time.time())
            yield chunk

    return StreamingResponse(gen(), media_type=f"multipart/x-mixed-replace; boundary={BOUNDARY}")


@app.get("/frame")
def frame():
    """Single latest JPEG frame, ported from stream_server._handle_frame (293-320)."""
    srv = _require_stream()
    fr = None
    for _ in range(5):
        fr = srv.camera.read_frame()
        if fr is not None:
            break
        time.sleep(0.1)
    if fr is None:
        raise HTTPException(status_code=503, detail="no frame available")
    data = camera_module.CameraManager.encode_jpeg(fr, srv.jpeg_quality)
    if not data:
        raise HTTPException(status_code=503, detail="encode failed")
    metrics.update(last_frame_ts=time.time())
    return Response(
        content=data, media_type="image/jpeg",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


# ─── Current user ───────────────────────────────────────────────────────────

@app.get("/me", response_model=MeResponse)
def me(user: dict = Depends(get_current_user)):
    return user
