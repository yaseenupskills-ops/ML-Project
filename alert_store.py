"""Small, concurrency-safe local alert store.

The original dashboard used a JSONL file as both an append-only event log and a
mutable table.  Reads/writes could race, and float timestamps were used as
identifiers.  This module keeps the JSONL format for compatibility while adding
stable IDs, file locking, and atomic replacement for updates.
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


class AlertStore:
    """Read and update a local ``alerts.jsonl`` file safely."""

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

    @staticmethod
    def _line_id(record: dict[str, Any], index: int) -> str:
        value = record.get("id") or record.get("alert_id")
        if value:
            return str(value)
        # Legacy records do not have IDs. Include the line number so duplicate
        # timestamps remain independently addressable.
        timestamp = record.get("timestamp", "unknown")
        return f"legacy-{index}-{timestamp}"

    def _read_unlocked(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for index, line in enumerate(handle):
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(item, dict):
                    continue
                if not item.get("id"):
                    item["id"] = self._line_id(item, index)
                records.append(item)
        return records

    def _write_unlocked(self, records: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=str(self.path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                for record in records:
                    handle.write(json.dumps(record, separators=(",", ":")) + "\n")
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

    def read_all(self) -> list[dict[str, Any]]:
        with self._locked():
            return self._read_unlocked()

    def get(self, alert_id: str) -> dict[str, Any] | None:
        with self._locked():
            for record in self._read_unlocked():
                if str(record.get("id")) == str(alert_id):
                    return record
        return None

    def append(self, record: dict[str, Any]) -> str:
        """Append a record and return its stable ID."""

        with self._locked():
            record = dict(record)
            if not record.get("id"):
                record["id"] = uuid.uuid4().hex
            record.setdefault("created_at", time.time())
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, separators=(",", ":")) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass
            return str(record["id"])

    def update(
        self,
        *,
        alert_id: str | None = None,
        timestamp: float | None = None,
        action: str,
        user: str = "system",
        role: str = "system",
        extra_updates: dict[str, Any] | None = None,
    ) -> bool:
        """Update one alert, returning whether a record was changed.

        ``action`` is intentionally constrained to the workflow states used by
        the application.  A caller must use an ID for new records; timestamp is
        retained only as a compatibility fallback for legacy callers.
        """

        allowed_actions = {"acknowledged", "dismissed", "escalated", "cancelled"}
        if action not in allowed_actions:
            raise ValueError(f"Unsupported alert action: {action}")

        changed = False
        with self._locked():
            records = self._read_unlocked()
            for record in records:
                matches_id = alert_id is not None and str(record.get("id")) == str(alert_id)
                try:
                    matches_time = (
                        alert_id is None
                        and timestamp is not None
                        and abs(float(record.get("timestamp", 0)) - float(timestamp)) < 0.01
                    )
                except (TypeError, ValueError):
                    matches_time = False
                if not (matches_id or matches_time):
                    continue
                current_status = record.get("status", "pending")
                if current_status != "pending" and not (
                    action == current_status and extra_updates
                ):
                    continue
                if matches_time and changed:
                    # Legacy timestamp fallback must never update duplicate
                    # records in one call; new callers should use IDs.
                    continue
                record["status"] = action
                now = time.time()
                record["updated_at"] = now
                if action == "escalated":
                    record["escalated_by"] = user
                    record["escalated_by_role"] = role
                    record["escalated_at"] = now
                else:
                    record["acknowledged_by"] = user
                    record["acknowledged_by_role"] = role
                    record["acknowledged_at"] = now
                if extra_updates:
                    record.update(extra_updates)
                changed = True
            if changed:
                self._write_unlocked(records)
        return changed

    def update_many(
        self,
        alert_ids: list[str],
        *,
        action: str,
        user: str = "system",
        role: str = "system",
        extra_updates: dict[str, Any] | None = None,
    ) -> list[str]:
        """Update a set of alert IDs and return the IDs actually changed."""

        if action not in {"acknowledged", "dismissed", "escalated", "cancelled"}:
            raise ValueError(f"Unsupported alert action: {action}")
        targets = {str(alert_id) for alert_id in alert_ids}
        if not targets:
            return []

        changed: list[str] = []
        with self._locked():
            records = self._read_unlocked()
            for record in records:
                alert_id = str(record.get("id"))
                if alert_id not in targets:
                    continue
                if record.get("status", "pending") != "pending":
                    continue
                record["status"] = action
                now = time.time()
                record["updated_at"] = now
                if action == "escalated":
                    record["escalated_by"] = user
                    record["escalated_by_role"] = role
                    record["escalated_at"] = now
                else:
                    record["acknowledged_by"] = user
                    record["acknowledged_by_role"] = role
                    record["acknowledged_at"] = now
                if extra_updates:
                    record.update(extra_updates)
                changed.append(alert_id)
            if changed:
                self._write_unlocked(records)
        return changed
