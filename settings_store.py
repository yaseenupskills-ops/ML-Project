"""Concurrency-safe local stores for care-team contacts and app settings.

Follows the alert_store.py pattern: file locking plus atomic replacement so
the FastAPI server can read/write safely from multiple request handlers.
Both files live under data/ and are runtime state (not config.yaml).
"""

from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

try:  # pragma: no cover - fcntl is available on the supported macOS/Linux hosts
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]


DEFAULT_CONTACTS: list[dict[str, Any]] = [
    {
        "id": "c1",
        "name": "Sarah Miller",
        "role": "Daughter / Primary Caregiver",
        "phone": "(555) 234-5678",
        "email": "sarah.miller@example.com",
        "is_primary": True,
        "badge": "On Duty",
    },
    {
        "id": "c2",
        "name": "Dr. Robert Chen",
        "role": "Primary Care Physician",
        "phone": "(555) 876-5432",
        "email": "dr.chen@oakridgehealth.org",
        "is_primary": False,
        "badge": "Physician",
    },
    {
        "id": "c3",
        "name": "Oakridge Nursing Station",
        "role": "On-Site Nurse Team",
        "phone": "(555) 991-0022",
        "email": "nursing@oakridgecare.com",
        "is_primary": False,
        "badge": "Facility",
    },
    {
        "id": "c4",
        "name": "Emergency Medical Services",
        "role": "Local EMS / 911",
        "phone": "911",
        "email": "",
        "is_primary": False,
        "badge": "Emergency",
    },
]

DEFAULT_SETTINGS: dict[str, Any] = {
    "grace_period_sec": 20,
    "chime_volume": 80,
    "email_alerts": True,
    "sms_alerts": True,
}


class _JsonFileStore:
    """Base class: a locked, atomically-rewritten JSON file."""

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()
        self.lock_path = self.path.with_name(self.path.name + ".lock")

    @contextmanager
    def _locked(self) -> Iterator[None]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+", encoding="utf-8") as lock_file:
            try:
                os.chmod(self.lock_path, 0o600)
            except OSError:
                pass
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if fcntl is not None:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _read_unlocked(self, fallback: Any) -> Any:
        if not self.path.exists():
            return fallback
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except (json.JSONDecodeError, OSError):
            return fallback

    def _write_unlocked(self, payload: Any) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=str(self.path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, self.path)
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass
        finally:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass


class ContactStore(_JsonFileStore):
    """Persisted care-team contacts (data/contacts.json)."""

    def __init__(self, path: str | Path):
        super().__init__(path)
        self.defaults = [dict(c) for c in DEFAULT_CONTACTS]

    def list(self) -> list[dict[str, Any]]:
        with self._locked():
            records = self._read_unlocked(None)
            if not isinstance(records, list):
                records = []
            if not records and not self.path.exists():
                # First run: seed with the historical defaults.
                records = [dict(c) for c in self.defaults]
                self._write_unlocked(records)
            return records

    def add(self, data: dict[str, Any]) -> dict[str, Any]:
        with self._locked():
            records = self._read_unlocked([])
            record = {
                "id": uuid.uuid4().hex[:12],
                "name": str(data.get("name", "")).strip(),
                "role": str(data.get("role", "")).strip() or "Care Team Member",
                "phone": str(data.get("phone", "")).strip(),
                "email": str(data.get("email", "")).strip(),
                "is_primary": bool(data.get("is_primary", False)),
                "badge": str(data.get("badge", "")).strip() or "Care Team",
                "created_at": time.time(),
            }
            records.append(record)
            self._write_unlocked(records)
            return record

    def delete(self, contact_id: str) -> bool:
        with self._locked():
            records = self._read_unlocked([])
            remaining = [r for r in records if str(r.get("id")) != str(contact_id)]
            if len(remaining) == len(records):
                return False
            self._write_unlocked(remaining)
            return True


class SettingsStore(_JsonFileStore):
    """Persisted app settings (data/runtime_settings.json)."""

    RANGES: dict[str, tuple[type, Any, Any]] = {
        "grace_period_sec": (int, 5, 120),
        "chime_volume": (int, 0, 100),
        "email_alerts": (bool, None, None),
        "sms_alerts": (bool, None, None),
    }

    def get(self) -> dict[str, Any]:
        with self._locked():
            stored = self._read_unlocked({})
            if not isinstance(stored, dict):
                stored = {}
        merged = dict(DEFAULT_SETTINGS)
        for key in merged:
            if key in stored:
                merged[key] = stored[key]
        return merged

    def update(self, patch: dict[str, Any]) -> dict[str, Any]:
        with self._locked():
            stored = self._read_unlocked({})
            if not isinstance(stored, dict):
                stored = {}
            for key, value in (patch or {}).items():
                if key not in self.RANGES:
                    continue
                expected, low, high = self.RANGES[key]
                if expected is bool:
                    if not isinstance(value, bool):
                        raise ValueError(f"{key} must be a boolean")
                else:
                    if isinstance(value, bool) or not isinstance(value, (int, float)):
                        raise ValueError(f"{key} must be a number")
                    value = int(value)
                    if not (low <= value <= high):
                        raise ValueError(f"{key} must be between {low} and {high}")
                stored[key] = value
            self._write_unlocked(stored)

        merged = dict(DEFAULT_SETTINGS)
        for key in merged:
            if key in stored:
                merged[key] = stored[key]
        return merged
