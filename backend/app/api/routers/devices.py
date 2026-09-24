"""/devices, /devices/{id}/cameras, /cameras — PRD §7.2 "Devices and cameras",
§8.2 device auth, §10 device health."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    csrf_protect,
    enforce_device_rate_limit,
    get_current_device,
    get_db,
    request_id_of,
    require_role,
)
from app.database.models import Camera, Device, DeviceHealthSnapshot, User
from app.database.scoping import caregiver_subject_ids
from app.monitoring.audit import log_audit
from app.monitoring.health import DEFAULT_EXPECTED_INTERVAL_S, compute_state_from_snapshot
from app.security.device_keys import generate_device_key, hash_device_key, key_prefix

router = APIRouter(tags=["devices"])

VALID_CAMERA_SOURCE_TYPES = {"webcam", "usb", "csi", "rtsp", "file"}


# ---- schemas (local to this router) ----------------------------------

class DeviceCreateRequest(BaseModel):
    device_name: str
    device_type: str | None = None
    location: str | None = None
    subject_id: uuid.UUID | None = None


class DeviceCreateResponse(BaseModel):
    id: uuid.UUID
    device_name: str
    api_key: str


class DeviceUpdateRequest(BaseModel):
    device_name: str | None = None
    device_type: str | None = None
    location: str | None = None
    subject_id: uuid.UUID | None = None


class RotateKeyResponse(BaseModel):
    api_key: str


class CameraCreateRequest(BaseModel):
    name: str | None = None
    source_type: str | None = None
    resolution: str | None = None
    fps: float | None = None

    def validate_source_type(self) -> None:
        if self.source_type is not None and self.source_type not in VALID_CAMERA_SOURCE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"source_type must be one of {sorted(VALID_CAMERA_SOURCE_TYPES)}",
            )


class CameraUpdateRequest(BaseModel):
    name: str | None = None
    resolution: str | None = None
    fps: float | None = None
    status: str | None = None


class HeartbeatRequest(BaseModel):
    camera_status: str | None = None
    camera_fps: float | None = None
    last_frame_at: datetime | None = None
    inference_latency_ms: int | None = None
    model_loaded: bool | None = None
    cpu_pct: float | None = None
    mem_pct: float | None = None
    temperature_c: float | None = None
    queue_depth: int | None = None
    backend_connectivity: str | None = None
    software_version: str | None = None
    model_version: str | None = None


# ---- helpers -----------------------------------------------------------

def _device_or_404(db: Session, device_id: uuid.UUID) -> Device:
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    return device


def _ensure_device_in_scope(db: Session, current_user: User, device: Device) -> None:
    if current_user.role != "caregiver":
        return
    if device.subject_id is None or device.subject_id not in caregiver_subject_ids(db, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")


def _latest_snapshot(db: Session, device_id: uuid.UUID) -> DeviceHealthSnapshot | None:
    return db.execute(
        select(DeviceHealthSnapshot)
        .where(DeviceHealthSnapshot.device_id == device_id)
        .order_by(DeviceHealthSnapshot.recorded_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def _health_embed(db: Session, device: Device) -> dict:
    snapshot = _latest_snapshot(db, device.id)
    return {
        "state": device.health_state,
        "camera_status": snapshot.camera_status if snapshot else None,
        "model_loaded": snapshot.model_loaded if snapshot else None,
        "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None,
    }


def _device_summary(db: Session, device: Device) -> dict:
    return {
        "id": device.id,
        "device_name": device.device_name,
        "device_type": device.device_type,
        "location": device.location,
        "status": device.status,
        "subject_id": device.subject_id,
        "software_version": device.software_version,
        "model_version": device.model_version,
        "health": _health_embed(db, device),
    }


def _scoped_device_query(db: Session, current_user: User):
    stmt = select(Device)
    if current_user.role == "caregiver":
        subject_ids = caregiver_subject_ids(db, current_user.id)
        if not subject_ids:
            stmt = stmt.where(False)
        else:
            stmt = stmt.where(Device.subject_id.in_(subject_ids))
    return stmt


# ---- routes --------------------------------------------------------------

@router.post(
    "/devices",
    dependencies=[Depends(csrf_protect)],
    status_code=status.HTTP_201_CREATED,
)
def create_device(
    body: DeviceCreateRequest,
    request: Request,
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> DeviceCreateResponse:
    raw_key = generate_device_key()
    device = Device(
        device_name=body.device_name,
        device_type=body.device_type,
        location=body.location,
        subject_id=body.subject_id,
        api_key_hash=hash_device_key(raw_key),
        api_key_prefix=key_prefix(raw_key),
        status="active",
    )
    db.add(device)
    db.flush()
    log_audit(db, action="device_register", result="success", user_id=admin.id,
              resource_type="device", resource_id=str(device.id), request_id=request_id_of(request))
    db.commit()
    return DeviceCreateResponse(id=device.id, device_name=device.device_name, api_key=raw_key)


@router.get("/devices")
def list_devices(
    limit: int = Query(default=25, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_role("admin", "caregiver", "ml_engineer", "operator")),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.execute(_scoped_device_query(db, current_user)).scalars().all()
    page = rows[offset : offset + limit]
    return {
        "items": [_device_summary(db, d) for d in page],
        "total": len(rows),
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/devices/{device_id}")
def get_device(
    device_id: uuid.UUID,
    current_user: User = Depends(require_role("admin", "caregiver", "ml_engineer", "operator")),
    db: Session = Depends(get_db),
) -> dict:
    device = _device_or_404(db, device_id)
    _ensure_device_in_scope(db, current_user, device)
    return _device_summary(db, device)


@router.patch("/devices/{device_id}", dependencies=[Depends(csrf_protect)])
def update_device(
    device_id: uuid.UUID,
    body: DeviceUpdateRequest,
    request: Request,
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> dict:
    device = _device_or_404(db, device_id)
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(device, field, value)
    device.updated_at = datetime.now(timezone.utc)
    log_audit(db, action="device_update", result="success", user_id=admin.id,
              resource_type="device", resource_id=str(device.id), request_id=request_id_of(request),
              metadata={k: str(v) for k, v in updates.items()})
    db.commit()
    return _device_summary(db, device)


@router.post("/devices/{device_id}/rotate-key", dependencies=[Depends(csrf_protect)])
def rotate_key(
    device_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> RotateKeyResponse:
    device = _device_or_404(db, device_id)
    raw_key = generate_device_key()
    device.api_key_hash = hash_device_key(raw_key)
    device.api_key_prefix = key_prefix(raw_key)
    device.key_rotated_at = datetime.now(timezone.utc)
    log_audit(db, action="device_rotate_key", result="success", user_id=admin.id,
              resource_type="device", resource_id=str(device.id), request_id=request_id_of(request))
    db.commit()
    return RotateKeyResponse(api_key=raw_key)


@router.post("/devices/{device_id}/revoke", dependencies=[Depends(csrf_protect)])
def revoke_device(
    device_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> dict:
    device = _device_or_404(db, device_id)
    device.status = "revoked"
    device.revoked_at = datetime.now(timezone.utc)
    log_audit(db, action="device_revoke", result="success", user_id=admin.id,
              resource_type="device", resource_id=str(device.id), request_id=request_id_of(request))
    db.commit()
    return {"status": "revoked"}


@router.get("/devices/{device_id}/health")
def device_health(
    device_id: uuid.UUID,
    hours: int = Query(default=24, ge=1, le=24 * 30),
    current_user: User = Depends(require_role("admin", "caregiver", "ml_engineer", "operator")),
    db: Session = Depends(get_db),
) -> dict:
    device = _device_or_404(db, device_id)
    _ensure_device_in_scope(db, current_user, device)

    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    snapshots = db.execute(
        select(DeviceHealthSnapshot)
        .where(DeviceHealthSnapshot.device_id == device_id, DeviceHealthSnapshot.recorded_at >= since)
        .order_by(DeviceHealthSnapshot.recorded_at.desc())
    ).scalars().all()

    return {
        "current": {
            "state": device.health_state,
            "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None,
        },
        "snapshots": [
            {
                "recorded_at": s.recorded_at.isoformat(),
                "camera_status": s.camera_status,
                "camera_fps": s.camera_fps,
                "inference_latency_ms": s.inference_latency_ms,
                "model_loaded": s.model_loaded,
                "cpu_pct": s.cpu_pct,
                "mem_pct": s.mem_pct,
                "temperature_c": s.temperature_c,
                "queue_depth": s.queue_depth,
                "backend_connectivity": s.backend_connectivity,
                "computed_state": s.computed_state,
            }
            for s in snapshots
        ],
    }


@router.post(
    "/devices/{device_id}/cameras",
    dependencies=[Depends(csrf_protect)],
    status_code=status.HTTP_201_CREATED,
)
def create_camera(
    device_id: uuid.UUID,
    body: CameraCreateRequest,
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> dict:
    _device_or_404(db, device_id)
    body.validate_source_type()
    camera = Camera(
        device_id=device_id, name=body.name, source_type=body.source_type,
        resolution=body.resolution, fps=body.fps,
    )
    db.add(camera)
    db.commit()
    return {"id": camera.id, "device_id": camera.device_id, "name": camera.name,
            "source_type": camera.source_type, "resolution": camera.resolution, "fps": camera.fps}


@router.patch("/cameras/{camera_id}", dependencies=[Depends(csrf_protect)])
def update_camera(
    camera_id: uuid.UUID,
    body: CameraUpdateRequest,
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> dict:
    camera = db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(camera, field, value)
    db.commit()
    return {"id": camera.id, "device_id": camera.device_id, "name": camera.name,
            "source_type": camera.source_type, "resolution": camera.resolution,
            "fps": camera.fps, "status": camera.status}


@router.post("/devices/me/heartbeat")
def heartbeat(
    body: HeartbeatRequest,
    device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
) -> dict:
    enforce_device_rate_limit(device.id)

    computed_state = compute_state_from_snapshot(
        camera_status=body.camera_status,
        camera_fps=body.camera_fps,
        inference_latency_ms=body.inference_latency_ms,
        model_loaded=body.model_loaded,
        queue_depth=body.queue_depth,
        backend_connectivity=body.backend_connectivity,
        cpu_pct=body.cpu_pct,
        mem_pct=body.mem_pct,
    )

    now = datetime.now(timezone.utc)
    db.add(DeviceHealthSnapshot(
        device_id=device.id,
        recorded_at=now,
        camera_status=body.camera_status,
        camera_fps=body.camera_fps,
        last_frame_at=body.last_frame_at,
        inference_latency_ms=body.inference_latency_ms,
        model_loaded=body.model_loaded,
        cpu_pct=body.cpu_pct,
        mem_pct=body.mem_pct,
        temperature_c=body.temperature_c,
        queue_depth=body.queue_depth,
        backend_connectivity=body.backend_connectivity,
        software_version=body.software_version,
        model_version=body.model_version,
        computed_state=computed_state,
    ))

    device.last_seen_at = now
    device.health_state = computed_state
    if body.software_version is not None:
        device.software_version = body.software_version
    if body.model_version is not None:
        device.model_version = body.model_version

    db.commit()
    return {"server_time": now.isoformat(), "expected_interval_s": DEFAULT_EXPECTED_INTERVAL_S}
