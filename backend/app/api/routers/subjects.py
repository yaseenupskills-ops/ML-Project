"""/subjects — PRD §7.2 Subjects table, §4 RBAC, masking for ml_engineer."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import csrf_protect, get_current_user, get_db, request_id_of, require_role
from app.database.models import Subject, User
from app.database.scoping import caregiver_subject_ids, ensure_subject_in_scope
from app.monitoring.audit import log_audit

router = APIRouter(prefix="/subjects", tags=["subjects"])


class SubjectCreateRequest(BaseModel):
    display_name: str
    location_label: str | None = None


class SubjectUpdateRequest(BaseModel):
    display_name: str | None = None
    location_label: str | None = None
    status: str | None = None


def _full(subject: Subject) -> dict:
    return {
        "id": subject.id,
        "display_name": subject.display_name,
        "location_label": subject.location_label,
        "status": subject.status,
        "created_at": subject.created_at,
        "updated_at": subject.updated_at,
    }


def _masked(subject: Subject) -> dict:
    return {"id": subject.id, "status": subject.status}


def _serialize(subject: Subject, current_user: User) -> dict:
    return _masked(subject) if current_user.role == "ml_engineer" else _full(subject)


def _get_subject_or_404(db: Session, subject_id: uuid.UUID) -> Subject:
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    return subject


@router.get("")
def list_subjects(
    limit: int = Query(default=25, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if current_user.role == "operator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    if current_user.role == "caregiver":
        ids = caregiver_subject_ids(db, current_user.id)
        all_subjects = (
            db.execute(select(Subject).where(Subject.id.in_(ids))).scalars().all() if ids else []
        )
    else:
        all_subjects = db.execute(select(Subject)).scalars().all()

    page = all_subjects[offset : offset + limit]
    return {
        "items": [_serialize(s, current_user) for s in page],
        "total": len(all_subjects),
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


@router.post("", dependencies=[Depends(csrf_protect)], status_code=status.HTTP_201_CREATED)
def create_subject(
    body: SubjectCreateRequest,
    request: Request,
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> dict:
    subject = Subject(display_name=body.display_name, location_label=body.location_label)
    db.add(subject)
    db.flush()
    log_audit(db, action="subject_create", result="success", user_id=admin.id,
               resource_type="subject", resource_id=str(subject.id), request_id=request_id_of(request))
    db.commit()
    return _full(subject)


@router.get("/{subject_id}")
def get_subject(
    subject_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if current_user.role == "operator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    ensure_subject_in_scope(db, current_user, subject_id)
    subject = _get_subject_or_404(db, subject_id)
    return _serialize(subject, current_user)


@router.patch("/{subject_id}", dependencies=[Depends(csrf_protect)])
def update_subject(
    subject_id: uuid.UUID,
    body: SubjectUpdateRequest,
    request: Request,
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> dict:
    subject = _get_subject_or_404(db, subject_id)
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(subject, field, value)
    subject.updated_at = datetime.now(timezone.utc)
    log_audit(db, action="subject_update", result="success", user_id=admin.id,
               resource_type="subject", resource_id=str(subject.id), request_id=request_id_of(request),
               metadata=updates)
    db.commit()
    return _full(subject)
