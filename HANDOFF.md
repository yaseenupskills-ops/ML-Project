# Progress Handoff — Fall Detection Project

> **Current implementation note:** The dashboard now has stable alert IDs,
> live grace-period cancellation, local authenticated stream endpoints, and a
> caregiver Overview page. The saved evaluation artifact remains provisional
> until actor-level data provenance and held-out subject splits are regenerated.

Last updated: 2026-09-23 (Demo-mode video source session)

## Goal (as of now)
Dashboard phases 1–4 done + verified. NEW: demo-mode video source (`camera.source`) added for live presentation.

## Current status
### Demo-mode video source (NEW this session): DONE & verified
- `config.yaml`: added `camera.source` (int = webcam index | str = file path | str = RTSP). `camera.index` kept as deprecated fallback. Default is `0` (webcam).
- `dashboard/app.py` `_stream_server_config()`: reads `cam.get("source", cam.get("index", 0))` → passes single `source` into stream server config.
- `stream_server.py` `_ensure_camera()`: `src = cam_cfg.get("source", cam_cfg.get("index", 0))`; `_probe_camera()` now forwards `loop=video.loop, real_time=video.real_time`.
- `camera.py` `create_camera()`: pops `loop`/`real_time` kwargs for webcam/RTSP (CameraManager doesn't accept them); passes them only to `VideoFileCamera`.
- `camera.py` `VideoFileCamera._capture_loop()`: real-time throttle now uses the video's **native** FPS (`video_fps`), not config target FPS — keeps grace-period timing wall-clock-aligned for file sources.
- `simulate_stream.py`:
  - `run_live_detection()` now builds camera via `create_camera()` using `camera.source` (fallback `camera.index`); added optional `camera_source` arg; source label derived from cam attrs.
  - Fixed pre-existing `UnboundLocalError`: `cam_config` was referenced after the `camera_obj` branch that skipped defining it (2 spots).
  - Fixed pre-existing `NameError`: `run_live_detection` used `simulate_grace_period` without import (only a local import existed in `process_keypoint_sequence`). Moved `simulate_grace_period` to module-level import, removed the local one.
  - `--video` CLI now actually passes the created `VideoFileCamera` via `camera_obj=` (was created but never used before).
- Demo video built: `data/demo/demo_fall.mp4` (65 frames @ 30fps, 640x480, 2.2s) from UR Fall Detection Dataset `fall-02` clip (trimmed frames 45→109 so the fall peak lands mid-clip; loops for a continuous demo).

Verified:
- `py_compile` all modules + `tests/test_system.py` all pass.
- `create_camera()` returns: `CameraManager` for `0`, `VideoFileCamera` (loop+real_time=True) for file, `CameraManagerRTSP` for rtsp://.
- StreamServer probe with demo file → `VideoFileCamera`, native fps 30, duration 2.17s.
- Manual demo run (`simulate_stream.py --video data/demo/demo_fall.mp4`): detected fall candidate → 20s grace period → alert triggered. Repeated **7x over ~28s** proving looping (`cap.set(POS_FRAMES,0)`) + FPS-sync keep pipeline live.
- Config restored to `camera.source: 0`; `_ensure_camera()` opens real `CameraManager` webcam (hardware present).

How to run the demo (tomorrow):
```
# 1) back up current config
cp config.yaml /tmp/config.yaml.bak
# 2) set camera.source to the demo file (edit config.yaml)
#    camera:
#      source: "data/demo/demo_fall.mp4"
# 3) run the dashboard
streamlit run dashboard/app.py
# 4) restore webcam mode
cp /tmp/config.yaml.bak config.yaml
```
CLI-only alternative: `python simulate_stream.py --video data/demo/demo_fall.mp4 models/rf_baseline.joblib`

### Phase 4 Sprint 1 (Analytics, caregiver-only): DONE & verified
Decisions honored: no accuracy metrics (no ground-truth label in `alerts.jsonl` — only ack/dismiss workflow data, not confirmed-fall/false-positive), no role-gated toggle views, CSV only, time-to-acknowledge prioritized over heatmap, per-subject trends instead of heatmap, reporting boundary NOT built.

Changes in `dashboard/app.py` `render_analytics()`:
1. **CSV export** — `st.download_button` above tabs; exports role-filtered alerts as CSV with human-readable `datetime`/`acknowledged_at` (unix→string); columns: datetime, timestamp, subject_id, clip_id, confidence, tier, status, acknowledged_by, acknowledged_at, grace_period_outcome, grace_period_response_time.
2. **Response-time metrics row** — Avg/Median/P95 response (minutes) from `acknowledged_at - timestamp` for actioned alerts (filtered to `>= 0`), plus Actioned-alerts count.
3. **Per-subject trend cards** — Subjects tab now renders a bordered container per subject: 14-day line chart (aggregated daily, `reindex` to trailing 14 days), metrics sub-row (Alerts, High-risk, Avg response, Escalation %).
4. **Response tab** — 5th tab with histogram of response-time distribution (20 bins, minutes).

Verified:
- `py_compile` + `tests/test_system.py` pass.
- AppTest (admin) Analytics page: 9 metric cells correct (16 total / 0 high-risk / 6 pending / 6 escalated / avg resp 1396.2m / median 123.4m / p95 3462.9m / 10 actioned), 5 tabs, Download button present, subject card renders.
- CSR CSV validated: 16 rows, headers correct, parse-back OK.
- AppTest caregiver: role filter yields empty state ("Analytics will appear once alerts...") — correct, no exceptions.

## How to run
```
cd "/Users/yaseensmac/Documents/ML Project"
source .venv/bin/activate
python -m py_compile dashboard/app.py alert.py stream_server.py simulate_stream.py metrics.py grace_period.py camera.py
PYTHONPATH=. python tests/test_system.py
python -m pyflakes dashboard/app.py stream_server.py   # benign: 2 unused imports + 1 dead local
streamlit run dashboard/app.py          # Analytics page to review sprint 1 additions
```

## Known issues / caveats
- `tests/test_units.py`: 5 pre-existing stale failures (old MediaPipe `.pose` + hardcoded conf thresholds). Unrelated to our work.
- Streamlit 1.63: `st.components.v1.html` deprecated → use `st.html`; `st.js_on_event` absent; AppTest no video element / no dataframe row-selection simulate; `download_button` value is bool (validate CSV via code, not AppTest).
- macOS: `timeout` command not available.
- Privacy constraints remain: no raw video transmission/storage outside device, no activity-behavioral reporting without an explicit boundary decision (flagged, NOT built).
- Roles: caregiver sees only assigned subjects' alerts (S1/S2/S3); sample `alerts.jsonl` subjects don't match → caregiver sees empty analytics. That is correct behavior.
- `data/recordings/rec_20260923_102025.mp4` is a synthetic 8s test segment for Phase 3 Playback manual check — safe to delete.
- `simulate_stream.py` single-file CLI branch references undefined `simulate_from_keypoints_file` (dead code path, pre-existing, untouched).
- `data/demo/demo_fall.mp4` is the built demo clip for the presentation — keep it.

## Roadmap
- Phase 1 Behavior detection: DONE
- Phase 2 Alert Management: DONE
- Phase 3 Live Dashboard + timeline scrubbing: DONE
- Phase 4 Analytics sprint 1 (CSV export, response-time metrics, per-subject trend cards): DONE
- Phase 4 Analytics sprint 2 (heatmap, week-over-week, escalation funnel): DONE
- Phase 4 sprint 3 (optional): week-over-week trend-shape chart, Sankey, aggregation over time — explicitly deferred
- Detection accuracy metrics (precision/recall/ROC): DEFERRED — no ground-truth confirm/false-positive label exists in alert log; decide labeling approach first if ever wanted
- Scheduled/monthly PDF reports: BLOCKED pending explicit privacy-boundary decision (alert counts/timestamps likely OK; behavioral/activity patterns likely not)

## Next steps
1. Optional: sprint 3 analytics or fix the 5 stale unit tests on request.
2. Decide reporting-boundary if PDF reports are ever desired.
3. Remove synthetic test recording when done with manual Phase 3 verification.
4. Demo presentation: flip `camera.source` to `data/demo/demo_fall.mp4`, run dashboard, restore to `0` after (backup config at `/tmp/config.yaml.bak`).
5. Alert-log field-mapping BUG FOUND & FIXED: `load_alert_history()` renamed `fall_event_*`/`grace_period_*` JSONL keys → `subject_id`/`confidence`/`tier`/`outcome`/`response_time`; previously those columns never existed in the JSONL, so every alert displayed as `unknown / LOW / 0%`. Fixed in `dashboard/app.py:276` and verified (archived 157 alerts + live demo alert now render real values). `archive_alerts.sh` added (archives + clears alert log for clean demo).

---

## Prior session details (Phase 2 + 3, retained)

### Phase 2 (Alert Management): DONE
- `alert.py`: `AlertManager.bulk_update_alerts(...)`, `send_escalation_email(...)`, `auto_escalate_stale(...)`; `send_email_alert(..., log_alert=True)`.
- `config.yaml`: `escalation:` block.
- Alerts page: metrics, Tier/Status pills, From/To date filters, multi-row bulk toolbar (Ack/Dismiss/Escalate), keyboard shortcuts, auto-escalate; helpers `_escalation_config()`, `_auto_escalate_stale(...)`, `_escalate_alerts(...)`.

### Phase 3 (Live Dashboard + Timeline Scrubbing): DONE
- `stream_server.py`: MJPEG `/video_feed`, `/frame`, `/metrics`, `/health`, `/recordings`, `/record/start|stop`, NEW `/recordings/<name>/info`, `_parse_segment_start()`.
- `dashboard/app.py`: `_map_alerts_to_recordings()`, `_fetch_recording_info()`, `_render_recording_timeline()` (st.html dots, `?seek=` query-param seeking), extended `_render_recording_panel(..., alerts_df)` with `st.video(path, start_time=seek)`.
- Fixed latent bug: bulk Acknowledge/Dismiss buttons had undefined `AlertManager` (added local import).