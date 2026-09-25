"""Regression tests for safety and inference contracts."""

import unittest

import numpy as np

from features import FeatureEngineer
from model_rf import FallDetectionRF
from project_config import validate_config
from stream_server import StreamServer


class TestInferenceContract(unittest.TestCase):
    def test_predict_proba_scales_raw_features_once(self):
        model = FallDetectionRF()
        model.feature_names = ["a", "b"]
        raw = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
        labels = np.array([0, 1, 1])
        model.scaler.fit(raw)
        model.model.fit(model.scaler.transform(raw), labels)
        model.is_fitted = True

        actual = model.predict_proba(raw)
        expected = model.model.predict_proba(model.scaler.transform(raw))
        np.testing.assert_allclose(actual, expected)
    def test_frame_stride_changes_effective_sampling_rate(self):
        engineer = FeatureEngineer()
        engineer.set_frame_stride(2)
        sequence = [np.ones((33, 3), dtype=float) for _ in range(20)]
        features = engineer.compute_features(sequence)
        self.assertGreater(len(features), 0)
        self.assertEqual(int(features.iloc[0]["window_size"]), 10)


class TestConfigurationSafety(unittest.TestCase):
    def test_remote_streaming_is_rejected(self):
        config = {
            "streaming": {"allow_remote": True},
            "features": {"fps": 30, "window_sec": 0.7, "overlap": 0.5},
        }
        self.assertTrue(any("allow_remote" in error for error in validate_config(config)))

    def test_invalid_overlap_is_rejected(self):
        config = {"features": {"fps": 30, "window_sec": 0.7, "overlap": 1.0}}
        self.assertTrue(any("overlap" in error for error in validate_config(config)))


class TestStreamSafety(unittest.TestCase):
    def test_server_generates_process_token(self):
        server = StreamServer({"recording_enabled": False})
        self.assertGreaterEqual(len(server.auth_token), 32)
        self.assertIn("http://localhost:8501", server.allowed_origins)

    def test_recording_is_disabled_by_default(self):
        server = StreamServer({})
        self.assertFalse(server.recording_enabled)


if __name__ == "__main__":
    unittest.main()
