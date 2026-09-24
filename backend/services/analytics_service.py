"""Analytics math ported verbatim from dashboard/app.py's render_analytics()
(lines 1055-1300). No streamlit/chart rendering here -- callers turn these
plain dict/list return values into JSON.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

# Same (pre-existing) column list dashboard.app used for the analytics CSV
# export (lines 1114-1116). Note: "grace_period_outcome"/"grace_period_response_time"
# no longer exist post-rename (they became "outcome"/"response_time"), so -- exactly
# as in the original dashboard -- those two columns are silently dropped from the
# export. Preserved as-is; not a new bug introduced by this port.
_EXPORT_COLS = [
    "datetime", "timestamp", "subject_id", "clip_id", "confidence", "tier",
    "status", "acknowledged_by", "acknowledged_at",
    "grace_period_outcome", "grace_period_response_time",
]


def _actioned(df: pd.DataFrame) -> pd.DataFrame:
    actioned = df[df["acknowledged_at"].notna()].copy() if len(df) else df
    if len(actioned):
        actioned["response_sec"] = actioned["acknowledged_at"] - actioned["timestamp"]
        actioned = actioned[actioned["response_sec"] >= 0]
    return actioned


def response_times(df: pd.DataFrame) -> dict:
    """Avg/median/p95 response time (minutes) + histogram (lines 1098-1105, 1289-1299)."""
    actioned = _actioned(df)
    n = len(actioned)
    mean_min = float(actioned["response_sec"].mean()) / 60 if n else None
    median_min = float(actioned["response_sec"].median()) / 60 if n else None
    p95_min = float(actioned["response_sec"].quantile(0.95)) / 60 if n else None
    histogram: List[dict] = []
    if n:
        counts, edges = np.histogram(actioned["response_sec"] / 60, bins=20)
        histogram = [
            {"range_min": f"{int(edges[i])}-{int(edges[i + 1])}", "count": int(counts[i])}
            for i in range(len(counts))
        ]
    return {
        "mean_min": mean_min,
        "median_min": median_min,
        "p95_min": p95_min,
        "n_actioned": n,
        "histogram": histogram,
    }


def confidence_histogram(df: pd.DataFrame) -> List[dict]:
    """Confidence value histogram, 5% buckets (lines 1233-1244)."""
    conf = df["confidence"].dropna() if len(df) else pd.Series(dtype=float)
    if not len(conf):
        return []
    bins = np.arange(0, 1.05, 0.05)
    counts, edges = np.histogram(conf, bins=bins)
    return [
        {"range_pct": f"{int(edges[i] * 100)}-{int(edges[i + 1] * 100)}", "count": int(counts[i])}
        for i in range(len(counts))
    ]


def by_tier(df: pd.DataFrame) -> Dict[str, int]:
    return {k: int(v) for k, v in df["tier"].value_counts().to_dict().items()} if len(df) else {}


def by_status(df: pd.DataFrame) -> Dict[str, int]:
    return {k: int(v) for k, v in df["status"].value_counts().to_dict().items()} if len(df) else {}


def heatmap(df: pd.DataFrame) -> List[List[int]]:
    """Hour x weekday alert-count grid, 7 rows (Mon-Sun) x 24 cols (lines 1165-1194)."""
    valid = df[df["datetime"].notna()].copy() if len(df) else df
    if not len(valid):
        return [[0] * 24 for _ in range(7)]
    valid["hour"] = valid["datetime"].dt.hour
    valid["weekday"] = valid["datetime"].dt.weekday
    grid = valid.groupby(["weekday", "hour"]).size().unstack(fill_value=0)
    grid = grid.reindex(index=range(7), columns=range(24), fill_value=0).astype(int)
    return grid.values.tolist()


def week_over_week(df: pd.DataFrame) -> dict:
    """This-week vs last-week delta (lines 1142-1155)."""
    valid = df[df["datetime"].notna()] if len(df) else df
    now = pd.Timestamp.now().normalize()
    week_ago = now - pd.Timedelta(days=7)
    if len(valid):
        this_week = valid[valid["datetime"] >= week_ago]
        last_week = valid[(valid["datetime"] >= (now - pd.Timedelta(days=14))) & (valid["datetime"] < week_ago)]
    else:
        this_week = last_week = valid
    this_n, last_n = int(len(this_week)), int(len(last_week))
    delta = this_n - last_n
    pct = delta / max(last_n, 1) * 100
    return {"this_week": this_n, "last_week": last_n, "delta": delta, "pct_change": pct, "daily_avg": this_n / 7}


def escalation_funnel(df: pd.DataFrame) -> dict:
    """Pending -> acknowledged -> escalated -> dismissed funnel (lines 1210-1229)."""
    stages = [
        ("pending", int((df["status"] == "pending").sum()) if len(df) else 0),
        ("acknowledged", int((df["status"] == "acknowledged").sum()) if len(df) else 0),
        ("escalated", int((df["status"] == "escalated").sum()) if len(df) else 0),
        ("dismissed", int((df["status"] == "dismissed").sum()) if len(df) else 0),
    ]
    pending_n, acked_n, esc_n = stages[0][1], stages[1][1], stages[2][1]
    return {
        "stages": [{"stage": s, "count": c} for s, c in stages],
        "acknowledged_rate_pct": acked_n / max(pending_n, 1) * 100,
        "escalated_rate_pct": esc_n / max(pending_n, 1) * 100,
    }


def subject_trends(df: pd.DataFrame) -> List[dict]:
    """Per-subject alert count, escalation rate, avg response, 14-day trend (lines 1246-1287)."""
    out: List[dict] = []
    subjects = df["subject_id"].dropna().unique() if len(df) else []
    for sid in subjects:
        sub_df = df[df["subject_id"] == sid]
        acked = _actioned(sub_df)
        avg_resp = float(acked["response_sec"].mean()) / 60 if len(acked) else None
        esc_rate = float((sub_df["status"] == "escalated").mean() * 100) if len(sub_df) else 0.0
        high_risk_n = int((sub_df["tier"] == "high").sum())
        avg_conf = float(sub_df["confidence"].fillna(0).mean())
        valid = sub_df[sub_df["datetime"].notna()].copy()
        trend: List[dict] = []
        if len(valid):
            valid["date"] = valid["datetime"].dt.normalize()
            counts = valid.groupby("date").size()
            idx = pd.date_range(end=pd.Timestamp.now().normalize(), periods=14, freq="D")
            cnt = counts.reindex(idx).fillna(0).astype(int)
            trend = [{"date": d.strftime("%Y-%m-%d"), "count": int(c)} for d, c in zip(idx, cnt.values)]
        out.append({
            "subject_id": str(sid),
            "alerts": int(len(sub_df)),
            "high_risk": high_risk_n,
            "avg_response_min": avg_resp,
            "escalation_rate_pct": esc_rate,
            "avg_confidence": avg_conf,
            "trend": trend,
        })
    return out


def summary(df: pd.DataFrame) -> dict:
    """Aggregate payload for GET /analytics/summary: counts (lines 1081-1095,
    532-537) + breakdown/trend/funnel sections used by the old Analytics page."""
    total = int(len(df))
    return {
        "total": total,
        "pending": int((df["status"] == "pending").sum()) if total else 0,
        "acknowledged": int((df["status"] == "acknowledged").sum()) if total else 0,
        "escalated": int((df["status"] == "escalated").sum()) if total else 0,
        "dismissed": int((df["status"] == "dismissed").sum()) if total else 0,
        "high_risk": int((df["tier"] == "high").sum()) if total else 0,
        "high_confidence": int(df["confidence"].fillna(0).ge(0.85).sum()) if total else 0,
        "avg_confidence": float(df["confidence"].fillna(0).mean()) if total else 0.0,
        "by_tier": by_tier(df),
        "by_status": by_status(df),
        "confidence_histogram": confidence_histogram(df),
        "heatmap": heatmap(df),
        "week_over_week": week_over_week(df),
        "escalation_funnel": escalation_funnel(df),
    }


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    """CSV export (lines 1113-1131), same column selection as the original."""
    export_df = df[[c for c in _EXPORT_COLS if c in df.columns]].copy()
    if "datetime" in export_df.columns:
        export_df["datetime"] = export_df["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
    if "acknowledged_at" in export_df.columns:
        export_df["acknowledged_at"] = pd.to_datetime(
            export_df["acknowledged_at"], unit="s", errors="coerce"
        ).dt.strftime("%Y-%m-%d %H:%M:%S")
    return export_df.to_csv(index=False).encode("utf-8")
