"""Caregiver subject-scoping (PRD §4), against an in-memory SQLite DB so it
runs without a real Postgres."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.models import CaregiverAssignment, Subject, User
from app.database.scoping import caregiver_subject_ids, ensure_subject_in_scope


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    tables = [User.__table__, Subject.__table__, CaregiverAssignment.__table__]
    User.metadata.create_all(engine, tables=tables)
    session = Session(engine)
    yield session
    session.close()


def _make_caregiver(db: Session) -> User:
    user = User(email="care@test.local", name="Care", role="caregiver",
                password_hash="x", must_change_password=False)
    db.add(user)
    db.commit()
    return user


def _make_subject(db: Session, name: str) -> Subject:
    subject = Subject(display_name=name)
    db.add(subject)
    db.commit()
    return subject


def test_caregiver_subject_ids_returns_only_assigned(db):
    caregiver = _make_caregiver(db)
    assigned = _make_subject(db, "Assigned")
    other = _make_subject(db, "Other")
    db.add(CaregiverAssignment(user_id=caregiver.id, subject_id=assigned.id))
    db.commit()

    ids = caregiver_subject_ids(db, caregiver.id)
    assert ids == {assigned.id}
    assert other.id not in ids


def test_ensure_subject_in_scope_allows_assigned_subject(db):
    caregiver = _make_caregiver(db)
    subject = _make_subject(db, "Assigned")
    db.add(CaregiverAssignment(user_id=caregiver.id, subject_id=subject.id))
    db.commit()

    ensure_subject_in_scope(db, caregiver, subject.id)  # must not raise


def test_ensure_subject_in_scope_returns_404_for_unassigned_subject(db):
    from fastapi import HTTPException

    caregiver = _make_caregiver(db)
    other_subject = _make_subject(db, "Not assigned")

    with pytest.raises(HTTPException) as exc_info:
        ensure_subject_in_scope(db, caregiver, other_subject.id)
    assert exc_info.value.status_code == 404


def test_ensure_subject_in_scope_skips_check_for_non_caregiver_roles(db):
    admin = User(email="admin@test.local", name="Admin", role="admin",
                 password_hash="x", must_change_password=False)
    db.add(admin)
    db.commit()
    subject = _make_subject(db, "Any")

    ensure_subject_in_scope(db, admin, subject.id)  # must not raise, no assignment needed
