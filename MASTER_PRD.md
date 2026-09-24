# Fall Detection System — Master Product Requirements Document (PRD)

**Product:** Privacy-Preserving Vision-Based Fall Detection and Response System  
**Document Type:** Master / Production PRD  
**Version:** 2.0  
**Status:** Proposed target architecture with verified current-state baseline  
**Reference Structure:** Adapted from the provided Capacity Connect Production PRD v1.0  
**Primary Deployment Context:** Elderly-care common areas / assisted living environments  
**Primary Modalities:** Camera-based pose intelligence, with optional future non-visual sensors  
**Core Principle:** Detect fall-like events locally while minimizing exposure of raw visual data

---

## 1. Product Overview

The Fall Detection System is a privacy-preserving real-time computer-vision and machine-learning platform designed to detect possible falls, verify the event through temporal reasoning, provide a short cancellation window for false alarms, and notify designated caregivers.

The current repository implements a prototype based on:

- Webcam/CCTV/video inputs
- MediaPipe Pose
- Pose smoothing
- Velocity, stillness, orientation, and dispersion features
- Random Forest baseline classification
- CNN-LSTM as an advanced/stretch model path
- Decision logic with confidence tiers
- 20-second grace-period confirmation
- Email alerting
- Streamlit alert and analytics dashboards
- Local alert logs
- Subject-independent evaluation

The target product extends that foundation into a robust event-detection platform with:

- Multi-person detection and tracking
- Pose-quality and occlusion handling
- Rich spatial and temporal feature engineering
- Temporal deep-learning models
- Calibrated probabilities
- Multi-window decision state machine
- Stronger hard-negative / ADL training data
- Multiple training data sources
- Consent-based real-world validation
- FastAPI backend and PostgreSQL persistence
- Caregiver acknowledgement and feedback
- Model versioning and evaluation tracking
- Edge deployment and health monitoring
- Explainable event evidence without retaining raw video

The product is not intended to replace medical diagnosis or emergency services. It is a safety-assistance system intended to detect a possible fall and initiate a caregiver response workflow.

---

## 2. Problem Statement

Falls can be difficult to detect quickly when an individual is alone or when caregivers are not continuously observing a monitored area.

Traditional monitoring approaches can create several problems:

1. Continuous human observation is expensive and difficult to scale.
2. Conventional camera systems may create privacy concerns when video is stored or transmitted.
3. Naive image-level classifiers can confuse normal activities such as sitting, bending, kneeling, lying down, or picking up objects with falls.
4. A single model prediction may not capture the temporal progression of a real fall.
5. Public fall datasets often use controlled environments and actors who may not represent real elderly users.
6. Camera occlusion, lighting changes, background clutter, and multiple people can reduce pose quality.
7. Local log files are not sufficient for multi-device production operations.
8. A caregiver needs actionable event information, not merely a model probability.
9. A deployed system needs monitoring, retries, alert acknowledgement, and failure handling.
10. Model performance cannot be assumed from laboratory data alone; real-world validation is required.

The current repository already demonstrates the basic detection loop, but its documented limitations include a high false-positive rate, small data volume, controlled young-actor data, no robust occlusion or multi-person handling, probability-calibration limitations, and unfinished production deployment work.

---

## 3. Product Vision

**Build a privacy-first intelligent fall-event detection platform that can continuously observe a permitted environment, detect fall-like motion locally, distinguish normal activity from emergency-like events through temporal reasoning, and trigger a reliable caregiver response without transmitting raw video.**

The system should answer:

- Did a possible fall happen?
- Which tracked person was affected?
- Where and when did the event occur?
- How confident is the system?
- What evidence caused the event state to change?
- Is the person recovering or remaining inactive?
- Has the caregiver acknowledged the event?
- Was the event a true fall or a false positive?
- Which model version produced the decision?
- Can the labelled event improve future model performance?

---

## 4. Product Goals

### Primary Goals

1. Detect fall events with strong recall while substantially reducing false positives.
2. Use temporal evidence instead of relying on a single frame/window.
3. Preserve privacy by keeping raw video on the edge device.
4. Support webcam, video-file, USB camera, CSI camera, and RTSP/IP-camera inputs.
5. Support multi-person tracking so fall states are maintained per person.
6. Handle missing/low-confidence pose landmarks gracefully.
7. Use multiple complementary training-data sources rather than depending on one small dataset.
8. Maintain subject-independent and dataset-independent evaluation.
9. Provide a clear 20-second confirmation/cancellation workflow.
10. Provide reliable caregiver alerting and escalation.
11. Persist structured alert/event data in a production database.
12. Provide dashboards for event history, system status, and analytics.
13. Capture caregiver feedback for false-positive/true-event analysis.
14. Track model versions, training datasets, metrics, and deployment state.

### Secondary Goals

1. Support non-visual sensing in privacy-sensitive areas.
2. Support optional multimodal fusion in later phases.
3. Optimize inference for edge hardware.
4. Support explainable alert evidence.
5. Support automated health monitoring and service restart.
6. Establish a reproducible model-training pipeline.

### Non-Goals

The MVP will not:

- Provide medical diagnosis.
- Replace emergency services.
- Store continuous raw surveillance footage in the cloud.
- Monitor bathroom/private areas using conventional cameras.
- Claim clinical-grade performance without appropriate validation.
- Automatically retrain and deploy a model without human review.

---

## 5. Target Users

### 5.1 Caregiver

A caregiver is responsible for responding to possible fall events.

Primary needs:

- Receive reliable alerts.
- See event timestamp and affected subject/device.
- See confidence and event state.
- Acknowledge, dismiss, or escalate an event.
- Record whether the alert was a true event or false positive.
- Review alert history and response times.
- Confirm that devices and cameras are operational.

### 5.2 Administrator

The administrator manages the deployed system.

Primary needs:

- Register and manage devices.
- Manage monitored subjects.
- Assign caregivers.
- Configure alert channels.
- Review system health.
- Review model versions and performance.
- Manage deployment configuration.
- Review analytics and false positives.
- Audit important changes.

### 5.3 ML Engineer / Data Scientist

Responsible for model and dataset lifecycle.

Primary needs:

- Ingest and version datasets.
- Run preprocessing pipelines.
- Generate pose/keypoint datasets.
- Engineer features.
- Train baseline and temporal models.
- Compare experiments.
- Evaluate by subject and dataset.
- Analyze false positives/false negatives.
- Register model versions.
- Promote approved models.

### 5.4 System Operator / Developer

Responsible for application operation.

Primary needs:

- Start/stop services.
- Inspect logs.
- Monitor camera health.
- Monitor API health.
- Replace failed devices.
- Diagnose event-pipeline failures.

---

## 6. Product Principles

### Privacy First

Raw camera frames must remain on the edge device by default. The backend should receive structured event information, not continuous raw video.

### Event-Driven

The platform should treat a fall as an event with a lifecycle rather than as a single classifier output.

### Temporal Evidence Over Single-Frame Decisions

A fall should be interpreted as a sequence such as:

```text
Stable posture
    ↓
Rapid downward motion
    ↓
Body-orientation change
    ↓
Low body position / ground interaction
    ↓
Post-event stillness
    ↓
Confirmation
```

### Human-in-the-Loop

A caregiver should have the ability to acknowledge, cancel/dismiss, or escalate events.

### Reproducible ML

Every deployed model must have:

- Model version
- Training dataset version
- Feature version
- Configuration version
- Validation metrics
- Creation timestamp

### Fail Safely

When the system is uncertain because of camera failure, insufficient pose visibility, or missing data, it must avoid pretending to have high confidence.

---

## 7. High-Level Product Architecture

```text
                         FALL DETECTION PLATFORM
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
   EDGE DEVICE              BACKEND PLATFORM          CAREGIVER UI
        │                         │                         │
        │                         │                         │
 Camera / RTSP              FastAPI API              Web Dashboard
        │                         │                         │
        ▼                         │                         │
 Person Detection               │                         │
 + Tracking                     │                         │
        │                         │                         │
        ▼                         │                         │
 Pose Extraction                 │                         │
        │                         │                         │
        ▼                         │                         │
 Pose Quality                    │                         │
 + Occlusion                    │                         │
        │                         │                         │
        ▼                         │                         │
 Feature Engineering             │                         │
        │                         │                         │
        ▼                         │                         │
 Temporal ML Model               │                         │
        │                         │                         │
        ▼                         │                         │
 Decision State Machine ───────► Event Ingestion ───────► Alert View
        │                         │                         │
        ▼                         ▼                         ▼
  Grace Period              PostgreSQL                Acknowledge
        │                    + Event Store             / Dismiss
        ▼                         │                         │
 Alert Trigger ───────────────► Notification Service       │
                                  │                         │
                           Email / SMS / Push              │
                                  │                         │
                                  ▼                         │
                           Caregiver Feedback ◄────────────┘
                                  │
                                  ▼
                           ML Feedback Dataset
                                  │
                                  ▼
                           Retraining / Evaluation
                                  │
                                  ▼
                           Model Registry
```

---

## 8. Current System Baseline

The current GitHub repository is a small one-commit prototype repository whose main files include:

- `camera.py`
- `pose_extraction.py`
- `features.py`
- `model_rf.py`
- `model_cnn_lstm.py`
- `decision_logic.py`
- `grace_period.py`
- `alert.py`
- `simulate_stream.py`
- `stream_server.py`
- `evaluate.py`
- `metrics.py`
- `dashboard/app.py`
- `tests/`
- `AGENTS.md`
- `HANDOFF.md`
- `PROJECT_SUMMARY.md`
- `README.md`

The current README describes an on-device privacy-preserving workflow:

```text
Webcam Feed
    ↓
MediaPipe Pose
    ↓
Feature Engineering
    ↓
Classification
    ↓
Decision Logic
    ↓
Grace Period
    ↓
Alert
    ↓
Dashboard
```

The repository currently supports webcam, file, and RTSP-style source handling in the live/demo code path, and the September 23, 2026 handoff records a verified demo-video workflow.

### Current ML Baseline Snapshot

The repository's project summary reports:

| Metric | Current reported value |
|---|---:|
| URFD sequences | 70 |
| Falls | 30 |
| ADL / non-fall sequences | 40 |
| Feature windows | 104 |
| Random Forest | 100 trees, max depth 10 |
| Fall detection rate | 86.7% |
| ADL false-positive rate | 62.5% |
| Cross-validation F1 | 0.647 ± 0.204 |
| Reported inference latency | ~20 ms/frame on M4 MacBook Air |

These values are a **baseline snapshot**, not production acceptance criteria.

---

## 9. Current-State Problems to Be Addressed

### 9.1 Training Data Is Too Limited

Current training is centered on URFD-derived data. The project summary reports that the Le2i dataset is not actually available in the current archive.

### 9.2 High ADL False Positives

Normal activities are overlapping with fall predictions. This indicates that classification and decision logic need to distinguish difficult ADLs from actual falls.

### 9.3 Limited Temporal Reasoning

The current configuration uses `vote_windows: 1`, which makes the decision layer too sensitive to a single model window.

### 9.4 Probability Calibration

Current confidence thresholds are engineering thresholds rather than validated probability estimates.

### 9.5 Young Actors / Controlled Environment

The current README explicitly warns that public datasets use controlled environments and young actors; performance on real elderly users and uncontrolled homes may vary.

### 9.6 Occlusion

The current system does not have a robust pose-occlusion strategy.

### 9.7 Multi-Person Handling

The current system does not robustly maintain independent fall states for multiple people.

### 9.8 Storage

Local JSON/JSONL logs are acceptable for a prototype but are not the target persistence architecture for a multi-device platform.

### 9.9 Feedback Labels

The existing alert log does not contain sufficient ground-truth information to calculate real-world detection metrics from production alerts.

### 9.10 Production Deployment

The handoff still identifies deployment and operational hardening work such as target-device installation, camera connection, graceful shutdown, and system service configuration.

### 9.11 Test Debt

The handoff reports five stale unit-test failures associated with older MediaPipe API usage and hardcoded confidence thresholds.

### 9.12 Dead Code Path

The handoff identifies a pre-existing dead CLI path referencing `simulate_from_keypoints_file`.

---

# 10. Updated Data Strategy

The new master PRD changes the training-data strategy from “depend mainly on URFD” to a **multi-source training and validation program**.

## 10.1 Data Source Architecture

```text
                 TRAINING DATA PROGRAM
                         │
       ┌─────────────────┼──────────────────┐
       │                 │                  │
       ▼                 ▼                  ▼
 Public Fall Data   Public ADL Data   Self-Collected Data
       │                 │                  │
       └─────────────────┼──────────────────┘
                         ▼
                 Data Harmonization
                         │
                         ▼
                  Pose / Keypoints
                         │
                         ▼
                Feature / Sequence Set
                         │
                         ▼
                   Model Training
                         │
        ┌────────────────┴────────────────┐
        ▼                                 ▼
 Internal Validation              Cross-Dataset Test
        │                                 │
        └────────────────┬────────────────┘
                         ▼
                  Release Decision
```

## 10.2 Primary Supplemental Dataset: UP-Fall Detection

UP-Fall Detection should be introduced as a major supplemental source because it is explicitly built for fall detection and includes falls plus daily activities using a multimodal acquisition setup.

The official dataset page describes 11 activities, including six daily activities and five fall types, collected across subjects with vision, ambient, and wearable modalities.

Important limitation: the published collection also consists of healthy young adults, so it improves diversity but does not solve the real-elderly-domain problem by itself.

### Intended use

- Fall-event training
- ADL diversity
- Temporal sequence modeling
- Cross-dataset generalization
- Optional future sensor-fusion experimentation

### Important implementation rule

Only use the modalities needed for the current model. The vision/keypoint pipeline must remain the primary MVP path.

## 10.3 Secondary Hard-Negative / ADL Source: NTU RGB+D

NTU RGB+D / RGB+D 120 should be considered for difficult non-fall activities and posture transitions.

The official ROSE Lab dataset contains RGB video, depth, 3D skeletal data, and infrared data. It includes actions such as:

- Sit down
- Stand up
- Pick up
- Drop
- Squat down
- Staggering
- Falling down
- Other daily and interaction actions

NTU RGB+D is valuable because it provides large variation in subjects, camera setups, and daily actions.

### Intended use

- ADL hard negatives
- Posture transitions
- Skeleton-sequence experimentation
- Domain robustness
- Multi-person and interaction research

### Dataset constraint

The official dataset is distributed under academic/research use terms and requires registration/release agreement. It must not be redistributed or incorporated into commercial training flows without complying with its terms.

## 10.4 Existing URFD

Keep URFD as a baseline/reference dataset.

URFD should be used for:

- Regression testing
- Baseline reproducibility
- Benchmark comparison
- Existing demo compatibility

It should no longer be the only source used to justify model readiness.

## 10.5 Real-World Data

A separate real-world validation program should be introduced.

Data collection must use explicit consent and an approved privacy process.

For early development, prioritize:

- Normal home-like activities
- Controlled simulated falls
- Different room layouts
- Different clothing
- Different lighting
- Different camera distances
- Different camera heights
- Occluded poses
- Multiple-person scenes
- Assistive devices where appropriately and safely collected

Raw video should not be uploaded to the cloud as the default. Where practical, store anonymized pose/keypoint representations after local processing.

## 10.6 Training vs Validation Data Rules

The system must maintain clear boundaries:

```text
TRAINING
---------
URFD
UP-Fall
Approved additional datasets
Approved synthetic augmentation

VALIDATION
----------
Held-out subjects
Held-out environments
Held-out camera positions

REAL-WORLD VALIDATION
---------------------
Consented pilot data
Not automatically mixed into training

TEST
----
Never used for model tuning
```

---

# 11. Data Requirements

Every processed sequence should have metadata.

```json
{
  "sequence_id": "upfall_subject_03_trial_02",
  "dataset": "UP-Fall",
  "subject_id": "03",
  "activity_label": "fall",
  "activity_type": "fall_forward",
  "camera_id": "camera_01",
  "environment_id": "env_01",
  "frame_rate": 30,
  "resolution": "640x480",
  "pose_format": "mediapipe_33x3",
  "quality_score": 0.92,
  "split": "train",
  "consent_status": "dataset_license",
  "dataset_version": "v1"
}
```

### Data quality checks

Each sequence must be checked for:

- Missing frames
- Corrupt frames
- Invalid labels
- Duplicate sequences
- Missing keypoints
- Low pose confidence
- Unrealistic coordinate jumps
- Incorrect timestamps
- Duplicate subject leakage

---

# 12. Data Preprocessing Pipeline

```text
Raw Dataset / Video
        ↓
Dataset Adapter
        ↓
Frame Normalization
        ↓
Pose Extraction
        ↓
Pose Confidence Filtering
        ↓
Missing Landmark Handling
        ↓
Smoothing
        ↓
Coordinate Normalization
        ↓
Feature Extraction
        ↓
Temporal Windowing
        ↓
Sequence Labeling
        ↓
Train / Validation / Test Split
```

### Split policy

The system should support:

1. Subject-independent split
2. Dataset-independent test
3. Environment-independent test where metadata is available

No sequence from the same subject should accidentally appear in both training and test partitions.

---

# 13. Computer Vision Pipeline

## 13.1 Camera Ingestion

Supported:

- Webcam
- USB camera
- CSI camera
- IP/RTSP camera
- Recorded test video

The camera abstraction must expose:

```text
source
fps
resolution
status
last_frame_timestamp
read_latency
```

## 13.2 Person Detection

Add a person-detection stage before pose analysis.

Possible implementation path:

```text
YOLO / lightweight detector
        ↓
Person bounding boxes
        ↓
Tracker
        ↓
Per-person identity
```

The exact detector should be benchmarked against edge-device constraints.

## 13.3 Person Tracking

Each detected person should receive a temporary `track_id`.

```text
Camera
  ↓
Person A → track_id = 101
Person B → track_id = 102
```

The system must maintain a history buffer per track.

## 13.4 Pose Extraction

Current baseline uses MediaPipe Pose.

Target pipeline:

```text
Person Crop
    ↓
Pose Model
    ↓
33 Keypoints
    ↓
Visibility / Confidence
    ↓
Smoothed Pose
```

---

# 14. Pose Quality and Occlusion Handling

Each frame should produce:

```text
pose_quality_score
visible_joint_count
critical_joint_visibility
tracking_confidence
```

Critical joints include, at minimum:

- Hips
- Shoulders
- Knees
- Ankles

### Policy

```text
High pose quality
    ↓
Normal inference

Medium pose quality
    ↓
Inference with uncertainty penalty

Low pose quality
    ↓
Do not confidently classify
Wait for more observations
```

This avoids turning bad pose extraction into a false high-confidence alert.

---

# 15. Feature Engineering

The system must retain the current feature families and extend them.

## 15.1 Spatial Features

- Joint angles
- Torso angle
- Hip-to-shoulder geometry
- Limb lengths
- Relative joint distances
- Body aspect ratio
- Body centroid
- Hip height
- Shoulder height
- Knee height

## 15.2 Kinematic Features

- Velocity
- Acceleration
- Jerk
- Angular velocity
- Change in orientation
- Vertical displacement
- Vertical velocity

## 15.3 Temporal Features

For each tracked person:

```text
t-29
t-28
...
t-1
t
```

Calculate:

- Rolling mean
- Rolling variance
- Peak velocity
- Peak acceleration
- Change-point magnitude
- Time-to-low-height
- Post-event stillness duration

## 15.4 Pose Quality Features

- Mean landmark confidence
- Missing-joint ratio
- Pose stability
- Tracking stability

---

# 16. Temporal Sequence Representation

The target model should process sequences rather than a single feature window.

Example:

```text
30 frames × N features
```

or another empirically selected window size.

The system must make window length, stride, and overlap configurable.

---

# 17. Machine Learning Architecture

## 17.1 Baseline Model

Random Forest remains the baseline.

Purpose:

- Regression benchmark
- Fast edge baseline
- Feature importance analysis
- Fallback classifier

## 17.2 Target Temporal Model

Evaluate:

- CNN-LSTM
- TCN
- Other lightweight temporal sequence architectures

The initial recommended path is:

```text
Keypoint Sequence
       ↓
Temporal Feature Representation
       ↓
CNN
       ↓
LSTM / TCN
       ↓
Fall Probability
```

The final production model should be selected using measured trade-offs among:

- Recall
- Precision
- F1
- False alerts/hour
- Detection latency
- Memory
- CPU/GPU utilization

## 17.3 Ensemble Strategy

A potential production setup:

```text
Random Forest
      +
Temporal Neural Model
      ↓
Calibrated Evidence Fusion
      ↓
Decision Engine
```

The ensemble must only be adopted if it improves validation performance enough to justify additional complexity.

---

# 18. Probability Calibration

Raw model scores must not automatically be presented as real-world probabilities.

The pipeline should support:

- Platt scaling
- Isotonic regression

Calibration dataset:

```text
Training data
   ↓
Model training
   ↓
Dedicated calibration split
   ↓
Calibration model
   ↓
Calibrated output
```

The calibration split must not be used to tune the production classifier itself.

---

# 19. Decision Engine

The decision engine is a core component.

### Proposed state machine

```text
                 ┌──────────┐
                 │  NORMAL  │
                 └────┬─────┘
                      │
               suspicious motion
                      ▼
               ┌─────────────┐
               │ SUSPICIOUS  │
               └──────┬──────┘
                      │
             repeated fall evidence
                      ▼
              ┌──────────────┐
              │ POSSIBLE FALL│
              └──────┬───────┘
                     │
            confirmation sequence
                     ▼
             ┌──────────────┐
             │ CONFIRMATION │
             └──────┬───────┘
                ┌────┴────┐
             recover      persist
               │             │
               ▼             ▼
            NORMAL     CONFIRMED FALL
```

### Evidence used

- Model confidence
- Consecutive fall windows
- Vertical movement
- Orientation change
- Body position
- Post-event stillness
- Pose quality
- Track stability

---

# 20. Fall Confirmation Policy

A production event should not be created from one model window alone.

Example decision:

```text
Window 1 → possible fall
Window 2 → possible fall
Window 3 → strong fall evidence
        ↓
Possible Fall Event
        ↓
20-second grace period
        ↓
Recovered?
   ├── YES → Cancel / False Alarm
   └── NO  → Confirmed Fall
```

The exact number of windows must be determined through validation rather than hardcoded as a universal value.

---

# 21. Grace Period

The current 20-second grace-period behavior is retained.

### Requirements

When a possible fall is confirmed by the decision engine:

1. Create a pending event.
2. Start a 20-second timer.
3. Notify the local interface.
4. Allow user/caregiver cancellation.
5. Record cancellation time.
6. If timeout occurs without cancellation, mark the event confirmed.
7. Trigger configured notifications.

### Event outcomes

- `CANCELLED`
- `CONFIRMED`
- `ESCALATED`
- `FAILED_NOTIFICATION`

---

# 22. Alert System

## Primary Channel

Email.

## Future / Optional Channels

- SMS
- Push notification
- Voice call integration
- External emergency workflow

### Alert contents

```text
Fall Detection Alert

Subject: Subject-02
Device: LivingRoom-Cam-01
Event Time: 2026-09-24 10:32:14
Confidence: 0.87
Decision Tier: HIGH
Event State: CONFIRMED

Evidence:
- Rapid downward motion
- Significant orientation change
- Post-event inactivity

Response:
[ACKNOWLEDGE]
[DISMISS]
[ESCALATE]
```

The exact external notification capabilities depend on the configured provider.

---

# 23. Backend Architecture

## 23.1 Backend Technology

Recommended:

- FastAPI
- Python
- PostgreSQL
- SQLAlchemy or equivalent ORM
- Redis for caching/queue support where required
- Object storage only for explicitly approved artifacts

## 23.2 Backend Flow

```text
Edge Device
    ↓
HTTPS / WebSocket
    ↓
FastAPI
    ↓
Authentication
    ↓
Event Validation
    ↓
Event Processing
    ↓
PostgreSQL
    ↓
Notification Service
    ↓
Dashboard
```

The edge device should not upload raw camera frames as part of the standard event workflow.

---

# 24. API Architecture

```text
/api/v1/auth
/api/v1/users
/api/v1/subjects
/api/v1/devices
/api/v1/cameras
/api/v1/events
/api/v1/alerts
/api/v1/notifications
/api/v1/caregiver-feedback
/api/v1/models
/api/v1/models/versions
/api/v1/analytics
/api/v1/system/health
/api/v1/system/metrics
```

## Example endpoints

### Events

```text
POST /api/v1/events
GET  /api/v1/events
GET  /api/v1/events/{event_id}
PATCH /api/v1/events/{event_id}
```

### Alerts

```text
GET   /api/v1/alerts
POST  /api/v1/alerts/{alert_id}/acknowledge
POST  /api/v1/alerts/{alert_id}/dismiss
POST  /api/v1/alerts/{alert_id}/escalate
```

### Devices

```text
POST /api/v1/devices
GET  /api/v1/devices
GET  /api/v1/devices/{device_id}
PATCH /api/v1/devices/{device_id}
GET /api/v1/devices/{device_id}/health
```

### Model management

```text
GET  /api/v1/models
POST /api/v1/models/register
GET  /api/v1/models/{model_id}
POST /api/v1/models/{model_id}/promote
```

---

# 25. Event Contract

A minimal backend event payload:

```json
{
  "device_id": "cam_01",
  "track_id": 2,
  "timestamp": "2026-09-24T10:32:14Z",
  "event_type": "possible_fall",
  "confidence": 0.87,
  "tier": "high",
  "model_version": "rf-v2.1.0",
  "feature_version": "features-v2",
  "pose_quality": 0.94,
  "evidence": {
    "rapid_downward_motion": true,
    "orientation_change": 0.71,
    "post_event_stillness": true
  }
}
```

Raw frame data is intentionally absent.

---

# 26. Database Architecture

## Core entities

```text
User
 │
 ├── Role
 ├── CaregiverAssignments
 └── AuditLogs

Subject
 │
 ├── DeviceAssignments
 └── Events

Device
 │
 ├── Camera
 ├── Health
 └── ModelDeployment

Event
 │
 ├── Alert
 ├── Evidence
 ├── Acknowledgement
 └── Feedback

Model
 │
 ├── ModelVersion
 ├── DatasetVersion
 └── Deployment

Dataset
 │
 ├── DatasetVersion
 ├── Sequence
 └── Label
```

## Suggested tables

### users

```text
id
name
email
role
status
created_at
updated_at
```

### subjects

```text
id
display_name
location_label
status
created_at
updated_at
```

### devices

```text
id
device_name
device_type
location
status
last_seen_at
software_version
created_at
```

### cameras

```text
id
device_id
source_type
resolution
fps
status
last_frame_at
```

### events

```text
id
subject_id
device_id
track_id
event_type
state
timestamp
confidence
tier
model_version
feature_version
pose_quality
created_at
```

### event_evidence

```text
id
event_id
rapid_motion
orientation_change
body_height_change
post_event_stillness
pose_quality
evidence_summary
```

### caregiver_feedback

```text
id
event_id
caregiver_id
label
comment
created_at
```

Recommended labels:

```text
TRUE_FALL
FALSE_POSITIVE
UNCERTAIN
SYSTEM_FAILURE
```

### model_versions

```text
id
model_name
version
model_type
artifact_uri
feature_version
dataset_version
metrics_json
status
created_at
approved_at
```

---

# 27. Model Registry

The system must never overwrite a production model without version tracking.

Example:

```text
Model: FallDetector

v1.0.0
    Random Forest
    URFD
    Baseline

v2.0.0
    Random Forest
    URFD + UP-Fall

v2.1.0
    CNN-LSTM
    URFD + UP-Fall + approved ADLs

v3.0.0
    Ensemble
    Multi-source dataset
```

Each model version must include:

- Training configuration
- Dataset version
- Feature version
- Evaluation metrics
- Calibration information
- Deployment status

---

# 28. Caregiver Feedback Loop

The system must turn operational events into labeled learning information.

```text
Possible / Confirmed Event
          ↓
Caregiver Action
          ↓
TRUE_FALL / FALSE_POSITIVE / UNCERTAIN
          ↓
Stored Feedback
          ↓
Data Analysis
          ↓
Hard-Negative Dataset
          ↓
Retraining
          ↓
Evaluation
          ↓
Human Approval
          ↓
New Model Version
```

The platform must not automatically promote a retrained model to production solely because a training job completed.

---

# 29. Analytics

## Caregiver Dashboard

Display:

- Pending alerts
- Confirmed alerts
- Dismissed alerts
- Escalated alerts
- Average response time
- Latest system status

## Administrator Dashboard

Display:

- Active devices
- Offline devices
- Total events
- Confirmed events
- False positives
- Alerts by location
- Alerts over time
- Notification failures
- Model version distribution

## ML Dashboard

Display:

- Precision
- Recall
- F1
- ROC-AUC where meaningful
- False alerts/hour
- Detection latency
- Confusion matrix
- Dataset-wise performance
- Subject-wise performance
- Environment-wise performance
- Calibration curve

---

# 30. Important Evaluation Metrics

Overall accuracy must not be the primary success metric.

The system must report:

### Precision

Of predicted falls, how many were actual falls?

### Recall

Of actual falls, how many were detected?

### F1

Balance of precision and recall.

### False Alerts per Hour

Critical for real-world usability.

```text
false alerts / monitored hours
```

### Time to Detection

```text
actual fall onset
        ↓
system confirmed event
```

### Time to Caregiver Acknowledgement

```text
alert created
        ↓
caregiver acknowledgement
```

### Dataset Generalization

Report metrics separately for:

- URFD
- UP-Fall
- NTU-derived hard negatives
- Real-world pilot

Metrics must not be blended into one number that hides domain differences.

---

# 31. Acceptance Targets

These are **development targets**, not claims about current performance.

## Detection

Target:

- High recall for clearly represented fall types
- Substantially lower false-alert rate than the current baseline
- Stable performance across held-out subjects

## Operational

Target:

- End-to-end event creation within a few seconds of detection evidence
- Grace-period timing remains wall-clock correct
- Notification retry behavior works during transient failures
- Device health status updates reliably

## Privacy

Target:

- No raw-frame upload in the standard inference/event path
- No cloud raw-video persistence
- Access-controlled structured event data
- Audit trail for sensitive actions

## Reliability

Target:

- Automatic process recovery
- Health endpoints
- Structured logs
- Backup strategy
- Graceful shutdown

---

# 32. Privacy Requirements

The privacy model is a core product requirement.

## Mandatory

1. Raw video remains on the edge device.
2. No raw image is transmitted as part of routine inference.
3. No continuous cloud recording.
4. Only approved structured event information leaves the edge.
5. Camera coverage should be limited to approved common areas.
6. Private-space coverage should use non-visual alternatives where required.
7. Event access must be role-controlled.
8. Model/feature logs must not contain unnecessary personal content.
9. Sensitive credentials must be stored outside source control.
10. Data retention must be configurable.

## Privacy-safe evidence

Store:

- confidence
- timestamps
- track ID
- feature summary
- pose-quality score
- decision state
- model version

Avoid storing:

- continuous raw video
- unnecessary face crops
- unnecessary identity images

---

# 33. Security Requirements

### Authentication

- Secure authentication
- Password hashing
- Session/token expiry
- Password recovery
- Optional MFA

### Authorization

Use:

- RBAC
- Object-level authorization

Example:

```text
Caregiver A
   ↓
Can access assigned subjects

Caregiver A
   X
Cannot access unrelated subject events
```

### API Security

- HTTPS
- Input validation
- Rate limiting
- Authentication middleware
- Structured error responses
- Request IDs

### Secrets

Never commit:

- SMTP passwords
- API keys
- JWT secrets
- Database passwords

Use environment variables or an approved secret store.

---

# 34. Audit Logging

Audit actions should include:

```text
user
action
resource
timestamp
result
request_id
```

Examples:

- User login
- Device registration
- Subject assignment
- Alert acknowledgement
- Alert escalation
- Model promotion
- Configuration change
- Notification-provider change
- Data deletion

---

# 35. Notification Reliability

Notifications must support:

```text
Create alert
   ↓
Send
   ├── SUCCESS
   │
   └── FAILURE
         ↓
      Retry
         ↓
      Retry
         ↓
    Escalation path
```

Notification records should track:

```text
notification_id
event_id
channel
provider
status
attempt_count
last_attempt
error_code
delivered_at
```

---

# 36. System Health Monitoring

Each edge device should expose or send:

```text
camera_status
camera_fps
last_frame_timestamp
inference_latency
model_loaded
cpu_usage
memory_usage
temperature
queue_depth
backend_connectivity
software_version
model_version
```

Health states:

```text
HEALTHY
DEGRADED
OFFLINE
ERROR
```

---

# 37. Edge Deployment

Target deployment classes:

### Development

Laptop / workstation

### Demonstration

Laptop with webcam or test video

### Edge

Potential targets:

- Raspberry Pi class hardware
- NVIDIA Jetson class hardware
- Other supported edge Linux systems

The exact hardware target must be selected after benchmarking.

### Containerization

Recommended:

```text
Docker
   ↓
Edge inference container
   ↓
Health check
   ↓
Automatic restart
```

---

# 38. Backend Deployment

Target:

```text
Internet / LAN
      ↓
Reverse Proxy
      ↓
FastAPI
      ↓
PostgreSQL
      ↓
Notification workers
```

Recommended infrastructure:

- Docker
- Reverse proxy
- PostgreSQL
- Redis where background jobs require it
- CI/CD
- Monitoring

---

# 39. Background Jobs

Use a worker/scheduler layer for:

- Notification retries
- Alert escalation
- Data cleanup
- Daily analytics
- Report generation if approved
- Dataset processing jobs
- Model-evaluation jobs
- Device health checks

Background jobs must never block the main event-ingestion request.

---

# 40. Dashboard Requirements

## Live Status

Display:

```text
Camera
   → ONLINE / OFFLINE

Model
   → LOADED / ERROR

Backend
   → CONNECTED / DISCONNECTED
```

## Alerts

Table fields:

```text
Timestamp
Subject
Device
Confidence
Tier
State
Acknowledged By
Response Time
Model Version
```

## Event Detail

```text
Event
 ├── Detection timestamp
 ├── Subject
 ├── Device
 ├── Confidence
 ├── Evidence
 ├── Grace-period outcome
 ├── Notification status
 ├── Caregiver response
 └── Model version
```

The dashboard should preserve the project's privacy-first principle and avoid becoming a raw-video surveillance console.

---

# 41. Explainable Alert Evidence

The product should explain the decision using interpretable signals.

Example:

```text
Possible Fall

Why detected:
✓ Rapid downward movement
✓ Significant orientation change
✓ Hip height reduced
✓ Post-event stillness observed

Pose quality:
94%

Model:
CNN-LSTM v2.1.0
```

The evidence should explain the event without exposing unnecessary raw visual information.

---

# 42. Testing Strategy

## Unit Tests

Test independently:

- Camera adapters
- Pose processing
- Feature functions
- Temporal windows
- Calibration
- Decision state machine
- Grace-period timer
- Alert formatting

## Integration Tests

Test:

```text
Camera
 ↓
Pose
 ↓
Features
 ↓
Model
 ↓
Decision
 ↓
Event
 ↓
Notification
```

## Backend Tests

- API authorization
- Request validation
- Event creation
- Alert updates
- Database transactions
- Notification queue

## End-to-End Tests

Test a full simulated event:

```text
demo video
 ↓
fall candidate
 ↓
decision
 ↓
grace period
 ↓
confirmed event
 ↓
database
 ↓
notification
 ↓
dashboard
```

## Model Tests

Every release must test:

- Held-out subjects
- Hard-negative ADLs
- Cross-dataset validation
- Missing-joint sequences
- Occlusion scenarios
- Multiple-person scenarios

---

# 43. Current Tests and Required Cleanup

The current handoff indicates:

- `tests/test_system.py` passes
- Several stale unit-test failures remain
- A dead keypoint-file CLI path exists

Before the new architecture is declared stable:

1. Fix or explicitly retire stale tests.
2. Remove or implement the dead CLI path.
3. Add tests for the new state machine.
4. Add tests for multi-person tracking.
5. Add tests for pose-quality rejection.
6. Add API integration tests.

---

# 44. User Journeys

## Caregiver

```text
Login
 ↓
Dashboard
 ↓
Possible Fall Alert
 ↓
Review event
 ↓
Acknowledge / Dismiss / Escalate
 ↓
Feedback
 ↓
Event history updated
```

## Administrator

```text
Login
 ↓
Register Device
 ↓
Assign Camera
 ↓
Assign Subject
 ↓
Assign Caregiver
 ↓
Configure Alerts
 ↓
Monitor Device Health
 ↓
Review Analytics
```

## ML Engineer

```text
Import Dataset
 ↓
Validate Dataset
 ↓
Generate Pose Data
 ↓
Generate Features
 ↓
Create Train/Validation/Test Sets
 ↓
Train Baseline
 ↓
Train Temporal Model
 ↓
Calibrate
 ↓
Evaluate
 ↓
Register Model
 ↓
Human Review
 ↓
Deploy
```

---

# 45. ML Development Workflow

```text
DATASET
   ↓
INGESTION
   ↓
QUALITY CHECK
   ↓
POSE EXTRACTION
   ↓
FEATURE / SEQUENCE GENERATION
   ↓
TRAIN / VAL / TEST SPLIT
   ↓
BASELINE
   ↓
TEMPORAL MODEL
   ↓
CALIBRATION
   ↓
CROSS-DATASET TEST
   ↓
ERROR ANALYSIS
   ↓
MODEL REGISTRATION
   ↓
APPROVAL
   ↓
EDGE DEPLOYMENT
   ↓
PRODUCTION FEEDBACK
   ↓
NEXT DATASET VERSION
```

---

# 46. Model Release Gate

A model cannot be promoted simply because F1 increased.

A production candidate must satisfy all applicable checks:

```text
Dataset integrity
        +
No subject leakage
        +
Acceptable fall recall
        +
Acceptable false-alert rate
        +
Acceptable detection latency
        +
Calibration check
        +
Edge performance
        +
Regression tests
        +
Privacy review
        +
Human approval
        ↓
PRODUCTION
```

---

# 47. Recommended Repository Structure

```text
fall-detection/
│
├── app/
│   ├── ingestion/
│   ├── detection/
│   ├── features/
│   ├── models/
│   ├── decision/
│   ├── alerts/
│   ├── api/
│   ├── database/
│   ├── monitoring/
│   └── config/
│
├── training/
│   ├── adapters/
│   ├── preprocessing/
│   ├── features/
│   ├── models/
│   ├── evaluation/
│   └── experiments/
│
├── data/
│   ├── raw/
│   ├── intermediate/
│   ├── processed/
│   └── metadata/
│
├── models/
│   ├── registry/
│   └── artifacts/
│
├── dashboard/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── model/
│   └── e2e/
│
├── scripts/
│
├── docs/
│
├── docker/
│
├── config/
│
├── .env.example
├── requirements.txt
└── README.md
```

---

# 48. Recommended Technology Stack

## Edge / ML

```text
Python
OpenCV
MediaPipe
PyTorch
scikit-learn
NumPy
Pandas
```

Potential tracking/detection components should be benchmarked before locking a library.

## Backend

```text
FastAPI
Python
Pydantic
SQLAlchemy
PostgreSQL
Redis
```

## Dashboard

For the first production iteration, existing Streamlit can remain for rapid delivery.

For a more scalable frontend:

```text
Next.js
TypeScript
Tailwind CSS
TanStack Query
```

## Deployment

```text
Docker
Nginx or equivalent reverse proxy
GitHub Actions / CI
Cloud or self-hosted Linux
```

---

# 49. Non-Functional Requirements

## Performance

Development target:

- Low-latency camera ingestion
- Stable real-time inference
- Bounded event-processing latency
- API response under approximately 500 ms for normal CRUD operations

ML inference latency must be benchmarked separately from API latency.

## Scalability

Architecture should support:

- Multiple edge devices
- Multiple cameras
- Multiple subjects
- Horizontal API scaling
- Centralized event storage

## Reliability

Must support:

- Health monitoring
- Restart/recovery
- Retries
- Graceful shutdown
- Database backups
- Structured logging

## Maintainability

Required:

- Type hints
- Modular services
- Configuration management
- Unit/integration tests
- API schema documentation
- Model metadata
- Dataset manifests

---

# 50. Failure Modes

## Camera Failure

```text
Camera unavailable
   ↓
DEVICE DEGRADED
   ↓
Dashboard warning
   ↓
Retry/reconnect
```

## Pose Failure

```text
Low pose quality
   ↓
No high-confidence decision
   ↓
Wait / mark uncertain
```

## Model Failure

```text
Model unavailable
   ↓
Device health error
   ↓
No false "normal" assumption
   ↓
Operator notification
```

## Backend Failure

The edge device should be able to continue local processing temporarily.

Events should be buffered locally until the backend becomes available, provided this does not violate the privacy/retention policy.

## Notification Failure

```text
Email failed
   ↓
Retry
   ↓
Secondary channel / escalation
```

---

# 51. Data Retention

The product must separate:

### Raw video

Short-lived / local only unless an explicit approved recording feature exists.

### Pose/keypoint data

Retain only when necessary for approved debugging, evaluation, or model-development workflows.

### Event metadata

Retain according to operational and privacy policy.

### Caregiver feedback

Retain long enough to support model-quality analysis and auditing.

Retention duration should be configurable by deployment environment.

---

# 52. Observability

## Logs

Structured JSON logs should include:

```text
timestamp
service
device_id
event_id
request_id
level
message
error_code
```

## Metrics

Recommended:

```text
frames_processed_total
inference_latency_ms
pose_quality_avg
events_created_total
possible_falls_total
confirmed_falls_total
false_positive_feedback_total
notification_failures_total
api_request_latency
device_disconnects_total
```

## Tracing

Add request/event tracing when system complexity justifies it.

---

# 53. Security and Privacy Boundaries for Multi-Device Systems

A device should authenticate to the backend.

Device credentials should be unique per device.

Do not use one shared credential across every camera/edge unit.

Example:

```text
Device A → credential A
Device B → credential B
Device C → credential C
```

Compromised devices must be revocable without rotating every device credential.

---

# 54. MVP Scope

The first production-oriented release should prioritize:

## Detection

- Camera abstraction
- Person detection/tracking
- MediaPipe pose
- Pose-quality check
- Current feature extraction
- Random Forest baseline
- Temporal model prototype
- Multi-window state machine
- 20-second grace period

## Data

- URFD baseline
- UP-Fall integration
- Approved ADL hard-negative data
- Reproducible preprocessing
- Subject-independent evaluation
- Cross-dataset validation

## Backend

- FastAPI
- PostgreSQL
- Device registration
- Subject assignment
- Event ingestion
- Alert management
- Caregiver feedback

## Notifications

- Email
- Retry logic
- Escalation state

## Dashboard

- Alerts
- Event detail
- Device health
- Response-time analytics
- Feedback

## Operations

- Docker
- Health checks
- CI tests
- Model versioning
- Secure configuration

---

# 55. Phase 2

Add:

- CNN-LSTM / TCN production candidate
- Probability calibration
- Better pose-quality modeling
- More hard-negative ADLs
- Multi-person robustness
- Explainable event evidence
- SMS/push
- Redis queue where necessary
- Advanced analytics
- Edge optimization

---

# 56. Phase 3

Add:

- Multimodal fusion
- Non-visual private-space sensing
- Radar/thermal integration where appropriate
- Caregiver feedback-driven retraining
- Model drift monitoring
- Automated evaluation pipelines
- Enterprise device management
- Advanced deployment orchestration

---

# 57. Future Research Track

Potential research directions:

1. Skeleton-based temporal transformers
2. Graph neural networks for skeletal joints
3. Self-supervised representation learning
4. Domain adaptation
5. Personalized calibration
6. Multi-camera fusion
7. Audio-assisted fall confirmation
8. Edge quantization
9. Continual learning with safeguards
10. Privacy-preserving federated learning

These are research opportunities, not MVP requirements.

---

# 58. Key Product Differentiator

The product should not be presented merely as:

> “An ML model that detects falls.”

The differentiator is:

> **A privacy-preserving, temporal, event-driven fall-response platform that connects edge computer vision, robust fall reasoning, caregiver workflows, and continuous model-quality improvement.**

The complete loop is:

```text
              CAMERA / SENSOR INPUT
                       ↓
               PERSON + POSE
                       ↓
              TEMPORAL FEATURES
                       ↓
               FALL ML ENGINE
                       ↓
            CALIBRATION + DECISION
                       ↓
                 POSSIBLE FALL
                       ↓
               20-SEC CONFIRM
                       ↓
              CONFIRMED EVENT
                       ↓
             BACKEND EVENT STORE
                       ↓
            CAREGIVER NOTIFICATION
                       ↓
             ACK / DISMISS / ESCALATE
                       ↓
                 FEEDBACK LABEL
                       ↓
               ERROR ANALYSIS
                       ↓
                 RETRAINING
                       ↓
               MODEL VALIDATION
                       ↓
               MODEL VERSIONING
                       ↓
               NEXT DEPLOYMENT
```

This creates a continuous quality-improvement cycle rather than a one-time ML demo.

---

# 59. Development Priority Matrix

| Priority | Workstream | Objective |
|---|---|---|
| P0 | Data | Replace single-dataset dependency |
| P0 | False-positive reduction | Improve ADL discrimination |
| P0 | Temporal decision logic | Reduce single-window alerts |
| P0 | Test cleanup | Establish trustworthy CI |
| P0 | Production data schema | Move beyond JSONL |
| P1 | Temporal model | Evaluate CNN-LSTM / TCN |
| P1 | Calibration | Make confidence meaningful |
| P1 | Tracking | Support multiple people |
| P1 | Pose quality | Handle missing/occluded joints |
| P1 | Backend API | Separate platform services |
| P1 | Model registry | Version and approve models |
| P2 | Feedback loop | Build hard-negative dataset |
| P2 | Explainability | Provide evidence summary |
| P2 | Edge optimization | Benchmark target devices |
| P3 | Multimodal sensing | Cover private spaces |
| P3 | Advanced research | GNN/Transformer/federated paths |

---

# 60. Current vs Target Architecture

| Area | Current System | Target System |
|---|---|---|
| Input | Webcam/video/RTSP support in prototype | Multi-source production edge ingestion |
| Person handling | Limited | Multi-person tracking |
| Pose | MediaPipe | MediaPipe + quality checks |
| Features | Velocity, stillness, orientation, dispersion | Spatial + kinematic + temporal + quality |
| Model | RF baseline | RF + evaluated temporal model |
| Decision | Threshold / `vote_windows=1` | Sliding-window state machine |
| Confidence | Raw threshold tiers | Calibrated confidence |
| Grace period | 20 sec | 20 sec, integrated with event state machine |
| Alerts | Email | Email + retry + optional SMS/push |
| Storage | JSON/JSONL | PostgreSQL |
| Backend | Local prototype services | FastAPI event platform |
| Dashboard | Streamlit | Streamlit MVP / scalable web frontend |
| Data | Mostly URFD | Multi-source + hard negatives + pilot validation |
| Feedback | Basic acknowledgement workflow | Structured true/false/uncertain labels |
| Model lifecycle | Manual | Versioned registry and release gate |
| Privacy | Local raw-video processing | Same principle with explicit backend boundary |
| Deployment | Local/demo | Docker + health monitoring + edge operations |

---

# 61. Definition of Done

The project is considered ready for the first production-oriented pilot only when:

### ML

- The baseline is reproducible.
- New multi-source data pipeline is reproducible.
- Subject leakage is prevented.
- Temporal model is benchmarked.
- Calibration is tested.
- Hard-negative ADLs are included.
- False-positive behavior is measured.

### Runtime

- Camera source can be switched without code modification.
- Multi-person tracking works on supported scenarios.
- Pose quality handling works.
- Decision state machine works.
- Grace-period timing is correct.
- System recovers from camera failure.

### Backend

- API authentication works.
- Events persist in PostgreSQL.
- Device and subject assignment works.
- Caregiver feedback persists.
- Notification status is recorded.

### Operations

- Docker deployment works.
- Health checks work.
- Tests pass.
- Secrets are externalized.
- Logs are structured.
- Model version is visible in events.

### Privacy

- Raw video does not leave the edge in the standard path.
- Access controls are enforced.
- Retention policy exists.
- Audit logging exists.

---

# 62. Implementation Order

The recommended engineering sequence is:

```text
STEP 1
Stabilize current repository
   ↓
Remove dead code
Fix stale tests
Lock configuration

STEP 2
Build dataset adapter framework
   ↓
URFD
UP-Fall
Approved ADL source
   ↓
Common schema

STEP 3
Build data-quality pipeline
   ↓
Pose extraction
Missing joint handling
Subject-safe splits

STEP 4
Improve feature pipeline
   ↓
Spatial
Kinematics
Temporal
Pose quality

STEP 5
Build temporal model
   ↓
CNN-LSTM / TCN
   ↓
Compare with RF

STEP 6
Build calibration
   ↓
Probability calibration

STEP 7
Build decision state machine
   ↓
Multi-window evidence
   ↓
Grace period

STEP 8
Add multi-person tracking
   ↓
Per-person state

STEP 9
Build FastAPI + PostgreSQL
   ↓
Event ingestion
   ↓
Alert management
   ↓
Feedback

STEP 10
Production dashboard
   ↓
Health
Alerts
Analytics

STEP 11
Edge deployment
   ↓
Docker
Health checks
Monitoring

STEP 12
Pilot validation
   ↓
Caregiver feedback
   ↓
Hard-negative mining
   ↓
Next model cycle
```

---

# 63. Reference Data Sources

The following sources are recommended for the revised training/evaluation program.

### Existing baseline

UR Fall Detection Dataset (URFD)

### Supplemental fall/ADL dataset

UP-Fall Detection Dataset  
Official source: https://sites.google.com/up.edu.mx/challenge-up-2019/data

### Supplemental action/skeleton dataset

NTU RGB+D / NTU RGB+D 120  
Official source: https://rose1.ntu.edu.sg/dataset/actionRecognition/

### Source-use rule

Each dataset must be reviewed for:

- License
- Academic/commercial restrictions
- Redistribution restrictions
- Allowed derivatives
- Privacy requirements

---

# 64. Documentation Set

The project should maintain:

```text
README.md
MASTER_PRD.md
ARCHITECTURE.md
DATA.md
MODEL.md
API.md
DEPLOYMENT.md
PRIVACY.md
SECURITY.md
TESTING.md
HANDOFF.md
CHANGELOG.md
```

`MASTER_PRD.md` is the product source of truth.

`ARCHITECTURE.md` is the engineering source of truth.

`DATA.md` is the dataset/source-of-truth document.

`MODEL.md` is the ML methodology and model-release document.

---

# 65. Final Product Summary

The current project provides the foundation for a privacy-preserving fall-detection prototype. Its strongest existing components are the on-device processing principle, pose-based feature extraction, Random Forest baseline, grace-period mechanism, alert workflow, dashboard, and subject-independent evaluation.

The master target is to evolve that prototype into a production-oriented event platform.

The central engineering change is:

```text
CURRENT
Frame / feature classification
        ↓
Basic threshold decision
        ↓
Alert

TARGET
Camera
  ↓
Person tracking
  ↓
Pose + pose quality
  ↓
Spatial + kinematic + temporal features
  ↓
Temporal model
  ↓
Calibrated probability
  ↓
Temporal state machine
  ↓
20-second confirmation
  ↓
Event API
  ↓
PostgreSQL
  ↓
Notification + caregiver workflow
  ↓
Structured feedback
  ↓
Continuous model-quality cycle
```

The central ML change is:

```text
URFD-only baseline
        ↓
Multi-source dataset strategy
        ↓
UP-Fall + hard-negative ADLs + approved validation data
        ↓
Better temporal representation
        ↓
Temporal model
        ↓
Calibration
        ↓
Real-world validation
```

The central product change is:

> **Move from a fall-classification demo to a privacy-preserving, event-driven fall detection and caregiver-response system with a reproducible data and model lifecycle.**

---

## Appendix A — Current Repository to Target Mapping

| Current file/component | Target responsibility |
|---|---|
| `camera.py` | `app/ingestion/` |
| `pose_extraction.py` | `app/detection/pose_extractor.py` |
| `features.py` | `app/features/` + training feature pipeline |
| `model_rf.py` | `app/models/random_forest.py` |
| `model_cnn_lstm.py` | `app/models/temporal_model.py` |
| `decision_logic.py` | `app/decision/state_machine.py` |
| `grace_period.py` | `app/decision/grace_period.py` |
| `alert.py` | `app/alerts/` |
| `stream_server.py` | `app/ingestion/` / edge gateway |
| `simulate_stream.py` | `tests/e2e/` + demo tooling |
| `evaluate.py` | `training/evaluation/` |
| `metrics.py` | `training/evaluation/metrics.py` |
| `dashboard/app.py` | `dashboard/` |
| JSON/JSONL logs | PostgreSQL event/alert store |
| `models/` | Versioned model registry/artifacts |
| `data/raw/` | Dataset adapters and raw source area |
| `data/processed/` | Reproducible processed-data outputs |

---

## Appendix B — Example Event Lifecycle

```text
1. Camera captures frame
2. Person tracker updates track 17
3. Pose extractor generates keypoints
4. Pose quality passes threshold
5. Feature engine updates track-17 sequence buffer
6. Temporal model returns calibrated fall score
7. Decision engine enters SUSPICIOUS
8. Consecutive evidence moves state to POSSIBLE_FALL
9. Grace period begins
10. Caregiver/local user can cancel
11. If not cancelled, event becomes CONFIRMED
12. Backend persists event
13. Notification service sends alert
14. Caregiver acknowledges
15. Caregiver marks TRUE_FALL / FALSE_POSITIVE / UNCERTAIN
16. Feedback enters quality-analysis dataset
17. ML engineer reviews error patterns
18. New model candidate is trained
19. Candidate is evaluated and approved
20. Model version is deployed to selected devices
```

---

## Appendix C — Decision Rules

The final system must avoid treating any single signal as definitive.

A candidate fall should preferably require a combination of:

```text
High / rising fall-model evidence
+
Temporal consistency
+
Meaningful vertical motion
+
Meaningful orientation change
+
Compatible low-body posture
+
Post-event stillness
+
Sufficient pose quality
```

When evidence is ambiguous:

```text
AMBIGUOUS
   ↓
WAIT FOR MORE OBSERVATIONS
```

rather than:

```text
AMBIGUOUS
   ↓
HIGH-CONFIDENCE ALERT
```

---

## Appendix D — Product Boundary

### Included

- Common-area fall detection
- Privacy-preserving edge inference
- Caregiver alerts
- Event analytics
- Model lifecycle
- Multi-source training
- Production backend

### Excluded from MVP

- Bathroom visual monitoring
- Medical diagnosis
- Autonomous emergency-service dispatch
- Unreviewed automatic model promotion
- Cloud storage of continuous raw video
- Guaranteed clinical-level detection claims

---

## Appendix E — Source Notes

This master PRD is structured after the supplied Capacity Connect PRD, preserving its emphasis on:

- Product overview
- Problem statement
- Product vision
- Product goals
- Target users
- High-level architecture
- Functional requirements
- Security
- Non-functional requirements
- Technology stack
- Database model
- API architecture
- Analytics
- User journeys
- MVP and phased scope
- Product differentiator

The domain-specific contents in this document are rewritten for the Fall Detection System and include a verified snapshot of the current public repository plus proposed target-state requirements.

### External research references used for the revised data strategy

- UP-Fall Detection Dataset official competition/data page: https://sites.google.com/up.edu.mx/challenge-up-2019/data
- UP-Fall Detection Dataset publication: https://pmc.ncbi.nlm.nih.gov/articles/PMC6539235/
- NTU RGB+D / RGB+D 120 official dataset page: https://rose1.ntu.edu.sg/dataset/actionRecognition/

---

## Document Status

**Current system:** Prototype / demonstration-capable baseline with ongoing engineering work.

**Target system:** Production-oriented privacy-preserving fall-event detection platform.

**Next engineering decision:** Implement the data-source abstraction and multi-source preprocessing pipeline before replacing the current ML decision architecture.
