#!/usr/bin/env python
"""Create the first admin, or any user with a role and optional subject
assignments (PRD §12). Prints the one-time temporary password.

Usage:
  python scripts/create_user.py --email a@b.com --name "Admin" --role admin
  python scripts/create_user.py --email c@b.com --name "Care" --role caregiver \
      --subject-id <uuid> --subject-id <uuid>
"""

import argparse
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.database.models import CaregiverAssignment, Subject, User
from app.database.session import SessionLocal
from app.security.passwords import generate_temporary_password, hash_password

VALID_ROLES = {"admin", "caregiver", "ml_engineer", "operator"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", required=True, choices=sorted(VALID_ROLES))
    parser.add_argument(
        "--subject-id", action="append", default=[], dest="subject_ids",
        help="repeatable; only meaningful for --role caregiver",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if db.execute(select(User).where(User.email == args.email)).scalar_one_or_none():
            print(f"error: a user with email {args.email} already exists", file=sys.stderr)
            return 1

        subject_ids = [uuid.UUID(s) for s in args.subject_ids]
        if subject_ids:
            found = set(
                db.execute(select(Subject.id).where(Subject.id.in_(subject_ids))).scalars()
            )
            missing = set(subject_ids) - found
            if missing:
                print(f"error: unknown subject ids: {sorted(str(s) for s in missing)}", file=sys.stderr)
                return 1

        temp_password = generate_temporary_password()
        user = User(
            email=args.email,
            name=args.name,
            role=args.role,
            password_hash=hash_password(temp_password),
            must_change_password=True,
        )
        db.add(user)
        db.flush()

        for subject_id in subject_ids:
            db.add(CaregiverAssignment(user_id=user.id, subject_id=subject_id))

        db.commit()

        print(f"Created user {user.email} ({user.role}), id={user.id}")
        print(f"Temporary password (change on first login): {temp_password}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
