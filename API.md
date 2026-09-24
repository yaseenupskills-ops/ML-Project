# FallGuard AI API

FastAPI backend for the privacy-preserving fall-detection system. This is the
only contract a frontend needs — build against this file alone.

- Base URL (default): `http://127.0.0.1:8000`
- Run: `uvicorn api.main:app --host 127.0.0.1 --port 8000`
- Interactive docs: `GET /docs` (Swagger UI), `GET /openapi.json`
- CORS: only one origin is allowed, set via the `FRONTEND_ORIGIN` env var
  (default `http://localhost:3000`). Not `*`.
- Privacy: binds `127.0.0.1` by default; no raw video is ever saved unless
  `POST /record/start` is called explicitly, and no video/images ever leave
  the device — only alert text (timestamp, confidence, tier) does, via email.

## Auth model

`GET /me` and every alerts/analytics/recordings endpoint depend on
`get_current_user()`.

- **Default (matches `config.yaml.example` — no `auth:` section, or
  `auth.enabled: false`)**: every request is treated as
  `{"username": "guest", "role": "admin", "display_name": "Guest User"}`.
  No `Authorization` header is needed.
- **If `auth.enabled: true` in `config.yaml`**: every request (except none —
  there is no login endpoint yet) must send
  `Authorization: Bearer <token>`, where `<token>` is an HMAC token of the
  form `username:role:issued_at:signature` (see `services/roles.py`). Missing
  or invalid token → `401`. There is no `/login` endpoint in this version;
  tokens are minted out-of-band. This dependency is intentionally isolated
  so a real auth provider (OAuth/JWT/session) can replace it later without
  touching any endpoint.

### Roles / permissions

| Permission | admin | caregiver | viewer |
|---|---|---|---|
| `can_acknowledge` | yes | yes | no |
| `can_dismiss` | yes | no | no |
| `can_escalate` | yes | yes | no |
| `can_export` | yes | yes | no |
| `can_view_all` | yes | no | no |
| `can_manage_settings` | yes | no | no |

- **admin** (or any role with `can_view_all`) sees every alert.
- **caregiver**/**viewer** only see alerts whose `subject_id` is in
  `config.yaml: auth.role_permissions[<role>]` (default `["S1", "S2", "S3"]`
  if that key is absent). This filter applies to `GET /alerts`,
  `GET /analytics/*`, and `GET /recordings` (its alert-overlay).
- Action endpoints (`PATCH /alerts/{id}`, `POST /alerts/bulk`,
  `GET /analytics/export.csv`) additionally check the specific permission for
  the requested action and return `403` if the role doesn't have it.

## Alert object schema

Every alert record in `logs/alerts.jsonl` is written by `alert.py` with
`fall_event_*`/`grace_period_*` key names; the API renames them before
returning JSON. Fields on every `Alert` returned by this API:

| Field | Type | Notes |
|---|---|---|
| `timestamp` | float | Unix seconds. **This is the alert's id** — used in `PATCH /alerts/{id}` and `POST /alerts/bulk`'s `ids`. |
| `subject_id` | string | e.g. `"S1"`. `"unknown"` if missing. |
| `clip_id` | string | `"N/A"` if missing. |
| `confidence` | float | 0.0–1.0. `0.0` if missing. |
| `tier` | string | `"high" \| "medium" \| "low"`. `"low"` if missing. |
| `outcome` | string | Grace-period outcome: `"cancelled" \| "timeout" \| "error" \| "unknown"`. |
| `response_time` | float \| null | Grace-period response time in **seconds** (time the user had to cancel), not the same as ack response time below. |
| `status` | string | `"pending" \| "acknowledged" \| "dismissed" \| "escalated"`. |
| `acknowledged_by` | string \| null | Username who last acted on the alert. |
| `acknowledged_at` | float \| null | Unix seconds when last acted on. `acknowledged_at - timestamp` is the "response time" analytics uses. |
| `video_clip_path` | string \| null | Local path only; no video is embedded in the API response. |
| `datetime` | string \| null | `timestamp` formatted `"%Y-%m-%d %H:%M:%S"` for display. |

## Endpoints

### `GET /health`
No auth. Liveness/camera check.
```json
{"status": "ok", "camera": true, "time": 1790246285.02}
```
`status` is `"degraded"` if no camera object is initialized yet.

### `GET /metrics`
No auth. Live in-memory metrics (`metrics.py`), refreshed on each call.
```json
{
  "camera_online": true, "camera_available": true, "fps": 24.3,
  "capture_latency_ms": 0.0, "pipeline_latency_ms": 0.0,
  "pipeline_running": false, "frames_processed": 0, "windows_evaluated": 0,
  "alerts_triggered": 0, "fall_candidates": 0, "false_positives_cancelled": 0,
  "recorded_segments": 0, "recording_active": false, "last_frame_ts": 1790246285.0,
  "started_at": 1790246277.0, "last_update": 1790246285.0,
  "uptime_sec": 8.05, "falls_per_min": 0.0, "last_frame_age_sec": 0.1
}
```
Returns `503` if `streaming.enabled: false` in `config.yaml`.

### `GET /alerts`
Auth required. Query params (all optional, combine with AND):

| Param | Type | Meaning |
|---|---|---|
| `tier` | string | exact match: `high`/`medium`/`low` |
| `status` | string | exact match: `pending`/`acknowledged`/`dismissed`/`escalated` |
| `subject_id` | string | case-insensitive exact match |
| `from` | string `YYYY-MM-DD` | inclusive lower bound on `datetime` |
| `to` | string `YYYY-MM-DD` | inclusive upper bound on `datetime` |

Role-filtered first (caregiver/viewer only see their assigned subjects), then
the above filters are applied. Sorted newest-first.

```
GET /alerts?tier=high&status=pending
```
```json
{
  "total": 2,
  "alerts": [
    {"timestamp": 1790237148.94, "subject_id": "S1", "clip_id": "clip_S1",
     "confidence": 0.91, "tier": "high", "outcome": "timeout", "response_time": 30.0,
     "status": "pending", "acknowledged_by": null, "acknowledged_at": null,
     "video_clip_path": "", "datetime": "2026-09-24 08:05:48"}
  ]
}
```

### `PATCH /alerts/{id}`
Auth required + the matching permission (`can_acknowledge`/`can_dismiss`/`can_escalate`).
`{id}` is an alert's `timestamp` (float).

Request:
```json
{"action": "acknowledge"}
```
`action` is one of `acknowledge` | `dismiss` | `escalate` (present tense in
the request; stored `status` is the past-tense form: `acknowledged` /
`dismissed` / `escalated`). `escalate` also re-sends an urgent email to the
configured recipient if `escalation.notify_on_escalate` (default `true`).

Response:
```json
{"ok": true, "timestamp": 1790237148.94, "status": "acknowledged"}
```
`400` for an unrecognized action, `403` if the role lacks permission, `404`
if no alert with that timestamp exists.

### `POST /alerts/bulk`
Auth required + the matching permission. Same action semantics as above,
applied to a batch.

Request:
```json
{"ids": [1790237148.94, 1790159388.94], "action": "escalate"}
```
Response:
```json
{"ok": true, "updated": [1790237148.94, 1790159388.94]}
```
`updated` only lists ids that actually matched an existing alert; unmatched
ids are silently skipped (not an error).

### `GET /analytics/summary`
Auth required. Role-filtered. One bundled payload covering everything the
old dashboard's Analytics page showed except per-subject trends and response
times, which have their own endpoints below.

```json
{
  "total": 6, "pending": 3, "acknowledged": 2, "escalated": 1, "dismissed": 0,
  "high_risk": 3, "high_confidence": 3, "avg_confidence": 0.768,
  "by_tier": {"high": 3, "medium": 2, "low": 1},
  "by_status": {"pending": 3, "acknowledged": 2, "escalated": 1},
  "confidence_histogram": [{"range_pct": "55-60", "count": 1}, "... 20 buckets, 5% wide"],
  "heatmap": ["... 7 arrays (Mon-Sun) x 24 ints (alert count per hour)"],
  "week_over_week": {"this_week": 5, "last_week": 1, "delta": 4, "pct_change": 400.0, "daily_avg": 0.71},
  "escalation_funnel": {
    "stages": [{"stage": "pending", "count": 3}, {"stage": "acknowledged", "count": 2},
               {"stage": "escalated", "count": 1}, {"stage": "dismissed", "count": 0}],
    "acknowledged_rate_pct": 66.7, "escalated_rate_pct": 33.3
  }
}
```
`high_confidence` = count with `confidence >= 0.85`. `heatmap[weekday][hour]`,
`weekday` 0=Monday. Funnel rates are relative to the `pending` count (matches
the original dashboard's funnel math).

### `GET /analytics/subjects`
Auth required. Role-filtered. Per-subject rollup + 14-day trailing trend.
```json
[
  {
    "subject_id": "S1", "alerts": 3, "high_risk": 2,
    "avg_response_min": 1440.1, "escalation_rate_pct": 0.0, "avg_confidence": 0.827,
    "trend": [{"date": "2026-09-11", "count": 0}, "... 14 days, oldest first"]
  }
]
```
`avg_response_min` is `null` if the subject has no acknowledged alerts yet.

### `GET /analytics/response-times`
Auth required. Role-filtered. Time-to-acknowledge stats (minutes) over alerts
that have been actioned (`acknowledged_at` set).
```json
{
  "mean_min": 2880.1, "median_min": 2880.1, "p95_min": 4176.1, "n_actioned": 3,
  "histogram": [{"range_min": "1440-1584", "count": 1}, "... 20 buckets"]
}
```
All three of `mean_min`/`median_min`/`p95_min` are `null` if `n_actioned` is 0.

### `GET /analytics/export.csv`
Auth required + `can_export`. Role-filtered. Streams `text/csv`,
`Content-Disposition: attachment`.

Columns: `datetime, timestamp, subject_id, clip_id, confidence, tier, status,
acknowledged_by, acknowledged_at`.

> **Known quirk, preserved from the original dashboard:** the export column
> list also names `grace_period_outcome`/`grace_period_response_time`, but
> those columns don't exist under those names after the `outcome`/
> `response_time` rename — so they're silently dropped. This was a
> pre-existing bug in `dashboard/app.py`'s CSV export, not something
> introduced by this API; it is reproduced as-is rather than "fixed" as part
> of a behavior-preserving refactor.

### `GET /recordings`
Auth required. Role-filtered alert overlay. Lists recorded segments plus any
alerts whose timestamp falls inside that segment's time window.
```json
[
  {"name": "rec_20260924_160807.mp4", "path": "data/recordings/rec_20260924_160807.mp4",
   "size_mb": 0.13, "created": 1790246289.44,
   "alerts": [{"offset_sec": 12.4, "tier": "high", "subject_id": "S1", "confidence": 0.91, "timestamp": 1790246301.8}]}
]
```
`503` if streaming is disabled.

### `GET /recordings/{name}/info`
No auth (matches the original `stream_server.py` behavior). `{name}` must be
exactly the segment filename, e.g. `rec_20260924_160807.mp4`.
```json
{"name": "rec_20260924_160807.mp4", "size_mb": 0.13, "duration_sec": 2.77,
 "fps": 30.0, "width": 640, "height": 480, "frame_count": 83, "segment_start": 1790246289.44}
```
`404` if the name doesn't exist, doesn't start with `rec_`, or resolves
outside the recordings directory (path-traversal guard).

### `GET /recordings/{name}/video`
**New in this API** (not present in the old `stream_server.py`). Streams the
raw `.mp4` file (`video/mp4`) for playback in a `<video>` element. Same
path-traversal guard as `/info`. `404` on the same conditions.

### `POST /record/start`
No auth. Starts opt-in recording to `data/recordings/` (rotating segments,
default 300s, retained `recording.max_days`, default 7 days).
```json
{"ok": true, "recording": true, "path": "data/recordings", "error": null}
```

### `POST /record/stop`
No auth. Stops recording and finalizes the current segment.
```json
{"ok": true, "recording": false, "path": null, "error": null}
```

### `GET /video_feed`
No auth. MJPEG stream (`multipart/x-mixed-replace; boundary=fallguard-frame`)
for a `<img>` tag. Falls back to a synthetic "LIVE PREVIEW" feed if no real
camera is available or configured (`camera.source: "synthetic"`).

### `GET /frame`
No auth. A single current JPEG frame (`image/jpeg`), for polling-based
preview instead of MJPEG. `503` if no frame is available yet.

### `GET /me`
Auth required (or the default guest/admin — see Auth model above).
```json
{"username": "guest", "role": "admin", "display_name": "Guest User"}
```

## Error shape

All errors use FastAPI's default:
```json
{"detail": "not permitted for this role"}
```
with the corresponding HTTP status code (`400`, `401`, `403`, `404`, `503`).
