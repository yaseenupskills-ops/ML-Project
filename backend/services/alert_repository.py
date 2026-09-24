"""Alert storage abstraction over alerts.jsonl.

All actual file I/O is delegated to alert.AlertManager's existing static
methods (acknowledge_alert/bulk_update_alerts/read_alerts/auto_escalate_stale)
so there is exactly one place that parses/rewrites the JSONL file.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from alert import AlertManager

DEFAULT_ALERT_LOG = Path("logs/alerts.jsonl")


class AlertRepository(ABC):
    """Storage-agnostic interface so a real database can replace JSONL later."""

    @abstractmethod
    def load_all(self) -> List[dict]:
        ...

    @abstractmethod
    def update_one(self, timestamp: float, user: str, role: str, action: str) -> bool:
        ...

    @abstractmethod
    def update_many(self, timestamps: List[float], user: str, role: str, action: str) -> List[float]:
        ...

    @abstractmethod
    def auto_escalate_stale(self, max_age_sec: float, user: str = "system", role: str = "system") -> List[float]:
        ...


class JsonlAlertRepository(AlertRepository):
    """JSONL-backed implementation (logs/alerts.jsonl, same path as today). No Postgres yet."""

    def __init__(self, log_path: Path = DEFAULT_ALERT_LOG):
        self.log_path = Path(log_path)

    def load_all(self) -> List[dict]:
        return AlertManager.read_alerts(self.log_path)

    def update_one(self, timestamp: float, user: str, role: str, action: str) -> bool:
        return AlertManager.acknowledge_alert(self.log_path, timestamp, user, role, action)

    def update_many(self, timestamps: List[float], user: str, role: str, action: str) -> List[float]:
        return AlertManager.bulk_update_alerts(self.log_path, timestamps, user, role, action)

    def auto_escalate_stale(self, max_age_sec: float, user: str = "system", role: str = "system") -> List[float]:
        return AlertManager.auto_escalate_stale(self.log_path, max_age_sec, user, role)
