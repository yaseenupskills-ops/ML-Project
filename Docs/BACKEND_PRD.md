# Backend PRD — FallGuard Event Platform

**Version:** 1.0
**Derived from:** Master PRD v2.0 (§21–26, 32–36, 39, 50, 52–54, 62 step 9)
**Audience:** Claude Code / engineers implementing the backend
**App name:** "FallGuard" is a placeholder (`APP_NAME`); change it in one place.

---

## 1. Purpose and scope

Build the backend that turns the fall-detection prototype into a multi-device, privacy-preserving event platform:

```text
Edge device (existing ML pipeline)  ──HTTPS, structured events only──►  FastAPI  ►  PostgreSQL
                                                                          │
                                                          worker: email, retry, escalation, health
                                                                          │
                                                                Next.js dashboard (frontend/)
```

### In scope (MVP, Master §54)
- Auth, roles, object-level authorization, audit log
- Subjects, devices (per-device credentials), cameras, caregiver assignments
- Event ingestion from edge devices, 20 s grace-period lifecycle
- Alert workflow: acknowledge / dismiss / escalate, caregiver feedback
- Email notifications with retry and escalation
- Device health monitoring
- Analytics (response time, counts, false-positive feedback)
- Model version registry with human-approved promotion
- One-time import of existing `alerts.jsonl`
- Docker, health checks, CI, structured logs, externalized secrets

### Out of scope (later phases or the ML PRD)
- Dataset ingestion, training, calibration, temporal models, multi-person tracking, pose-quality modeling
- SMS / push / voice, Redis queue (Master §55), WebSockets, MFA
- Raw video, images or face crops of any kind: **never** accepted, stored or served by this backend
- Dataset/sequence/label tables (Master §26 "Dataset" branch)

### Explicit removals
The backend has **no** `/video_feed`, `/frame`, recording, or `/record/*` endpoints. The dashboard is not a video console (Master §32, §40). Any local video preview on the edge stays local-only on `127.0.0.1` and is a dev tool.

---

## 2. Current state (baseline)

- Root-level Python ML modules: `camera.py`, `pose_extraction.py`, `features.py`, `model_rf.py`, `model_cnn_lstm.py`, `decision_logic.py`, `grace_period.py`, `alert.py`, `simulate_stream.py`, `stream_server.py`, `metrics.py`, `evaluate.py`
- Streamlit `dashboard/app.py` holds real logic (alert history loading with `fall_event_*` / `grace_period_*` key mapping, ack/dismiss/escalate, auto-escalate, analytics math, role filtering)
- Alerts in `alerts.jsonl`; email sent from the edge via SMTP in `alert.py`
- Frontend: cleaned Next.js skeleton in `frontend/` (branch `frontend-cleanup`)
- Known debt (Master §43): 5 stale tests in `tests/test_units.py`, dead CLI path `simulate_from_keypoints_file`

**Rule for this PRD:** do not move or rewrite the root ML modules. New code goes in `app/` (see §14). ML restructuring belongs to the ML PRD.

---

## 3. Architecture and boundaries

### 3.1 Components

| Component | Responsibility |
|---|---|
| **API** (`uvicorn app.api.main:app`) | Auth, CRUD, event ingestion, alert workflow, analytics, OpenAPI |
| **Worker** (`python -m app.worker`) | Notification sending + retry, escalation sweeper, grace-deadline sweeper, device-health sweeper, retention cleanup |
| **PostgreSQL 16** | System of record. Also the job queue for MVP (notifications table + `FOR UPDATE SKIP LOCKED`). No Redis in MVP |
| **Edge client** (`app/edge_client/`) | Used by the existing pipeline to post events/heartbeats with a local outbox |
| **SMTP provider** | Configured by env. Credentials never on edge devices and never in git |

### 3.2 Privacy boundary (mandatory)
- Only structured JSON crosses edge → backend: confidence, timestamps, track id, tier, model/feature version, pose quality, evidence flags/summaries.
- API request validation must **reject** unknown large fields and any field that looks like image data (base64 blobs > 4 KB in any string). Request body limit: 64 KB on device endpoints.
- No endpoint returns or accepts images or video.
- Logs must not contain email bodies, passwords, tokens, or API keys.

### 3.3 Technology
Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2 (typed), Alembic, psycopg 3, argon2-cffi, PyJWT, `email` + `smtplib` (via a provider interface), pytest, ruff, Docker Compose. Type hints required.

---

## 4. Roles and permissions

Roles: `admin`, `caregiver`, `ml_engineer`, `operator` (Master §5).

| Resource | admin | caregiver | ml_engineer | operator |
|---|---|---|---|---|
| Users (manage) | full | self only (profile, password) | self | self |
| Subjects | full | read assigned | read (masked, see below) | none |
| Devices | full | read devices of assigned subjects | read | read |
| Device health | read | read (assigned) | read | read |
| Events / alerts | read all, act | read + act on **assigned subjects only** | read-only (masked) | none |
| Cancel a pending event | yes | yes (assigned) | no | no |
| Feedback | read all, write | write on assigned; read own | read all (masked) | none |
| Notifications | read, retry | none | none | read (no recipient/subject content) |
| Analytics | all | assigned subjects only | all (masked) | none |
| Models | read, promote | none | read, register | read |
| Audit logs | read | none | none | none |
| System metrics | read | none | none | read |

**Object-level authorization** is enforced in one place: a query-scoping dependency that every list/detail query passes through. Caregiver access to a subject outside their assignments returns **404**, not 403 (no existence leak).

**Masking for `ml_engineer`:** responses include `subject_id` only; `display_name`, `location_label` and user names/emails are omitted.

**Devices** authenticate with a per-device key (§8.2). A device can only act on its own events.

---

## 5. Domain model and lifecycles

### 5.1 Event (detection lifecycle)

```text
edge decides POSSIBLE_FALL
        │  POST /events
        ▼
     PENDING  (grace_seconds = 20, grace_deadline set by server)
        │
   ┌────┴─────────────────┐
   ▼                      ▼
CANCELLED             CONFIRMED  → alert created → notifications queued
(edge or caregiver    (no cancel by grace_deadline + GRACE_SLACK,
 before deadline)      or edge reports confirmation)
```

- **Backend is authoritative.** The grace-deadline sweeper (runs every 2 s) moves `PENDING → CONFIRMED` at `grace_deadline + GRACE_SLACK` (default 5 s) if no cancel arrived. This also covers an edge device that dies mid-grace-period. Rationale: same rule as Master §21 step 6 (timeout without cancellation = confirmed), biased toward alerting.
- Late cancel (after the event is `CONFIRMED`) → `409 event_already_confirmed`; the caregiver can still dismiss the alert.
- Valid transitions: `PENDING→CANCELLED`, `PENDING→CONFIRMED`. Everything else → `409 invalid_transition`.
- `resolved_by` ∈ `edge | caregiver | backend_timeout`.

### 5.2 Alert (caregiver workflow)
Created atomically when an event becomes `CONFIRMED`.

```text
OPEN ──► ACKNOWLEDGED (terminal)
  ├────► DISMISSED    (terminal)
  └────► ESCALATED ──► ACKNOWLEDGED
```

`escalation_reason` ∈ `manual | auto_timeout | notification_failed`. Auto-escalation: alert stays `OPEN` longer than `ESCALATION_MINUTES` (default 10, configurable) → `ESCALATED` by the sweeper (`escalated_by = null`) and an escalation email is queued.

**Mapping to Master §21 outcomes:** `CANCELLED` = event CANCELLED; `CONFIRMED` = event CONFIRMED; `ESCALATED` = alert ESCALATED; `FAILED_NOTIFICATION` = `alerts.notification_status = FAILED`.

### 5.3 Feedback
Labels: `TRUE_FALL`, `FALSE_POSITIVE`, `UNCERTAIN`, `SYSTEM_FAILURE`. One row per `(event, caregiver)`, upsertable. Never triggers retraining or model changes automatically (Master §28).

### 5.4 Confidence honesty (Master §18)
Every event carries `confidence_calibrated: bool`. Until calibration exists this is `false`, and the API and UI present the value as a **model score**, not a probability.

---

## 6. Database schema

PostgreSQL 16. UUID primary keys (`gen_random_uuid()`), `timestamptz` in UTC, enums as `text` + `CHECK`. Alembic migrations only; no manual DDL.

**users** — `id`, `email` (citext, unique), `name`, `password_hash`, `role`, `status` (active|disabled), `must_change_password` (bool), `notify_email` (bool, default true), `last_login_at`, `created_at`, `updated_at`

**refresh_tokens** — `id`, `user_id`, `token_hash`, `expires_at`, `revoked_at`, `replaced_by`, `created_at`

**subjects** — `id`, `display_name`, `location_label`, `status` (active|inactive), `created_at`, `updated_at`

**caregiver_assignments** — `user_id`, `subject_id`, `created_at`; PK `(user_id, subject_id)`

**devices** — `id`, `device_name` (unique), `device_type`, `location`, `status` (registered|active|revoked), `subject_id` (nullable; one subject per device in MVP, changes go to audit log), `api_key_hash`, `api_key_prefix`, `key_rotated_at`, `last_seen_at`, `software_version`, `model_version`, `health_state` (HEALTHY|DEGRADED|OFFLINE|ERROR|UNKNOWN), `created_at`, `updated_at`, `revoked_at`

**cameras** — `id`, `device_id`, `name`, `source_type` (webcam|usb|csi|rtsp|file), `resolution`, `fps`, `status`, `last_frame_at`

**device_health_snapshots** — `id`, `device_id`, `recorded_at`, `camera_status`, `camera_fps`, `last_frame_at`, `inference_latency_ms`, `model_loaded`, `cpu_pct`, `mem_pct`, `temperature_c`, `queue_depth`, `backend_connectivity`, `software_version`, `model_version`, `computed_state`; index `(device_id, recorded_at DESC)`

**events** — `id`, `client_event_id` (uuid), `device_id`, `subject_id` (resolved from device at ingest), `track_id`, `event_type` (`possible_fall`), `state` (PENDING|CANCELLED|CONFIRMED), `detected_at`, `received_at`, `grace_seconds`, `grace_deadline`, `resolved_at`, `resolved_by`, `confidence`, `confidence_calibrated`, `tier` (low|medium|high), `model_version`, `feature_version`, `pose_quality`, `legacy` (bool), `created_at`; **unique `(device_id, client_event_id)`**; indexes on `(detected_at DESC)`, `(subject_id, detected_at DESC)`, `(state)`

**event_evidence** — `event_id` (PK, FK), `rapid_motion` (bool), `orientation_change` (real), `body_height_change` (real), `post_event_stillness` (bool), `pose_quality` (real), `evidence_summary` (text), `extra` (jsonb, size-capped)

**alerts** — `id`, `event_id` (unique), `status` (OPEN|ACKNOWLEDGED|DISMISSED|ESCALATED), `notification_status` (PENDING|SENT|FAILED), `created_at`, `acknowledged_by`, `acknowledged_at`, `dismissed_by`, `dismissed_at`, `escalated_by`, `escalated_at`, `escalation_reason`; index `(status, created_at DESC)`

**alert_actions** — `id`, `alert_id`, `user_id` (nullable = system), `action`, `note`, `created_at` (drives the detail-page timeline)

**notifications** — `id`, `event_id`, `alert_id`, `recipient_user_id`, `channel` (`email`), `provider`, `kind` (fall_alert|escalation), `status` (QUEUED|SENDING|SENT|FAILED), `attempt_count`, `next_attempt_at`, `last_attempt_at`, `error_code`, `delivered_at`, `created_at`; index `(status, next_attempt_at)`

**caregiver_feedback** — `id`, `event_id`, `caregiver_id`, `label`, `comment`, `created_at`, `updated_at`; unique `(event_id, caregiver_id)`

**model_versions** — `id`, `model_name`, `version`, `model_type` (random_forest|cnn_lstm|tcn|ensemble), `artifact_uri`, `feature_version`, `dataset_version`, `metrics_json` (jsonb), `release_gate` (jsonb), `status` (registered|candidate|approved|production|retired), `created_by`, `created_at`, `approved_by`, `approved_at`; unique `(model_name, version)`

**audit_logs** — `id`, `user_id` (nullable), `device_id` (nullable), `action`, `resource_type`, `resource_id`, `result` (success|failure), `request_id`, `ip`, `metadata` (jsonb), `created_at`

---

## 7. API contract

Base path `/api/v1`. JSON only. OpenAPI at `/docs` and `/openapi.json` (the frontend generates TypeScript types from it).

### 7.1 Conventions
- **Auth:** users via httpOnly cookies; devices via `X-Device-Key` header.
- **Errors:** `{ "error": { "code": "string", "message": "string", "request_id": "string", "details": {} } }`
- **Request id:** accept `X-Request-ID` or generate one; return it in the response header and the error body.
- **Pagination:** `?limit=` (default 25, max 100) and `?offset=`; list responses are `{ "items": [...], "total": n, "server_time": "ISO-8601" }`.
- **Sorting:** `?sort=field` / `?sort=-field` with an allow-list per endpoint.
- **Times:** ISO-8601 UTC with `Z`.
- **Status codes:** 200/201, 204, 400 validation, 401, 403, 404, 409 (state conflicts), 422, 429.
- **Rate limits:** login 5/min per IP+email; users 300/min; devices 120/min; 429 with `Retry-After`.

### 7.2 Endpoints

**Auth**

| Method | Path | Who | Notes |
|---|---|---|---|
| POST | `/auth/login` | public | body `{email, password}`; sets access + refresh cookies |
| POST | `/auth/refresh` | cookie | rotates refresh token |
| POST | `/auth/logout` | user | revokes refresh token, clears cookies |
| GET | `/auth/me` | user | `{id, name, email, role, must_change_password, assigned_subject_ids}` |
| POST | `/auth/change-password` | user | requires current password |

**Users** (admin)

| Method | Path | Notes |
|---|---|---|
| GET, POST | `/users` | create returns a one-time temporary password, `must_change_password = true` |
| GET, PATCH | `/users/{id}` | name, role, status, notify_email |
| POST | `/users/{id}/reset-password` | new one-time temporary password, revokes sessions |
| PUT | `/users/{id}/subjects` | body `{subject_ids: []}` replaces caregiver assignments |

**Subjects**

| Method | Path | Who |
|---|---|---|
| GET | `/subjects` | scoped by role |
| POST | `/subjects` | admin |
| GET, PATCH | `/subjects/{id}` | admin (PATCH); scoped read |

**Devices and cameras**

| Method | Path | Who | Notes |
|---|---|---|---|
| POST | `/devices` | admin | returns the API key **once** |
| GET | `/devices` | scoped | items embed `health: {state, camera_status, model_loaded, last_seen_at}` |
| GET, PATCH | `/devices/{id}` | scoped / admin | PATCH: name, type, location, `subject_id` |
| POST | `/devices/{id}/rotate-key` | admin | returns new key once |
| POST | `/devices/{id}/revoke` | admin | immediate; device gets 401 |
| GET | `/devices/{id}/health` | scoped | `?hours=24` snapshot history + current state |
| POST | `/devices/{id}/cameras` | admin | |
| PATCH | `/cameras/{id}` | admin | |
| POST | `/devices/me/heartbeat` | **device** | health snapshot; returns `{server_time, expected_interval_s}` |

**Events**

| Method | Path | Who | Notes |
|---|---|---|---|
| POST | `/events` | **device** | idempotent on `client_event_id` (duplicate returns 200 with the existing event) |
| GET | `/events/{id}` | device (own) / scoped user | full detail incl. evidence, alert, notifications, feedback, timeline |
| PATCH | `/events/{id}` | **device** | body `{state: "CANCELLED"\|"CONFIRMED", occurred_at}` |
| POST | `/events/{id}/cancel` | caregiver (assigned), admin | valid only while `PENDING` |
| GET | `/events` | scoped user | filters: `state`, `alert_status`, `tier`, `subject_id`, `device_id`, `from`, `to`; items embed `alert` (nullable) and `notification_status` |

**Alerts**

| Method | Path | Notes |
|---|---|---|
| GET | `/alerts` | filters: `status`, `tier`, `subject_id`, `from`, `to` |
| GET | `/alerts/{id}` | |
| POST | `/alerts/{id}/acknowledge` | body `{note?}` |
| POST | `/alerts/{id}/dismiss` | body `{note?}` |
| POST | `/alerts/{id}/escalate` | body `{note?}` |
| POST | `/alerts/bulk` | body `{action, alert_ids[]}`, max 100; returns per-id results, partial success allowed |
| GET | `/alerts/export.csv` | same filters; scoped; columns: datetime, subject, device, confidence, tier, state, status, acknowledged_by, response_time_s, model_version |

**Feedback / notifications**

| Method | Path | Who |
|---|---|---|
| POST | `/caregiver-feedback` | caregiver, admin; body `{event_id, label, comment?}` (upsert) |
| GET | `/caregiver-feedback` | admin, ml_engineer (masked); filters `label`, `from`, `to` |
| GET | `/notifications` | admin, operator (no recipient/subject content); filters `status`, `event_id` |
| POST | `/notifications/{id}/retry` | admin |

**Models**

| Method | Path | Who |
|---|---|---|
| GET | `/models`, `/models/versions` | admin, ml_engineer, operator |
| POST | `/models/register` | ml_engineer, admin |
| GET | `/models/{id}` | admin, ml_engineer, operator |
| POST | `/models/{id}/promote` | **admin only** |

`promote` body: `{release_gate: {dataset_integrity, no_subject_leakage, recall_ok, false_alert_rate_ok, latency_ok, calibration_ok, edge_perf_ok, regression_tests_ok, privacy_review_ok}, approver_note}`. All booleans must be `true`, otherwise `422`. Records `approved_by/at`, audit-logged. Promotion never happens automatically (Master §28, §46).

**Analytics** (scoped; date range `?from=&to=`, default last 30 days)

| Path | Returns |
|---|---|
| `/analytics/summary` | counts: events, confirmed, cancelled, alerts open/acknowledged/dismissed/escalated; response time avg/median/p95 (s); notification failures; false-positive feedback count |
| `/analytics/timeseries` | alerts per day by tier and by status |
| `/analytics/by-subject` | per-subject counts + avg response |
| `/analytics/by-device` | per-device counts, monitored hours, false alerts per monitored hour (admin, ml_engineer) |
| `/analytics/response-times` | histogram buckets |
| `/analytics/feedback` | counts by label; false-positive rate |
| `/analytics/model-distribution` | devices per model version (admin, ml_engineer) |

**System**

| Path | Who | Notes |
|---|---|---|
| GET `/system/health` | public | liveness/readiness: `{status, db, worker_last_tick}`; no sensitive data |
| GET `/system/metrics` | admin, operator | Prometheus text: frames_processed_total (from heartbeats), events_created_total, possible_falls_total, confirmed_falls_total, false_positive_feedback_total, notification_failures_total, api_request_latency, device_disconnects_total |

### 7.3 Key payloads

**Edge → `POST /events`**
```json
{
  "client_event_id": "6f1c1c1e-8a1e-4d0e-9d65-0d7a0c6a0b11",
  "track_id": 2,
  "detected_at": "2026-09-24T10:32:14Z",
  "event_type": "possible_fall",
  "confidence": 0.87,
  "confidence_calibrated": false,
  "tier": "high",
  "model_version": "rf-v2.1.0",
  "feature_version": "features-v2",
  "pose_quality": 0.94,
  "grace_seconds": 20,
  "evidence": {
    "rapid_downward_motion": true,
    "orientation_change": 0.71,
    "body_height_change": 0.58,
    "post_event_stillness": true,
    "summary": "Rapid downward motion, orientation change, post-event inactivity"
  }
}
```
Response `201`: `{ "id", "state": "PENDING", "grace_deadline", "server_time" }`. `device_id` and `subject_id` come from the device key, never from the body.

**Edge → `POST /devices/me/heartbeat`** (every 30 s)
```json
{
  "camera_status": "online",
  "camera_fps": 14.8,
  "last_frame_at": "2026-09-24T10:32:13Z",
  "inference_latency_ms": 22,
  "model_loaded": true,
  "cpu_pct": 41.2,
  "mem_pct": 55.0,
  "temperature_c": 58.5,
  "queue_depth": 0,
  "backend_connectivity": "connected",
  "software_version": "0.9.0",
  "model_version": "rf-v2.1.0"
}
```

**`GET /events/{id}` (user view, abridged)**
```json
{
  "id": "…", "state": "CONFIRMED", "detected_at": "…", "grace_deadline": "…",
  "resolved_at": "…", "resolved_by": "backend_timeout",
  "subject": {"id": "…", "display_name": "Subject-02", "location_label": "Living room"},
  "device": {"id": "…", "device_name": "LivingRoom-Cam-01"},
  "confidence": 0.87, "confidence_calibrated": false, "tier": "high", "track_id": 2,
  "model_version": "rf-v2.1.0", "feature_version": "features-v2", "pose_quality": 0.94,
  "evidence": { "rapid_motion": true, "orientation_change": 0.71, "body_height_change": 0.58,
                "post_event_stillness": true, "evidence_summary": "…" },
  "alert": { "id": "…", "status": "OPEN", "notification_status": "SENT", "acknowledged_by": null,
             "acknowledged_at": null, "response_time_s": null },
  "notifications": [ { "channel": "email", "kind": "fall_alert", "status": "SENT", "attempt_count": 1,
                       "last_attempt_at": "…", "error_code": null } ],
  "feedback": [ { "caregiver_id": "…", "label": "TRUE_FALL", "comment": null, "created_at": "…" } ],
  "timeline": [ { "at": "…", "actor": "system", "action": "event_confirmed", "note": null } ],
  "server_time": "…"
}
```

---

## 8. Authentication and security

### 8.1 Users
- Passwords: argon2id; min length 10; admin-initiated reset only in MVP (no self-service email reset, no MFA)
- Access token JWT, 15 min, in httpOnly + `Secure` (prod) + `SameSite=Lax` cookie; refresh token opaque, 7 days, stored hashed, rotated on use, reuse detection revokes the family
- **Not** localStorage
- CSRF: all non-GET requests must carry `X-CSRF-Token` matching a readable double-submit cookie
- CORS: allow only `CORS_ORIGINS` (default `http://localhost:3000`), `allow_credentials=True`
- Disabled users: existing sessions rejected immediately

### 8.2 Devices
- One key per device: 32+ random bytes, shown once at registration/rotation, stored as SHA-256 hash + short prefix for identification
- Revocation and rotation take effect on the next request
- A device key can only reach: `POST /events`, `PATCH /events/{id}` and `GET /events/{id}` for its own events, and `POST /devices/me/heartbeat`
- Never a shared credential across devices (Master §53)

### 8.3 General
- HTTPS terminated at the reverse proxy in production; API binds `127.0.0.1` in dev
- Input validation on every endpoint, response models on every endpoint (no accidental field leaks)
- Secrets only via env: `DATABASE_URL`, `JWT_SECRET`, `CSRF_SECRET`, `SMTP_*`; `.env.example` committed, `.env` and `config.yaml` gitignored
- The app **refuses to start** in production mode with default/empty secrets
- Audit log (Master §34) for: login success/failure, logout, user create/update/disable/reset, device register/rotate/revoke/assign, subject create/update/assignment, alert acknowledge/dismiss/escalate, event cancel, feedback create, model register/promote, config change, data deletion

---

## 9. Notifications, escalation and background jobs

### 9.1 Email
- Recipients on `CONFIRMED`: users assigned to the subject with `status = active` and `notify_email = true`; if none, all active admins
- Content per Master §22 (subject, device, event time, confidence labeled "model score" while uncalibrated, tier, state, evidence bullets, model version). Links open the dashboard event page; **no unauthenticated action links**
- Provider interface (`EmailProvider`) with SMTP implementation; a `console`/`file` provider for dev and tests

### 9.2 Retry
Attempt schedule: immediately, then +30 s, +2 min, +10 min (jitter ±20 %). After the 4th failure: `notification.status = FAILED`, `alert.notification_status = FAILED`, alert auto-escalates with `escalation_reason = notification_failed`, and an escalation email goes to admins. Every attempt increments `attempt_count` and records `error_code`.

### 9.3 Worker jobs (must never block ingestion, Master §39)

| Job | Interval | Behavior |
|---|---|---|
| Notification dispatcher | 2 s | picks due `QUEUED` rows with `FOR UPDATE SKIP LOCKED`, sends, updates status |
| Grace-deadline sweeper | 2 s | `PENDING` past `grace_deadline + GRACE_SLACK` → `CONFIRMED` (`resolved_by = backend_timeout`), creates alert, queues notifications |
| Escalation sweeper | 30 s | `OPEN` alerts older than `ESCALATION_MINUTES` → `ESCALATED` + escalation email |
| Health sweeper | 15 s | recompute device `health_state`, mark `OFFLINE` per §10 |
| Retention cleanup | daily | delete `device_health_snapshots` older than `HEALTH_RETENTION_DAYS` (default 30), audit logs older than `AUDIT_RETENTION_DAYS` (default 365); events/feedback retention configurable via `EVENT_RETENTION_DAYS` (default: keep) |

All sweepers are idempotent and safe to run in two worker instances at once.

---

## 10. Device health

Snapshot fields follow Master §36. `computed_state` rules (thresholds configurable):

| State | Rule |
|---|---|
| **OFFLINE** | no heartbeat for > 3 × `expected_interval_s` (default 90 s) |
| **ERROR** | `model_loaded = false`, or `camera_status = error` |
| **DEGRADED** | `camera_status != online`, or `camera_fps < 5`, or `inference_latency_ms > 500`, or `queue_depth > 50`, or `backend_connectivity != connected`, or `cpu_pct > 95`, or `mem_pct > 95` |
| **HEALTHY** | none of the above |

- `devices.health_state` and `last_seen_at` update on each heartbeat and in the sweeper
- State changes are recorded in `device_health_snapshots.computed_state` history and as an audit entry
- **Monitored hours** per device = sum of heartbeat intervals where `camera_status = online` and model loaded; used for **false alerts per monitored hour** (feedback `FALSE_POSITIVE` count ÷ monitored hours)

---

## 11. Edge integration (changes to the existing Python pipeline)

New package `app/edge_client/`:
- `EventClient`: `post_event()`, `patch_event()`, `get_event()`, `heartbeat()`, using `BACKEND_URL`, `DEVICE_KEY`
- **Outbox:** local SQLite file (`data/outbox.db`), event JSON only, no frames. Retries with backoff until delivered; preserves `client_event_id`. Buffer cap and age limit configurable (`OUTBOX_MAX_EVENTS`, `OUTBOX_MAX_AGE_HOURS`), oldest dropped and logged when exceeded
- During the grace period the edge polls `GET /events/{id}` every 2 s. If state becomes `CANCELLED` (caregiver cancelled), the edge stops its own timer. A local recovery cancel sends `PATCH {state: CANCELLED}`
- The edge does **not** send email and holds **no** SMTP credentials. Remove SMTP sending from the edge path once the backend notifier is verified; `alert.py`'s email and escalation logic moves to `app/alerts/`
- Edge continues local detection if the backend is unreachable (Master §50)
- Edge config (new env/config keys): `BACKEND_URL`, `DEVICE_KEY`, `HEARTBEAT_INTERVAL_S` (30)

Streamlit `dashboard/` and `stream_server.py` are removed only after: the Next.js dashboard reaches parity for alerts, analytics, and role scoping, and the demo run passes (§14).

---

## 12. Migration from JSONL

`scripts/import_jsonl.py`:
- Reads `alerts.jsonl` and archived alert files; applies the existing key mapping (`fall_event_*` and `grace_period_*` → `subject_id`, `confidence`, `tier`, `outcome`, `response_time`)
- Creates subjects on demand, a placeholder device `legacy-import`, events with `legacy = true`, alerts with statuses mapped from the old ack/dismiss/escalate data, and stores the original record in `event_evidence.extra`
- Idempotent: a stable hash of each record is stored and re-runs skip duplicates
- Prints counts (read / imported / skipped / failed); imported counts must equal the source counts

`scripts/create_user.py` (CLI): create the first admin, and users with roles and subject assignments.

---

## 13. Non-functional requirements

- CRUD response p95 < 500 ms on the dev dataset (Master §49); event ingestion p95 < 200 ms
- Structured JSON logs: `timestamp, service, device_id, event_id, request_id, level, message, error_code`
- `/system/health` used by Docker health checks; graceful shutdown (finish in-flight requests, stop worker loops cleanly)
- Docker Compose services: `db`, `api`, `worker`, plus `mailhog` for dev; volumes for Postgres; env-driven config
- Database backup: documented `pg_dump` procedure and a compose profile/script; restore tested once
- Type hints everywhere; `ruff` clean; OpenAPI accurate (frontend types are generated from it)
- No deployment-specific paths hard-coded; all thresholds in config with the defaults named in this PRD

---

## 14. Repository layout for this work

```text
app/
  api/            # routers, deps (auth, scoping), schemas, main.py
  database/       # models, session, alembic/, repositories
  alerts/         # event lifecycle, alert workflow, notifier, email providers
  edge_client/    # EventClient, outbox
  monitoring/     # health rules, metrics
  config/         # settings (pydantic-settings)
  worker.py
scripts/          # import_jsonl.py, create_user.py
tests/
  unit/  integration/  e2e/
docker/  docker-compose.yml  .env.example
```
Existing root ML modules stay where they are in this phase.

---

## 15. Testing and acceptance

### Required tests
- **Authorization:** caregiver cannot read/act on another subject's event, alert, feedback, analytics, or device (expects 404); ml_engineer responses contain no names; operator cannot read events; device key cannot reach user endpoints; revoked key gets 401
- **Ingestion:** idempotent duplicate returns the same event; unknown/oversized/image-like fields rejected; `device_id` from the body is ignored
- **Lifecycle:** valid and invalid transitions; grace sweeper confirms exactly once with two workers; late cancel returns 409; caregiver cancel during grace works
- **Alerts:** ack/dismiss/escalate rules, bulk partial success, response time computed from alert creation
- **Notifications:** fake SMTP failure → 4 attempts on schedule → FAILED → auto-escalation; recipients selection and fallback to admins
- **Escalation sweeper** honors `ESCALATION_MINUTES`
- **Health:** each state rule; offline detection; monitored-hours math
- **Auth:** refresh rotation and reuse detection; CSRF enforcement; rate limiting; password change; disabled user
- **Migration:** counts match the source; re-run is a no-op
- **Model promotion:** fails with any checklist item false; admin-only; audit entry written
- **Privacy:** no endpoint returns image/video content types; logs contain no secrets

### End-to-end demo (Master §42)
`data/demo/demo_fall.mp4` → detection → possible fall → `POST /events` → `PENDING` with countdown → no cancel → `CONFIRMED` → alert in DB → email captured in MailHog → visible in the dashboard → acknowledge → feedback recorded. A second run cancels during grace and produces no email.

### Definition of done (backend slice of Master §61)
- API authentication and RBAC work; events, feedback, notification status persist in PostgreSQL
- Device and subject assignment work; model version visible on events
- Docker deployment, health checks, CI green, secrets externalized, structured logs
- Raw video never leaves the edge; retention configurable; audit log exists

---

## 16. Build phases (each ends with a passing check and a commit)

| Phase | Deliverable | Done when |
|---|---|---|
| **BE-0** | Stabilize: fix or retire the 5 stale tests, remove the dead CLI path, add CI skeleton | `pytest` green in CI |
| **BE-1** | `app/` skeleton, settings, Docker Compose (db, api, mailhog), Alembic baseline, `/system/health`, request-id + error format, structured logging | compose up gives a healthy API |
| **BE-2** | Schema + migrations, users/auth (cookies, CSRF, refresh), `create_user.py`, audit logging, RBAC + scoping dependency | auth and authorization tests pass |
| **BE-3** | Subjects, devices (keys), cameras, assignments, heartbeat, health rules + sweeper | device lifecycle + health tests pass |
| **BE-4** | Event ingestion, lifecycle, grace sweeper, alert creation, alert actions, bulk, feedback, cancel | lifecycle + alert tests pass |
| **BE-5** | Worker: notifier, retry, escalation, MailHog e2e | notification tests + e2e email pass |
| **BE-6** | Analytics endpoints, CSV export, models registry + promote | analytics matches hand-computed fixtures |
| **BE-7** | Edge client + outbox, wire the existing pipeline, JSONL import | demo e2e passes end to end |
| **BE-8** | Remove Streamlit + `stream_server.py` (after frontend parity), docs (`API.md` from OpenAPI, `DEPLOYMENT.md`, `PRIVACY.md`), backup/restore check | full Definition of done |

The frontend can start at **BE-3** (auth, subjects, devices, health) and needs **BE-4** for alerts and events.

---

## 17. Open decisions (defaults chosen; confirm or change)

| # | Decision | Default in this PRD |
|---|---|---|
| 1 | Backend confirms at deadline if the edge never reports | yes, `GRACE_SLACK = 5 s` |
| 2 | Escalation timeout | 10 min |
| 3 | Escalation recipients | assigned caregivers + admins |
| 4 | Email provider | SMTP (any); Gmail app password only in `.env` |
| 5 | Retention: health 30 d, audit 365 d, events keep | proposed, configurable |
| 6 | One subject per device | yes in MVP |
| 7 | App name | "FallGuard" placeholder |
| 8 | Edge cancel from a local UI | dashboard cancel is required; a local cancel control is optional |
