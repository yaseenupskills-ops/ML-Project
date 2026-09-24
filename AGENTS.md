# AGENTS.md — Fall Detection System

## Project Overview
Privacy-preserving fall detection for elderly care. Webcam → MediaPipe Pose → Features → RF/CNN-LSTM → Decision Logic → Grace Period → Email Alert → FastAPI backend (`api/main.py`) → frontend (built separately against `API.md`). **No video leaves the device.**

## Key Entry Points
| Purpose | Command / File |
|---------|----------------|
| Train RF baseline | `python model_rf.py data/processed/features/train.csv` |
| Evaluate (subject-independent) | `python evaluate.py data/processed/features/test.csv` |
| End-to-end simulation | `python simulate_stream.py --video data/demo/demo_fall.mp4 models/rf_baseline.joblib` |
| API server | `uvicorn api.main:app --host 127.0.0.1 --port 8000` (docs at `/docs`) |
| Unit tests | `PYTHONPATH=. python tests/test_system.py` |

## Environment
- Python 3.10+ (tested on 3.14, Apple Silicon MPS)
- Virtual env: `.venv` (already exists)
- Activate: `source .venv/bin/activate`
- Dependencies: `requirements.txt` (mediapipe, opencv, numpy, pandas, scikit-learn, torch, fastapi, uvicorn, pydantic, pyyaml)

## Configuration
**Single source of truth: `config.yaml`** (copy from `config.yaml.example`)
- All hyperparameters live here: pose, features, camera, streaming, recording, decision, grace_period, escalation, email, auth, paths, model
- **Camera source switching**: `camera.source` (int = webcam index, str = file path/RTSP). Default `0`.
- **Video demo**: set `camera.source: "data/demo/demo_fall.mp4"` in config.yaml
- **Email**: Gmail SMTP (requires app password, not regular password)

## Verification Commands (run in order)
```bash
# Compile check
python -m py_compile api/main.py services/*.py alert.py simulate_stream.py metrics.py grace_period.py camera.py

# Test suite
PYTHONPATH=. python tests/test_system.py

# Lint (pyflakes)
python -m pyflakes api/main.py services/*.py
```

## Demo Mode (for live presentation)
```bash
# 1) Backup
cp config.yaml /tmp/config.yaml.bak
# 2) Edit config.yaml: camera.source: "data/demo/demo_fall.mp4"
# 3) Run the API
uvicorn api.main:app --host 127.0.0.1 --port 8000
# 4) Restore
cp /tmp/config.yaml.bak config.yaml
```
- Demo video: `data/demo/demo_fall.mp4` (65 frames, 30fps, 2.2s loop from UR Fall Dataset `fall-02`)
- CLI alternative: `python simulate_stream.py --video data/demo/demo_fall.mp4 models/rf_baseline.joblib`

## Architecture Notes
- **Alert log field names**: `alert.py` writes `fall_event_subject`, `fall_event_confidence`, `fall_event_tier`, `grace_period_outcome`, `grace_period_response_time`. `services/alerts_service.load_alert_history()` **renames these** to `subject_id`, `confidence`, `tier`, `outcome`, `response_time` (same fix, moved from the old `dashboard/app.py:276`).
- **Grace period timing**: wall-clock based (20s). Video file playback throttles to **native FPS** (`video_fps` in `VideoFileCamera._capture_loop`), not config target FPS, to keep alert timing correct.
- **Camera factory**: `camera.create_camera(source)` routes int→CameraManager, file→VideoFileCamera (pops `loop`/`real_time` kwargs for webcam/RTSP), rtsp://→CameraManagerRTSP.
- **Business logic layer** (`services/`): `alerts_service.py` (load/filter/ack/dismiss/escalate/auto-escalate), `recordings_service.py` (alert↔recording mapping, video metadata), `analytics_service.py` (all analytics math), `roles.py` (`get_current_user()` dependency + role filtering), `alert_repository.py` (JSONL storage behind an `AlertRepository` interface).
- **API** (`api/main.py`): single FastAPI app, one origin. All routes formerly served by the now-deleted `stream_server.py` (MJPEG on `/video_feed`, `/frame`, `/metrics`, `/health`, `/recordings`, record start/stop) are FastAPI endpoints; camera lifecycle (lazy open, `SyntheticFrameSource` fallback) lives in `services/camera_service.py`. Binds 127.0.0.1 by default (privacy). CORS restricted to `FRONTEND_ORIGIN` env var (default `http://localhost:3000`). See `API.md` for the full contract.

## Privacy Constraints (Hard Rules)
- ❌ No `cv2.imwrite()` or raw frame storage/transmission
- ❌ No activity/behavioral reporting without explicit boundary decision
- ✅ Only alert text (timestamp, confidence, tier) leaves device
- ✅ Camera scope: living areas only (bathroom out-of-scope)

## Known Issues / Gotchas
- `tests/test_units.py`: 5 pre-existing stale failures (MediaPipe `.pose` attr, hardcoded thresholds) — unrelated
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

## Files to Skip / Not Owned
- `.venv/`, `__pycache__/`, `logs/` (runtime), `data/raw/` (manual), `models/` (artifacts)
- `report/`, `scripts/` (one-off)
