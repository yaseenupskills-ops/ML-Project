"""
Streaming Server (Phase 3)
--------------------------
Lightweight HTTP server (stdlib only) that serves:
  GET /video_feed   → MJPEG stream from the active camera source
  GET /metrics      → JSON snapshot of live metrics
  GET /health       → health check
  POST /record/<start|stop> → opt-in recording control
  GET /recordings   → list recorded segments
  GET /recordings/<name>/info → video metadata for one segment

The server runs in a background thread so it can coexist with the Streamlit
dashboard process. Binding defaults to 127.0.0.1 to keep video on-device
(privacy-first).
"""

import json
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

import camera as camera_module
import metrics

logger = logging.getLogger(__name__)

BOUNDARY = "fallguard-frame"


class SyntheticFrameSource:
    """Generates synthetic warm gray frames when no real camera is available.

    Keeps the live-monitor page functional (video + metrics) even on machines
    without a physical camera, with a subtle moving element and timestamp so
    the feed is visibly 'alive'.
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
            frame = np.full(
                (self.height, self.width, 3), (26, 26, 46), dtype=np.uint8
            )
            y = int(self.height * 0.5 + np.sin(x / 30.0) * 40)
            cv2.circle(frame, (x, y), 24, (215, 184, 55), -1)  # gold orb
            cv2.rectangle(
                frame, (0, 0), (self.width, 34), (20, 20, 34), -1
            )
            cv2.putText(
                frame,
                f"LIVE PREVIEW - {time.strftime('%H:%M:%S')}",
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


class StreamServer:
    """Threaded HTTP server for live video + metrics."""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.host = self.config.get("host", "127.0.0.1")
        self.port = int(self.config.get("port", 8091))
        self.jpeg_quality = int(self.config.get("jpeg_quality", 80))
        self.max_fps = float(self.config.get("max_fps", 15))
        self._httpd: Optional[ThreadingHTTPServer] = None
        self._http_thread: Optional[threading.Thread] = None
        self._camera = None
        self._camera_owner = False
        self._rec_path = Path(self.config.get("record_path", "data/recordings"))
        self._max_days = int(self.config.get("recording_max_days", 7))
        self._segment_duration = float(
            self.config.get("recording_segment_duration", 300)
        )
        self._recording_started = False

    # ─── Camera source ─────────────────────────────────────────────────────

    def attach_camera(self, cam) -> None:
        """Attach a camera the server should stream (server won't own it)."""
        self._camera = cam
        self._camera_owner = False

    def _ensure_camera(self):
        """Lazily open a camera (or synthetic fallback) owned by the server."""
        if self._camera is not None:
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
            self._camera = opened
            self._camera_owner = True
            logger.info(f"Live camera source: {src}")
            return
        logger.info("Using synthetic live-preview source (no camera available)")
        self._camera = SyntheticFrameSource(width, height, min(fps, self.max_fps))
        self._camera.start()
        self._camera_owner = False

    @staticmethod
    def _probe_camera(src, width, height, fps, loop: bool = True, real_time: bool = True,
                      timeout: float = 3.0):
        """Try to open a real camera with a hard timeout."""
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
            # Best-effort cleanup of the hung attempt
            if result["cam"] is not None:
                try:
                    result["cam"].stop()
                except Exception:
                    pass
            return None
        return result["cam"]

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    def start(self) -> bool:
        """Start the HTTP server in a background thread."""
        self._rec_path.mkdir(parents=True, exist_ok=True)
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):  # silence noisy logging
                return

            def do_GET(self):
                if self.path.split("?", 1)[0].startswith("/video_feed"):
                    server._handle_video_feed(self)
                elif self.path.split("?", 1)[0] == "/frame":
                    server._handle_frame(self)
                elif self.path.split("?", 1)[0] == "/metrics":
                    server._handle_metrics(self)
                elif self.path.split("?", 1)[0] == "/health":
                    server._handle_health(self)
                elif self.path.split("?", 1)[0] == "/recordings":
                    server._handle_recordings(self)
                elif self.path.split("?", 1)[0].startswith("/recordings/"):
                    parts = self.path.split("?", 1)[0].split("/")
                    if len(parts) == 4 and parts[3] == "info":
                        server._handle_recording_info(self, parts[2])
                    else:
                        self.send_response(404)
                        self.end_headers()
                        self.wfile.write(b"Not found")
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b"Not found")

            def do_POST(self):
                if self.path.split("?", 1)[0] == "/record/start":
                    server._handle_record_start(self)
                elif self.path.split("?", 1)[0] == "/record/stop":
                    server._handle_record_stop(self)
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b"Not found")

        try:
            self._httpd = ThreadingHTTPServer((self.host, self.port), Handler)
        except OSError as e:
            logger.warning(
                f"Could not bind stream server on {self.host}:{self.port}: {e}"
            )
            return False
        self._http_thread = threading.Thread(
            target=self._httpd.serve_forever, daemon=True, name="stream"
        )
        self._http_thread.start()
        logger.info(
            f"Stream server listening on http://{self.host}:{self.port}"
        )
        return True

    def stop(self):
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self._recording_started and self._camera is not None:
            try:
                self._camera.stop_recording()
            except Exception:
                pass
        if self._camera_owner and self._camera is not None:
            try:
                self._camera.stop()
            except Exception:
                pass
            self._camera = None

    # ─── Handlers ───────────────────────────────────────────────────────────

    def _handle_video_feed(self, handler: BaseHTTPRequestHandler):
        self._ensure_camera()
        handler.send_response(200)
        handler.send_header(
            "Content-Type", f"multipart/x-mixed-replace; boundary={BOUNDARY}"
        )
        handler.send_header("Cache-Control", "no-cache")
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.end_headers()
        try:
            for chunk in self._camera.generate_mjpeg_stream(
                quality=self.jpeg_quality, max_fps=self.max_fps
            ):
                handler.wfile.write(chunk)
                handler.wfile.flush()
                metrics.update(last_frame_ts=time.time())
        except (BrokenPipeError, ConnectionResetError):
            pass  # viewer disconnected

    def _handle_frame(self, handler: BaseHTTPRequestHandler):
        """Serve a single latest JPEG frame (browser frame-poller friendly)."""
        self._ensure_camera()
        frame = None
        for _ in range(5):
            frame = self._camera.read_frame()
            if frame is not None:
                break
            time.sleep(0.1)
        if frame is None:
            self._respond_json(handler, 503, {"error": "no frame available"})
            return
        data = camera_module.CameraManager.encode_jpeg(frame, self.jpeg_quality)
        if not data:
            self._respond_json(handler, 503, {"error": "encode failed"})
            return
        handler.send_response(200)
        handler.send_header("Content-Type", "image/jpeg")
        handler.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        handler.send_header("Pragma", "no-cache")
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.send_header("Content-Length", str(len(data)))
        handler.end_headers()
        try:
            handler.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass
        metrics.update(last_frame_ts=time.time())

    def _handle_metrics(self, handler: BaseHTTPRequestHandler):
        self._ensure_camera()
        fps = getattr(self._camera, "get_fps", lambda: 0.0)()
        metrics.update(
            camera_online=True,
            camera_available=True,
            fps=round(fps, 2),
            recording_active=self._recording_started,
        )
        payload = json.dumps(metrics.format_summary()).encode()
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.send_header("Content-Length", str(len(payload)))
        handler.end_headers()
        handler.wfile.write(payload)

    def _handle_health(self, handler: BaseHTTPRequestHandler):
        metrics.update(camera_online=self._camera is not None)
        ok = self._camera is not None
        payload = json.dumps(
            {"status": "ok" if ok else "degraded",
             "camera": ok,
             "time": time.time()}
        ).encode()
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.end_headers()
        handler.wfile.write(payload)

    def _handle_record_start(self, handler: BaseHTTPRequestHandler):
        self._ensure_camera()
        cam = self._camera
        if cam is None:
            self._respond_json(handler, 500, {"ok": False, "error": "no source"})
            return
        try:
            ok = cam.start_recording(
                self._rec_path,
                segment_duration=self._segment_duration,
                max_days=self._max_days,
            )
            self._recording_started = ok
            # Count existing segments for telemetry
            segs = len(self._camera.list_recordings(self._rec_path))
            metrics.update(recording_active=ok, recorded_segments=segs)
            self._respond_json(
                handler, 200, {"ok": ok, "recording": ok, "path": str(self._rec_path)}
            )
        except Exception as e:
            self._respond_json(handler, 500, {"ok": False, "error": str(e)})

    def _handle_record_stop(self, handler: BaseHTTPRequestHandler):
        cam = self._camera
        if cam is not None:
            try:
                cam.stop_recording()
            except Exception:
                pass
        self._recording_started = False
        metrics.update(recording_active=False)
        self._respond_json(handler, 200, {"ok": True, "recording": False})

    def _handle_recordings(self, handler: BaseHTTPRequestHandler):
        self._ensure_camera()
        try:
            recs = self._camera.list_recordings(self._rec_path)
            self._respond_json(handler, 200, {"recordings": recs})
        except Exception as e:
            self._respond_json(handler, 500, {"ok": False, "error": str(e)})

    @staticmethod
    def _parse_segment_start(name: str) -> Optional[float]:
        """Parse segment start time (unix) from `rec_YYYYMMDD_HHMMSS.mp4`."""
        import datetime as dt
        try:
            stem = name.split(".mp4", 1)[0]
            if not stem.startswith("rec_"):
                return None
            ts = dt.datetime.strptime(stem[4:], "%Y%m%d_%H%M%S")
            return ts.timestamp()
        except Exception:
            return None

    def _handle_recording_info(self, handler: BaseHTTPRequestHandler, name: str):
        """Serve metadata for a single recorded segment (duration/fps/dims)."""
        p = (self._rec_path / name).resolve()
        if self._rec_path.resolve() not in p.parents or not p.name.startswith("rec_"):
            self._respond_json(handler, 404, {"ok": False, "error": "not found"})
            return
        if not p.exists():
            self._respond_json(handler, 404, {"ok": False, "error": "not found"})
            return
        seg_start = self._parse_segment_start(p.name)
        cap = cv2.VideoCapture(str(p))
        try:
            dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS) if cap.get(cv2.CAP_PROP_FPS) > 0 else 0.0
            self._respond_json(handler, 200, {
                "name": p.name,
                "size_mb": round(p.stat().st_size / 1024 / 1024, 2),
                "duration_sec": round(max(dur, 0.0), 2),
                "fps": round(cap.get(cv2.CAP_PROP_FPS) or 0.0, 2),
                "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0),
                "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0),
                "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0),
                "segment_start": seg_start,
            })
        finally:
            cap.release()

    def _respond_json(self, handler: BaseHTTPRequestHandler, code: int, data: dict):
        payload = json.dumps(data).encode()
        handler.send_response(code)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(payload)))
        handler.end_headers()
        handler.wfile.write(payload)


# ─── Module-level singleton ────────────────────────────────────────────────────

_server_singleton: Optional[StreamServer] = None
_singleton_lock = threading.Lock()


def get_stream_server(config: dict = None) -> StreamServer:
    """Return the process-wide stream server, creating it if needed."""
    global _server_singleton
    with _singleton_lock:
        if _server_singleton is None:
            _server_singleton = StreamServer(config or {})
        return _server_singleton


def ensure_stream_server_running(config: dict = None) -> StreamServer:
    """
    Start (idempotently) the process-wide stream server.

    Returns:
        The StreamServer instance (may not be serving if bind failed).
    """
    server = get_stream_server(config)
    if server._httpd is None:
        server.start()
    return server


def stop_stream_server():
    global _server_singleton
    with _singleton_lock:
        if _server_singleton is not None:
            _server_singleton.stop()
            _server_singleton = None