"""Object-level authorization scoping (PRD §4): one place every list/detail
query for a caregiver-owned resource passes through. Caregiver access to a
subject outside their assignments returns 404, not 403 (no existence leak).
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import CaregiverAssignment, User


def caregiver_subject_ids(db: Session, user_id: uuid.UUID) -> set[uuid.UUID]:
    rows = db.execute(
        select(CaregiverAssignment.subject_id).where(CaregiverAssignment.user_id == user_id)
    ).scalars()
    return set(rows)


def ensure_subject_in_scope(db: Session, current_user: User, subject_id: uuid.UUID) -> None:
    """Raise 404 (never 403) if a caregiver isn't assigned to this subject.

    Admin, ml_engineer and operator roles have their own read scope handled
    by the endpoint (full access, or none); this only restricts caregivers.
    """
    if current_user.role != "caregiver":
        return
    if subject_id not in caregiver_subject_ids(db, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
