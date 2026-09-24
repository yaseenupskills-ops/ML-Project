"""Event and alert lifecycle (PRD §5.1, §5.2, §9.1).

The backend is authoritative: an event moves PENDING -> CONFIRMED or
PENDING -> CANCELLED exactly once, even if two paths race for it (an edge
device reporting confirmation vs. the grace-deadline sweeper timing out).
That's enforced with a single guarded UPDATE (`WHERE state = 'PENDING'`)
rather than a read-then-write check, so the DB itself picks the one winner
regardless of how many callers/workers attempt it concurrently.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.database.models import Alert, CaregiverAssignment, Event, Notification, User

GRACE_SLACK_SECONDS = 5


def _claim_event(db: Session, event_id: uuid.UUID, new_state: str, resolved_by: str) -> bool:
    """Atomically move an event out of PENDING. Returns True if this call
    was the one that made the transition (False if someone else already
    resolved it first)."""
    result = db.execute(
        text(
            """
            UPDATE events
            SET state = :new_state, resolved_at = :now, resolved_by = :resolved_by
            WHERE id = :event_id AND state = 'PENDING'
            """
        ),
        {
            "new_state": new_state,
            "now": datetime.now(timezone.utc),
            "resolved_by": resolved_by,
            "event_id": event_id,
        },
    )
    return result.rowcount == 1


def _select_notification_recipients(db: Session, subject_id: uuid.UUID | None) -> list[User]:
    """PRD §9.1: users assigned to the subject with status=active and
    notify_email=true; if none, all active admins."""
    recipients: list[User] = []
    if subject_id is not None:
        recipients = list(
            db.execute(
                select(User)
                .join(CaregiverAssignment, CaregiverAssignment.user_id == User.id)
                .where(
                    CaregiverAssignment.subject_id == subject_id,
                    User.status == "active",
                    User.notify_email.is_(True),
                )
            ).scalars()
        )
    if recipients:
        return recipients
    return list(
        db.execute(select(User).where(User.role == "admin", User.status == "active")).scalars()
    )


def confirm_event(db: Session, event: Event, resolved_by: str) -> Alert | None:
    """Try to move `event` PENDING -> CONFIRMED. On success, atomically
    creates the Alert and queues notifications. Returns None if the event
    was already resolved by someone else (safe to call from a race)."""
    if not _claim_event(db, event.id, "CONFIRMED", resolved_by):
        db.commit()
        return None

    db.refresh(event)

    alert = Alert(event_id=event.id)
    db.add(alert)
    db.flush()

    for recipient in _select_notification_recipients(db, event.subject_id):
        db.add(
            Notification(
                event_id=event.id,
                alert_id=alert.id,
                recipient_user_id=recipient.id,
                kind="fall_alert",
            )
        )

    db.commit()
    db.refresh(alert)
    return alert


def cancel_event(db: Session, event: Event, resolved_by: str) -> bool:
    """Try to move `event` PENDING -> CANCELLED. Returns True on success,
    False if it was already resolved (caller should re-check event.state
    to decide between 409 event_already_confirmed vs. already cancelled)."""
    claimed = _claim_event(db, event.id, "CANCELLED", resolved_by)
    db.commit()
    if claimed:
        db.refresh(event)
    return claimed
