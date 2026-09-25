"""
Simulation Module
-----------------
Simulates real-time processing of fall detection pipeline.
Used for testing and demonstration.
"""

import numpy as np
import time
import logging
from typing import Generator, Optional, Tuple, List
from pathlib import Path

from project_config import load_config
import sys

# Import our modules
from pose_extraction import PoseExtractor
from features import FeatureEngineer
from model_rf import FallDetectionRF
from decision_logic import DecisionLogic
from grace_period import GracePeriodManager, simulate_grace_period
from alert import AlertManager
from camera import VideoFileCamera, create_camera
import metrics

logger = logging.getLogger(__name__)

class FallDetectionSimulator:
    """Simulates the full fall detection pipeline on recorded data."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize simulator with all pipeline components."""
        self.config_path = config_path
        self.config = load_config(config_path)
        
        # Initialize pipeline components
        self.pose_extractor = PoseExtractor(config_path)
        self.feature_engineer = FeatureEngineer(config_path)
        self.decision_logic = DecisionLogic(config_path)
        self.grace_period_manager = GracePeriodManager(config_path)
        self.alert_manager = AlertManager(config_path)
        
        # State tracking
        self.is_model_loaded = False
        self.model = None
        self.feature_names = None
        
        # Statistics
        self.stats = {
            'frames_processed': 0,
            'windows_evaluated': 0,
            'fall_candidates': 0,
            'alerts_triggered': 0,
            'false_positives_cancelled': 0,
            'processing_time_ms': 0.0
        }
        
        logger.info("FallDetectionSimulator initialized")
    
    def load_model(self, model_path: str):
        """Load trained classification model."""
        try:
            self.model = FallDetectionRF(self.config_path)
            self.model.load_model(Path(model_path))
            self.is_model_loaded = True
            logger.info(f"Model loaded from {model_path}")
        except Exception as e:
            logger.error(f"Failed to load model from {model_path}: {e}")
            raise
    
    def process_keypoint_sequence(self, 
                                 keypoints_sequence: List[np.ndarray],
                                 subject_id: str = "unknown",
                                 clip_id: str = "unknown") -> Generator[Tuple, None, None]:
        """
        Process a keypoint sequence through the full pipeline.
        
        Args:
            keypoints_sequence: List of keypoint arrays
            subject_id: Subject identifier
            clip_id: Clip identifier
            
        Yields:
            Tuples of (stage_name, stage_data) for monitoring pipeline progress
        """
        if not self.is_model_loaded:
            raise RuntimeError("Model must be loaded before processing")
        
        if len(keypoints_sequence) < 2:
            logger.warning("Keypoint sequence too short for processing")
            return
        
        # Extract features
        start_time = time.time()
        features_df = self.feature_engineer.compute_features(
            keypoints_sequence, subject_id, clip_id
        )
        feature_time = (time.time() - start_time) * 1000
        
        if len(features_df) == 0:
            logger.warning("No features extracted from sequence")
            return
        
        self.stats['windows_evaluated'] += len(features_df)
        yield ("features_extracted", {
            'feature_count': len(features_df),
            'feature_time_ms': feature_time,
            'features_df': features_df.copy()
        })
        
        # Prepare features for model (add dummy label for inference)
        try:
            features_df_with_label = features_df.copy()
            features_df_with_label['label'] = 0  # Dummy label
            
            X, y, groups = self.model.prepare_features(features_df_with_label)
            
        except Exception as e:
            logger.error(f"Failed to prepare features for model: {e}")
            return
        
        # Model inference. ``predict_proba`` applies the fitted scaler once.
        start_time = time.time()
        try:
            fall_probabilities = self.model.predict_proba(X)
            inference_time = (time.time() - start_time) * 1000
            self.stats['processing_time_ms'] += inference_time
            metrics.update(pipeline_latency_ms=round(inference_time, 2))
            
            # Extract positive class probability (class 1 = fall)
            if fall_probabilities.ndim == 2 and fall_probabilities.shape[1] == 2:
                fall_probabilities = fall_probabilities[:, 1]
            
            yield ("model_inference", {
                'probabilities': fall_probabilities,
                'inference_time_ms': inference_time,
                'num_windows': len(fall_probabilities)
            })
            
        except Exception as e:
            logger.error(f"Model inference failed: {e}")
            return
        
        # Add probabilities to dataframe
        features_df['fall_probability'] = fall_probabilities
        features_df['fall_prediction'] = (fall_probabilities >= 0.5).astype(int)
        
        # Apply decision logic (majority voting + confidence tiers)
        start_time = time.time()
        fall_events = self.decision_logic.process_predictions(features_df)
        decision_time = (time.time() - start_time) * 1000
        
        self.stats['fall_candidates'] += len(fall_events)
        yield ("decision_logic", {
            'fall_events': fall_events,
            'decision_time_ms': decision_time,
            'num_candidates': len(fall_events)
        })
        
        # Process each fall event through grace period and alerting
        for event in fall_events:
            # Convert FallEvent to dict for grace period
            event_dict = {
                # Decision windows use source-relative seconds; alert records
                # need an absolute Unix timestamp for response-time analysis.
                'timestamp': event.timestamp if event.timestamp > 1_000_000_000 else time.time(),
                'subject_id': event.subject_id,
                'clip_id': event.clip_id,
                'confidence': event.confidence,
                'tier': event.tier,
                'window_start': event.window_start,
                'window_end': event.window_end,
                'video_clip_path': ''
            }
            
            # Grace period (use simulate_grace_period for testing with auto-respond)
            start_time = time.time()
            grace_result = simulate_grace_period(event_dict, auto_respond_after=None)
            grace_time = (time.time() - start_time) * 1000
            
            yield ("grace_period", {
                'event': event_dict,
                'result': grace_result,
                'grace_time_ms': grace_time
            })
            
            if grace_result.alert_triggered:
                self.stats['alerts_triggered'] += 1
                metrics.register_alert(grace_result.timestamp or time.time())
                if grace_result.outcome == 'cancelled':
                    self.stats['false_positives_cancelled'] += 1
            
            metrics.update(
                frames_processed=self.stats['frames_processed'],
                windows_evaluated=self.stats['windows_evaluated'],
                pipeline_running=True,
            )
            
            # Alerting
            if grace_result.alert_triggered:
                start_time = time.time()
                alert_sent = self.alert_manager.send_alert(
                    event_dict, 
                    {
                        'outcome': grace_result.outcome,
                        'response_time': grace_result.response_time,
                        'timestamp': grace_result.timestamp
                    },
                    method='email'  # Could make configurable
                )
                alert_time = (time.time() - start_time) * 1000
                
                yield ("alert_sent", {
                    'event': event_dict,
                    'grace_result': grace_result,
                    'alert_sent': alert_sent,
                    'alert_time_ms': alert_time
                })
    
    def simulate_from_file(self, 
                          keypoints_file: Path,
                          subject_id: str = "unknown",
                          clip_id: str = "unknown") -> dict:
        """
        Simulate processing from a saved keypoints file.
        
        Args:
            keypoints_file: Path to .npy file containing keypoint sequence
            subject_id: Subject identifier
            clip_id: Clip identifier
            
        Returns:
            Dictionary with simulation results and statistics
        """
        # Load keypoints
        try:
            keypoints_sequence = []
            data = np.load(keypoints_file)
            for i in range(data.shape[0]):
                keypoints_sequence.append(data[i])
            logger.info(f"Loaded {len(keypoints_sequence)} keypoint frames from {keypoints_file}")
        except Exception as e:
            logger.error(f"Failed to load keypoints from {keypoints_file}: {e}")
            return {'error': str(e)}
        
        # Reset statistics
        self.stats = {
            'frames_processed': len(keypoints_sequence),
            'windows_evaluated': 0,
            'fall_candidates': 0,
            'alerts_triggered': 0,
            'false_positives_cancelled': 0,
            'processing_time_ms': 0.0
        }
        
        # Process sequence
        events_processed = 0
        alerts_sent = 0
        false_positives = 0
        
        try:
            for stage, data in self.process_keypoint_sequence(
                keypoints_sequence, subject_id, clip_id
            ):
                events_processed += 1
                
                if stage == "alert_sent" and data['alert_sent']:
                    alerts_sent += 1
                elif stage == "grace_period" and data['result'].outcome == 'cancelled':
                    false_positives += 1
                    
        except Exception as e:
            logger.error(f"Error during simulation: {e}")
            return {'error': str(e), 'stats': self.stats}
        
        # Compile results
        results = {
            'subject_id': subject_id,
            'clip_id': clip_id,
            'total_frames': len(keypoints_sequence),
            'stats': self.stats.copy(),
            'summary': {
                'events_processed': events_processed,
                'alerts_sent': alerts_sent,
                'false_positives_cancelled': false_positives,
                'true_positives': alerts_sent - false_positives
            }
        }
        
        logger.info(f"Simulation complete: {results['summary']}")
        return results

    def run_live_detection(
        self,
        camera_index: int = 0,
        subject_id: str = "live",
        duration_sec: Optional[float] = None,
        max_frames: Optional[int] = None,
        display: bool = False,
        camera_obj: Optional[object] = None,
        camera_source: Optional[str] = None
    ) -> dict:
        """
        Run live fall detection from camera or video file.
        
        Args:
            camera_index: Camera device index (used if camera_obj/source not set)
            subject_id: Subject identifier
            duration_sec: Maximum duration in seconds (None for infinite)
            max_frames: Maximum frames to process (None for infinite)
            display: Show live preview window
            camera_obj: Pre-initialized camera object (CameraManager or VideoFileCamera)
            camera_source: Unified source (int index | file path | RTSP URL). If None,
                           reads camera.source from config (fallback camera.index).
            
        Returns:
            Dictionary with detection statistics
        """
        if not self.is_model_loaded:
            raise RuntimeError("Model must be loaded before processing")
        
        cam_config = self.config.get('camera', {})
        # Initialize camera
        if camera_obj is not None:
            cam = camera_obj
        else:
            src = camera_source if camera_source is not None else cam_config.get(
                'source', cam_config.get('index', camera_index)
            )
            cam = create_camera(
                src,
                width=cam_config.get('width', 640),
                height=cam_config.get('height', 480),
                fps=cam_config.get('fps', 30),
                buffer_size=cam_config.get('buffer_size', 3)
            )
        
        if not cam.start():
            raise RuntimeError("Failed to start camera")
        
        src_label = getattr(cam, 'video_path', None) or getattr(cam, 'camera_index', 'unknown')
        logger.info(f"Starting live detection on source {src_label}")
        
        # Statistics
        stats = {
            'frames_processed': 0,
            'windows_evaluated': 0,
            'fall_candidates': 0,
            'alerts_triggered': 0,
            'false_positives_cancelled': 0,
            'processing_time_ms': 0.0,
            'fps': 0.0
        }
        
        start_time = time.time()
        frame_count = 0
        keypoint_buffer = []
        last_fps_time = time.time()
        frames_since_fps = 0
        
        try:
            logger.info("Starting live fall detection... Press Ctrl+C to stop")
            
            while True:
                # Check stop conditions
                if duration_sec and (time.time() - start_time) >= duration_sec:
                    logger.info(f"Duration limit reached ({duration_sec}s)")
                    break
                if max_frames and frame_count >= max_frames:
                    logger.info(f"Max frames reached ({max_frames})")
                    break
                
                # Read frame
                frame = cam.read_frame()
                if frame is None:
                    time.sleep(0.01)
                    continue
                
                frame_count += 1
                frames_since_fps += 1
                
                # Update FPS counter
                if time.time() - last_fps_time >= 1.0:
                    cam.fps_actual = frames_since_fps / (time.time() - last_fps_time)
                    frames_since_fps = 0
                    last_fps_time = time.time()
                
                # Process every Nth frame
                if frame_count % cam_config.get('frame_stride', 1) != 0:
                    continue
                
                # Extract keypoints
                keypoints = self.pose_extractor.extract_keypoints_from_frame(frame)
                if keypoints is None:
                    continue
                
                # Smooth keypoints
                smoothed = self.pose_extractor.smooth_keypoints(keypoints)
                keypoint_buffer.append(smoothed)
                
                # Keep buffer size reasonable
                if len(keypoint_buffer) > 30:
                    keypoint_buffer.pop(0)
                
                # Need enough frames for feature extraction
                if len(keypoint_buffer) < 2:
                    continue
                
                # Extract features
                self.feature_engineer.set_frame_stride(
                    int(cam_config.get('frame_stride', 1))
                )
                features_df = self.feature_engineer.compute_features(
                    keypoint_buffer, subject_id='live', clip_id='live'
                )
                
                if len(features_df) == 0:
                    continue
                
                # Prepare features for model
                features_df_with_label = features_df.copy()
                features_df_with_label['label'] = 0
                
                try:
                    X, _, _ = self.model.prepare_features(features_df_with_label)
                    
                    # Model inference. The model wrapper applies scaling once.
                    fall_probabilities = self.model.predict_proba(X)
                    
                    # Extract positive class probability (class 1 = fall)
                    if fall_probabilities.ndim == 2 and fall_probabilities.shape[1] == 2:
                        fall_probabilities = fall_probabilities[:, 1]
                    
                    features_df['fall_probability'] = fall_probabilities
                    features_df['fall_prediction'] = (fall_probabilities >= 0.5).astype(int)
                    
                    # Apply decision logic (majority voting + confidence tiers)
                    fall_events = self.decision_logic.process_predictions(features_df)
                    
                    for event in fall_events:
                        event.subject_id = 'live'
                        event.clip_id = 'live'
                        stats['fall_candidates'] += 1
                        
                        # Grace period (non-blocking for live mode)
                        grace_result = simulate_grace_period(
                            {
                                'timestamp': event.timestamp,
                                'subject_id': event.subject_id,
                                'clip_id': event.clip_id,
                                'confidence': event.confidence,
                                'tier': event.tier
                            },
                            auto_respond_after=None  # No auto-respond in live mode
                        )
                        
                        if grace_result.alert_triggered:
                            stats['alerts_triggered'] += 1
                            metrics.register_alert(grace_result.timestamp or time.time())
                            
                            # Send alert
                            event_dict = {
                                'timestamp': time.time(),
                                'subject_id': event.subject_id,
                                'clip_id': event.clip_id,
                                'confidence': event.confidence,
                                'tier': event.tier
                            }
                            grace_result_dict = {
                                'outcome': grace_result.outcome,
                                'response_time': grace_result.response_time,
                                'timestamp': grace_result.timestamp
                            }
                            self.alert_manager.send_alert(event_dict, grace_result_dict)
                
                except Exception as e:
                    logger.error(f"Processing error: {e}")
                    continue
                
                metrics.update(
                    frames_processed=frame_count,
                    fps=round(getattr(cam, 'fps_actual', 0.0), 2),
                    pipeline_running=True,
                )
                
                # Display FPS
                if time.time() - last_fps_time >= 1.0:
                    cam.fps_actual = frames_since_fps / (time.time() - last_fps_time)
                    frames_since_fps = 0
                    last_fps_time = time.time()
                    print(f"FPS: {cam.fps_actual:.1f} | Frames: {frame_count} | Falls: {stats['fall_candidates']} | Alerts: {stats['alerts_triggered']}")
            
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            cam.stop()
        
        stats['fps'] = frame_count / (time.time() - start_time) if time.time() > start_time else 0
        stats['total_frames'] = frame_count
        
        summary = {
            'frames_processed': frame_count,
            'windows_evaluated': stats['windows_evaluated'],
            'fall_candidates': stats['fall_candidates'],
            'alerts_triggered': stats['alerts_triggered'],
            'false_positives_cancelled': stats['false_positives_cancelled'],
        }
        return {
            'subject_id': 'live',
            'clip_id': 'live',
            'total_frames': frame_count,
            'stats': stats,
            'summary': summary,
        }

def simulate_from_keypoints_file(
    keypoints_file: str,
    model_path: str,
    subject_id: str = "unknown",
    clip_id: str = "unknown",
    config_path: str = "config.yaml",
) -> dict:
    """Run the simulator for one saved keypoint file."""
    simulator = FallDetectionSimulator(config_path)
    simulator.load_model(model_path)
    return simulator.simulate_from_file(
        Path(keypoints_file), subject_id=subject_id, clip_id=clip_id
    )


def simulate_stream(keypoints_directory: str,
                    model_path: str,
                    config_path: str = "config.yaml",
                    max_files: Optional[int] = None) -> List[dict]:
    """
    Simulate processing multiple keypoint files from a directory.
    
    Args:
        keypoints_directory: Directory containing .npy keypoint files
        model_path: Path to trained model
        config_path: Path to configuration file
        max_files: Maximum number of files to process (None for all)
        
    Returns:
        List of simulation results for each file
    """
    # Initialize simulator
    # Initialize simulator
    simulator = FallDetectionSimulator(config_path)
    simulator.load_model(model_path)
    
    # Find keypoint files
    kp_dir = Path(keypoints_directory)
    if not kp_dir.exists():
        raise FileNotFoundError(f"Directory not found: {keypoints_directory}")
    
    kp_files = list(kp_dir.glob("*.npy"))
    if max_files is not None:
        kp_files = kp_files[:max_files]
    
    logger.info(f"Found {len(kp_files)} keypoint files to process")
    
    results = []
    for i, kp_file in enumerate(kp_files):
        logger.info(f"Processing file {i+1}/{len(kp_files)}: {kp_file.name}")
        
        # Extract subject/clip from filename if possible
        # Expected format: {subject}_{clip}_{angle}.npy or similar
        stem = kp_file.stem
        parts = stem.split('_')
        subject_id = parts[0] if len(parts) > 0 else "unknown"
        clip_id = '_'.join(parts[1:-1]) if len(parts) > 2 else "unknown"
        
        # Process file
        result = simulator.simulate_from_file(kp_file, subject_id, clip_id)
        results.append(result)
        
        # Progress update
        if (i + 1) % 10 == 0 or i == len(kp_files) - 1:
            logger.info(f"Processed {i+1}/{len(kp_files)} files")
    
    return results

def evaluate_simulation_results(results: List[dict]) -> dict:
    """
    Aggregate and evaluate simulation results across multiple files.
    
    Args:
        results: List of simulation result dictionaries
        
    Returns:
        Dictionary with aggregated metrics
    """
    total_frames = 0
    total_windows = 0
    total_candidates = 0
    total_alerts = 0
    total_false_positives = 0
    total_processing_time = 0.0
    
    file_results = []
    
    for result in results:
        if 'error' in result:
            continue
            
        stats = result['stats']

        total_frames += stats['frames_processed']
        total_windows += stats['windows_evaluated']
        total_candidates += stats['fall_candidates']
        total_alerts += stats['alerts_triggered']
        total_false_positives += stats['false_positives_cancelled']
        total_processing_time += stats['processing_time_ms']
        
        file_results.append({
            'subject_id': result['subject_id'],
            'clip_id': result['clip_id'],
            'frames': stats['frames_processed'],
            'windows': stats['windows_evaluated'],
            'candidates': stats['fall_candidates'],
            'alerts': stats['alerts_triggered'],
            'false_positives': stats['false_positives_cancelled'],
            'processing_time_ms': stats['processing_time_ms']
        })
    
    # Calculate aggregated metrics
    if total_windows > 0:
        avg_windows_per_second = total_windows / (total_processing_time / 1000) if total_processing_time > 0 else 0
        fall_rate = total_candidates / total_windows if total_windows > 0 else 0
        alert_rate = total_alerts / total_windows if total_windows > 0 else 0
        false_positive_rate = total_false_positives / total_windows if total_windows > 0 else 0
        precision = (total_alerts - total_false_positives) / total_alerts if total_alerts > 0 else 0
    else:
        avg_windows_per_second = 0
        fall_rate = 0
        alert_rate = 0
        false_positive_rate = 0
        precision = 0
    
    aggregated = {
        'total_files_processed': len([r for r in results if 'error' not in r]),
        'total_frames': total_frames,
        'total_windows_evaluated': total_windows,
        'total_fall_candidates': total_candidates,
        'total_alerts_triggered': total_alerts,
        'total_false_positives_cancelled': total_false_positives,
        'total_processing_time_ms': total_processing_time,
        'metrics': {
            'windows_per_second': avg_windows_per_second,
            'fall_candidate_rate': fall_rate,
            'alert_rate': alert_rate,
            'false_positive_rate': false_positive_rate,
            'precision_estimate': precision,
            'avg_processing_time_per_window_ms': total_processing_time / total_windows if total_windows > 0 else 0
        },
        'per_file_results': file_results
    }
    
    return aggregated



if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python simulate_stream.py --camera <index> [model_path] [duration_sec]")
        print("  python simulate_stream.py --video <video_file> [model_path] [duration_sec]")
        print("  python simulate_stream.py <keypoints_file.npy> <model_path> [subject_id] [clip_id]")
        print("  python simulate_stream.py <keypoints_dir> <model_path> --dir [max_files]")
        sys.exit(1)
    
    if sys.argv[1] in ("-h", "--help"):
        print("Usage:")
        print("  python simulate_stream.py --camera <index> [model_path] [duration_sec]")
        print("  python simulate_stream.py --video <video_file> [model_path] [duration_sec]")
        print("  python simulate_stream.py <keypoints_file.npy> <model_path> [subject_id] [clip_id]")
        print("  python simulate_stream.py <keypoints_dir> <model_path> --dir [max_files]")
        sys.exit(0)
    
    if sys.argv[1] == "--camera":
        # Live camera mode
        if len(sys.argv) < 3:
            print("Usage: python simulate_stream.py --camera <index> [model_path] [duration_sec]")
            sys.exit(1)
        camera_index = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        model_path = sys.argv[3] if len(sys.argv) > 3 else "models/rf_baseline.joblib"
        duration_sec = float(sys.argv[4]) if len(sys.argv) > 4 else None
        
        sim = FallDetectionSimulator()
        sim.load_model(model_path)
        result = sim.run_live_detection(camera_index=camera_index, duration_sec=duration_sec)
        print(f"Live detection complete: {result['summary']}")
    elif sys.argv[1] == "--video":
        # Video file mode (for demos)
        if len(sys.argv) < 3:
            print("Usage: python simulate_stream.py --video <video_file> [model_path] [duration_sec]")
            sys.exit(1)
        video_file = sys.argv[2]
        model_path = sys.argv[3] if len(sys.argv) > 3 else "models/rf_baseline.joblib"
        duration_sec = float(sys.argv[4]) if len(sys.argv) > 4 else None
        
        sim = FallDetectionSimulator()
        sim.load_model(model_path)
        
        # Create video file camera
        video_config = sim.config.get('video', {})
        cam = VideoFileCamera(
            video_path=sys.argv[2],
            width=sim.config.get('video', {}).get('width', 640),
            height=sim.config.get('video', {}).get('height', 480),
            fps=sim.config.get('video', {}).get('fps', 30),
            loop=sim.config.get('video', {}).get('loop', True),
            frame_stride=sim.config.get('video', {}).get('frame_stride', 1),
            real_time=sim.config.get('video', {}).get('real_time', True)
        )
        
        print(f"Processing video: {sys.argv[2]}")
        result = sim.run_live_detection(camera_obj=cam, duration_sec=duration_sec)
        print(f"Video detection complete: {result['summary']}")
    elif len(sys.argv) > 3 and sys.argv[3] == "--dir":
        # Directory mode
        keypoints_dir = sys.argv[1]
        model_path = sys.argv[2]
        max_files = int(sys.argv[4]) if len(sys.argv) > 4 else None
        
        print(f"Simulating stream from directory: {keypoints_dir}")
        results = simulate_stream(keypoints_dir, model_path, max_files=max_files)
        
        # Evaluate results
        evaluation = evaluate_simulation_results(results)
        
        print("\n" + "="*50)
        print("SIMULATION RESULTS")
        print("="*50)
        print(f"Files processed: {evaluation['total_files_processed']}")
        print(f"Total frames: {evaluation['total_frames']}")
        print(f"Total windows evaluated: {evaluation['total_windows_evaluated']}")
        print(f"Total fall candidates: {evaluation['total_fall_candidates']}")
        print(f"Total alerts triggered: {evaluation['total_alerts_triggered']}")
        print(f"Total false positives cancelled: {evaluation['total_false_positives_cancelled']}")
        print(f"Total processing time: {evaluation['total_processing_time_ms']:.1f} ms")
        
        print("\nMetrics:")
        for key, value in evaluation['metrics'].items():
            if isinstance(value, float):
                print(f"  {key}: {value:.3f}")
            else:
                print(f"  {key}: {value}")
    else:
        # Single file mode
        keypoints_file = sys.argv[1]
        model_path = sys.argv[2]
        subject_id = sys.argv[3] if len(sys.argv) > 3 else "unknown"
        clip_id = sys.argv[4] if len(sys.argv) > 4 else "unknown"
        
        print(f"Simulating stream from file: {keypoints_file}")
        result = simulate_from_keypoints_file(
            keypoints_file, model_path, subject_id, clip_id
        )
        
        if 'error' in result:
            print(f"Error: {result['error']}")
            sys.exit(1)
        
        print("\n" + "="*50)
        print("SIMULATION RESULTS")
        print("="*50)
        print(f"Subject: {result['subject_id']}")
        print(f"Clip: {result['clip_id']}")
        print(f"Frames processed: {result['stats']['frames_processed']}")
        print(f"Windows evaluated: {result['stats']['windows_evaluated']}")
        print(f"Fall candidates: {result['stats']['fall_candidates']}")
        print(f"Alerts triggered: {result['stats']['alerts_triggered']}")
        print(f"False positives cancelled: {result['stats']['false_positives_cancelled']}")
        print(f"Processing time: {result['stats']['processing_time_ms']:.1f} ms")
        
        if result['stats']['windows_evaluated'] > 0:
            windows_per_sec = result['stats']['windows_evaluated'] / (result['stats']['processing_time_ms'] / 1000)
            print(f"\nProcessing rate: {windows_per_sec:.1f} windows/second")

if __name__ == "__main__":
    pass  # Main block ends here