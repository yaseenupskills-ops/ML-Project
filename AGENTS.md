# AGENTS.md — Fall Detection System

## Project Overview
Privacy-preserving fall detection for elderly care. Webcam → MediaPipe Pose → Features → RF/CNN-LSTM → Decision Logic → Grace Period → Email Alert → Streamlit Dashboard. **Raw video stays local by default; recording is opt-in and local.**

## Key Entry Points
| Purpose | Command / File |
|---------|----------------|
| Train RF baseline | `python model_rf.py data/processed/features/train.csv` |
| Evaluate (subject-independent) | `python evaluate.py data/processed/features/test.csv` |
| End-to-end simulation | `python simulate_stream.py --video data/demo/demo_fall.mp4 models/rf_baseline.joblib` |
| Dashboard | `streamlit run dashboard/app.py --server.address 127.0.0.1` |
| Setup check | `python scripts/verify_setup.py` |
| Unit tests | `PYTHONPATH=. python tests/test_system.py` |

## Environment
- Python 3.10+ (tested on 3.14, Apple Silicon MPS)
- Virtual env: `.venv` (already exists)
- Activate: `source .venv/bin/activate`
- Dependencies: `requirements.txt` (mediapipe, opencv, numpy, pandas, scikit-learn, torch, streamlit, pyyaml)

## Configuration
**Single source of truth: `config.yaml`** (copy from `config.yaml.example`)
- All hyperparameters live here: pose, features, camera, streaming, recording, decision, grace_period, escalation, email, dashboard, auth, paths, model
- **Camera source switching**: `camera.source` (int = webcam index, str = file path/RTSP). Default `0`.
- **Video demo**: set `camera.source: "data/demo/demo_fall.mp4"` in config.yaml
- **Email**: Gmail SMTP (requires app password, not regular password); prefer `FALLGUARD_EMAIL_*` environment variables.
- **Auth**: Set `FALLGUARD_AUTH_SECRET` in deployment; query-string tokens are disabled by default.

## Verification Commands (run in order)
```bash
# Setup/artifact check
python scripts/verify_setup.py

# Compile check
python -m py_compile dashboard/app.py alert.py stream_server.py simulate_stream.py metrics.py grace_period.py camera.py

# Test suite
PYTHONPATH=. python tests/test_system.py
PYTHONPATH=. python tests/test_units.py
PYTHONPATH=. python tests/test_regressions.py

# Lint (pyflakes)
python -m pyflakes dashboard/app.py stream_server.py
```

## Demo Mode (for live presentation)
```bash
# 1) Backup
cp config.yaml /tmp/config.yaml.bak
# 2) Edit config.yaml: camera.source: "data/demo/demo_fall.mp4"
# 3) Run (local-only)
streamlit run dashboard/app.py --server.address 127.0.0.1
# 4) Restore
cp /tmp/config.yaml.bak config.yaml
```
- Demo video: `data/demo/demo_fall.mp4` (65 frames, 30fps, 2.2s loop from UR Fall Dataset `fall-02`)
- CLI alternative: `python simulate_stream.py --video data/demo/demo_fall.mp4 models/rf_baseline.joblib`

## Architecture Notes
- **Alert storage**: `alert_store.py` adds stable IDs, file locking, and atomic JSONL updates. `alert.py` and the dashboard use IDs for new actions.
- **Alert log field names**: `alert.py` writes `fall_event_subject`, `fall_event_confidence`, `fall_event_tier`, `grace_period_outcome`, `grace_period_response_time`. Dashboard `load_alert_history()` **renames these** to `subject_id`, `confidence`, `tier`, `outcome`, `response_time`.
- **Grace period timing**: wall-clock based (20s). Video file playback throttles to **native FPS** (`video_fps` in `VideoFileCamera._capture_loop`), not config target FPS, to keep alert timing correct.
- **Camera factory**: `camera.create_camera(source)` routes int→CameraManager, file→VideoFileCamera (pops `loop`/`real_time` kwargs for webcam/RTSP), rtsp://→CameraManagerRTSP.
- **Stream server** (`stream_server.py`): authenticated local HTTP endpoints for `/video_feed`, `/metrics`, and recordings. It binds 127.0.0.1 and generates a per-process token.

## Privacy Constraints (Hard Rules)
- ❌ No raw-frame storage or transmission by default
- ❌ No activity/behavioral reporting without explicit boundary decision
- ✅ Only alert text/metadata leaves the device
- ✅ Recording is opt-in, local, retention-limited, and admin-controlled
- ✅ Camera scope: living areas only (bathroom out-of-scope)

## Known Issues / Gotchas
- Current processed feature data/report are provisional until actor IDs and a genuine held-out subject split are verified.
- Streamlit 1.63: `st.components.v1.html` deprecated → use `st.html`; `st.js_on_event` absent; AppTest no video element / no dataframe row-selection; `download_button` value is bool.
- macOS: `timeout` command is not available.
- The stream server requires its per-process token; direct remote binding is intentionally forced to localhost.
- Recording is disabled unless `recording.enabled` is true and the active source supports recording.
- Caregiver role sees only explicitly assigned subjects; empty analytics can be correct when no matching alerts exist.

## Data Paths
- Raw datasets (manual download): `data/raw/URFD/`, `data/raw/Le2i/`
- Processed: `data/processed/` (keypoints `.npy`, features `.csv`)
- Demo clip: `data/demo/demo_fall.mp4`
- Recordings: `data/recordings/`
- Models: `models/` (rf_baseline.joblib, cnn_lstm.pt)
- Logs: `logs/alerts.jsonl`, `logs/archive/`, `logs/false_positives.jsonl`

## Testing Quirks
- `tests/test_system.py`: import + instantiation smoke test.
- `tests/test_units.py` and `tests/test_regressions.py`: focused unit/regression tests.
- AppTest headless: set `FG_PAGE` (`overview`, `alerts`, `live`, `analytics`, `settings`); authentication-enabled runs require a valid session token.

## Files to Skip / Not Owned
- `.venv/`, `__pycache__/`, `logs/` (runtime), `data/raw/` (manual), `models/` (artifacts)
- `report/`, `scripts/` (one-off)
