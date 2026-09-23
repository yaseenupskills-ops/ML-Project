# Vision-Based Fall Detection System for Elderly Care

A privacy-preserving fall detection system that processes webcam/CCTV feeds entirely on-device. The system extracts pose keypoints using MediaPipe, engineers temporal features, classifies fall events, and alerts caretakers via email (with SMS stretch goal) after a grace period for false alarm cancellation.

## Key Features
- **On-device processing only**: No video frames ever saved to disk or transmitted
- **Privacy-first**: Only numeric pose keypoint data processed in memory
- **Grace period**: 20-second confirmation window to cancel false alarms
- **Multi-signal fusion**: Combines velocity, stillness, and orientation features
- **Subject-independent evaluation**: Train/test split by actor ID to prevent data leakage
- **Alert history dashboard**: Minimal Streamlit UI showing past alerts only

## System Overview
```
[Webcam Feed] → [MediaPipe Pose] → [Feature Engineering] → 
[Classification (RF/CNN-LSTM)] → [Decision Logic] → 
[Grace Period] → [Alert (Email/SMS)] → [Dashboard]
```

## Privacy Guarantees
- ✅ No `cv2.imwrite()` or equivalent - raw frames never saved
- ✅ No network transmission of video/images
- ✅ All inference runs locally on device
- ✅ Only alert text/email leaves the device
- ✅ Camera scope limited to living areas (bathroom out-of-scope)

## Project Structure
```
fall-detection/
├── data/
│   ├── raw/                 # Manual download: URFD + Le2i datasets
│   └── processed/           # Extracted keypoints only (.npy files)
├── models/                  # Trained models (joblib/.pt)
├── logs/                    # Alert history, false positives
├── scripts/
│   └── download_datasets.py # Setup instructions
├── config.yaml              # User-editable hyperparameters
├── config.yaml.example      # Template with documentation
├── pose_extraction.py       # MediaPipe wrapper + smoothing
├── features.py              # Velocity, stillness, orientation
├── model_rf.py              # Random Forest baseline
├── model_cnn_lstm.py        # CNN-LSTM stretch goal
├── decision_logic.py        # Majority voting + confidence tiers
├── grace_period.py          # 20s confirmation window
├── alert.py                 # Email/SMS alerting
├── simulate_stream.py       # End-to-end pipeline test
├── evaluate.py              # Subject-independent evaluation
├── dashboard/
│   └── app.py               # Streamlit alert history viewer
└── report/
    └── report.md            # Methodology, results, limitations
```

## Quick Start

1. **Setup environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
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
   # Extract pose keypoints from datasets
   python pose_extraction.py
   
   # Engineer features
   python features.py
   
   # Train Random Forest baseline
   python model_rf.py data/processed/features/train.csv
   
   # Evaluate with subject-independent split
   python evaluate.py data/processed/features/test.csv
   
   # Test end-to-end with simulation
   python simulate_stream.py data/processed/keypoints/ models/rf_baseline.joblib
   
   # Launch dashboard (shows alert history only)
   streamlit run dashboard/app.py
   ```

## Requirements
- Python 3.10+ (tested on 3.14 with Apple Silicon MPS)
- Dependencies in `requirements.txt`
- Webcam or access to test video files
- Gmail account with app password for email alerts

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