"""Focused unit tests for core fall-detection contracts."""

import tempfile
import unittest
from pathlib import Path

import numpy as np

from alert_store import AlertStore
from decision_logic import DecisionLogic, majority_vote_probabilities
from features import FeatureEngineer
from grace_period import GracePeriodManager, simulate_grace_period
from pose_extraction import PoseExtractor


class TestPoseExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = PoseExtractor()

    def tearDown(self):
        self.extractor.close()

    def test_initialization_uses_current_tasks_api(self):
        self.assertTrue(self.extractor.model_path.exists())
        self.assertIsNotNone(self.extractor.detector)
        self.assertEqual(self.extractor.frame_stride, 1)

    def test_reset_clears_smoothing_state(self):
        keypoints = np.ones((33, 3), dtype=float)
        self.extractor.smooth_keypoints(keypoints)
        self.assertTrue(self.extractor.keypoint_buffer)
        self.extractor.reset()
        self.assertFalse(self.extractor.keypoint_buffer)


class TestFeatureEngineer(unittest.TestCase):
    def setUp(self):
        self.engineer = FeatureEngineer()

    def test_aspect_ratio_calculation(self):
        keypoints = np.zeros((33, 3), dtype=float)
        keypoints[11, :2] = [0.4, 0.8]
        keypoints[12, :2] = [0.6, 0.8]
        keypoints[23, :2] = [0.45, 0.2]
        keypoints[24, :2] = [0.55, 0.2]
        keypoints[:, 2] = 0.9
        self.assertGreater(self.engineer.compute_aspect_ratio(keypoints), 1.0)

    def test_torso_orientation_contract(self):
        keypoints = np.zeros((33, 3), dtype=float)
        keypoints[:, 2] = 0.9
        keypoints[11, :2] = [0.4, 0.8]
        keypoints[12, :2] = [0.6, 0.8]
        keypoints[23, :2] = [0.45, 0.2]
        keypoints[24, :2] = [0.55, 0.2]
        upright = self.engineer.compute_torso_orientation(keypoints)

        keypoints[11, :2] = [0.2, 0.5]
        keypoints[12, :2] = [0.8, 0.5]
        keypoints[23, :2] = [0.25, 0.5]
        keypoints[24, :2] = [0.75, 0.5]
        lying = self.engineer.compute_torso_orientation(keypoints)
        self.assertLess(upright, 30.0)
        self.assertGreater(lying, 60.0)

    def test_invalid_overlap_is_rejected(self):
        # The production constructor reads config.yaml; this assertion protects
        # the public feature contract used by future config injection.
        with self.assertRaises(ValueError):
            self.engineer.overlap = 1.0
            self.engineer.compute_features([np.ones((33, 3)) for _ in range(3)])


class TestDecisionLogic(unittest.TestCase):
    def setUp(self):
        self.logic = DecisionLogic()

    def test_current_threshold_contract(self):
        self.assertEqual(self.logic.confidence_tier(0.9), "high")
        self.assertEqual(self.logic.confidence_tier(0.45), "medium")
        self.assertEqual(self.logic.confidence_tier(0.2), "low")

    def test_majority_vote_requires_enough_windows(self):
        detected, _, _ = majority_vote_probabilities(
            [0.9], vote_windows=3, high_conf=0.5, low_conf=0.4
        )
        self.assertFalse(detected)
        detected, _, _ = majority_vote_probabilities(
            [0.1, 0.1, 0.1], vote_windows=3, high_conf=0.5, low_conf=0.4
        )
        self.assertFalse(detected)
        detected, _, _ = majority_vote_probabilities(
            [0.9, 0.9, 0.1], vote_windows=3, high_conf=0.5, low_conf=0.4
        )
        self.assertTrue(detected)


class TestGracePeriod(unittest.TestCase):
    def test_grace_manager_uses_configured_timeout(self):
        manager = GracePeriodManager()
        self.assertGreater(manager.timeout_sec, 0)

    def test_simulation_helper_honors_explicit_timeout(self):
        result = simulate_grace_period(
            {"timestamp": 1.0, "subject_id": "S1", "clip_id": "c1"},
            timeout_sec=0.05,
            auto_respond_after=0.01,
        )
        self.assertFalse(result.alert_triggered)
        self.assertEqual(result.outcome, "cancelled")
        self.assertIsNotNone(result.response_time)


class TestAlertStore(unittest.TestCase):
    def test_duplicate_timestamps_receive_independent_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "alerts.jsonl"
            store = AlertStore(path)
            first = store.append({"timestamp": 10.0, "status": "pending"})
            second = store.append({"timestamp": 10.0, "status": "pending"})
            self.assertNotEqual(first, second)
            self.assertTrue(store.update(alert_id=first, action="acknowledged"))
            records = {record["id"]: record for record in store.read_all()}
            self.assertEqual(records[first]["status"], "acknowledged")
            self.assertEqual(records[second]["status"], "pending")


if __name__ == "__main__":
    unittest.main()
