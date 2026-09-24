"""Camera lifecycle: lazy camera open, SyntheticFrameSource fallback, and
opt-in recording state -- extracted from stream_server.py's StreamServer
class so api/main.py no longer needs stream_server.py at all (it can be
deleted once this module is the only thing serving camera access).
"""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

import camera as camera_module

logger = logging.getLogger(__name__)

BOUNDARY = "fallguard-frame"


class SyntheticFrameSource:
    """Generates synthetic warm gray frames when no real camera is available.

    Keeps the live-monitor feed functional (video + metrics) even on machines
    without a physical camera, with a subtle moving element and timestamp so
    the feed is visibly 'alive'. (Verbatim port of stream_server.SyntheticFrameSource.)
    """

    def __init__(self, width: int = 640, height: int = 480, fps: float = 15.0):
        self.width = width
        self.height = height
        self.fps = fps
        self.running = False
        self._latest: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._fps_actual = 0.0
        self._frame_count = 0
        self.start_time = time.time()

    def _loop(self):
        interval = 1.0 / self.fps
        x = 0
        while self.running:
            start = time.time()
            frame = np.full((self.height, self.width, 3), (26, 26, 46), dtype=np.uint8)
            y = int(self.height * 0.5 + np.sin(x / 30.0) * 40)
            cv2.circle(frame, (x, y), 24, (215, 184, 55), -1)  # gold orb
            cv2.rectangle(frame, (0, 0), (self.width, 34), (20, 20, 34), -1)
            cv2.putText(
                frame, f"LIVE PREVIEW - {time.strftime('%H:%M:%S')}",
                (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                (240, 240, 255), 2, cv2.LINE_AA,
            )
            with self._lock:
                self._latest = frame
            x = (x + 6) % self.width
            self._frame_count += 1
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                self._fps_actual = self._frame_count / elapsed
            time.sleep(max(0.0, interval - (time.time() - start)))

    def start(self):
        if self.running:
            return True
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True

    def read_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            if self._latest is None:
                return None
            return self._latest.copy()

    def get_fps(self) -> float:
        return self._fps_actual

    def stop(self):
        self.running = False


class CameraState:
    """Owns the API process's active camera source + recording settings.

    Extracted from stream_server.StreamServer, minus the http.server plumbing
    -- FastAPI is the single origin, so no separate HTTP server is started.
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.jpeg_quality = int(self.config.get("jpeg_quality", 80))
        self.max_fps = float(self.config.get("max_fps", 15))
        self.camera = None
        self.camera_owner = False
        self.rec_path = Path(self.config.get("record_path", "data/recordings"))
        self.max_days = int(self.config.get("recording_max_days", 7))
        self.segment_duration = float(self.config.get("recording_segment_duration", 300))
        self.recording_started = False

    def ensure_camera(self) -> None:
        """Lazily open a camera (or synthetic fallback). Same logic as
        stream_server.StreamServer._ensure_camera."""
        if self.camera is not None:
            return
        cam_cfg = self.config.get("camera", {})
        src = cam_cfg.get("source", cam_cfg.get("index", 0))
        width = int(cam_cfg.get("width", 640))
        height = int(cam_cfg.get("height", 480))
        fps = float(cam_cfg.get("fps", 30))
        vid_cfg = self.config.get("video", {})
        use_synthetic = self.config.get("use_synthetic", False)
        if src == "synthetic":
            use_synthetic = True

        opened = None
        if not use_synthetic:
            opened = self._probe_camera(
                src, width, height, fps,
                loop=vid_cfg.get("loop", True),
                real_time=vid_cfg.get("real_time", True),
            )
        if opened is not None:
            self.camera = opened
            self.camera_owner = True
            logger.info(f"Live camera source: {src}")
            return
        logger.info("Using synthetic live-preview source (no camera available)")
        self.camera = SyntheticFrameSource(width, height, min(fps, self.max_fps))
        self.camera.start()
        self.camera_owner = False

    @staticmethod
    def _probe_camera(src, width, height, fps, loop: bool = True, real_time: bool = True,
                       timeout: float = 3.0):
        """Try to open a real camera with a hard timeout, falling back to
        synthetic if it hangs or fails (same as stream_server._probe_camera)."""
        result = {"cam": None}

        def attempt():
            try:
                cam = camera_module.create_camera(
                    src, width=width, height=height, fps=fps,
                    loop=loop, real_time=real_time,
                )
                if cam.start():
                    result["cam"] = cam
            except Exception as e:
                logger.debug(f"Camera probe failed: {e}")

        t = threading.Thread(target=attempt, daemon=True)
        t.start()
        t.join(timeout=timeout)
        if t.is_alive():
            logger.warning("Camera open timed out - falling back to synthetic")
            if result["cam"] is not None:
                try:
                    result["cam"].stop()
                except Exception:
                    pass
            return None
        return result["cam"]

    def stop(self) -> None:
        """Release camera/recording resources on shutdown."""
        try:
            if self.recording_started and self.camera is not None:
                self.camera.stop_recording()
        except Exception:
            pass
        try:
            if self.camera_owner and self.camera is not None:
                self.camera.stop()
        except Exception:
            pass
        self.camera = None
