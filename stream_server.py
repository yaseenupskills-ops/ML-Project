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
import secrets
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
        self.supports_recording = False

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

    def generate_mjpeg_stream(self, quality: int = 80, max_fps: float = 15.0):
        # Reuse the common camera encoder/stream pacing implementation.
        yield from camera_module.CameraManager.generate_mjpeg_stream(
            self, quality=quality, max_fps=max_fps
        )

    def stop(self):
        self.running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._thread = None

    def get_latest_frame_with_timestamp(self):
        frame = self.read_frame()
        return (time.time(), frame) if frame is not None else None

    def start_recording(self, *args, **kwargs):
        return False

    @staticmethod
    def list_recordings(output_dir):
        return camera_module.CameraManager.list_recordings(output_dir)


class StreamServer:
    """Threaded HTTP server for live video + metrics."""

    def __init__(self, config: dict = None):
        self.config = config or {}
        requested_host = str(self.config.get("host", "127.0.0.1"))
        if requested_host not in {"127.0.0.1", "localhost", "::1"}:
            logger.warning(
                "Forcing stream server to localhost; remote binding requires a secured proxy"
            )
            requested_host = "127.0.0.1"
        self.host = requested_host
        self.port = int(self.config.get("port", 8091))
        self.jpeg_quality = int(self.config.get("jpeg_quality", 80))
        self.max_fps = float(self.config.get("max_fps", 15))
        self._httpd: Optional[ThreadingHTTPServer] = None
        self._http_thread: Optional[threading.Thread] = None
        self._camera = None
        self._camera_owner = False
        rec_path = Path(self.config.get("record_path", "data/recordings"))
        if not rec_path.is_absolute():
            rec_path = Path(__file__).resolve().parent / rec_path
        self._rec_path = rec_path
        self._max_days = int(self.config.get("recording_max_days", 7))
        self._segment_duration = float(
            self.config.get("recording_segment_duration", 300)
        )
        self._recording_started = False
        self.recording_enabled = bool(self.config.get("recording_enabled", False))
        # This token is generated per process and is required by local HTTP
        # clients. It is not placed in a public URL or exposed in metrics.
        self.auth_token = secrets.token_urlsafe(32)
        origins = self.config.get(
            "allowed_origins",
            [
                "http://localhost:8501",
                "http://127.0.0.1:8501",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ],
        )
        self.allowed_origins = {str(origin).rstrip("/") for origin in origins}

    # ─── Camera source ─────────────────────────────────────────────────────

    def attach_camera(self, cam) -> None:
        """Attach a camera the server should stream (server won't own it)."""
        self._camera = cam
        self._camera_owner = False

    def get_camera(self):
        """Return the active camera instance (may be None until first request)."""
        return self._camera

    def ensure_camera(self):
        """Ensure a camera is open (lazily re-opens after a source switch)."""
        self._ensure_camera()
        return self._camera

    def switch_source(self, source) -> None:
        """Swap the camera source at runtime (webcam index | file path | RTSP).

        Stops the currently owned camera (and any active recording) so the next
        request lazily re-opens the new source via `_ensure_camera()`.
        """
        import logging as _logging
        _logging.getLogger(__name__).info(f"Switching camera source to: {source}")
        if isinstance(source, str):
            self.config.setdefault("camera", {})["source"] = source
        else:
            self.config.setdefault("camera", {})["source"] = int(source)
        if self._recording_started:
            try:
                if self._camera is not None:
                    self._camera.stop_recording()
            except Exception:
                pass
            self._recording_started = False
        if self._camera is not None:
            try:
                self._camera.stop()
            except Exception:
                pass
        self._camera = None
        metrics.update(
            camera_available=False,
            camera_online=False,
            recording_active=False,
            source=self.config.get("camera", {}).get("source", source),
        )

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
            source_type = (
                "video_file" if isinstance(opened, camera_module.VideoFileCamera)
                else "rtsp" if isinstance(opened, camera_module.CameraManagerRTSP)
                else "real_camera"
            )
            metrics.update(source_type=source_type)
            logger.info(f"Live camera source: {src}")
            return
        logger.info("Using synthetic live-preview source (no camera available)")
        self._camera = SyntheticFrameSource(width, height, min(fps, self.max_fps))
        self._camera.start()
        self._camera_owner = False
        metrics.update(source_type="synthetic_preview")

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

    def _origin_allowed(self, handler: BaseHTTPRequestHandler) -> bool:
        origin = handler.headers.get("Origin")
        return not origin or origin.rstrip("/") in self.allowed_origins

    def _is_authorized(self, handler: BaseHTTPRequestHandler) -> bool:
        if not self._origin_allowed(handler):
            return False
        supplied = handler.headers.get("X-FallGuard-Token")
        if not supplied:
            from urllib.parse import parse_qs, urlsplit
            supplied = (parse_qs(urlsplit(handler.path).query).get("token") or [None])[0]
        return bool(supplied) and secrets.compare_digest(
            str(supplied), self.auth_token
        )

    def _require_auth(self, handler: BaseHTTPRequestHandler) -> bool:
        if self._is_authorized(handler):
            self._send_cors_headers(handler)
            return True
        self._respond_json(handler, 403, {"ok": False, "error": "unauthorized"})
        return False

    def _send_cors_headers(self, handler: BaseHTTPRequestHandler) -> None:
        origin = handler.headers.get("Origin")
        if origin and origin.rstrip("/") in self.allowed_origins:
            handler.send_header("Access-Control-Allow-Origin", origin)
            handler.send_header("Vary", "Origin")
            handler.send_header("Access-Control-Allow-Headers", "Content-Type, X-FallGuard-Token")
            handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _source_allowed(self, source) -> bool:
        camera_cfg = self.config.get("camera", {}) or {}
        allowed = {
            str(camera_cfg.get("source")),
            str(camera_cfg.get("webcam_source", 0)),
            str(camera_cfg.get("demo_source")),
            "0",
            "synthetic",
        }
        return str(source) in allowed

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    def start(self) -> bool:
        """Start the HTTP server in a background thread."""
        self._rec_path.mkdir(parents=True, exist_ok=True)
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):  # silence noisy logging
                return

            def do_OPTIONS(self):
                server._send_cors_headers(self)
                self.send_response(204)
                self.end_headers()

            def do_GET(self):
                if not server._require_auth(self):
                    return
                path = self.path.split("?", 1)[0]
                if path.startswith("/video_feed"):
                    server._handle_video_feed(self)
                elif path == "/frame":
                    server._handle_frame(self)
                elif path == "/metrics":
                    server._handle_metrics(self)
                elif path == "/health":
                    server._handle_health(self)
                elif path == "/recordings":
                    server._handle_recordings(self)
                elif path.startswith("/recordings/"):
                    parts = path.split("/")
                    if len(parts) == 4 and parts[3] == "info":
                        from urllib.parse import unquote
                        server._handle_recording_info(self, unquote(parts[2]))
                    else:
                        self.send_response(404)
                        self.end_headers()
                        self.wfile.write(b"Not found")
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b"Not found")

            def do_POST(self):
                if not server._require_auth(self):
                    return
                path = self.path.split("?", 1)[0]
                if path == "/record/start":
                    server._handle_record_start(self)
                elif path == "/record/stop":
                    server._handle_record_stop(self)
                elif path == "/source":
                    server._handle_source_switch(self)
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
        if self._http_thread is not None:
            self._http_thread.join(timeout=2.0)
            self._http_thread = None
        if self._recording_started and self._camera is not None:
            try:
                self._camera.stop_recording()
            except Exception:
                pass
        if self._camera is not None:
            try:
                self._camera.stop()
            except Exception:
                pass
        self._camera = None
        self._camera_owner = False

    # ─── Handlers ───────────────────────────────────────────────────────────

    def _handle_video_feed(self, handler: BaseHTTPRequestHandler):
        self._ensure_camera()
        handler.send_response(200)
        handler.send_header(
            "Content-Type", f"multipart/x-mixed-replace; boundary={BOUNDARY}"
        )
        handler.send_header("Cache-Control", "no-cache")
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
            source=self.config.get("camera", {}).get("source", None),
            source_type=metrics.get().get("source_type", "unknown"),
        )
        payload = json.dumps(metrics.format_summary()).encode()
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json")
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
        handler.end_headers()
        handler.wfile.write(payload)

    def _handle_record_start(self, handler: BaseHTTPRequestHandler):
        if not self.recording_enabled:
            self._respond_json(handler, 403, {"ok": False, "error": "recording disabled"})
            return
        self._ensure_camera()
        cam = self._camera
        if cam is None:
            self._respond_json(handler, 500, {"ok": False, "error": "no source"})
            return
        if not getattr(cam, "supports_recording", True):
            self._respond_json(handler, 409, {"ok": False, "error": "source does not support recording"})
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

    def _handle_source_switch(self, handler: BaseHTTPRequestHandler):
        """Switch camera source from JSON body or query string (?source=...)."""
        import urllib.parse
        source = None
        try:
            length = int(handler.headers.get("Content-Length") or 0)
            if length > 64 * 1024:
                self._respond_json(handler, 413, {"ok": False, "error": "request too large"})
                return
            if length > 0:
                raw = handler.rfile.read(length).decode("utf-8")
                try:
                    source = json.loads(raw).get("source")
                except Exception:
                    qs = urllib.parse.parse_qs(raw)
                    source = (qs.get("source") or [None])[0]
        except Exception:
            source = None
        if source is None and "?" in handler.path:
            qs = urllib.parse.parse_qs(handler.path.split("?", 1)[1])
            source = (qs.get("source") or [None])[0]
        if source is None:
            self._respond_json(handler, 400, {"ok": False, "error": "missing source"})
            return
        if isinstance(source, str) and source.isdigit():
            source = int(source)
        if not self._source_allowed(source):
            self._respond_json(handler, 400, {"ok": False, "error": "source is not allowed"})
            return
        self.switch_source(source)
        self._respond_json(
            handler, 200,
            {"ok": True, "source": self.config.get("camera", {}).get("source")},
        )

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
        try:
            lister = getattr(self._camera, "list_recordings", None)
            recs = lister(self._rec_path) if lister else camera_module.CameraManager.list_recordings(self._rec_path)
            # Do not disclose absolute local paths to a browser/API client.
            safe = [
                {
                    "name": item.get("name"),
                    "size_mb": item.get("size_mb", 0),
                    "created": item.get("created"),
                }
                for item in recs
            ]
            self._respond_json(handler, 200, {"recordings": safe})
        except Exception as e:
            self._respond_json(handler, 500, {"ok": False, "error": str(e)})

    @staticmethod
    def _parse_segment_start(name: str) -> Optional[float]:
        """Parse the timestamp prefix from a recording segment filename."""
        import datetime as dt
        import re
        try:
            match = re.match(r"^rec_(\d{8}_\d{6})", name)
            if not match:
                return None
            return dt.datetime.strptime(match.group(1), "%Y%m%d_%H%M%S").timestamp()
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
    """Return the process-wide stream server, creating/configuring it if needed."""
    global _server_singleton
    with _singleton_lock:
        if _server_singleton is None:
            _server_singleton = StreamServer(config or {})
        elif config and _server_singleton._httpd is None:
            # Dashboard health checks may create the singleton before the
            # server is started. Apply the real config before binding.
            _server_singleton.config.update(config)
            _server_singleton.recording_enabled = bool(
                config.get("recording_enabled", _server_singleton.recording_enabled)
            )
            _server_singleton.port = int(config.get("port", _server_singleton.port))
            _server_singleton.jpeg_quality = int(
                config.get("jpeg_quality", _server_singleton.jpeg_quality)
            )
            _server_singleton.max_fps = float(
                config.get("max_fps", _server_singleton.max_fps)
            )
            if config.get("record_path"):
                record_path = Path(config["record_path"])
                if not record_path.is_absolute():
                    record_path = Path(__file__).resolve().parent / record_path
                _server_singleton._rec_path = record_path
            origins = config.get("allowed_origins")
            if origins:
                _server_singleton.allowed_origins = {
                    str(origin).rstrip("/") for origin in origins
                }
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