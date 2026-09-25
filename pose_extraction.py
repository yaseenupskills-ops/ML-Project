"""
Pose Extraction Module
----------------------
Extracts body keypoints from video using MediaPipe Pose.
Outputs only keypoint sequences (no frames saved to disk).
"""

from __future__ import annotations

import cv2
import mediapipe as mp
import numpy as np
from pathlib import Path
from typing import List, Generator, Optional, Tuple
import logging

from project_config import load_config

logger = logging.getLogger(__name__)

class PoseExtractor:
    """MediaPipe Pose wrapper with frame sampling and smoothing."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with configuration."""
        self.config = load_config(config_path)
        
        pose_config = self.config['pose']
        self.frame_stride = pose_config['frame_stride']
        self.smooth_window = pose_config['smooth_window']
        self.min_confidence = pose_config['min_confidence']
        if self.frame_stride < 1 or self.smooth_window < 1:
            raise ValueError("pose.frame_stride and pose.smooth_window must be positive")
        if not 0 <= self.min_confidence <= 1:
            raise ValueError("pose.min_confidence must be between 0 and 1")
        
        # Resolve the bundled model relative to the project, not the caller's cwd.
        self.model_path = Path(__file__).resolve().parent / 'models' / 'pose_landmarker_lite.task'
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Pose landmarker model not found: {self.model_path}. "
                "Run the project setup/model-download step first."
            )

        # Initialize MediaPipe Pose Landmarker (Tasks API)
        self.base_options = mp.tasks.BaseOptions(
            model_asset_path=str(self.model_path)
        )
        self.options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=self.base_options,
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=self.min_confidence,
            min_pose_presence_confidence=self.min_confidence,
            min_tracking_confidence=self.min_confidence,
        )
        self.detector = mp.tasks.vision.PoseLandmarker.create_from_options(self.options)
        
        # For smoothing
        self.keypoint_buffer = []
        
        logger.info(f"PoseExtractor initialized: "
                   f"frame_stride={self.frame_stride}, "
                   f"smooth_window={self.smooth_window}, "
                   f"min_confidence={self.min_confidence}")

    def reset(self) -> None:
        """Clear temporal state before starting a new sequence."""
        self.keypoint_buffer.clear()

    def close(self) -> None:
        """Release the MediaPipe landmarker."""
        detector = getattr(self, "detector", None)
        if detector is not None:
            try:
                detector.close()
            except Exception:
                logger.debug("Pose landmarker close failed", exc_info=True)
            self.detector = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def extract_keypoints_from_frame(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract pose keypoints from a single frame.
        
        Args:
            frame: BGR image from OpenCV
            
        Returns:
            Array of shape (33, 3) with [x, y, visibility] for each keypoint,
            or None if pose not detected with sufficient confidence
        """
        if frame is None or getattr(frame, "ndim", 0) != 3 or frame.shape[2] != 3:
            raise ValueError("Expected a BGR frame with shape (H, W, 3)")
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process with MediaPipe Pose Landmarker
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        detection_result = self.detector.detect(mp_image)
        
        if detection_result.pose_landmarks:
            # Extract landmarks: 33 keypoints with x, y, z, visibility
            landmarks = detection_result.pose_landmarks[0]
            keypoints = np.array([[lm.x, lm.y, lm.visibility] for lm in landmarks])
            
            # Check confidence: mean visibility > threshold
            if np.mean(keypoints[:, 2]) >= self.min_confidence:
                return keypoints
        
        return None
     
    def smooth_keypoints(self, keypoints: np.ndarray) -> np.ndarray:
        """
        Apply moving average smoothing to reduce noise.
        
        Args:
            keypoints: Current frame keypoints (33, 3)
            
        Returns:
            Smoothed keypoints (33, 3)
        """
        self.keypoint_buffer.append(keypoints)
        
        # Keep only recent frames
        if len(self.keypoint_buffer) > self.smooth_window:
            self.keypoint_buffer.pop(0)
        
        # Return mean of buffer
        if len(self.keypoint_buffer) > 0:
            return np.mean(self.keypoint_buffer, axis=0)
        return keypoints
    
    def process_video(self, video_path: str) -> Generator[Tuple[float, Optional[np.ndarray]], None, None]:
        """Process a video and yield ``(timestamp, keypoints_or_none)`` pairs."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError(f"Cannot open video file: {video_path}")

        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        if fps <= 0:
            cap.release()
            raise IOError(f"Video has an invalid FPS: {video_path}")

        self.reset()
        frame_count = 0
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                timestamp = frame_count / fps
                if frame_count % self.frame_stride == 0:
                    keypoints = self.extract_keypoints_from_frame(frame)
                    smoothed = self.smooth_keypoints(keypoints) if keypoints is not None else None
                    yield timestamp, smoothed
                frame_count += 1
        finally:
            cap.release()
            self.reset()


def extract_keypoints_from_video(
    video_path: str,
    config_path: str = "config.yaml",
) -> List[np.ndarray]:
    """Extract a compact keypoint sequence from one video file.

    This helper is intentionally small and is used by the feature CLI. It does
    not write frames or videos to disk.
    """
    extractor = PoseExtractor(config_path)
    try:
        return [
            keypoints
            for _, keypoints in extractor.process_video(video_path)
            if keypoints is not None
        ]
    finally:
        extractor.close()


def main() -> int:
    """Extract one video's pose sequence to a compact .npy file."""
    import argparse

    parser = argparse.ArgumentParser(description="Extract MediaPipe pose keypoints from a video")
    parser.add_argument("video", help="Input video path")
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output .npy path (default: data/processed/keypoints/<video-stem>.npy)",
    )
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    output = Path(args.output) if args.output else (
        Path(__file__).resolve().parent / "data" / "processed" / "keypoints" /
        (Path(args.video).stem + ".npy")
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    sequence = extract_keypoints_from_video(args.video, args.config)
    if not sequence:
        print("No pose keypoints detected; no output written.")
        return 1
    np.save(output, np.asarray(sequence, dtype=np.float32))
    print(f"Saved {len(sequence)} keypoint frames to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
