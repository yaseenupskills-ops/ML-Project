"""/caregiver-feedback — PRD §5.3, §7.2."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import csrf_protect, get_current_user, get_db, request_id_of, require_role
from app.database.models import CaregiverFeedback, Event, Subject, User
from app.database.scoping import ensure_subject_in_scope
from app.monitoring.audit import log_audit

router = APIRouter(prefix="/caregiver-feedback", tags=["feedback"])

VALID_LABELS = {"TRUE_FALL", "FALSE_POSITIVE", "UNCERTAIN", "SYSTEM_FAILURE"}


class FeedbackRequest(BaseModel):
    event_id: uuid.UUID
    label: str
    comment: str | None = None


def _serialize(feedback: CaregiverFeedback, masked: bool) -> dict:
    return {
        "id": feedback.id,
        "event_id": feedback.event_id,
        "caregiver_id": None if masked else feedback.caregiver_id,
        "label": feedback.label,
        "comment": feedback.comment,
        "created_at": feedback.created_at,
        "updated_at": feedback.updated_at,
    }


@router.post("", dependencies=[Depends(csrf_protect)])
def create_or_update_feedback(
    body: FeedbackRequest,
    request: Request,
    current_user: User = Depends(require_role("admin", "caregiver")),
    db: Session = Depends(get_db),
) -> dict:
    if body.label not in VALID_LABELS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid_label")

    event = db.get(Event, body.event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    if current_user.role == "caregiver":
        if event.subject_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
        ensure_subject_in_scope(db, current_user, event.subject_id)

    existing = db.execute(
        select(CaregiverFeedback).where(
            CaregiverFeedback.event_id == body.event_id,
            CaregiverFeedback.caregiver_id == current_user.id,
        )
    ).scalar_one_or_none()

    if existing is not None:
        existing.label = body.label
        existing.comment = body.comment
        existing.updated_at = datetime.now(timezone.utc)
        feedback = existing
        action = "feedback_update"
    else:
        feedback = CaregiverFeedback(
            event_id=body.event_id, caregiver_id=current_user.id,
            label=body.label, comment=body.comment,
        )
        db.add(feedback)
        action = "feedback_create"

    db.flush()
    log_audit(db, action=action, result="success", user_id=current_user.id,
              resource_type="caregiver_feedback", resource_id=str(feedback.id),
              request_id=request_id_of(request))
    db.commit()
    return _serialize(feedback, masked=False)


@router.get("")
def list_feedback(
    label: str | None = Query(default=None),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    limit: int = Query(default=25, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_role("admin", "ml_engineer")),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(CaregiverFeedback)
    if label:
        stmt = stmt.where(CaregiverFeedback.label == label)
    if from_:
        stmt = stmt.where(CaregiverFeedback.created_at >= from_)
    if to:
        stmt = stmt.where(CaregiverFeedback.created_at <= to)

    rows = db.execute(stmt).scalars().all()
    page = rows[offset : offset + limit]
    masked = current_user.role == "ml_engineer"
    return {
        "items": [_serialize(f, masked) for f in page],
        "total": len(rows),
        "server_time": datetime.now(timezone.utc).isoformat(),
    }
