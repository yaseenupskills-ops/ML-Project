# AGENTS.md — Fall Detection System

## Project Overview
Privacy-preserving fall detection for elderly care. Webcam → MediaPipe Pose → Features → RF/CNN-LSTM → Decision Logic → Grace Period → Email Alert → Streamlit Dashboard. **No video leaves the device.**

## Key Entry Points
| Purpose | Command / File |
|---------|----------------|
| Train RF baseline | `python model_rf.py data/processed/features/train.csv` |
| Evaluate (subject-independent) | `python evaluate.py data/processed/features/test.csv` |
| End-to-end simulation | `python simulate_stream.py --video data/demo/demo_fall.mp4 models/rf_baseline.joblib` |
| Dashboard | `streamlit run dashboard/app.py` |
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
- **Email**: Gmail SMTP (requires app password, not regular password)

## Verification Commands (run in order)
```bash
# Compile check
python -m py_compile dashboard/app.py alert.py stream_server.py simulate_stream.py metrics.py grace_period.py camera.py

# Test suite
PYTHONPATH=. python tests/test_system.py

# Lint (pyflakes)
python -m pyflakes dashboard/app.py stream_server.py
# → benign: 2 unused imports + 1 dead local `config` warning
```

## Demo Mode (for live presentation)
```bash
# 1) Backup
cp config.yaml /tmp/config.yaml.bak
# 2) Edit config.yaml: camera.source: "data/demo/demo_fall.mp4"
# 3) Run
streamlit run dashboard/app.py
# 4) Restore
cp /tmp/config.yaml.bak config.yaml
```
- Demo video: `data/demo/demo_fall.mp4` (65 frames, 30fps, 2.2s loop from UR Fall Dataset `fall-02`)
- CLI alternative: `python simulate_stream.py --video data/demo/demo_fall.mp4 models/rf_baseline.joblib`

## Architecture Notes
- **Alert log field names**: `alert.py` writes `fall_event_subject`, `fall_event_confidence`, `fall_event_tier`, `grace_period_outcome`, `grace_period_response_time`. Dashboard `load_alert_history()` **renames these** to `subject_id`, `confidence`, `tier`, `outcome`, `response_time` (fixed in `dashboard/app.py:276`).
- **Grace period timing**: wall-clock based (20s). Video file playback throttles to **native FPS** (`video_fps` in `VideoFileCamera._capture_loop`), not config target FPS, to keep alert timing correct.
- **Camera factory**: `camera.create_camera(source)` routes int→CameraManager, file→VideoFileCamera (pops `loop`/`real_time` kwargs for webcam/RTSP), rtsp://→CameraManagerRTSP.
- **Stream server** (`stream_server.py`): MJPEG on `/video_feed`, metrics on `/metrics`, recordings on `/recordings`. Binds 127.0.0.1 by default (privacy).

## Privacy Constraints (Hard Rules)
- ❌ No `cv2.imwrite()` or raw frame storage/transmission
- ❌ No activity/behavioral reporting without explicit boundary decision
- ✅ Only alert text (timestamp, confidence, tier) leaves device
- ✅ Camera scope: living areas only (bathroom out-of-scope)

## Known Issues / Gotchas
- `tests/test_units.py`: 5 pre-existing stale failures (MediaPipe `.pose` attr, hardcoded thresholds) — unrelated
- Streamlit 1.63: `st.components.v1.html` deprecated → use `st.html`; `st.js_on_event` absent; AppTest no video element / no dataframe row-selection; `download_button` value is bool
- macOS: `timeout` command not available
- `simulate_stream.py` single-file CLI branch references undefined `simulate_from_keypoints_file` (dead code)
- Caregiver role sees only assigned subjects (S1/S2/S3); sample `alerts.jsonl` subjects don't match → empty analytics is correct

## Data Paths
- Raw datasets (manual download): `data/raw/URFD/`, `data/raw/Le2i/`
- Processed: `data/processed/` (keypoints `.npy`, features `.csv`)
- Demo clip: `data/demo/demo_fall.mp4`
- Recordings: `data/recordings/`
- Models: `models/` (rf_baseline.joblib, cnn_lstm.pt)
- Logs: `logs/alerts.jsonl`, `logs/archive/`, `logs/false_positives.jsonl`

## Testing Quirks
- `tests/test_system.py`: import + instantiation smoke test (passes)
- `tests/test_units.py`: 5 stale failures (do not block)
- AppTest headless: seed admin session via HMAC token (`fall-detect-secret-change-in-prod`), set `FG_PAGE` env (`alerts`, `live`, `analytics`)

## Files to Skip / Not Owned
- `.venv/`, `__pycache__/`, `logs/` (runtime), `data/raw/` (manual), `models/` (artifacts)
- `report/`, `scripts/` (one-off)
