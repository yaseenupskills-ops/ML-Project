"""Audit log writer (PRD §8.3): login/logout, user/device/subject changes,
alert actions, feedback, model register/promote, config change, deletion."""

import uuid

from sqlalchemy.orm import Session

from app.database.models import AuditLog


def log_audit(
    db: Session,
    *,
    action: str,
    result: str,
    user_id: uuid.UUID | None = None,
    device_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    request_id: str | None = None,
    ip: str | None = None,
    metadata: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            device_id=device_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            result=result,
            request_id=request_id,
            ip=ip,
            metadata_=metadata,
        )
    )
