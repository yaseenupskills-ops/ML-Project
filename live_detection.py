"""
Live Detection Session
----------------------
Runs the fall-detection pipeline on the currently active stream-server camera.
Each `run_session(source)` starts a fresh detection pass; the first detected fall
runs a full grace period and then sends exactly one alert (email + log entry).
Used by the dashboard Live Monitor source toggle (Live webcam <-> Preloaded video).
"""

import logging
import threading
import time
from pathlib import Path
from typing import Optional

from project_config import load_config, resolve_path
from pose_extraction import PoseExtractor
from features import FeatureEngineer
from model_rf import FallDetectionRF
from decision_logic import DecisionLogic
from grace_period import GracePeriodManager
from alert import AlertManager
import metrics

logger = logging.getLogger(__name__)

DEFAULT_BUFFER_SIZE = 30

_detector_singleton: Optional["LiveDetector"] = None
_detector_lock = threading.Lock()
_active_grace_lock = threading.Lock()
_active_grace_events: dict[str, threading.Event] = {}


def cancel_active_alert(alert_id: str) -> bool:
    """Signal the live grace-period worker for an alert ID.

    The dashboard calls this before updating the persisted alert. The worker
    observes the signal and finalizes the event without sending email.
    """
    with _active_grace_lock:
        event = _active_grace_events.get(str(alert_id))
        if event is None:
            return False
        event.set()
        return True



def get_live_detector(config_path: str = "config.yaml") -> "LiveDetector":
    """Return the process-wide LiveDetector singleton (created once)."""
    global _detector_singleton
    with _detector_lock:
        if _detector_singleton is None:
            _detector_singleton = LiveDetector(config_path)
        return _detector_singleton


class LiveDetector:
    """Per-switch fall detection session over the shared stream-server camera."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = load_config(config_path)

        self.pose_extractor = PoseExtractor(config_path)
        self.feature_engineer = FeatureEngineer(config_path)
        self.decision_logic = DecisionLogic(config_path)
        self.grace_manager = GracePeriodManager(config_path)
        self.alert_manager = AlertManager(config_path)

        self.model = FallDetectionRF(config_path)
        self.model_path = resolve_path(
            self.config.get("model", {}).get("rf_path", "models/rf_baseline.joblib"),
            base=Path(__file__).resolve().parent,
        ) or Path("models/rf_baseline.joblib")
        self._load_model()

        self._lock = threading.Lock()
        self._session_thread: Optional[threading.Thread] = None
        self._session_stop_event: Optional[threading.Event] = None
        self._session_active = False
        self.session_source: Optional[str] = None
        self.last_alert_at: Optional[float] = None
        self.session_error: Optional[str] = None
        self.grace_timeout_sec = float(
            self.config.get("grace_period", {}).get("timeout_sec", 20)
        )

        logger.info("LiveDetector initialized")

    def _load_model(self):
        if not self.model_path.exists():
            raise FileNotFoundError(f"RF model not found: {self.model_path}")
        self.model.load_model(self.model_path)
        trained_config = self.model.artifact_metadata.get('feature_config', {})
        schema_version = self.model.artifact_metadata.get('feature_schema_version', 0)
        if schema_version == 0:
            logger.warning(
                "RF model is a legacy artifact without feature-schema metadata; "
                "regenerate it before production deployment"
            )
        current_config = {
            'window_sec': self.config.get('features', {}).get('window_sec'),
            'fps': self.config.get('features', {}).get('fps'),
            'frame_stride': self.config.get('pose', {}).get('frame_stride', 1),
        }
        if trained_config and trained_config != current_config:
            logger.warning(
                "RF feature configuration differs from the artifact: "
                "trained=%s runtime=%s", trained_config, current_config
            )
        logger.info(f"RF model loaded: {self.model_path}")

    # ─── session lifecycle ──────────────────────────────────────────────────

    def run_session(self, source) -> bool:
        """Start a fresh detection session on ``source``."""
        stop_event = threading.Event()
        with self._lock:
            previous_thread = self._session_thread
            previous_stop = self._session_stop_event
        if previous_thread and previous_thread.is_alive():
            if previous_stop is not None:
                previous_stop.set()
            previous_thread.join(timeout=2.0)

        with self._lock:
            self.session_source = str(source)
            self.session_error = None
            self._session_active = True
            self._session_stop_event = stop_event
            metrics.update(pipeline_running=True)
            thread = threading.Thread(
                target=self._session_loop,
                args=(stop_event,),
                name="live-detection",
                daemon=True,
            )
            self._session_thread = thread
            thread.start()
        logger.info(f"Live detection session started on source: {source}")
        return True

    def stop(self):
        """Stop any running session and its grace-period worker."""
        with self._lock:
            stop_event = self._session_stop_event
            thread = self._session_thread
            self._session_active = False
        if stop_event is not None:
            stop_event.set()
        metrics.update(pipeline_running=False)
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        with self._lock:
            if self._session_thread is thread:
                self._session_thread = None
                self._session_stop_event = None
        logger.info("Live detection session stopped")

    def is_active(self) -> bool:
        return self._session_active

    def _is_current_session(self, stop_event: threading.Event) -> bool:
        with self._lock:
            return self._session_stop_event is stop_event

    def status(self) -> dict:
        return {
            "active": self._session_active,
            "source": self.session_source,
            "error": self.session_error,
            "last_alert_at": self.last_alert_at,
            "grace_timeout_sec": self.grace_timeout_sec,
        }

    # ─── detection loop ─────────────────────────────────────────────────────

    def _session_loop(self, stop_event: threading.Event):
        import stream_server as ss

        try:
            cam = ss.get_stream_server().ensure_camera()
        except Exception as e:
            self.session_error = f"camera unavailable: {e}"
            if self._is_current_session(stop_event):
                self._session_active = False
            return

        cam_cfg = self.config.get("camera", {})
        stride = int(cam_cfg.get("frame_stride", 1))
        keypoint_buffer = []
        frame_count = 0

        while not stop_event.is_set():
            try:
                cam_get = getattr(ss.get_stream_server(), "get_camera", None)
                cam = cam_get() if cam_get else cam
                if cam is None:
                    cam = ss.get_stream_server().ensure_camera()
            except Exception:
                pass

            frame = None
            try:
                frame = cam.read_frame() if cam is not None else None
            except Exception as e:
                self.session_error = f"frame read error: {e}"
                time.sleep(0.2)
                continue

            if frame is None:
                time.sleep(0.05)
                continue

            frame_count += 1
            if frame_count % stride != 0:
                continue

            keypoints = self.pose_extractor.extract_keypoints_from_frame(frame)
            if keypoints is None:
                continue
            smoothed = self.pose_extractor.smooth_keypoints(keypoints)
            keypoint_buffer.append(smoothed)
            if len(keypoint_buffer) > DEFAULT_BUFFER_SIZE:
                keypoint_buffer.pop(0)

            events = self._process_buffer(keypoint_buffer)
            if not events:
                continue

            # One session = one fall event. Run grace period, then alert once.
            event = events[0]
            event.timestamp = time.time()
            triggered = self._run_grace_and_alert(event, stop_event)
            if triggered:
                self.last_alert_at = time.time()
                metrics.register_alert(self.last_alert_at)
                metrics.increment("fall_candidates")
                metrics.update(pipeline_running=False)
            if self._is_current_session(stop_event):
                self._session_active = False
            metrics.update(pipeline_running=False)
            return  # session complete

        if self._is_current_session(stop_event):
            self._session_active = False
        metrics.update(pipeline_running=False)

    def _process_buffer(self, keypoint_buffer):
        subject_id = self._subject_id()
        clip_id = "live" if subject_id == "live" else "demo_fall"
        if len(keypoint_buffer) < 2:
            return []
        try:
            self.feature_engineer.set_frame_stride(
                int(self.config.get("camera", {}).get("frame_stride", 1))
            )
            features_df = self.feature_engineer.compute_features(
                list(keypoint_buffer), subject_id=subject_id, clip_id=clip_id
            )
        except Exception as e:
            logger.warning(f"Feature extraction failed: {e}")
            return []
        if len(features_df) == 0:
            return []

        features_df_with_label = features_df.copy()
        features_df_with_label["label"] = 0
        try:
            X, _, _ = self.model.prepare_features(features_df_with_label)
            fall_probabilities = self.model.predict_proba(X)
            if fall_probabilities.ndim == 2 and fall_probabilities.shape[1] == 2:
                fall_probabilities = fall_probabilities[:, 1]
            features_df["fall_probability"] = fall_probabilities
            return self.decision_logic.process_predictions(features_df)
        except Exception as e:
            logger.warning(f"Model inference failed: {e}")
            return []

    def _run_grace_and_alert(self, event, stop_event: threading.Event) -> bool:
        """Persist a candidate, run its grace period, then deliver if needed."""
        event_dict = {
            "timestamp": event.timestamp,
            "subject_id": event.subject_id,
            "clip_id": event.clip_id,
            "confidence": event.confidence,
            "tier": event.tier,
            "window_start": event.window_start,
            "window_end": event.window_end,
            "video_clip_path": "",
        }

        # Make the candidate visible before waiting. This is what allows a
        # caregiver to acknowledge/cancel it from the dashboard.
        alert_id = self.alert_manager.log_alert_event(
            event_dict,
            {"outcome": "pending", "response_time": None, "timestamp": time.time()},
            status="pending",
            delivery_status="not_sent",
        )
        if not alert_id:
            self.session_error = "could not persist detection event"
            return False

        cancel_event = threading.Event()
        with _active_grace_lock:
            _active_grace_events[str(alert_id)] = cancel_event

        def user_response(timeout_sec):
            start = time.time()
            while time.time() - start < timeout_sec:
                if cancel_event.is_set() or stop_event.is_set():
                    return True
                time.sleep(0.1)
            return False

        try:
            try:
                grace_result = self.grace_manager.confirm_fall(
                    event_dict, get_user_input=user_response
                )
            except Exception as e:
                logger.error(f"Grace period failed: {e}")
                self.alert_manager.update_alert(
                    alert_id, "escalated", "system", "system",
                    {"delivery_status": "failed", "grace_period_outcome": "error"},
                )
                return False

            if not grace_result.alert_triggered:
                current = self.alert_manager.store.get(alert_id) or {}
                # Preserve a dashboard acknowledgement if it arrived first.
                action = current.get("status") if current.get("status") in {
                    "acknowledged", "dismissed"
                } else "dismissed"
                self.alert_manager.update_alert(
                    alert_id, action, "system", "system",
                    {
                        "grace_period_outcome": "cancelled",
                        "grace_period_response_time": grace_result.response_time,
                        "delivery_status": "cancelled",
                    },
                )
                logger.info("Alert %s cancelled during grace period", alert_id)
                return False

            grace_dict = {
                "outcome": grace_result.outcome,
                "response_time": grace_result.response_time,
                "timestamp": grace_result.timestamp,
            }
            self.alert_manager.update_alert(
                alert_id, "escalated", "system", "system",
                {
                    "grace_period_outcome": grace_result.outcome,
                    "grace_period_response_time": grace_result.response_time,
                    "delivery_status": "pending",
                },
            )
            try:
                # The provisional row already exists; do not append a second
                # event after delivery.
                ok = self.alert_manager.send_email_alert(
                    event_dict, grace_dict, log_alert=False
                )
                self.alert_manager.update_alert(
                    alert_id, "escalated", "system", "system",
                    {
                        "delivery_status": "sent" if ok else "failed",
                        "alert_success": ok,
                    },
                )
                logger.info("Fall alert %s delivery result: %s", alert_id, ok)
                if not ok:
                    self.session_error = "alert delivery failed"
                return ok
            except Exception as e:
                self.session_error = f"alert send failed: {e}"
                self.alert_manager.update_alert(
                    alert_id, "escalated", "system", "system",
                    {"delivery_status": "failed", "alert_error": str(e)},
                )
                return False
        finally:
            with _active_grace_lock:
                _active_grace_events.pop(str(alert_id), None)

    # ─── helpers ────────────────────────────────────────────────────────────

    def _subject_id(self) -> str:
        src = str(self.session_source or "")
        if src == "live" or src.isdigit() or src.startswith(("rtsp://", "http://")):
            return "live"
        return "demo"