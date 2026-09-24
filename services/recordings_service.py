"""Recording listing, alert-to-recording mapping, and video metadata,
ported from dashboard/app.py (_map_alerts_to_recordings/_parse_segment_start,
lines 839-885) and stream_server.py (_handle_recording_info, lines 394-431).
Reuses camera.py as-is for the actual file listing.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import pandas as pd

import camera as camera_module


def parse_segment_start(name: str) -> Optional[float]:
    """Parse segment start unix time from `rec_YYYYMMDD_HHMMSS.mp4`."""
    try:
        stem = name.split(".mp4", 1)[0]
        if not stem.startswith("rec_"):
            return None
        return datetime.strptime(stem[4:], "%Y%m%d_%H%M%S").timestamp()
    except Exception:
        return None


def list_recordings(rec_path: Path) -> List[dict]:
    return camera_module.CameraManager.list_recordings(rec_path)


def map_alerts_to_recordings(
    alerts_df: pd.DataFrame, recordings: list, segment_duration: float = 300.0
) -> Dict[str, list]:
    """Map alerts to recording segments by timestamp correlation (verbatim
    port of dashboard._map_alerts_to_recordings, lines 850-885)."""
    if alerts_df is None or len(alerts_df) == 0 or not recordings:
        return {}
    mapping: Dict[str, list] = {}
    idx_by_name = {}
    for rec in recordings:
        name = rec.get("name", "")
        seg_start = parse_segment_start(name)
        if seg_start is None:
            continue
        idx_by_name[name] = (seg_start, seg_start + max(float(segment_duration), 1.0))
        mapping.setdefault(name, [])
    if not idx_by_name:
        return mapping
    for _, row in alerts_df.iterrows():
        ts = float(row.get("timestamp") or 0)
        if ts <= 0:
            continue
        for name, (lo, hi) in idx_by_name.items():
            if lo <= ts < hi:
                mapping[name].append({
                    "offset_sec": round(ts - lo, 2),
                    "tier": str(row.get("tier", "low")),
                    "subject_id": str(row.get("subject_id", "unknown")),
                    "confidence": float(row.get("confidence", 0) or 0),
                    "timestamp": ts,
                })
                break
    return {k: v for k, v in mapping.items() if v}


def safe_recording_path(rec_path: Path, name: str) -> Optional[Path]:
    """Path-traversal guard, identical to stream_server._handle_recording_info
    (lines 407-415): resolved path must stay under rec_path and start with rec_."""
    p = (rec_path / name).resolve()
    if rec_path.resolve() not in p.parents or not p.name.startswith("rec_"):
        return None
    if not p.exists():
        return None
    return p


def recording_info(rec_path: Path, name: str) -> Optional[dict]:
    """Video metadata for one segment (duration/fps/dims), same computation as
    stream_server._handle_recording_info (lines 407-431)."""
    p = safe_recording_path(rec_path, name)
    if p is None:
        return None
    seg_start = parse_segment_start(p.name)
    cap = cv2.VideoCapture(str(p))
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps if fps > 0 else 0.0
        return {
            "name": p.name,
            "size_mb": round(p.stat().st_size / 1024 / 1024, 2),
            "duration_sec": round(max(dur, 0.0), 2),
            "fps": round(fps, 2),
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0),
            "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0),
            "segment_start": seg_start,
        }
    finally:
        cap.release()
