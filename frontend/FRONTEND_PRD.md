# Frontend PRD — FallGuard Caregiver & Operations Dashboard

**Version:** 1.0
**Derived from:** Master PRD v2.0 (§5, 22, 29, 32, 40, 41, 44, 54) and `BACKEND_PRD.md` v1.0
**Design source:** `frontend/DESIGN_SYSTEM.md` (visual source of truth)
**Audience:** Claude Code / engineers implementing `frontend/`

---

## 1. Purpose and scope

A web dashboard for caregivers, administrators, ML engineers and operators to respond to possible falls, monitor device health, review analytics, and manage the platform.

### In scope (MVP, Master §54 "Dashboard")
Alerts, event detail, device health, response-time analytics, caregiver feedback, plus the admin screens needed to run the system (devices, subjects, users, models).

### Out of scope
- **Any video, image, thumbnail or face crop.** No live feed, no playback, no snapshots. The dashboard must not become a surveillance console (Master §32, §40).
- ML training dashboards (dataset-wise, subject-wise, calibration curves): Phase 2. MVP shows registered model metrics read-only.
- SMS/push configuration, WebSockets, MFA, dark/light toggle (dark only).

---

## 2. Current state (after cleanup, branch `frontend-cleanup`)

- Next.js App Router + TypeScript + Tailwind 4, design tokens (`ink-*`, `space-*`), fonts wired
- `components/ui/`: `Card, StatCard, Pill, Button, Input, Select, DataTable, EmptyState, Loading, PageHeader`
- `components/layout/`: `Sidebar` (desktop rail + mobile bar, role-filtered), `TopHeaderBar` (role badge + logout)
- `lib/store.ts`: zustand, `user`, `isLoggedIn`, `setUser`, `logout`
- `services/api.ts`: typed fetch wrapper + `ApiError`; `services/auth.ts`: dev-bypass stub
- `app/providers.tsx`: TanStack Query provider
- Routes (placeholders): `/login`, `/app`, `/app/alerts`, `/app/alerts/[id]`, `/app/devices`, `/app/subjects`, `/app/analytics`, `/app/models`, `/app/system`, `/app/settings`
- `types/index.ts`: only `UserRole`

This PRD turns those placeholders into working screens against the backend contract.

---

## 3. Users, roles and access

Roles: `caregiver`, `admin`, `ml_engineer`, `operator`. The server is the authority; the UI only hides what the API would refuse.

| Route | caregiver | admin | ml_engineer | operator |
|---|---|---|---|---|
| `/app` Dashboard | ✓ | ✓ | ✓ | ✓ |
| `/app/alerts`, `/app/alerts/[id]` | ✓ (assigned subjects) | ✓ | ✗ | ✗ |
| `/app/devices` | ✗ | ✓ manage | ✗ | ✓ read-only |
| `/app/subjects` | ✗ | ✓ | ✗ | ✗ |
| `/app/analytics` | ✓ (assigned) | ✓ | ✓ (masked) | ✗ |
| `/app/models` | ✗ | ✓ promote | ✓ read | ✗ |
| `/app/system` | ✓ (assigned devices) | ✓ | ✗ | ✓ |
| `/app/settings` | Profile | Profile, Notifications, Users | Profile | Profile |

Nav items keep the `roles[]` field from the skeleton. A route the user may not access shows a **403 page** (not a redirect loop). Sidebar hides it.

**Masking:** for `ml_engineer` the API omits subject names and locations (analytics and feedback views). The UI must render `Subject ···{last 4 of id}` when `display_name` is absent, and never assume it exists.

The table mirrors the nav `roles[]` already in the skeleton. The API allows slightly broader read access (e.g. operator can read models); widen the nav later only if needed.

---

## 4. Principles

1. **Privacy first:** the app never requests or displays images/video. No third-party analytics scripts, no external fonts other than `next/font`, no external images.
2. **Fail safe, never falsely reassuring:** show stale-data and offline states loudly. An unreachable API must not look like "no alerts".
3. **Honest confidence:** while `confidence_calibrated = false`, label it **"Model score"** with a tooltip "Uncalibrated model score, not a probability" (Master §18). Never show a bare "87% probability".
4. **Cautious wording:** "possible fall", never "diagnosis". No medical claims.
5. **Severity is not color-only:** every tier/state/status pill has an icon and text.
6. **Follow `DESIGN_SYSTEM.md`:** tokens, radii, spacing, component recipes. Use the shared UI kit; no one-off styles for things the kit covers.

---

## 5. Technical requirements

- Next.js (version already in the repo; read `node_modules/next/dist/docs/` first per `AGENTS.md`), TypeScript `strict`, Tailwind 4, `@tanstack/react-query`, `zustand` (session only), `recharts`, `lucide-react`
- **API types generated from the backend OpenAPI** (`openapi-typescript` → `types/api.ts`, script `npm run gen:api`). Do not hand-write response types that the schema already defines
- **Server state lives in TanStack Query;** zustand holds only the session user
- One service module per resource in `services/` (`alerts.ts`, `events.ts`, `devices.ts`, `subjects.ts`, `users.ts`, `analytics.ts`, `models.ts`, `feedback.ts`, `system.ts`), each returning typed data through `services/api.ts`
- Query key convention: `[resource, scope, params]` (e.g. `['events', 'list', filters]`)
- Env: `NEXT_PUBLIC_API_URL` only. The dev-auth bypass from the skeleton must be **compiled out** in production (`process.env.NODE_ENV !== 'production'` guard) and removed once real login works
- Dates: API sends UTC ISO strings; display in the browser's local time with a visible timezone label on detail pages; use one formatter module
- Lint and build clean; no `any`

### Polling and freshness (no WebSockets in MVP)

| Data | Interval |
|---|---|
| Alerts/events list, dashboard "needs attention" | 10 s |
| Event detail while `state = PENDING` | 2 s |
| Event detail otherwise | 15 s |
| Device/health lists | 15 s |
| Analytics | 60 s + manual refresh |

Pause polling when the tab is hidden; refetch on focus. Show "Updated 12 s ago". After **2 consecutive failures**, show a persistent banner: "Connection problem. Data may be out of date." and keep the last data visible but visually marked stale.

---

## 6. Authentication and session

- Login: `POST /auth/login` (cookies set by the server; no tokens in JS). Then `GET /auth/me` fills the store
- App boot: call `/auth/me`; 401 → try `/auth/refresh` once → else redirect to `/login?next=<path>`
- Every non-GET request sends the CSRF header from the double-submit cookie (handled in `services/api.ts`)
- Logout: `POST /auth/logout`, clear query cache and store
- `must_change_password = true` → forced redirect to Settings › Profile › Change password until done
- 403 from API → in-page "not allowed" state; 429 → "Too many attempts, wait N seconds" (use `Retry-After`)
- Session expiry mid-use: modal "Session expired", preserve current path

---

## 7. Screens

Every screen implements **loading (skeleton), empty, error (retry), and stale states**.

### 7.1 Login `/login`
Email + password, show/hide password, inline error ("Invalid email or password", generic on purpose), disabled button while submitting, rate-limit message. No role picker, no registration.
**Done when:** valid login lands on `/app` (or `next`), invalid shows the error, locked-out shows countdown.

### 7.2 Dashboard `/app` (role-adaptive)

Shared top strip: **Live Status** per Master §40, aggregated over the user's visible devices: Camera `ONLINE/OFFLINE`, Model `LOADED/ERROR`, Backend `CONNECTED/DISCONNECTED` (backend state comes from whether the API is reachable). Any non-healthy device turns the strip amber/rose and links to `/app/system`.

**Grace-period banner** (all roles that see events): for every event with `state = PENDING`, a rose banner: "Possible fall · Subject · Device · **0:14** until confirmation" with a **Cancel event** button (caregiver/admin). Countdown uses `grace_deadline` and the API's `server_time` offset, not the browser clock alone. When it resolves, the banner updates to the outcome for 10 s.

| Role | Widgets |
|---|---|
| **caregiver** | StatCards: Open alerts, Escalated, Confirmed today, Avg response time. "Needs attention" list (open + escalated, newest first, tier pill, subject, time, quick **Acknowledge**). Latest system status |
| **admin** | StatCards: Active devices, Offline devices, Events (30 d), Confirmed, False positives (feedback), Notification failures. Alerts-over-time chart. Needs-attention list |
| **operator** | Device health grid (state counts + list of non-healthy devices), notification failure count |
| **ml_engineer** | StatCards: Events, Confirmed, False-positive feedback, Uncertain feedback; model version distribution; link to Models (no event list; their view is aggregate and masked) |

**Data:** `/analytics/summary`, `/alerts?status=OPEN`, `/events?state=PENDING`, `/devices`.
**Done when:** a new confirmed alert appears within one poll interval and the banner countdown matches the server deadline within 1 s.

### 7.3 Alerts `/app/alerts`

Single list backed by `GET /events` (each item embeds its `alert`, nullable).

- **Columns (Master §40):** Timestamp, Subject, Device, Model score, Tier, State, Status (alert status), Acknowledged by, Response time, Model version
- **Filters:** State (All / Pending grace / Cancelled / Confirmed), Alert status, Tier, Date range, Subject, Device. Default filter: `state = CONFIRMED`. Filters persist in the URL query string
- **Sort:** timestamp (default newest first), tier, response time. Server-side pagination (25/page)
- **Row select + bulk bar** (only rows that have an alert): Acknowledge, Dismiss, Escalate → `POST /alerts/bulk`. **Dismiss and Escalate require a confirm dialog** with optional note. Show per-item results on partial failure
- **Row click** → `/app/alerts/[eventId]`
- **Export CSV** button → `GET /alerts/export.csv` with current filters
- New alerts arriving during polling get a brief highlight and an `aria-live="polite"` announcement ("New alert: Subject-02, high")
- Pending-grace banner (as in 7.2) at the top

**Done when:** filters, sort, pagination and bulk actions work against the API; a caregiver never sees another subject's rows.

### 7.4 Event detail `/app/alerts/[id]` (`id` = **event id**)

Per Master §40 "Event Detail" and §41 "Explainable alert evidence":

- **Header:** subject, device, detection timestamp (local + tz), tier pill, state pill, alert status pill
- **Model score:** "Model score 0.87" with the calibration tooltip (§4.3), tier, model version + feature version, track id
- **Why detected** (evidence list, ✓ / — icons): rapid downward movement, significant orientation change, hip/body height reduced, post-event stillness. Pose quality as a percentage bar. Evidence summary text. **No imagery**
- **Grace-period outcome:** cancelled/confirmed, by whom (edge / caregiver / automatic timeout), timestamps
- **Notification status:** per notification: channel, kind, status pill, attempts, last attempt, error code (admin only sees error code)
- **Caregiver response:** acknowledged/dismissed/escalated by whom, when, **response time**
- **Actions:** Acknowledge, Dismiss, Escalate (per alert state rules: buttons disabled with a reason when not allowed); **Cancel event** while `PENDING`
- **Feedback form** (caregiver/admin): radio of `TRUE_FALL`, `FALSE_POSITIVE`, `UNCERTAIN`, `SYSTEM_FAILURE`, optional comment, upsert; show existing feedback
- **Timeline:** chronological list from `timeline[]`

**Done when:** all actions update the page without reload; a PENDING event counts down and flips to its outcome; 404 shows a clean not-found.

### 7.5 Devices `/app/devices` (admin manage, operator read-only)

- **Table:** Name, Type, Location, Status pill (health state), Last seen, Software version, Model version, Subject
- **Register device** dialog (name, type, location, optional subject) → success panel shows the **API key once** with a copy button, a warning ("This key will not be shown again"), and cannot be reopened
- **Detail drawer:** current health snapshot (camera status/fps, last frame, inference latency, model loaded, CPU, memory, temperature, queue depth, backend connectivity), 24 h sparkline(s) from `/devices/{id}/health?hours=24`, cameras list (add/edit), assign subject, **Rotate key** and **Revoke** (both confirm dialogs, rotate shows the new key once)
- Operator: no mutating buttons rendered

**Done when:** register → key shown once → device appears; revoke marks it revoked; health drawer refreshes every 15 s.

### 7.6 Subjects `/app/subjects` (admin)

Table (Display name, Location, Status, Assigned caregivers count, Device). Create/edit dialog. Assign caregivers (multi-select of caregiver users → `PUT /users/{id}/subjects` handled per user, or a subject-side picker calling the same API). Assign device.
**Done when:** a caregiver assigned here sees that subject's events and no others.

### 7.7 Analytics `/app/analytics`

Date range selector (7 / 30 / 90 days / custom), refresh button, all scoped by the server.

- **StatCards:** Total events, Confirmed, Cancelled (false alarms), Open, Escalated, Response time avg / median / p95
- **Charts (recharts):** alerts over time (by tier), state breakdown, response-time histogram, alerts by subject (bar). Admin/ml_engineer additionally: by device / location, feedback breakdown (`TRUE_FALL` vs `FALSE_POSITIVE` vs `UNCERTAIN`), false-alert rate per monitored hour, notification failures, model version distribution
- Chart rules: series colors from `DESIGN_SYSTEM.md` §6; axes labeled with units; each chart has a text summary or table alternative for accessibility; empty state when no data
- **Not shown:** precision/recall/F1/ROC (need labeled evaluation data; these appear on Models)

**Done when:** numbers match `/analytics/*` responses exactly and a caregiver sees only assigned subjects.

### 7.8 Models `/app/models` (admin, ml_engineer)

- **Table:** Model, Version, Type, Feature version, Dataset version, Status pill (`registered/candidate/approved/production/retired`), Created, Approved
- **Detail drawer:** metric tiles for known `metrics_json` keys (`precision`, `recall`, `f1`, `false_alerts_per_hour`, `detection_latency_ms`, `roc_auc`), remaining keys as key/value rows; **release-gate checklist** (9 items from the backend PRD) with pass/fail icons; devices currently running this version (from analytics)
- **Promote** (admin only): confirm dialog that lists the checklist; the button is enabled only when all items are true, with an approver note field. On success show the audit confirmation
- Registration is API/CLI only in MVP; a read-only banner explains this for admins

**Done when:** promote is impossible in the UI with any gate item false and the API's 422 is surfaced clearly if attempted.

### 7.9 System `/app/system`

- **Fleet summary:** counts by `HEALTHY / DEGRADED / OFFLINE / ERROR`
- **Device status cards** (scoped): name, state pill, camera, model, backend connectivity, last seen, "offline for 4 min"
- **Notification failures** (admin, operator): list from `/notifications?status=FAILED` with retry button (admin) — recipients and subject content hidden for operators
- **Backend health:** from `/system/health` (db, worker last tick)
- **Done when:** taking a device offline in the backend turns its card OFFLINE within ~2 poll intervals

### 7.10 Settings `/app/settings` (tabs)

- **Profile (all):** name, email (read-only), change password (current + new, strength hint), sign out
- **Notifications (admin):** shows configured escalation timeout and email provider status (read-only from API config if exposed; otherwise a note that these are set via environment), test-email button if the API offers it
- **Users (admin):** table (Name, Email, Role, Status, Assigned subjects), create user (shows the temporary password once), edit role/status, reset password (temporary password once, confirm), assign subjects
- **Done when:** admin can onboard a caregiver end to end without touching the database

---

## 8. Shared components to add to the UI kit

`Modal/Dialog` (focus trap, Esc), `Drawer`, `ConfirmDialog`, `Toast`, `Tabs`, `Pagination`, `DateRangePicker`, `FilterBar` (URL-synced), `Checkbox`, `Countdown` (server-time based), `TierPill`, `StateBadge`, `HealthDot`, `EvidenceList`, `Timeline`, `CopyOnce` (secret shown once), `StaleBanner`, `LiveStatusStrip`, `Skeleton`, `ErrorState`, `ForbiddenState`, `NotFoundState`.

**Status/tier colors** follow `DESIGN_SYSTEM.md` §8: HIGH rose, MEDIUM amber, LOW cyan; Open amber, Acknowledged emerald, Dismissed slate, Escalated orange; Healthy emerald, Degraded amber, Offline slate, Error rose; Pending-grace rose with `animate-ping` dot.

---

## 9. Accessibility, responsiveness, performance

- Target WCAG 2.1 AA: contrast on the dark theme, visible focus rings (`ring-cyan-500`), full keyboard operation of tables, dialogs, drawers and bulk actions, labelled inputs, `aria-live` for new alerts and countdown milestones (10 s, 5 s), reduced-motion support (disable pings/pulses)
- Mobile-first for the caregiver flow: alerts list becomes cards under `md`; bottom nav from the skeleton; tap targets ≥ 44 px
- Route-level code splitting; charts loaded dynamically; server-side pagination only; skeletons instead of spinners for lists
- Table with 1,000 rows must not be rendered at once (pagination guarantees this)

---

## 10. Backend dependencies by screen

| Screen | Endpoints |
|---|---|
| Login / session | `POST /auth/login`, `/auth/refresh`, `/auth/logout`, `GET /auth/me`, `POST /auth/change-password` |
| Dashboard | `GET /analytics/summary`, `/alerts`, `/events?state=PENDING`, `/devices` |
| Alerts | `GET /events`, `POST /alerts/bulk`, `GET /alerts/export.csv`, `GET /subjects`, `GET /devices` (filter options) |
| Event detail | `GET /events/{id}`, `POST /alerts/{id}/acknowledge|dismiss|escalate`, `POST /events/{id}/cancel`, `POST /caregiver-feedback` |
| Devices | `GET/POST /devices`, `PATCH /devices/{id}`, `GET /devices/{id}/health`, `POST /devices/{id}/rotate-key|revoke`, `POST /devices/{id}/cameras`, `PATCH /cameras/{id}` |
| Subjects | `GET/POST /subjects`, `PATCH /subjects/{id}`, `PUT /users/{id}/subjects` |
| Analytics | `GET /analytics/*` |
| Models | `GET /models`, `/models/{id}`, `POST /models/{id}/promote` |
| System | `GET /devices`, `/notifications`, `POST /notifications/{id}/retry`, `GET /system/health` |
| Settings › Users | `GET/POST /users`, `PATCH /users/{id}`, `POST /users/{id}/reset-password` |

If an endpoint needed by a screen is missing from `BACKEND_PRD.md`, stop and list the gap; do not invent endpoints or mock data in the app.

---

## 11. Testing

- **Unit/component:** Vitest + React Testing Library for UI kit components (pills, countdown, evidence list, confirm dialog, filter bar)
- **API mocking:** MSW **in tests only**, generated from the OpenAPI schema. The running app always talks to the real backend
- **E2E:** Playwright against the docker-compose stack with seeded users (caregiver A with subject 1, caregiver B with subject 2, admin, operator, ml_engineer):
  1. caregiver login → alert appears → acknowledge → feedback submitted → timeline shows both
  2. caregiver A cannot open caregiver B's event (not-found state)
  3. grace-period banner counts down and cancel works; a second event confirms on its own
  4. admin registers a device, key shown once and not retrievable afterwards
  5. operator sees no event/subject content and no mutating controls
  6. API killed → stale banner appears; restored → clears
- **Accessibility:** `axe` checks on login, dashboard, alerts, detail
- CI: lint, typecheck, unit, build; E2E on the compose stack

---

## 12. Build phases (each ends with a passing check and a commit)

Requires the backend phase shown in brackets.

| Phase | Deliverable | Done when | Needs |
|---|---|---|---|
| **FE-0** | `gen:api` script, generated types, service modules skeleton, CSRF + refresh handling in `api.ts`, error/stale plumbing, missing UI-kit components | build + lint pass, types generate from a running API | BE-1 |
| **FE-1** | Real login/session, role guard, 403/404 pages, forced password change, remove dev bypass | login works for all four roles | BE-2 |
| **FE-2** | Devices, Subjects, Settings › Users, Profile | admin onboarding flow works end to end | BE-3 |
| **FE-3** | Alerts list, filters, URL state, bulk actions, CSV, grace banner | alerts list matches API, scoping verified | BE-4 |
| **FE-4** | Event detail, actions, feedback, timeline, cancel | detail e2e passes | BE-4 |
| **FE-5** | Dashboard (role-adaptive), Live Status strip | widgets match analytics numbers | BE-6 |
| **FE-6** | Analytics page + charts | numbers match API, empty/loading/error states | BE-6 |
| **FE-7** | System page, Models page + promote flow | promote gating works | BE-6 |
| **FE-8** | Accessibility pass, mobile polish, E2E suite, README + docs, Streamlit parity checklist | Playwright suite green; parity checklist signed off | BE-7 |

**Streamlit parity checklist (before `dashboard/` is deleted):** alert filters, bulk ack/dismiss/escalate, auto-escalation visible, CSV export, response-time metrics (avg/median/p95), per-subject trends, response-time histogram, role scoping, correct field mapping (subject, confidence, tier, outcome, response time).

---

## 13. Definition of done (frontend slice of Master §61)

- All four roles can log in and see only what they are allowed to
- A caregiver can go from alert to acknowledge to feedback on desktop and mobile
- Grace-period countdown is correct against server time
- Device health and stale-data states are visible and truthful
- No video/image request is ever made by the app (verified in a Playwright network assertion)
- Build, lint, typecheck, unit, E2E and axe checks are green

---

## 14. Open decisions (defaults chosen; confirm or change)

| # | Decision | Default in this PRD |
|---|---|---|
| 1 | Detail route key | event id |
| 2 | Users management location | Settings › Users tab (no new nav item) |
| 3 | Confidence label | "Model score" until the API reports `confidence_calibrated = true` |
| 4 | Real-time updates | polling only in MVP |
| 5 | Timezone display | browser local time, tz label on detail pages |
| 6 | Model registration UI | API/CLI only in MVP |
| 7 | App name | "FallGuard" placeholder |
