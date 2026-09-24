"""/alerts — PRD §7.2 Alerts table, §5.2 alert lifecycle, §4 RBAC."""

import csv
import io
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import csrf_protect, get_current_user, get_db, request_id_of
from app.database.models import Alert, AlertAction, Device, Event, Subject, User
from app.database.scoping import caregiver_subject_ids
from app.monitoring.audit import log_audit

router = APIRouter(prefix="/alerts", tags=["alerts"])

MAX_BULK_ALERTS = 100

_OPEN_TO_ACK_OR_ESCALATED = {"OPEN", "ESCALATED"}


class ActionRequest(BaseModel):
    note: str | None = None


class BulkRequest(BaseModel):
    action: str
    alert_ids: list[uuid.UUID] = Field(max_length=MAX_BULK_ALERTS)


# ---- scoping / access ----------------------------------------------------

def _require_alerts_access(current_user: User) -> None:
    if current_user.role == "operator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


def _alert_query_for_user(db: Session, current_user: User):
    stmt = select(Alert).join(Event, Event.id == Alert.event_id)
    if current_user.role == "caregiver":
        subject_ids = caregiver_subject_ids(db, current_user.id)
        if not subject_ids:
            return stmt.where(False)
        stmt = stmt.where(Event.subject_id.in_(subject_ids))
    return stmt


def _alert_in_scope_or_404(db: Session, current_user: User, alert: Alert) -> None:
    if current_user.role == "caregiver":
        event = db.get(Event, alert.event_id)
        subject_ids = caregiver_subject_ids(db, current_user.id)
        if event is None or event.subject_id is None or event.subject_id not in subject_ids:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")


# ---- serialization --------------------------------------------------------

def _response_time_s(alert: Alert) -> float | None:
    if alert.acknowledged_at is None:
        return None
    return (alert.acknowledged_at - alert.created_at).total_seconds()


def _serialize(db: Session, alert: Alert, current_user: User) -> dict:
    event = db.get(Event, alert.event_id)
    masked = current_user.role == "ml_engineer"

    subject = db.get(Subject, event.subject_id) if event and event.subject_id else None
    subject_payload = None
    if subject is not None:
        subject_payload = {"id": subject.id} if masked else {
            "id": subject.id, "display_name": subject.display_name,
            "location_label": subject.location_label,
        }

    def _user_field(user_id: uuid.UUID | None) -> uuid.UUID | None:
        return None if masked else user_id

    return {
        "id": alert.id,
        "event_id": alert.event_id,
        "status": alert.status,
        "notification_status": alert.notification_status,
        "created_at": alert.created_at,
        "subject": subject_payload,
        "tier": event.tier if event else None,
        "confidence": event.confidence if event else None,
        "acknowledged_by": _user_field(alert.acknowledged_by),
        "acknowledged_at": alert.acknowledged_at,
        "dismissed_by": _user_field(alert.dismissed_by),
        "dismissed_at": alert.dismissed_at,
        "escalated_by": _user_field(alert.escalated_by),
        "escalated_at": alert.escalated_at,
        "escalation_reason": alert.escalation_reason,
        "response_time_s": _response_time_s(alert),
    }


def _get_alert_or_404(db: Session, alert_id: uuid.UUID) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    return alert


# ---- transitions -----------------------------------------------------------

def _apply_action(db: Session, alert: Alert, action: str, user: User, note: str | None) -> None:
    now = datetime.now(timezone.utc)
    if action == "acknowledge":
        if alert.status not in _OPEN_TO_ACK_OR_ESCALATED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="invalid_transition")
        alert.status = "ACKNOWLEDGED"
        alert.acknowledged_by = user.id
        alert.acknowledged_at = now
    elif action == "dismiss":
        if alert.status != "OPEN":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="invalid_transition")
        alert.status = "DISMISSED"
        alert.dismissed_by = user.id
        alert.dismissed_at = now
    elif action == "escalate":
        if alert.status != "OPEN":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="invalid_transition")
        alert.status = "ESCALATED"
        alert.escalated_by = user.id
        alert.escalated_at = now
        alert.escalation_reason = "manual"
    else:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid_action")

    db.add(AlertAction(alert_id=alert.id, user_id=user.id, action=action, note=note))


# ---- routes ----------------------------------------------------------------

@router.get("")
def list_alerts(
    status_filter: str | None = Query(default=None, alias="status"),
    tier: str | None = Query(default=None),
    subject_id: uuid.UUID | None = Query(default=None),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    limit: int = Query(default=25, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _require_alerts_access(current_user)
    stmt = _alert_query_for_user(db, current_user)
    if status_filter:
        stmt = stmt.where(Alert.status == status_filter)
    if tier:
        stmt = stmt.where(Event.tier == tier)
    if subject_id:
        stmt = stmt.where(Event.subject_id == subject_id)
    if from_:
        stmt = stmt.where(Alert.created_at >= from_)
    if to:
        stmt = stmt.where(Alert.created_at <= to)

    rows = db.execute(stmt).scalars().all()
    page = rows[offset : offset + limit]
    return {
        "items": [_serialize(db, a, current_user) for a in page],
        "total": len(rows),
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/export.csv")
def export_alerts_csv(
    status_filter: str | None = Query(default=None, alias="status"),
    tier: str | None = Query(default=None),
    subject_id: uuid.UUID | None = Query(default=None),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    _require_alerts_access(current_user)
    stmt = _alert_query_for_user(db, current_user)
    if status_filter:
        stmt = stmt.where(Alert.status == status_filter)
    if tier:
        stmt = stmt.where(Event.tier == tier)
    if subject_id:
        stmt = stmt.where(Event.subject_id == subject_id)
    if from_:
        stmt = stmt.where(Alert.created_at >= from_)
    if to:
        stmt = stmt.where(Alert.created_at <= to)
    rows = db.execute(stmt).scalars().all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "datetime", "subject", "device", "confidence", "tier", "state", "status",
        "acknowledged_by", "response_time_s", "model_version",
    ])
    for alert in rows:
        event = db.get(Event, alert.event_id)
        subject = db.get(Subject, event.subject_id) if event and event.subject_id else None
        device = db.get(Device, event.device_id) if event else None
        ack_user = db.get(User, alert.acknowledged_by) if alert.acknowledged_by else None
        writer.writerow([
            event.detected_at.isoformat() if event else "",
            subject.display_name if subject else "",
            device.device_name if device else "",
            event.confidence if event else "",
            event.tier if event else "",
            event.state if event else "",
            alert.status,
            ack_user.name if ack_user else "",
            _response_time_s(alert) or "",
            event.model_version if event else "",
        ])

    return Response(content=buf.getvalue(), media_type="text/csv")


@router.get("/{alert_id}")
def get_alert(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _require_alerts_access(current_user)
    alert = _get_alert_or_404(db, alert_id)
    _alert_in_scope_or_404(db, current_user, alert)
    return _serialize(db, alert, current_user)


@router.post("/{alert_id}/acknowledge", dependencies=[Depends(csrf_protect)])
def acknowledge_alert(
    alert_id: uuid.UUID,
    body: ActionRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _require_alerts_access(current_user)
    alert = _get_alert_or_404(db, alert_id)
    _alert_in_scope_or_404(db, current_user, alert)
    _apply_action(db, alert, "acknowledge", current_user, body.note)
    log_audit(db, action="alert_acknowledge", result="success", user_id=current_user.id,
              resource_type="alert", resource_id=str(alert.id), request_id=request_id_of(request))
    db.commit()
    return _serialize(db, alert, current_user)


@router.post("/{alert_id}/dismiss", dependencies=[Depends(csrf_protect)])
def dismiss_alert(
    alert_id: uuid.UUID,
    body: ActionRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _require_alerts_access(current_user)
    alert = _get_alert_or_404(db, alert_id)
    _alert_in_scope_or_404(db, current_user, alert)
    _apply_action(db, alert, "dismiss", current_user, body.note)
    log_audit(db, action="alert_dismiss", result="success", user_id=current_user.id,
              resource_type="alert", resource_id=str(alert.id), request_id=request_id_of(request))
    db.commit()
    return _serialize(db, alert, current_user)


@router.post("/{alert_id}/escalate", dependencies=[Depends(csrf_protect)])
def escalate_alert(
    alert_id: uuid.UUID,
    body: ActionRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _require_alerts_access(current_user)
    alert = _get_alert_or_404(db, alert_id)
    _alert_in_scope_or_404(db, current_user, alert)
    _apply_action(db, alert, "escalate", current_user, body.note)
    log_audit(db, action="alert_escalate", result="success", user_id=current_user.id,
              resource_type="alert", resource_id=str(alert.id), request_id=request_id_of(request))
    db.commit()
    return _serialize(db, alert, current_user)


@router.post("/bulk", dependencies=[Depends(csrf_protect)])
def bulk_alerts(
    body: BulkRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _require_alerts_access(current_user)
    if body.action not in ("acknowledge", "dismiss", "escalate"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid_action")

    results = []
    for alert_id in body.alert_ids:
        try:
            alert = db.get(Alert, alert_id)
            if alert is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
            _alert_in_scope_or_404(db, current_user, alert)
            _apply_action(db, alert, body.action, current_user, None)
            log_audit(db, action=f"alert_{body.action}", result="success", user_id=current_user.id,
                      resource_type="alert", resource_id=str(alert.id),
                      request_id=request_id_of(request))
            db.commit()
            results.append({"alert_id": alert_id, "status": "ok", "detail": None})
        except HTTPException as exc:
            db.rollback()
            results.append({"alert_id": alert_id, "status": "error", "detail": str(exc.detail)})

    return {"results": results}
