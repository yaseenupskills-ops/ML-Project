"""
Pose Extraction Module
----------------------
Extracts body keypoints from video using MediaPipe Pose.
Outputs only keypoint sequences (no frames saved to disk).
"""

import cv2
import mediapipe as mp
import numpy as np
from pathlib import Path
from typing import List, Generator, Optional, Tuple
import yaml
import logging

logger = logging.getLogger(__name__)

class PoseExtractor:
    """MediaPipe Pose wrapper with frame sampling and smoothing."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with configuration."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        pose_config = self.config['pose']
        self.frame_stride = pose_config['frame_stride']
        self.smooth_window = pose_config['smooth_window']
        self.min_confidence = pose_config['min_confidence']
        
        # Initialize MediaPipe Pose Landmarker (Tasks API)
        self.base_options = mp.tasks.BaseOptions(
            model_asset_path='models/pose_landmarker_lite.task'
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
     
    def extract_keypoints_from_frame(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract pose keypoints from a single frame.
        
        Args:
            frame: BGR image from OpenCV
            
        Returns:
            Array of shape (33, 3) with [x, y, visibility] for each keypoint,
            or None if pose not detected with sufficient confidence
        """
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
        """
        Process video file and yield timestamps and keypoints.
        
        Args:
            video_path: Path to video file
            
        Yields:
            Tuple of (timestamp_seconds, keypoints_array or None)
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError(f"Cannot open video file: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            timestamp = frame_count / fps
            
            # Process every Nth frame based on frame_stride
            if frame_count % self.frame_stride == 0:
                keypoints = self.extract_keypoints_from_frame(frame)
                smoothed_keypoints = self.smooth_keypoints(keypoints) if keypoints is not None else None
                yield timestamp, smoothed_keypoints
            
            frame_count += 1
        
        cap.release()
        # Flush any remaining buffered keypoints
        if len(self.keypoint_buffer) > 0:
            yield timestamp, self.smooth_keypoints(np.zeros((33, 3)))  # Return zeros to flush buffer