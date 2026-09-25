# Vision-Based Fall Detection System for Elderly Care

A privacy-preserving fall detection system that processes webcam/CCTV feeds entirely on-device. The system extracts pose keypoints using MediaPipe, engineers temporal features, classifies fall events, and alerts caretakers via email (with SMS stretch goal) after a grace period for false alarm cancellation.

## Key Features
- **On-device processing only**: Raw frames are not stored or transmitted by default
- **Privacy-first**: Only numeric pose keypoint data is analyzed; recording is opt-in and local
- **Grace period**: Configurable confirmation window to cancel false alarms
- **Multi-signal fusion**: Combines velocity, stillness, and orientation features
- **Reproducible evaluation**: Held-out subject splits must be generated from actor metadata
- **Caregiver dashboard**: Streamlit overview, alert queue, live monitor, and privacy status

## System Overview
```
[Webcam Feed] → [MediaPipe Pose] → [Feature Engineering] → 
[Classification (RF/CNN-LSTM)] → [Decision Logic] → 
[Grace Period] → [Alert (Email/SMS)] → [Dashboard]
```

## Privacy Guarantees
- ✅ No raw-frame storage by default
- ✅ No video transmission to remote services
- ✅ All inference runs locally on device
- ✅ Alert text/metadata is the only external notification payload
- ✅ Recording is disabled by default and, when enabled, remains local with retention cleanup
- ✅ Camera scope is limited to living areas (bathroom is out of scope)

## Project Structure
```
fall-detection/
├── data/
│   ├── raw/                 # Manual download: URFD + Le2i datasets
│   └── processed/           # Extracted keypoints only (.npy files)
├── models/                  # Trained models (joblib/.pt)
├── logs/                    # Alert history, false positives
├── scripts/
│   ├── download_datasets.py # Manual dataset setup instructions
│   ├── preprocess_dataset.py# Subject-aware batch feature generation
│   └── verify_setup.py      # Artifact/configuration checks
├── config.yaml              # User-editable hyperparameters
├── config.yaml.example      # Template with documentation
├── project_config.py        # Project-root config/path validation
├── alert_store.py           # Locked, atomic local alert store
├── pose_extraction.py       # MediaPipe wrapper + smoothing
├── features.py              # Velocity, stillness, orientation
├── model_rf.py              # Random Forest baseline
├── model_cnn_lstm.py        # CNN-LSTM stretch goal
├── decision_logic.py        # Majority voting + confidence tiers
├── grace_period.py          # Configurable confirmation window
├── alert.py                 # Email/SMS alerting
├── simulate_stream.py       # End-to-end pipeline test
├── evaluate.py              # Held-out evaluation
├── dashboard/
│   └── app.py               # Streamlit caregiver dashboard
└── report/
    └── report.md            # Methodology, results, limitations
```

## Quick Start

1. **Setup environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python scripts/verify_setup.py
   ```

2. **Download datasets** (manual step):
   ```bash
   python scripts/download_datasets.py
   ```
   Follow the printed instructions to download:
   - UR Fall Detection Dataset → `data/raw/URFD/`
   - Le2i Fall Detection Dataset → `data/raw/Le2i/`

3. **Configure email alerts**:
   - Copy `config.yaml.example` → `config.yaml`
   - Fill in Gmail address and app password (enable 2FA first)
   - Set recipient email for alerts

4. **Run baseline pipeline**:
   ```bash
   # Extract pose keypoints from one video (repeat for the dataset)
   python pose_extraction.py path/to/video.mp4

   # Build a subject-aware dataset from labeled videos
   python scripts/preprocess_dataset.py --input-dir data/raw/URFD

   # Engineer features from a video
   python features.py path/to/video.mp4 subject_id clip_id
   
   # Train Random Forest baseline
   python model_rf.py data/processed/features/train.csv
   
   # Evaluate with subject-independent split
   python evaluate.py data/processed/features/test.csv
   
   # Test end-to-end with simulation
   python simulate_stream.py data/processed/keypoints/ models/rf_baseline.joblib
   
   # Launch caregiver dashboard
   streamlit run dashboard/app.py --server.address 127.0.0.1
   ```

## Requirements
- Python 3.10+ (tested on 3.14 with Apple Silicon MPS)
- Dependencies in `requirements.txt`
- Webcam or access to test video files
- Gmail account with app password for email alerts

## Setup and artifact notes

The MediaPipe landmarker model, trained RF artifact, and processed datasets are
ignored by Git. A fresh checkout must provision these artifacts before running
the live pipeline. Keep `config.yaml` local; use environment variables such as
`FALLGUARD_EMAIL_APP_PASSWORD` and `FALLGUARD_AUTH_SECRET` for secrets.

The preprocessing script refuses to use a dataset name as a subject ID. Add a
`metadata.json` mapping or subject/actor directory names before generating a
subject-independent split.

The current evaluation report is provisional and must be regenerated after
creating actor-level metadata and a genuine held-out subject split. Do not use
the existing report as a production performance claim.

## Customization
All key parameters are in `config.yaml`:
- Pose extraction: model complexity, frame stride, smoothing
- Features: window size, overlap
- Decision: voting windows, confidence thresholds
- Grace period: timeout duration
- Email: SMTP settings, recipients
- Paths: data/logs/model locations

## Evaluation Metrics
Reports focus on **fall class** (not overall accuracy):
- Precision: Of predicted falls, how many were actual falls
- Recall: Of actual falls, how many were detected
- F1-score: Harmonic mean of precision and recall
- Subject-independent splits prevent inflated metrics from
  learning subject-specific patterns

## Known Limitations
⚠️ **Dataset limitation**: Both UR Fall and Le2i datasets contain
    young actors performing falls in controlled environments.
    Performance with real elderly individuals in uncontrolled
    homes may vary. This is an acknowledged limitation - not
    an architectural flaw to be "fixed" by collecting more
    actor data.

⚠️ **Camera scope**: System assumes living room/common area
    coverage. Bathroom fall detection is explicitly out-of-scope
    due to privacy concerns; future work could use non-visual
    sensors (radar, thermal) for private spaces.

## Future Work
- Real-world data collection with elderly participants
- Multi-modal fusion (audio, wearable IMUs)
- Edge deployment optimization (Jetson, Raspberry Pi)
- Explainable AI for alert justification
- Caregiver feedback loop for continuous improvement

---
*Built with privacy as a first-class citizen. Your video stays yours.*