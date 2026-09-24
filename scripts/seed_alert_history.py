"""Seed a varied, realistic alert history for demo purposes.

Generated rows mirror the exact schema written by alert.py `AlertManager._log_alert`
plus the status columns managed by `AlertManager.acknowledge_alert`. Run after
`archive_alerts.sh` (or on a cleared logs/alerts.jsonl):

    python scripts/seed_alert_history.py
"""

import json
import math
import random
import time
from pathlib import Path

OUT = Path("logs/alerts.jsonl")

SUBJECT_POOL = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]
CONF_TIERS = [
    (0.14, "low"), (0.15, "low"), (0.28, "low"), (0.37, "low"),
    (0.43, "medium"), (0.47, "medium"), (0.5, "medium"), (0.59, "medium"),
    (0.6, "high"), (0.69, "high"), (0.73, "high"),
]
OUTCOMES = [
    ("timeout", None), ("timeout", None), ("timeout", None),
    ("acknowledged", 8.4), ("acknowledged", 14.7), ("cancelled", 5.2),
]


def gen_row(ts: float, n: int) -> dict:
    subject = random.choice(SUBJECT_POOL)
    conf, tier = random.choice(CONF_TIERS)
    outcome, resp = random.choice(OUTCOMES)
    status = random.choices(
        ["pending", "acknowledged", "dismissed", "escalated"],
        weights=[20, 30, 10, 40],
    )[0]
    acked_by = {"acknowledged": "admin", "dismissed": "caregiver"}.get(status)
    acked_at = ts + resp if (acked_by and resp) else ts + 30 if acked_by else None
    return {
        "timestamp": round(ts, 4),
        "fall_event_timestamp": round(ts - random.uniform(0.5, 3.0), 4),
        "fall_event_subject": subject,
        "fall_event_clip": f"clip_{n % 40 + 1:03d}",
        "fall_event_confidence": round(conf, 3),
        "fall_event_tier": tier,
        "grace_period_outcome": outcome,
        "grace_period_response_time": resp,
        "alert_type": "email",
        "alert_success": True,
        "video_clip_path": "",
        "status": status,
        "acknowledged_by": acked_by,
        "acknowledged_at": round(acked_at, 4) if acked_at else None,
        "acknowledged_by_role": acked_by,
        "logged_locally_only": True,
    }


def main() -> None:
    rng_state_bak = random.getstate()
    random.seed(2026)
    now = time.time()
    rows = []
    for i in range(24):
        for _ in range(random.randint(2, 8)):
            rows.append(gen_row(now - i * 3600 * random.uniform(3, 9), len(rows)))
    # Keep several 'pending' alerts fresh (within the auto-escalation window) so
    # the dashboard shows varied statuses on first render — otherwise stale
    # pending alerts are auto-escalated immediately on page load (180s threshold).
    pending_kept = 0
    for r in rows:
        if r["status"] == "pending" and pending_kept < 6:
            r["timestamp"] = now - random.uniform(0.5, 2.0)
            r["fall_event_timestamp"] = r["timestamp"] - random.uniform(0.5, 1.0)
            pending_kept += 1
    random.setstate(rng_state_bak)
    rows.sort(key=lambda r: r["timestamp"])

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    from collections import Counter
    print(f"Seeded {len(rows)} alerts -> {OUT}")
    print("  subjects:", dict(Counter(r["fall_event_subject"] for r in rows)))
    print("  tiers:", dict(Counter(r["fall_event_tier"] for r in rows)))
    print("  statuses:", dict(Counter(r["status"] for r in rows)))
    print("  confs:", sorted({r["fall_event_confidence"] for r in rows}))


if __name__ == "__main__":
    main()