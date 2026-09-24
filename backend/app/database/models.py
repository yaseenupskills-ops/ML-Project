"""SQLAlchemy 2 typed ORM models (PRD §3.3, §6).

Only the tables BE-2 (auth/RBAC) needs are mapped here. The remaining §6
tables already exist in the database (see the be2 schema migration) and get
their ORM models added in the phase that first uses them.

Primary keys and timestamps get Python-side defaults (matching the DB
defaults) so inserted objects have usable values immediately, without
depending on RETURNING/eager_defaults refresh behavior after commit.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    password_hash: Mapped[str]
    role: Mapped[str]
    status: Mapped[str] = mapped_column(default="active")
    must_change_password: Mapped[bool] = mapped_column(default=False)
    notify_email: Mapped[bool] = mapped_column(default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str]
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None] = mapped_column(default=None)
    replaced_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("refresh_tokens.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(default=_now)


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    display_name: Mapped[str]
    location_label: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(default="active")
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now)


class CaregiverAssignment(Base):
    __tablename__ = "caregiver_assignments"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    subject_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subjects.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    device_name: Mapped[str] = mapped_column(unique=True)
    device_type: Mapped[str | None] = mapped_column(default=None)
    location: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(default="registered")
    subject_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("subjects.id"), default=None)
    api_key_hash: Mapped[str | None] = mapped_column(default=None)
    api_key_prefix: Mapped[str | None] = mapped_column(default=None)
    key_rotated_at: Mapped[datetime | None] = mapped_column(default=None)
    last_seen_at: Mapped[datetime | None] = mapped_column(default=None)
    software_version: Mapped[str | None] = mapped_column(default=None)
    model_version: Mapped[str | None] = mapped_column(default=None)
    health_state: Mapped[str] = mapped_column(default="UNKNOWN")
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now)
    revoked_at: Mapped[datetime | None] = mapped_column(default=None)


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id"))
    name: Mapped[str | None] = mapped_column(default=None)
    source_type: Mapped[str | None] = mapped_column(default=None)
    resolution: Mapped[str | None] = mapped_column(default=None)
    fps: Mapped[float | None] = mapped_column(default=None)
    status: Mapped[str | None] = mapped_column(default=None)
    last_frame_at: Mapped[datetime | None] = mapped_column(default=None)


class DeviceHealthSnapshot(Base):
    __tablename__ = "device_health_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id"))
    recorded_at: Mapped[datetime] = mapped_column(default=_now)
    camera_status: Mapped[str | None] = mapped_column(default=None)
    camera_fps: Mapped[float | None] = mapped_column(default=None)
    last_frame_at: Mapped[datetime | None] = mapped_column(default=None)
    inference_latency_ms: Mapped[int | None] = mapped_column(default=None)
    model_loaded: Mapped[bool | None] = mapped_column(default=None)
    cpu_pct: Mapped[float | None] = mapped_column(default=None)
    mem_pct: Mapped[float | None] = mapped_column(default=None)
    temperature_c: Mapped[float | None] = mapped_column(default=None)
    queue_depth: Mapped[int | None] = mapped_column(default=None)
    backend_connectivity: Mapped[str | None] = mapped_column(default=None)
    software_version: Mapped[str | None] = mapped_column(default=None)
    model_version: Mapped[str | None] = mapped_column(default=None)
    computed_state: Mapped[str | None] = mapped_column(default=None)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_event_id: Mapped[uuid.UUID]
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id"))
    subject_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("subjects.id"), default=None)
    track_id: Mapped[int | None] = mapped_column(default=None)
    event_type: Mapped[str] = mapped_column(default="possible_fall")
    state: Mapped[str] = mapped_column(default="PENDING")
    detected_at: Mapped[datetime]
    received_at: Mapped[datetime] = mapped_column(default=_now)
    grace_seconds: Mapped[int] = mapped_column(default=20)
    grace_deadline: Mapped[datetime]
    resolved_at: Mapped[datetime | None] = mapped_column(default=None)
    resolved_by: Mapped[str | None] = mapped_column(default=None)
    confidence: Mapped[float | None] = mapped_column(default=None)
    confidence_calibrated: Mapped[bool] = mapped_column(default=False)
    tier: Mapped[str | None] = mapped_column(default=None)
    model_version: Mapped[str | None] = mapped_column(default=None)
    feature_version: Mapped[str | None] = mapped_column(default=None)
    pose_quality: Mapped[float | None] = mapped_column(default=None)
    legacy: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=_now)


class EventEvidence(Base):
    __tablename__ = "event_evidence"

    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), primary_key=True)
    rapid_motion: Mapped[bool | None] = mapped_column(default=None)
    orientation_change: Mapped[float | None] = mapped_column(default=None)
    body_height_change: Mapped[float | None] = mapped_column(default=None)
    post_event_stillness: Mapped[bool | None] = mapped_column(default=None)
    pose_quality: Mapped[float | None] = mapped_column(default=None)
    evidence_summary: Mapped[str | None] = mapped_column(default=None)
    extra: Mapped[dict | None] = mapped_column(JSONB, default=None)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), unique=True)
    status: Mapped[str] = mapped_column(default="OPEN")
    notification_status: Mapped[str] = mapped_column(default="PENDING")
    created_at: Mapped[datetime] = mapped_column(default=_now)
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), default=None)
    acknowledged_at: Mapped[datetime | None] = mapped_column(default=None)
    dismissed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), default=None)
    dismissed_at: Mapped[datetime | None] = mapped_column(default=None)
    escalated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), default=None)
    escalated_at: Mapped[datetime | None] = mapped_column(default=None)
    escalation_reason: Mapped[str | None] = mapped_column(default=None)


class AlertAction(Base):
    __tablename__ = "alert_actions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    alert_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("alerts.id"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), default=None)
    action: Mapped[str]
    note: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=_now)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"))
    alert_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("alerts.id"), default=None)
    recipient_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    channel: Mapped[str] = mapped_column(default="email")
    provider: Mapped[str | None] = mapped_column(default=None)
    kind: Mapped[str]
    status: Mapped[str] = mapped_column(default="QUEUED")
    attempt_count: Mapped[int] = mapped_column(default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(default=None)
    last_attempt_at: Mapped[datetime | None] = mapped_column(default=None)
    error_code: Mapped[str | None] = mapped_column(default=None)
    delivered_at: Mapped[datetime | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=_now)


class CaregiverFeedback(Base):
    __tablename__ = "caregiver_feedback"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"))
    caregiver_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    label: Mapped[str]
    comment: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), default=None)
    device_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    action: Mapped[str]
    resource_type: Mapped[str | None] = mapped_column(default=None)
    resource_id: Mapped[str | None] = mapped_column(default=None)
    result: Mapped[str]
    request_id: Mapped[str | None] = mapped_column(default=None)
    ip: Mapped[str | None] = mapped_column(default=None)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default=None)
    created_at: Mapped[datetime] = mapped_column(default=_now)
