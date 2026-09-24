"""/events — PRD §7.2 Events table, §7.3 payloads, §5.1 lifecycle, §3.2 privacy boundary."""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Query, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.alerts.lifecycle import cancel_event, confirm_event
from app.api.deps import (
    ACCESS_TOKEN_COOKIE,
    DEVICE_KEY_HEADER,
    csrf_protect,
    enforce_device_rate_limit,
    get_current_device,
    get_db,
    request_id_of,
    require_role,
)
from app.config.settings import get_settings
from app.database.models import (
    Alert,
    AlertAction,
    CaregiverFeedback,
    Device,
    Event,
    EventEvidence,
    Notification,
    Subject,
    User,
)
from app.database.scoping import caregiver_subject_ids, ensure_subject_in_scope
from app.monitoring.audit import log_audit
from app.security.device_keys import hash_device_key
from app.security.tokens import decode_access_token

router = APIRouter(tags=["events"])

MAX_EVENT_BODY_BYTES = 64 * 1024
MAX_STRING_BYTES = 4096

_KNOWN_EVIDENCE_FIELDS = {
    "rapid_downward_motion", "orientation_change", "body_height_change",
    "post_event_stillness", "summary",
}


# ---- schemas (local to this router) ----------------------------------

class EvidenceRequest(BaseModel):
    model_config = {"extra": "allow"}

    rapid_downward_motion: bool | None = None
    orientation_change: float | None = None
    body_height_change: float | None = None
    post_event_stillness: bool | None = None
    summary: str | None = None


class EventCreateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    client_event_id: uuid.UUID
    track_id: int | None = None
    detected_at: datetime
    event_type: str = "possible_fall"
    confidence: float | None = None
    confidence_calibrated: bool = False
    tier: str | None = None
    model_version: str | None = None
    feature_version: str | None = None
    pose_quality: float | None = None
    grace_seconds: int = 20
    evidence: EvidenceRequest | None = None


class EventStateUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    state: str
    occurred_at: datetime | None = None


# ---- privacy boundary helpers (PRD §3.2) --------------------------------

def _reject_oversized_strings(value) -> None:
    """Recursively reject any string > MAX_STRING_BYTES anywhere in the
    payload (image-blob heuristic)."""
    if isinstance(value, str):
        if len(value.encode("utf-8")) > MAX_STRING_BYTES:
            raise HTTPException(status_code=422, detail="field_too_large")
    elif isinstance(value, dict):
        for v in value.values():
            _reject_oversized_strings(v)
    elif isinstance(value, list):
        for v in value:
            _reject_oversized_strings(v)


# ---- helpers -------------------------------------------------------------

def _authenticate_for_event_read(
    db: Session, x_device_key: str | None, access_token: str | None
) -> tuple[Device | None, User | None]:
    if x_device_key:
        device = db.query(Device).filter(Device.api_key_hash == hash_device_key(x_device_key)).first()
        if device is None or device.status == "revoked":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_device_key")
        return device, None

    if access_token:
        try:
            payload = decode_access_token(access_token, get_settings().jwt_secret)
            user_id = uuid.UUID(payload["sub"])
        except (jwt.PyJWTError, ValueError, KeyError):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")
        user = db.get(User, user_id)
        if user is None or user.status != "active":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")
        return None, user

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")


def _serialize_event_detail(db: Session, event: Event, mask_subject: bool) -> dict:
    device = db.get(Device, event.device_id)
    subject = db.get(Subject, event.subject_id) if event.subject_id else None
    evidence = db.get(EventEvidence, event.id)
    alert = db.execute(select(Alert).where(Alert.event_id == event.id)).scalar_one_or_none()
    notifications = db.execute(
        select(Notification).where(Notification.event_id == event.id)
    ).scalars().all()
    feedback_rows = db.execute(
        select(CaregiverFeedback).where(CaregiverFeedback.event_id == event.id)
    ).scalars().all()

    timeline = [
        {"at": event.received_at.isoformat(), "actor": "device", "action": "event_created", "note": None}
    ]
    if event.resolved_at is not None:
        action = "event_confirmed" if event.state == "CONFIRMED" else "event_cancelled"
        actor = {"backend_timeout": "system", "edge": "device", "caregiver": "user"}.get(
            event.resolved_by, "system"
        )
        timeline.append({"at": event.resolved_at.isoformat(), "actor": actor, "action": action, "note": None})
    if alert is not None:
        actions = db.execute(
            select(AlertAction).where(AlertAction.alert_id == alert.id).order_by(AlertAction.created_at)
        ).scalars().all()
        for a in actions:
            timeline.append({
                "at": a.created_at.isoformat(),
                "actor": "system" if a.user_id is None else "user",
                "action": a.action,
                "note": a.note,
            })
    timeline.sort(key=lambda t: t["at"])

    subject_payload = None
    if subject is not None:
        subject_payload = {"id": subject.id}
        if not mask_subject:
            subject_payload["display_name"] = subject.display_name
            subject_payload["location_label"] = subject.location_label

    alert_payload = None
    if alert is not None:
        response_time_s = None
        if alert.acknowledged_at is not None:
            response_time_s = (alert.acknowledged_at - alert.created_at).total_seconds()
        alert_payload = {
            "id": alert.id,
            "status": alert.status,
            "notification_status": alert.notification_status,
            "acknowledged_by": alert.acknowledged_by,
            "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
            "response_time_s": response_time_s,
        }

    return {
        "id": event.id,
        "state": event.state,
        "detected_at": event.detected_at.isoformat(),
        "grace_deadline": event.grace_deadline.isoformat(),
        "resolved_at": event.resolved_at.isoformat() if event.resolved_at else None,
        "resolved_by": event.resolved_by,
        "subject": subject_payload,
        "device": {"id": device.id, "device_name": device.device_name},
        "confidence": event.confidence,
        "confidence_calibrated": event.confidence_calibrated,
        "tier": event.tier,
        "track_id": event.track_id,
        "model_version": event.model_version,
        "feature_version": event.feature_version,
        "pose_quality": event.pose_quality,
        "evidence": (
            {
                "rapid_motion": evidence.rapid_motion,
                "orientation_change": evidence.orientation_change,
                "body_height_change": evidence.body_height_change,
                "post_event_stillness": evidence.post_event_stillness,
                "evidence_summary": evidence.evidence_summary,
            }
            if evidence is not None
            else None
        ),
        "alert": alert_payload,
        "notifications": [
            {
                "channel": n.channel, "kind": n.kind, "status": n.status,
                "attempt_count": n.attempt_count,
                "last_attempt_at": n.last_attempt_at.isoformat() if n.last_attempt_at else None,
                "error_code": n.error_code,
            }
            for n in notifications
        ],
        "feedback": [
            {
                "caregiver_id": f.caregiver_id, "label": f.label, "comment": f.comment,
                "created_at": f.created_at.isoformat(),
            }
            for f in feedback_rows
        ],
        "timeline": timeline,
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


def _resolve_conflict(event: Event) -> str:
    return "event_already_confirmed" if event.state == "CONFIRMED" else "invalid_transition"


# ---- routes ----------------------------------------------------------------

@router.post("/events")
def create_event(
    body: EventCreateRequest,
    request: Request,
    response: Response,
    device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
) -> dict:
    enforce_device_rate_limit(device.id)

    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_EVENT_BODY_BYTES:
        raise HTTPException(status_code=422, detail="body_too_large")
    _reject_oversized_strings(body.model_dump(mode="json"))

    existing = db.execute(
        select(Event).where(Event.device_id == device.id, Event.client_event_id == body.client_event_id)
    ).scalar_one_or_none()
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return {
            "id": existing.id,
            "state": existing.state,
            "grace_deadline": existing.grace_deadline.isoformat(),
            "server_time": datetime.now(timezone.utc).isoformat(),
        }

    grace_deadline = body.detected_at + timedelta(seconds=body.grace_seconds)
    event = Event(
        client_event_id=body.client_event_id,
        device_id=device.id,
        subject_id=device.subject_id,
        track_id=body.track_id,
        event_type=body.event_type,
        detected_at=body.detected_at,
        grace_seconds=body.grace_seconds,
        grace_deadline=grace_deadline,
        confidence=body.confidence,
        confidence_calibrated=body.confidence_calibrated,
        tier=body.tier,
        model_version=body.model_version,
        feature_version=body.feature_version,
        pose_quality=body.pose_quality,
    )
    db.add(event)
    db.flush()

    if body.evidence is not None:
        evidence_dict = body.evidence.model_dump()
        extra = {k: v for k, v in evidence_dict.items() if k not in _KNOWN_EVIDENCE_FIELDS}
        db.add(EventEvidence(
            event_id=event.id,
            rapid_motion=body.evidence.rapid_downward_motion,
            orientation_change=body.evidence.orientation_change,
            body_height_change=body.evidence.body_height_change,
            post_event_stillness=body.evidence.post_event_stillness,
            evidence_summary=body.evidence.summary,
            extra=extra or None,
        ))

    db.commit()
    response.status_code = status.HTTP_201_CREATED
    return {
        "id": event.id,
        "state": "PENDING",
        "grace_deadline": grace_deadline.isoformat(),
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/events/{event_id}")
def get_event(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    x_device_key: str | None = Header(default=None, alias=DEVICE_KEY_HEADER),
    access_token: str | None = Cookie(default=None, alias=ACCESS_TOKEN_COOKIE),
) -> dict:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")

    device, user = _authenticate_for_event_read(db, x_device_key, access_token)

    if device is not None:
        if event.device_id != device.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
        return _serialize_event_detail(db, event, mask_subject=False)

    if user.role == "operator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    if user.role == "caregiver":
        ensure_subject_in_scope(db, user, event.subject_id)

    return _serialize_event_detail(db, event, mask_subject=(user.role == "ml_engineer"))


@router.patch("/events/{event_id}")
def update_event_state(
    event_id: uuid.UUID,
    body: EventStateUpdateRequest,
    device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
) -> dict:
    event = db.get(Event, event_id)
    if event is None or event.device_id != device.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")

    if body.state == "CANCELLED":
        if not cancel_event(db, event, resolved_by="edge"):
            db.refresh(event)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_resolve_conflict(event))
    elif body.state == "CONFIRMED":
        if confirm_event(db, event, resolved_by="edge") is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="invalid_transition")
    else:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="invalid_transition")

    db.refresh(event)
    return {
        "id": event.id, "state": event.state,
        "resolved_at": event.resolved_at.isoformat() if event.resolved_at else None,
    }


@router.post("/events/{event_id}/cancel", dependencies=[Depends(csrf_protect)])
def cancel_event_route(
    event_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_role("admin", "caregiver")),
    db: Session = Depends(get_db),
) -> dict:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")

    if current_user.role == "caregiver":
        ensure_subject_in_scope(db, current_user, event.subject_id)

    if not cancel_event(db, event, resolved_by="caregiver"):
        db.refresh(event)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_resolve_conflict(event))

    log_audit(db, action="event_cancel", result="success", user_id=current_user.id,
              resource_type="event", resource_id=str(event.id), request_id=request_id_of(request))
    db.commit()
    db.refresh(event)
    return {"id": event.id, "state": event.state}


@router.get("/events")
def list_events(
    limit: int = Query(default=25, le=100),
    offset: int = Query(default=0, ge=0),
    state: str | None = None,
    alert_status: str | None = None,
    tier: str | None = None,
    subject_id: uuid.UUID | None = None,
    device_id: uuid.UUID | None = None,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    current_user: User = Depends(require_role("admin", "caregiver", "ml_engineer")),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(Event)

    if current_user.role == "caregiver":
        subject_ids = caregiver_subject_ids(db, current_user.id)
        stmt = stmt.where(Event.subject_id.in_(subject_ids)) if subject_ids else stmt.where(False)

    if state:
        stmt = stmt.where(Event.state == state)
    if tier:
        stmt = stmt.where(Event.tier == tier)
    if subject_id:
        stmt = stmt.where(Event.subject_id == subject_id)
    if device_id:
        stmt = stmt.where(Event.device_id == device_id)
    if from_:
        stmt = stmt.where(Event.detected_at >= from_)
    if to:
        stmt = stmt.where(Event.detected_at <= to)

    rows = db.execute(stmt.order_by(Event.detected_at.desc())).scalars().all()

    if alert_status:
        filtered = []
        for e in rows:
            alert = db.execute(select(Alert).where(Alert.event_id == e.id)).scalar_one_or_none()
            if alert is not None and alert.status == alert_status:
                filtered.append(e)
        rows = filtered

    page = rows[offset : offset + limit]
    items = []
    for e in page:
        alert = db.execute(select(Alert).where(Alert.event_id == e.id)).scalar_one_or_none()
        items.append({
            "id": e.id, "state": e.state, "detected_at": e.detected_at.isoformat(),
            "tier": e.tier, "subject_id": e.subject_id, "device_id": e.device_id,
            "confidence": e.confidence,
            "alert": {"id": alert.id, "status": alert.status} if alert is not None else None,
            "notification_status": alert.notification_status if alert is not None else None,
        })

    return {
        "items": items, "total": len(rows),
        "server_time": datetime.now(timezone.utc).isoformat(),
    }
