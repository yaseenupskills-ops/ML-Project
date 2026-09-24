"""/users (admin) — PRD §7.2 Users table."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import csrf_protect, get_db, request_id_of, require_role
from app.api.schemas import (
    ResetPasswordResponse,
    SubjectIdsRequest,
    UserCreateRequest,
    UserCreateResponse,
    UserResponse,
    UserUpdateRequest,
)
from app.database.models import CaregiverAssignment, RefreshToken, Subject, User
from app.monitoring.audit import log_audit
from app.security.passwords import generate_temporary_password, hash_password

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_role("admin"))])


def _get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    return user


@router.get("")
def list_users(
    limit: int = Query(default=25, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    total = db.execute(select(User)).scalars().all()
    page = total[offset : offset + limit]
    return {
        "items": [UserResponse.model_validate(u, from_attributes=True) for u in page],
        "total": len(total),
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


@router.post("", dependencies=[Depends(csrf_protect)], status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreateRequest,
    request: Request,
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> UserCreateResponse:
    temp_password = generate_temporary_password()
    user = User(
        email=body.email,
        name=body.name,
        role=body.role,
        password_hash=hash_password(temp_password),
        must_change_password=True,
    )
    db.add(user)
    db.flush()
    log_audit(db, action="user_create", result="success", user_id=admin.id,
               resource_type="user", resource_id=str(user.id), request_id=request_id_of(request))
    db.commit()
    return UserCreateResponse(
        id=user.id, email=user.email, name=user.name, role=user.role,
        temporary_password=temp_password, must_change_password=True,
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db)) -> User:
    return _get_user_or_404(db, user_id)


@router.patch("/{user_id}", dependencies=[Depends(csrf_protect)], response_model=UserResponse)
def update_user(
    user_id: uuid.UUID,
    body: UserUpdateRequest,
    request: Request,
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> User:
    user = _get_user_or_404(db, user_id)
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(user, field, value)
    user.updated_at = datetime.now(timezone.utc)
    log_audit(db, action="user_update", result="success", user_id=admin.id,
               resource_type="user", resource_id=str(user.id), request_id=request_id_of(request),
               metadata=updates)
    db.commit()
    return user


@router.post("/{user_id}/reset-password", dependencies=[Depends(csrf_protect)])
def reset_password(
    user_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> ResetPasswordResponse:
    user = _get_user_or_404(db, user_id)
    temp_password = generate_temporary_password()
    user.password_hash = hash_password(temp_password)
    user.must_change_password = True
    db.execute(
        delete(RefreshToken).where(RefreshToken.user_id == user.id)
    )
    log_audit(db, action="user_reset_password", result="success", user_id=admin.id,
               resource_type="user", resource_id=str(user.id), request_id=request_id_of(request))
    db.commit()
    return ResetPasswordResponse(temporary_password=temp_password)


@router.put("/{user_id}/subjects", dependencies=[Depends(csrf_protect)])
def set_subject_assignments(
    user_id: uuid.UUID,
    body: SubjectIdsRequest,
    request: Request,
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> dict:
    _get_user_or_404(db, user_id)

    if body.subject_ids:
        found = set(
            db.execute(
                select(Subject.id).where(Subject.id.in_(body.subject_ids))
            ).scalars()
        )
        missing = set(body.subject_ids) - found
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"unknown subject_ids: {sorted(str(s) for s in missing)}",
            )

    db.execute(delete(CaregiverAssignment).where(CaregiverAssignment.user_id == user_id))
    for subject_id in body.subject_ids:
        db.add(CaregiverAssignment(user_id=user_id, subject_id=subject_id))

    log_audit(db, action="user_subjects_assign", result="success", user_id=admin.id,
               resource_type="user", resource_id=str(user_id), request_id=request_id_of(request),
               metadata={"subject_ids": [str(s) for s in body.subject_ids]})
    db.commit()
    return {"subject_ids": body.subject_ids}
