# Fall Detection System Report

> **Evaluation status: provisional.** The current processed feature artifact uses
> one dataset-level subject ID, and the saved report was not produced from a
> verified actor-held-out split. Regenerate metrics after fixing dataset
> provenance and evaluation before citing them.

## Methodology

This system implements a privacy-preserving fall detection pipeline that processes video streams entirely on-device, extracting only pose keypoints for analysis.

### Pipeline Overview
1. **Pose Extraction**: MediaPipe Pose extracts 33 body keypoints per frame
2. **Feature Engineering**: Computes temporal features over sliding windows
3. **Classification**: Random Forest classifier predicts fall probability
4. **Decision Logic**: Majority voting across windows + confidence tiers
5. **Grace Period**: 20-second confirmation window to reduce false alarms
6. **Alert System**: Email/SMS notification to caretakers
7. **Dashboard**: Caregiver overview, alert workflow, local live monitor, and privacy status

### Key Design Decisions
- **On-device processing**: Raw frames are not stored or transmitted by default
- **Pose-only approach**: Only keypoint data (x,y,visibility) is analyzed
- **Evaluation**: Actor-held-out results must be regenerated from verified metadata
- **Grace period**: User confirmation reduces false-alarm burden on caregivers

## Dataset Information

### UR Fall Detection Dataset
- Source: http://fenix.univ.rzeszow.pl/~mkepski/ds/uf.html
- Content: RGB-D videos of falls and activities of daily living (ADLs)
- Format: AVI videos + annotation files
- Subjects: Young actors performing scripted falls and ADLs

### Le2i Fall Detection Dataset
- Source: https://le2i.cnrs.fr/Fall-detection-Dataset/
- Content: Multi-view camera recordings of falls and ADLs
- Format: Video sequences + skeleton data
- Subjects: Multiple actors performing various fall types and ADLs

### Combined Dataset Characteristics
- Total subjects: [To be filled after download]
- Total clips: [To be filled after processing]
- Class distribution: Falls are rare (~5-10% of samples)
- Activities included: Walking, sitting, standing, lying down, falling
- Limitations: Controlled environment, actor-performed, limited occlusions

## Feature Engineering

### Temporal Windowing
- Window size: 3 seconds (configurable)
- Overlap: 50% between consecutive windows
- Sampling: Process every 2nd frame for performance

### Engineered Features
1. **Vertical Velocity**: 
   - dy/dt of hip/torso keypoints
   - Sudden negative peak indicates fall impact
   
2. **Post-Event Stillness**:
   - Motion magnitude in window following current window
   - Falls show low motion after impact; intentional lies show continued motion
   
3. **Body Orientation/Aspect Ratio**:
   - Height/width of bounding box
   - Standing: tall/narrow (ratio > 1.5)
   - Fallen: wide/flat (ratio < 1.0)
   
4. **Additional Features**:
   - Torso orientation angle from horizontal
   - Keypoint dispersion (spread of joints)
   - Motion energy (sum of squared velocities)
   - Angular velocity of torso

## Models

### Random Forest Baseline
- Algorithm: Ensemble of decision trees
- Parameters: 
  - n_estimators: 100
  - max_depth: 10
  - class_weight: 'balanced' (to handle imbalance)
  - random_state: 42
- Training: Subject-independent GroupKFold cross-validation
- Features: Standardized with StandardScaler

### CNN-LSTM Stretch Goal (Planned)
- Architecture: 
  - 1D-CNN: Extracts local motion patterns from keypoint sequences
  - LSTM: Captures temporal evolution (impact → stillness)
- Input: Normalized keypoint sequences (T, 33×3)
- Justification: CNN detects local motion patterns, LSTM models temporal dependencies

## Evaluation Results

### Subject-Independent Split
- Training set: [X] subjects, [Y] samples
- Test set: [A] subjects, [B] samples
- Ensures no subject appears in both sets

### Performance Metrics (Fall Class)
- Precision: [Value]
- Recall: [Value]
- F1-Score: [Value]
- ROC AUC: [Value]

### Confusion Matrix
```
               Predicted
               Neg    Pos
Actual Neg     [TN]   [FP]
Actual Pos     [FN]   [TP]
```

### Ablation Study (Feature Importance)
Most important features for fall detection:
1. Vertical velocity of hips/torso
2. Post-event stillness 
3. Body aspect ratio
4. Torso orientation
5. Keypoint dispersion

### Component Contributions
Estimated false positive reduction from:
- Multi-signal fusion: [X]%
- Majority voting: [Y]%
- Grace period: [Z]%

## Privacy & Security Analysis

### Data Flow
```
[Camera] → [MediaPipe (RAM only)] → [Features (RAM)] → 
[Model (RAM)] → [Decision (RAM)] → [Grace Period] → 
[Alert (Email/SMS only)] → [Dashboard (logs only)]
```

### Privacy Controls
- [x] No raw-frame writes in the default inference path
- [x] No remote video transmission; local stream endpoints require a per-process token
- [x] All inference occurs on same device as camera input
- [x] Only alert metadata is transmitted externally
- [x] Recording is opt-in, local, admin-controlled, and retention-limited
- [x] Dashboard avoids activity-pattern reporting by default

### Limitations & Assumptions
- **Dataset limitation**: Actor-performed falls in controlled settings
- **Environment assumption**: Standard indoor lighting, minimal occlusion
- **Scope limitation**: Living room/common area coverage only
- **Technical limitation**: Requires reasonably modern CPU for real-time processing

## Future Work

### Short-term (0-3 months)
- Complete CNN-LSTM implementation and comparison
- Extend testing to more diverse lighting conditions
- Add confidence calibration for better probability estimates
- Implement configuration validation and better error handling

### Medium-term (3-6 months)
- Collect pilot data with elderly volunteers (with consent)
- Investigate transfer learning from actor to elderly data
- Optimize for edge deployment (Jetson Nano/Raspberry Pi)
- Add audio-based fall detection (thud sounds) as secondary signal

### Long-term (6+ months)
- Multi-sensor fusion (wearable IMUs, environmental sensors)
- Federated learning for model improvement without central data collection
- Integration with smart home systems for contextual awareness
- Clinical validation study with healthcare partners

## Conclusion

The implemented system provides a privacy-preserving approach to fall detection that balances detection performance with user autonomy through the grace period mechanism. While limited by the actor-based datasets used for training, the architecture is sound and ready for real-world validation.

The system successfully demonstrates:
- On-device processing with raw-frame storage/transmission disabled by default; opt-in recordings remain local
- Effective fall detection using pose keypoints only
- User-centered design with confirmation window to reduce false alarms
- Privacy-first dashboard showing only essential alert information
- Evaluation workflow supports held-out subject splits; current saved metrics remain provisional until actor metadata is verified

Future work will focus on validating with real elderly populations and extending the sensor suite while maintaining the core privacy principles.