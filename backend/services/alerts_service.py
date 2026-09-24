"""Alert business logic ported from dashboard/app.py (non-UI parts only).

Covers: JSONL loading + field remap, filtering, single/bulk
acknowledge-dismiss-escalate, and auto-escalation of stale pending alerts.
No streamlit import anywhere in this module.
"""
from __future__ import annotations

from typing import List, Optional

import pandas as pd

from alert import AlertManager
from services.alert_repository import AlertRepository

# Exact mapping dashboard.app.load_alert_history used (lines 279-286) so real
# values (confidence, tier, subject) surface instead of defaults.
_RENAME_MAP = {
    "fall_event_subject": "subject_id",
    "fall_event_clip": "clip_id",
    "fall_event_confidence": "confidence",
    "fall_event_tier": "tier",
    "grace_period_outcome": "outcome",
    "grace_period_response_time": "response_time",
}

_DEFAULTS = {
    "subject_id": "unknown",
    "clip_id": "N/A",
    "confidence": 0.0,
    "tier": "low",
    "outcome": "unknown",
    "response_time": None,
    "status": "pending",
    "acknowledged_by": None,
    "acknowledged_at": None,
    "video_clip_path": None,
}

_EMPTY_COLS = [
    "datetime", "timestamp", "subject_id", "clip_id", "confidence", "tier",
    "outcome", "response_time", "status", "acknowledged_by", "acknowledged_at",
    "video_clip_path",
]


def load_alert_history(repo: AlertRepository) -> pd.DataFrame:
    """Load alerts.jsonl and remap fall_event_*/grace_period_* keys (dashboard.app.load_alert_history)."""
    records = repo.load_all()
    if not records:
        return pd.DataFrame(columns=_EMPTY_COLS)
    df = pd.DataFrame(records).rename(columns=_RENAME_MAP)
    if "timestamp" in df.columns:
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="s", errors="coerce")
    else:
        df["datetime"] = pd.NaT
    for col, default in _DEFAULTS.items():
        if col not in df.columns:
            df[col] = default
        if default is not None:
            df[col] = df[col].fillna(default)
    return df.sort_values("datetime", ascending=False, na_position="last").reset_index(drop=True)


def filter_alerts(
    df: pd.DataFrame,
    *,
    tier: Optional[str] = None,
    status: Optional[str] = None,
    subject_id: Optional[str] = None,
    date_from=None,
    date_to=None,
) -> pd.DataFrame:
    """Mirror render_alerts_page's tier/status/date/subject filters (lines 567-581)."""
    out = df
    if tier:
        out = out[out["tier"] == tier]
    if status:
        out = out[out["status"] == status]
    if subject_id:
        out = out[out["subject_id"].astype(str).str.lower() == subject_id.lower()]
    if date_from is not None:
        out = out[out["datetime"].dt.normalize() >= pd.Timestamp(date_from)]
    if date_to is not None:
        out = out[out["datetime"].dt.normalize() <= pd.Timestamp(date_to)]
    return out


def acknowledge_one(repo: AlertRepository, timestamp: float, user: str, role: str, action: str) -> bool:
    """action: 'acknowledged' | 'dismissed' (dashboard.render_alert_detail ack/dismiss buttons, lines 481-495)."""
    return repo.update_one(timestamp, user, role, action)


def bulk_update(repo: AlertRepository, timestamps: List[float], user: str, role: str, action: str) -> List[float]:
    """'acknowledged' | 'dismissed' bulk actions (render_alerts_page lines 658-667)."""
    return repo.update_many(timestamps, user, role, action)


def escalate_with_notify(
    repo: AlertRepository, timestamps: List[float], user: str, role: str, notify: bool = True
) -> List[float]:
    """Mirror dashboard._escalate_alerts (lines 247-257): bulk-escalate then
    re-send an urgent email per updated alert."""
    updated = repo.update_many(timestamps, user, role, "escalated")
    if notify and updated:
        manager = AlertManager()
        for ts in updated:
            manager.send_escalation_email(repo.log_path, ts)
    return updated


def auto_escalate_stale(repo: AlertRepository, max_age_sec: float, notify: bool = False) -> List[float]:
    """Mirror dashboard._auto_escalate_stale (lines 221-244), using
    AlertManager.auto_escalate_stale's file-level scan directly."""
    if max_age_sec <= 0:
        return []
    updated = repo.auto_escalate_stale(max_age_sec, "system", "system")
    if notify and updated:
        manager = AlertManager()
        for ts in updated:
            manager.send_escalation_email(repo.log_path, ts)
    return updated
