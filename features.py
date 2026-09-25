"""
Feature Engineering Module
--------------------------
Computes temporal features from pose keypoint sequences for fall detection.
Features include vertical velocity, post-event stillness, and body orientation.
"""

import numpy as np
import pandas as pd
from typing import List
import logging

from project_config import load_config
from pathlib import Path

logger = logging.getLogger(__name__)

class FeatureEngineer:
    """Engineers fall-relevant features from pose keypoint sequences."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with configuration."""
        self.config = load_config(config_path)
        
        feat_config = self.config['features']
        self.window_sec = feat_config['window_sec']
        self.overlap = feat_config['overlap']
        self.fps = feat_config['fps']
        pose_config = self.config.get('pose', {}) or {}
        self.frame_stride = max(1, int(pose_config.get('frame_stride', 1)))
        self.sample_fps = self.fps / self.frame_stride
        if self.window_sec <= 0 or self.fps <= 0:
            raise ValueError("features.window_sec and features.fps must be positive")
        if not 0 <= self.overlap < 1:
            raise ValueError("features.overlap must be in the range [0, 1)")
        
        # MediaPipe Pose keypoint indices
        # Reference: https://google.github.io/mediapipe/solutions/pose.html#pose-landmarks
        self.KEYPOINT_INDICES = {
            'nose': 0,
            'left_eye_inner': 1, 'left_eye': 2, 'left_eye_outer': 3,
            'right_eye_inner': 4, 'right_eye': 5, 'right_eye_outer': 6,
            'left_ear': 7, 'right_ear': 8,
            'mouth_left': 9, 'mouth_right': 10,
            'left_shoulder': 11, 'right_shoulder': 12,
            'left_elbow': 13, 'right_elbow': 14,
            'left_wrist': 15, 'right_wrist': 16,
            'left_pinky': 17, 'right_pinky': 18,
            'left_index': 19, 'right_index': 20,
            'left_thumb': 21, 'right_thumb': 22,
            'left_hip': 23, 'right_hip': 24,
            'left_knee': 25, 'right_knee': 26,
            'left_ankle': 27, 'right_ankle': 28,
            'left_heel': 29, 'right_heel': 30,
            'left_foot_index': 31, 'right_foot_index': 32
        }
        
        # Key points for fall detection
        self.HIP_KEYPOINTS = [self.KEYPOINT_INDICES['left_hip'], 
                              self.KEYPOINT_INDICES['right_hip']]
        self.SHOULDER_KEYPOINTS = [self.KEYPOINT_INDICES['left_shoulder'],
                                   self.KEYPOINT_INDICES['right_shoulder']]
        self.TORSO_KEYPOINTS = self.HIP_KEYPOINTS + self.SHOULDER_KEYPOINTS
        
        logger.info(f"FeatureEngineer initialized: "
                   f"window={self.window_sec}s, overlap={self.overlap}, fps={self.fps}")
    
    def set_frame_stride(self, frame_stride: int) -> None:
        """Set the stride used by the live camera feeding this engineer."""
        self.frame_stride = max(1, int(frame_stride))
        self.sample_fps = self.fps / self.frame_stride

    def compute_vertical_velocity(self, keypoints_seq: List[np.ndarray]) -> np.ndarray:
        """
        Compute vertical velocity (dy/dt) for hip/torso keypoints.
        
        Args:
            keypoints_seq: List of keypoint arrays (T, 33, 3)
            
        Returns:
            Array of vertical velocities (T-1,) - negative = downward movement
        """
        if len(keypoints_seq) < 2:
            return np.array([])
        
        # Extract hip keypoints (average of left and right hip)
        hip_ys = []
        for kps in keypoints_seq:
            hip_points = kps[self.HIP_KEYPOINTS, 1]  # y-coordinate
            hip_ys.append(np.mean(hip_points))
        
        hip_ys = np.array(hip_ys)
        
        # Time between consecutive processed frames includes any configured
        # frame stride. Using 1/fps here inflates velocities for strided input.
        dt = self.frame_stride / self.fps
        velocities = np.diff(hip_ys) / dt
        
        return velocities  # Length T-1
    
    def compute_motion_magnitude(self, keypoints_seq: List[np.ndarray]) -> np.ndarray:
        """
        Compute overall motion magnitude (for stillness detection).
        
        Args:
            keypoints_seq: List of keypoint arrays (T, 33, 3)
            
        Returns:
            Array of motion magnitudes (T-1,)
        """
        if len(keypoints_seq) < 2:
            return np.array([])
        
        motion_mags = []
        for i in range(1, len(keypoints_seq)):
            # Compute mean squared displacement of key points
            prev_kps = keypoints_seq[i-1][:, :2]  # x, y only
            curr_kps = keypoints_seq[i][:, :2]
            
            # Use torso points for more stable measurement
            torso_prev = prev_kps[self.TORSO_KEYPOINTS]
            torso_curr = curr_kps[self.TORSO_KEYPOINTS]
            
            # Mean squared displacement
            msd = np.mean(np.sum((torso_curr - torso_prev)**2, axis=1))
            motion_mags.append(np.sqrt(msd))  # RMS displacement
        
        return np.array(motion_mags)
    
    def compute_aspect_ratio(self, keypoints: np.ndarray) -> float:
        """
        Compute body aspect ratio (height/width) from bounding box.
        
        Args:
            keypoints: Single frame keypoints (33, 3)
            
        Returns:
            Aspect ratio: height / width (>1 = standing-like, <1 = fallen-like)
        """
        # Use only keypoints with sufficient visibility
        valid_mask = keypoints[:, 2] > self.config['pose']['min_confidence']
        if np.sum(valid_mask) < 5:  # Need minimum points
            return 1.0  # Default to upright
        
        valid_points = keypoints[valid_mask, :2]  # x, y only
        
        if len(valid_points) == 0:
            return 1.0
        
        # Compute bounding box
        min_coords = np.min(valid_points, axis=0)
        max_coords = np.max(valid_points, axis=0)
        
        width = max_coords[0] - min_coords[0]
        height = max_coords[1] - min_coords[1]
        
        # Avoid division by zero
        if width < 1e-6:
            return 1.0
        
        return height / width
    
    def compute_torso_orientation(self, keypoints: np.ndarray) -> float:
        """
        Compute torso orientation angle from horizontal.
        
        Args:
            keypoints: Single frame keypoints (33, 3)
            
        Returns:
            Angle in degrees from horizontal (0 = upright, 90 = lying flat)
        """
        # Use shoulders and hips to define torso axis
        left_shoulder = keypoints[self.KEYPOINT_INDICES['left_shoulder'], :2]
        right_shoulder = keypoints[self.KEYPOINT_INDICES['right_shoulder'], :2]
        left_hip = keypoints[self.KEYPOINT_INDICES['left_hip'], :2]
        right_hip = keypoints[self.KEYPOINT_INDICES['right_hip'], :2]
        
        # Check visibility
        pts = [left_shoulder, right_shoulder, left_hip, right_hip]
        vis = [keypoints[idx, 2] for idx in 
               [self.KEYPOINT_INDICES['left_shoulder'],
                self.KEYPOINT_INDICES['right_shoulder'],
                self.KEYPOINT_INDICES['left_hip'],
                self.KEYPOINT_INDICES['right_hip']]]
        
        valid_pts = [pt for pt, v in zip(pts, vis) if v > self.config['pose']['min_confidence']]
        
        if len(valid_pts) < 2:
            return 0.0  # Default to upright
        
        # Fit line to torso points
        points = np.array(valid_pts)
        if len(points) >= 2:
            # Use PCA to find principal axis
            centered = points - np.mean(points, axis=0)
            # V.T contains the principal directions as rows; use the first
            # right singular vector of the (n_points, 2) matrix.
            _, _, vh = np.linalg.svd(centered, full_matrices=False)
            principal_axis = vh[0]
            
            # Angle away from vertical: upright torso ≈ 0°, horizontal torso
            # ≈ 90°. This matches the public feature contract and tests.
            angle = np.arctan2(np.abs(principal_axis[0]), np.abs(principal_axis[1]))
            return float(min(abs(np.degrees(angle)), 90.0))
        
        return 0.0
    
    def extract_window_features(self, 
                               keypoints_seq: List[np.ndarray],
                               window_start_idx: int,
                               window_end_idx: int) -> dict:
        """
        Extract features for a single time window.
        
        Args:
            keypoints_seq: Full keypoint sequence
            window_start_idx: Start index (inclusive)
            window_end_idx: End index (exclusive)
            
        Returns:
            Dictionary of feature values for this window
        """
        window_keypoints = keypoints_seq[window_start_idx:window_end_idx]
        window_size = len(window_keypoints)
        
        if window_size < 2:
            # Not enough data for features
            return {
                'hip_vert_vel': 0.0,
                'torso_vert_vel': 0.0,
                'velocity_magnitude': 0.0,
                'stillness_post': 0.0,
                'aspect_ratio_mean': 1.0,
                'aspect_ratio_min': 1.0,
                'torso_orientation_mean': 0.0,
                'keypoint_dispersion': 0.0,
                'motion_energy': 0.0
            }
        
        # 1. Vertical velocity of hips/torso (negative = downward)
        # 2. Post-event stillness is filled in by compute_features once future
        #    context is available.
        # 3. Current window characteristics
        hip_ys = []
        for kps in window_keypoints:
            hip_points = kps[self.HIP_KEYPOINTS, 1]
            hip_ys.append(np.mean(hip_points))
        hip_ys = np.array(hip_ys)
        
        hip_vel_window = np.array([])
        if len(hip_ys) > 1:
            hip_vel_window = np.diff(hip_ys) / (self.frame_stride / self.fps)
            vel_mean = np.mean(np.abs(hip_vel_window))
            vel_max = np.max(np.abs(hip_vel_window)) if len(hip_vel_window) > 0 else 0.0
        else:
            vel_mean = 0.0
            vel_max = 0.0
        
        # 4. Aspect ratio statistics
        aspect_ratios = []
        for kps in window_keypoints:
            ratio = self.compute_aspect_ratio(kps)
            aspect_ratios.append(ratio)
        
        # 5. Torso orientation
        orientations = []
        for kps in window_keypoints:
            orient = self.compute_torso_orientation(kps)
            orientations.append(orient)
        
        # 6. Keypoint dispersion (spread of joints)
        dispersions = []
        for kps in window_keypoints:
            valid_mask = kps[:, 2] > self.config['pose']['min_confidence']
            if np.sum(valid_mask) > 0:
                valid_points = kps[valid_mask, :2]
                if len(valid_points) > 0:
                    centroid = np.mean(valid_points, axis=0)
                    distances = np.linalg.norm(valid_points - centroid, axis=1)
                    dispersion = np.mean(distances)
                    dispersions.append(dispersion)
                else:
                    dispersions.append(0.0)
            else:
                dispersions.append(0.0)
        
        # 7. Motion energy (sum of squared velocities)
        motion_energy = np.sum(hip_vel_window**2) if len(hip_vel_window) > 0 else 0.0
        
        features = {
            'hip_vert_vel_mean': np.mean(hip_vel_window) if len(hip_vel_window) > 0 else 0.0,
            'hip_vert_vel_max': np.max(hip_vel_window) if len(hip_vel_window) > 0 else 0.0,
            'torso_vert_vel_mean': np.mean(hip_vel_window) if len(hip_vel_window) > 0 else 0.0,
            'velocity_magnitude': vel_mean,
            'velocity_max': vel_max,
            'aspect_ratio_mean': np.mean(aspect_ratios) if aspect_ratios else 1.0,
            'aspect_ratio_min': np.min(aspect_ratios) if aspect_ratios else 1.0,
            'aspect_ratio_max': np.max(aspect_ratios) if aspect_ratios else 1.0,
            'torso_orientation_mean': np.mean(orientations) if orientations else 0.0,
            'torso_orientation_max': np.max(orientations) if orientations else 0.0,
            'keypoint_dispersion_mean': np.mean(dispersions) if dispersions else 0.0,
            'keypoint_dispersion_std': np.std(dispersions) if len(dispersions) > 1 else 0.0,
            'motion_energy': motion_energy,
            'window_size': window_size
        }
        
        return features
    
    def compute_features(self, 
                        keypoints_seq: List[np.ndarray],
                        subject_id: str = "unknown",
                        clip_id: str = "unknown") -> pd.DataFrame:
        """
        Compute features for all windows in a keypoint sequence.
        
        Args:
            keypoints_seq: List of keypoint arrays (T, 33, 3)
            subject_id: Identifier for subject/actor
            clip_id: Identifier for video clip
            
        Returns:
            DataFrame with features for each window
        """
        if not 0 <= self.overlap < 1:
            raise ValueError("features.overlap must be in the range [0, 1)")
        if len(keypoints_seq) < 2:
            logger.warning(f"Sequence too short for feature extraction: {len(keypoints_seq)} frames")
            return pd.DataFrame()
        invalid_shapes = [
            index for index, frame in enumerate(keypoints_seq)
            if np.asarray(frame).shape != (33, 3)
        ]
        if invalid_shapes:
            raise ValueError(f"Expected keypoint frames shaped (33, 3); invalid indices: {invalid_shapes[:5]}")
        if any(not np.isfinite(np.asarray(frame)).all() for frame in keypoints_seq):
            raise ValueError("Keypoint frames must contain only finite values")
        
        # Window parameters
        window_length = max(2, int(round(self.window_sec * self.sample_fps)))
        step_size = max(1, int(round(window_length * (1 - self.overlap))))
        
        if window_length < 2:
            window_length = 2
            step_size = 1
        
        features_list = []
        
        # First pass: compute all window features except post-event stillness
        window_features = []
        window_starts = []
        window_ends = []
        
        start_idx = 0
        while start_idx + window_length <= len(keypoints_seq):
            end_idx = start_idx + window_length
            
            feats = self.extract_window_features(keypoints_seq, start_idx, end_idx)
            feats['subject_id'] = subject_id
            feats['clip_id'] = clip_id
            feats['window_start'] = start_idx
            feats['window_end'] = end_idx
            feats['window_start_time'] = start_idx / self.sample_fps
            feats['window_end_time'] = end_idx / self.sample_fps
            
            window_features.append(feats)
            window_starts.append(start_idx)
            window_ends.append(end_idx)
            
            start_idx += step_size
        
        # Second pass: compute post-event stillness for each window
        # Stillness = motion magnitude in the window AFTER this window
        motion_mags = self.compute_motion_magnitude(keypoints_seq)
        
        for i, feats in enumerate(window_features):
            # motion_mags[i] describes the transition from frame i to i+1.
            # The first transition after an exclusive window ending at
            # ``window_end_idx`` therefore starts at ``window_end_idx - 1``.
            win_end_idx = int(feats['window_end'])
            stillness_start_idx = max(0, win_end_idx - 1)
            stillness_end_idx = stillness_start_idx + window_length
            if stillness_end_idx <= len(motion_mags):
                stillness_window = motion_mags[stillness_start_idx:stillness_end_idx]
                feats['stillness_post'] = float(np.mean(stillness_window)) if len(stillness_window) else 0.0
            else:
                # This is expected for the newest live windows. Keep the
                # sentinel explicit rather than silently using partial data.
                feats['stillness_post'] = 0.0
            
            features_list.append(feats)
        
        if len(features_list) == 0:
            if len(keypoints_seq) < window_length:
                logger.debug(
                    "Waiting for a complete feature window: %s/%s frames",
                    len(keypoints_seq), window_length,
                )
            else:
                logger.warning("No features extracted - check window parameters")
            return pd.DataFrame()
        
        df = pd.DataFrame(features_list)
        logger.info(f"Extracted {len(df)} feature windows for {subject_id}/{clip_id}")
        
        return df
    
    def save_features(self, features_df: pd.DataFrame, output_path: Path):
        """Save features DataFrame to CSV."""
        if len(features_df) == 0:
            logger.warning(f"No features to save to {output_path}")
            return
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        features_df.to_csv(output_path, index=False)
        logger.info(f"Saved {len(features_df)} feature rows to {output_path}")
    
    def load_features(self, csv_path: Path) -> pd.DataFrame:
        """Load features DataFrame from CSV."""
        if not csv_path.exists():
            logger.error(f"Feature file not found: {csv_path}")
            return pd.DataFrame()
        
        df = pd.read_csv(csv_path)
        logger.info(f"Loaded {len(df)} feature rows from {csv_path}")
        return df

# Convenience functions
def compute_features_from_keypoints(keypoints: List[np.ndarray],
                                   subject_id: str = "unknown",
                                   clip_id: str = "unknown",
                                   config_path: str = "config.yaml") -> pd.Data:
    """Compute features from keypoint sequence."""
    engineer = FeatureEngineer(config_path)
    return engineer.compute_features(keypoints, subject_id, clip_id)

def compute_features_from_video(video_path: str,
                               subject_id: str = "unknown", 
                               clip_id: str = "unknown",
                               config_path: str = "config.yaml") -> pd.DataFrame:
    """Extract keypoints then compute features from video."""
    from pose_extraction import extract_keypoints_from_video
    
    keypoints = extract_keypoints_from_video(video_path, config_path)
    if len(keypoints) == 0:
        logger.warning(f"No keypoints extracted from {video_path}")
        return pd.DataFrame()
    
    return compute_features_from_keypoints(keypoints, subject_id, clip_id, config_path)

if __name__ == "__main__":
    # Example usage
    import sys
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        subject_id = sys.argv[2] if len(sys.argv) > 2 else "test"
        clip_id = sys.argv[3] if len(sys.argv) > 3 else "clip1"
        
        print(f"Computing features for: {video_path}")
        features_df = compute_features_from_video(video_path, subject_id, clip_id)
        
        if len(features_df) > 0:
            print(f"Extracted {len(features_df)} feature windows")
            print("\nFirst few rows:")
            print(features_df.head())
            
            # Save example
            output_path = Path("data/processed/features/example.csv")
            engineer = FeatureEngineer()
            engineer.save_features(features_df, output_path)
        else:
            print("No features extracted")
    else:
        print("Usage: python features.py <video_path> [subject_id] [clip_id]")