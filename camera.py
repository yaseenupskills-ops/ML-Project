"""
Camera Manager
--------------
Abstraction layer for camera input (USB, CSI, RTSP).
Provides frame capture with buffering and FPS control.
"""

import cv2
import threading
import time
import uuid
import logging
from typing import Optional, Tuple, Generator
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)


class CameraManager:
    """Thread-safe camera manager with frame buffering."""
    
    def __init__(
        self,
        camera_index: int = 0,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        buffer_size: int = 3,
        backend: int = cv2.CAP_ANY
    ):
        """
        Initialize camera manager.
        
        Args:
            camera_index: Camera device index (0, 1, ...) or RTSP URL string
            width: Frame width
            height: Frame height
            fps: Target FPS
            buffer_size: Frame buffer size for smoothing
            backend: OpenCV backend (cv2.CAP_ANY, cv2.CAP_V4L2, cv2.CAP_GSTREAMER, etc.)
        """
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.target_fps = fps
        self.buffer_size = buffer_size
        self.backend = backend
        
        self.cap: Optional[cv2.VideoCapture] = None
        self.frame_buffer = []
        self.buffer_lock = threading.Lock()
        self.running = False
        self.capture_thread: Optional[threading.Thread] = None
        self.frame_count = 0
        self.start_time = 0
        self.fps_actual = 0.0
        self._consecutive_read_failures = 0

        # Recording state (Phase 3)
        self._recording_active = False
        self._rec_thread: Optional[threading.Thread] = None
        self._rec_writer = None
        self._rec_path: Optional[Path] = None
        self._record_dir: Optional[Path] = None
        self._rec_segment_start = None
        self._rec_segment_duration = 300.0
        self._rec_fps = 20.0
        self.supports_recording = True
        
        logger.info(f"CameraManager initialized: index={camera_index}, "
                   f"resolution={width}x{height}, target_fps={fps}")
    
    def start(self) -> bool:
        """Start camera capture thread."""
        if self.running:
            logger.warning("Camera already running")
            return True
        
        # Open camera
        if isinstance(self.camera_index, str):
            # RTSP or file URL
            self.cap = cv2.VideoCapture(self.camera_index, self.backend)
        else:
            self.cap = cv2.VideoCapture(self.camera_index, self.backend)
        
        if not self.cap.isOpened():
            logger.error(f"Failed to open camera index {self.camera_index}")
            return False
        
        # Set camera properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, self.buffer_size)
        
        # Verify actual settings
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
        
        logger.info(f"Camera opened: {actual_width}x{actual_height} @ {actual_fps:.1f}fps")
        
        # Read first frame to verify
        ret, frame = self.cap.read()
        if not ret:
            logger.error("Failed to read first frame")
            self.cap.release()
            return False
        
        self.running = True
        self.frame_count = 0
        self._consecutive_read_failures = 0
        self.start_time = time.time()
        
        # Start capture thread
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        
        logger.info("Camera capture started")
        return True
    
    def _capture_loop(self):
        """Background thread to continuously capture frames."""
        frame_interval = 1.0 / self.target_fps
        
        while self.running:
            loop_start = time.time()
            
            ret, frame = self.cap.read()
            if not ret:
                self._consecutive_read_failures += 1
                if self._consecutive_read_failures in {1, 5} or self._consecutive_read_failures % 50 == 0:
                    logger.warning(
                        "Failed to read frame (%s consecutive failures)",
                        self._consecutive_read_failures,
                    )
                time.sleep(min(0.01 * self._consecutive_read_failures, 1.0))
                continue
            self._consecutive_read_failures = 0

            # Add to buffer
            with self.buffer_lock:
                self.frame_buffer.append((time.time(), frame))
                if len(self.frame_buffer) > self.buffer_size:
                    self.frame_buffer.pop(0)
            
            self.frame_count += 1
            
            # Update FPS calculation
            elapsed = time.time() - self.start_time
            if elapsed > 1.0:
                self.fps_actual = self.frame_count / elapsed
            
            # Throttle to target FPS
            elapsed_loop = time.time() - loop_start
            sleep_time = frame_interval - elapsed_loop
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def read_frame(self) -> Optional[np.ndarray]:
        """
        Get latest frame from buffer.
        
        Returns:
            Latest frame as numpy array, or None if no frame available
        """
        with self.buffer_lock:
            if not self.frame_buffer:
                return None
            _, frame = self.frame_buffer[-1]
            return frame.copy()
    
    def get_latest_frame_with_timestamp(self) -> Optional[Tuple[float, np.ndarray]]:
        """
        Get latest frame with timestamp.
        
        Returns:
            Tuple of (timestamp, frame) or None
        """
        with self.buffer_lock:
            if not self.frame_buffer:
                return None
            timestamp, frame = self.frame_buffer[-1]
            return timestamp, frame.copy()
    
    # ─── MJPEG Streaming (Phase 3) ──────────────────────────────────────────

    @staticmethod
    def encode_jpeg(frame: np.ndarray, quality: int = 80) -> bytes:
        """
        Encode a BGR frame to JPEG bytes.

        Args:
            frame: BGR numpy array
            quality: JPEG quality (0-100)

        Returns:
            JPEG-encoded bytes
        """
        ok, buffer = cv2.imencode(
            ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, int(quality)]
        )
        if not ok:
            return b""
        return buffer.tobytes()

    @staticmethod
    def mjpeg_frame(frame_bytes: bytes, boundary: str = "frame") -> bytes:
        """Wrap JPEG bytes in a multipart/x-mixed-replace boundary."""
        return (
            b"--" + boundary.encode() + b"\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + frame_bytes + b"\r\n"
        )

    def generate_mjpeg_stream(
        self, quality: int = 80, max_fps: float = 15.0
    ) -> "Generator[bytes, None, None]":
        """
        Generator yielding multipart JPEG frames for HTTP MJPEG streaming.

        Args:
            quality: JPEG quality (0-100)
            max_fps: Maximum frames per second served to viewers

        Yields:
            Multipart JPEG boundary chunks
        """
        interval = 1.0 / max_fps if max_fps > 0 else 0.0
        last_ts = 0.0
        while True:
            ts = time.time()
            if interval > 0 and (ts - last_ts) < interval:
                time.sleep(interval - (ts - last_ts))
                continue
            frame = self.read_frame()
            if frame is None:
                time.sleep(0.05)
                continue
            frame_bytes = self.encode_jpeg(frame, quality)
            if not frame_bytes:
                continue
            last_ts = time.time()
            yield self.mjpeg_frame(frame_bytes)

    # ─── Recording (opt-in, Phase 3) ─────────────────────────────────────────

    def start_recording(
        self,
        output_dir,
        segment_duration: float = 300.0,
        max_days: int = 7,
        fps: float = None,
    ) -> bool:
        """
        Start background recording of captured frames.

        Args:
            output_dir: Directory to store recording segments
            segment_duration: Max seconds per segment file (auto-rotate)
            max_days: Auto-delete recordings older than this many days
            fps: Output video FPS (defaults to target FPS)

        Returns:
            True if recording started, False otherwise
        """
        if self._recording_active:
            logger.info("Recording already active")
            return True

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        self.cleanup_recordings(output_dir, max_days)

        out_fps = fps or self.target_fps or 20.0
        self._record_dir = output_dir
        self._record_segment_duration = float(segment_duration)
        self._rec_fps = float(out_fps)
        self._recording_active = True
        self._rec_writer = None
        self._rec_segment_start = None
        self._rec_thread = threading.Thread(
            target=self._recording_loop, daemon=True, name="recorder"
        )
        self._rec_thread.start()
        logger.info(
            f"Recording started -> {output_dir} (segment={segment_duration}s, "
            f"retention={max_days}d)"
        )
        return True

    def _open_segment(self) -> None:
        """Open a new recording segment file."""
        if not self._recording_active:
            return
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = self._record_dir / f"rec_{ts}.mp4"
        if path.exists():
            path = self._record_dir / f"rec_{ts}_{uuid.uuid4().hex[:8]}.mp4"
        frame = self.read_frame()
        if frame is None:
            return
        h, w = frame.shape[:2]
        self._rec_writer = cv2.VideoWriter(
            str(path), cv2.VideoWriter_fourcc(*"mp4v"), self._rec_fps, (w, h)
        )
        if not self._rec_writer.isOpened():
            logger.error("Could not open recording writer: %s", path)
            self._rec_writer.release()
            self._rec_writer = None
            return
        self._rec_path = path
        self._rec_segment_start = time.time()
        logger.info(f"Recording segment: {path}")

    def _recording_loop(self) -> None:
        """Background thread writing frames to rotating segments."""
        self._open_segment()
        frame_interval = 1.0 / self._rec_fps if self._rec_fps > 0 else 0.05
        while self._recording_active:
            frame = self.read_frame()
            if frame is not None and self._rec_writer is not None:
                self._rec_writer.write(frame)
            # Rotate segment on timeout
            if (
                self._rec_writer is not None
                and self._rec_segment_start is not None
                and time.time() - self._rec_segment_start
                >= self._record_segment_duration
            ):
                self._finalize_segment()
                self._open_segment()
            time.sleep(frame_interval)

    def _finalize_segment(self) -> None:
        """Close and release the current segment writer."""
        if self._rec_writer is not None:
            self._rec_writer.release()
            self._rec_writer = None
        self._rec_path = None
        self._rec_segment_start = None

    def stop_recording(self) -> Optional[Path]:
        """
        Stop recording and finalize the current segment.

        Returns:
            Path to the final segment, or None if nothing recorded
        """
        if not self._recording_active:
            return None
        self._recording_active = False
        if self._rec_thread and self._rec_thread.is_alive():
            self._rec_thread.join(timeout=2.0)
        self._finalize_segment()
        final_path = None
        if self._record_dir and self._record_dir.exists():
            files = sorted(self._record_dir.glob("rec_*.mp4"))
            if files:
                final_path = files[-1]
        logger.info("Recording stopped")
        return final_path

    @staticmethod
    def cleanup_recordings(output_dir, max_days: int = 7) -> int:
        """
        Delete recording segments older than `max_days`.

        Args:
            output_dir: Recording directory
            max_days: Retention window in days

        Returns:
            Number of files deleted
        """
        output_dir = Path(output_dir)
        if not output_dir.exists():
            return 0
        cutoff = time.time() - max(0, int(max_days)) * 86400
        deleted = 0
        for f in output_dir.glob("rec_*.mp4"):
            try:
                if f.stat().st_mtime < cutoff:
                    f.unlink()
                    deleted += 1
            except OSError:
                continue
        if deleted:
            logger.info(f"Cleanup deleted {deleted} expired recording(s)")
        return deleted

    @staticmethod
    def list_recordings(output_dir) -> list:
        """List recording segments with size and age metadata."""
        output_dir = Path(output_dir)
        if not output_dir.exists():
            return []
        results = []
        for f in sorted(output_dir.glob("rec_*.mp4"), reverse=True):
            try:
                st = f.stat()
                results.append({
                    "path": str(f),
                    "name": f.name,
                    "size_mb": round(st.st_size / 1024 / 1024, 2),
                    "created": st.st_mtime,
                })
            except OSError:
                continue
        return results

    def get_fps(self) -> float:
        """Get actual FPS."""
        return self.fps_actual
    
    def get_frame_count(self) -> int:
        """Get total frames captured."""
        return self.frame_count
    
    def is_running(self) -> bool:
        """Check if camera is running."""
        return self.running
    
    def get_resolution(self) -> Tuple[int, int]:
        """Get actual camera resolution."""
        if self.cap:
            w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return (w, h)
        return (self.width, self.height)
    
    def stop(self):
        """Stop camera capture."""
        if not self.running:
            return
        
        self.running = False
        
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
        
        if self._recording_active:
            self.stop_recording()
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
        with self.buffer_lock:
            self.frame_buffer.clear()
        
        logger.info("Camera stopped")
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class CameraManagerRTSP(CameraManager):
    """RTSP camera manager with reconnection logic."""
    
    def __init__(
        self,
        rtsp_url: str,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        buffer_size: int = 3,
        reconnect_delay: float = 5.0
    ):
        super().__init__(
            camera_index=rtsp_url,
            width=width,
            height=height,
            fps=fps,
            buffer_size=buffer_size,
            backend=cv2.CAP_FFMPEG
        )
        self.rtsp_url = rtsp_url
        self.reconnect_delay = reconnect_delay
        self.reconnecting = False
    
    def _capture_loop(self):
        """Capture loop with automatic reconnection."""
        frame_interval = 1.0 / self.target_fps
        
        while self.running:
            if not self.cap or not self.cap.isOpened():
                if not self._reconnect():
                    time.sleep(self.reconnect_delay)
                    continue
            
            loop_start = time.time()
            ret, frame = self.cap.read()
            
            if not ret:
                self._consecutive_read_failures += 1
                logger.warning(
                    "RTSP frame read failed (%s consecutive failures), reconnecting...",
                    self._consecutive_read_failures,
                )
                self.cap.release()
                self.cap = None
                time.sleep(self.reconnect_delay)
                continue
            self._consecutive_read_failures = 0

            with self.buffer_lock:
                self.frame_buffer.append((time.time(), frame))
                if len(self.frame_buffer) > self.buffer_size:
                    self.frame_buffer.pop(0)
            
            self.frame_count += 1
            
            elapsed = time.time() - self.start_time
            if elapsed > 1.0:
                self.fps_actual = self.frame_count / elapsed
            
            elapsed_loop = time.time() - loop_start
            sleep_time = frame_interval - elapsed_loop
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def _reconnect(self) -> bool:
        """Attempt to reconnect to RTSP stream."""
        if self.reconnecting:
            return False
        
        self.reconnecting = True
        logger.info(f"Attempting to reconnect to {self.rtsp_url}...")
        
        for attempt in range(3):
            try:
                self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)
                
                if self.cap.isOpened():
                    ret, _ = self.cap.read()
                    if ret:
                        logger.info("Reconnection successful")
                        self.reconnecting = False
                        return True
            except Exception as e:
                logger.error(f"Reconnect attempt {attempt + 1} failed: {e}")
            
            time.sleep(self.reconnect_delay)
        
        self.reconnecting = False
        return False


def list_cameras() -> list:
    """List available camera devices (Linux)."""
    cameras = []
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cameras.append({'index': i, 'width': w, 'height': h})
            cap.release()
    return cameras


def test_camera(camera_index: int = 0) -> bool:
    """Quick test if camera is accessible."""
    cap = cv2.VideoCapture(camera_index)
    if cap.isOpened():
        ret, _ = cap.read()
        cap.release()
        return ret
    return False


class VideoFileCamera:
    """Virtual camera that plays a video file as if it were a live camera."""
    
    def __init__(
        self,
        video_path: str,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        loop: bool = True,
        frame_stride: int = 1,
        real_time: bool = True,
        buffer_size: int = 3
    ):
        """
        Initialize video file camera.
        
        Args:
            video_path: Path to video file (.mp4, .avi, .mov, .mkv, .webm)
            width: Target frame width (resize if needed)
            height: Target frame height
            fps: Target playback FPS
            loop: Loop video when ended (default: True for demos)
            frame_stride: Process every Nth frame (default: 1)
            real_time: Sync playback to real-time (default: True)
            buffer_size: Frame buffer size for smoothing
        """
        self.video_path = video_path
        self.target_width = width
        self.target_height = height
        self.target_fps = fps
        self.loop = loop
        self.frame_stride = frame_stride
        self.real_time = real_time
        self.buffer_size = buffer_size
        
        self.cap: Optional[cv2.VideoCapture] = None
        self.frame_buffer = []
        self.buffer_lock = threading.Lock()
        self.running = False
        self.capture_thread: Optional[threading.Thread] = None
        self.frame_count = 0
        self.start_time = 0
        self.fps_actual = 0.0
        self.frame_count = 0
        self.frame_skip_counter = 0
        self.video_fps = 0
        self.total_frames = 0
        self.video_duration = 0
        self.supports_recording = False
        
        self._supported_formats = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'}
        
        # Pre-load video info if file exists
        self._load_video_info()
        
        logger.info(f"VideoFileCamera initialized: {video_path}, "
                   f"target={width}x{height}@{fps}fps, loop={loop}, real_time={real_time}")
    
    def _load_video_info(self):
        """Load video metadata without starting capture."""
        if not Path(self.video_path).exists():
            return
        
        ext = Path(self.video_path).suffix.lower()
        if ext not in self._supported_formats:
            logger.warning(f"Unsupported video format: {ext}. Supported: {self._supported_formats}")
            return
        
        cap = cv2.VideoCapture(self.video_path)
        if cap.isOpened():
            self.video_fps = cap.get(cv2.CAP_PROP_FPS)
            self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.video_duration = self.total_frames / self.video_fps if self.video_fps > 0 else 0
            cap.release()
            
            logger.info(f"Video info loaded: {self.total_frames} frames @ {self.video_fps:.1f}fps, "
                       f"duration: {self.video_duration:.1f}s")
    
    def start(self) -> bool:
        """Open video file and start capture thread."""
        if self.running:
            logger.warning("VideoFileCamera already running")
            return True
        
        # Check file exists
        if not Path(self.video_path).exists():
            logger.error(f"Video file not found: {self.video_path}")
            return False
        
        # Check format
        ext = Path(self.video_path).suffix.lower()
        if ext not in self._supported_formats:
            logger.warning(f"Unsupported video format: {ext}. Supported: {self._supported_formats}")
        
        # Open video
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            logger.error(f"Failed to open video: {self.video_path}")
            return False
        
        # Get video properties
        self.video_fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.video_duration = self.total_frames / self.video_fps if self.video_fps > 0 else 0
        
        logger.info(f"Video opened: {self.total_frames} frames @ {self.video_fps:.1f}fps, "
                   f"duration: {self.video_duration:.1f}s")
        
        # Read first frame to verify
        ret, frame = self.cap.read()
        if not ret:
            logger.error("Failed to read first frame from video")
            self.cap.release()
            return False
        
        self.running = True
        self.frame_count = 0
        self._consecutive_read_failures = 0
        self.start_time = time.time()
        
        # Start capture thread
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        
        logger.info("VideoFileCamera capture started")
        return True
    
    def _capture_loop(self):
        """Background thread to read video frames."""
        # Real-time throttle uses the video's native FPS (not the target FPS),
        # so grace-period timing stays aligned to wall-clock for file sources.
        throttle_fps = self.video_fps if self.real_time and self.video_fps > 0 else self.target_fps
        frame_interval = 1.0 / throttle_fps
        
        while self.running:
            loop_start = time.time()
            
            # Handle frame stride
            self.frame_skip_counter += 1
            if self.frame_skip_counter < self.frame_stride:
                # Still need to read frames to advance video position
                ret, _ = self.cap.read()
                if not ret:
                    if self.loop:
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, _ = self.cap.read()
                        if not ret:
                            logger.warning("Failed to read frame after loop")
                            time.sleep(0.01)
                            continue
                    else:
                        self.running = False
                        break
                self.frame_skip_counter = 0
            else:
                self.frame_skip_counter = 0
            
            ret, frame = self.cap.read()
            if not ret:
                if self.loop:
                    # Loop video - seek to beginning
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self.cap.read()
                    if not ret:
                        logger.warning("Failed to read frame after loop")
                        time.sleep(0.01)
                        continue
                else:
                    logger.info("Video ended, stopping")
                    self.running = False
                    break
            
            # Resize if needed
            if frame.shape[1] != self.target_width or frame.shape[0] != self.target_height:
                frame = cv2.resize(frame, (self.target_width, self.target_height))
            
            # Add to buffer
            with self.buffer_lock:
                self.frame_buffer.append((time.time(), frame))
                if len(self.frame_buffer) > self.buffer_size:
                    self.frame_buffer.pop(0)
            
            self.frame_count += 1
            
            # Update FPS calculation
            elapsed = time.time() - self.start_time
            if elapsed > 1.0:
                self.fps_actual = self.frame_count / elapsed
            
            # Throttle to target FPS (real-time mode)
            if self.real_time:
                elapsed_loop = time.time() - loop_start
                sleep_time = frame_interval - elapsed_loop
                if sleep_time > 0:
                    time.sleep(sleep_time)
    
    def read_frame(self) -> Optional[np.ndarray]:
        """
        Get latest frame from buffer.
        
        Returns:
            Latest frame as numpy array, or None if no frame available
        """
        with self.buffer_lock:
            if not self.frame_buffer:
                return None
            _, frame = self.frame_buffer[-1]
            return frame.copy()
    
    def get_latest_frame_with_timestamp(self) -> Optional[Tuple[float, np.ndarray]]:
        """
        Get latest frame with timestamp.
        
        Returns:
            Tuple of (timestamp, frame) or None
        """
        with self.buffer_lock:
            if not self.frame_buffer:
                return None
            timestamp, frame = self.frame_buffer[-1]
            return timestamp, frame.copy()
    
    def get_fps(self) -> float:
        """Get actual FPS."""
        return self.fps_actual
    
    def get_frame_count(self) -> int:
        """Get total frames processed."""
        return self.frame_count
    
    def is_running(self) -> bool:
        """Check if camera is running."""
        return self.running
    
    def get_resolution(self) -> Tuple[int, int]:
        """Get current resolution."""
        return (self.target_width, self.target_height)
    
    def get_video_info(self) -> dict:
        """Get video file information."""
        return {
            'path': self.video_path,
            'width': self.target_width,
            'height': self.target_height,
            'fps': self.video_fps,
            'total_frames': self.total_frames,
            'duration': self.video_duration,
            'loop': self.loop
        }
    
    def stop(self):
        """Stop video capture."""
        if not self.running:
            return
        
        self.running = False
        
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
        with self.buffer_lock:
            self.frame_buffer.clear()
        
        logger.info("VideoFileCamera stopped")
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def create_camera(source, **kwargs):
    """
    Factory function to create appropriate camera from source.
    
    Args:
        source: int (camera index), str (RTSP URL or video file path)
        **kwargs: Additional camera parameters
        
    Returns:
        CameraManager, CameraManagerRTSP, or VideoFileCamera instance
    """
    from pathlib import Path
    
    # Video file
    if isinstance(source, (str, Path)):
        path = Path(source) if isinstance(source, str) else source
        if path.suffix.lower() in {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'}:
            return VideoFileCamera(str(path), **kwargs)
        elif source.startswith(('rtsp://', 'http://', 'https://')):
            # Only forward file-specific kwargs (loop/real_time) to file cameras
            kwargs.pop('loop', None)
            kwargs.pop('real_time', None)
            return CameraManagerRTSP(source, **kwargs)
        else:
            # Try as camera index
            kwargs.pop('loop', None)
            kwargs.pop('real_time', None)
            try:
                return CameraManager(int(source), **kwargs)
            except ValueError:
                raise ValueError(f"Unsupported camera source: {source}")
    
    # Integer camera index
    elif isinstance(source, int):
        kwargs.pop('loop', None)
        kwargs.pop('real_time', None)
        return CameraManager(source, **kwargs)
    
    raise ValueError(f"Unsupported camera source: {source}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Available cameras:")
    cams = list_cameras()
    for cam in cams:
        print(f"  Camera {cam['index']}: {cam['width']}x{cam['height']}")
    
    if cams:
        print("\nTesting first camera...")
        with CameraManager(camera_index=cams[0]['index']) as cam:
            time.sleep(2)
            print(f"FPS: {cam.get_fps():.1f}")
            frame = cam.read_frame()
            if frame is not None:
                print(f"Frame shape: {frame.shape}")