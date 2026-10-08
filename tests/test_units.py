"""Focused unit tests for core fall-detection contracts."""

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from fallguard.alert_store import AlertStore
from fallguard.decision_logic import DecisionLogic, majority_vote_probabilities
from fallguard.evaluate_video_split import split_by_video
from fallguard.features import FeatureEngineer
from fallguard.grace_period import GracePeriodManager, simulate_grace_period
from fallguard.pose_extraction import PoseExtractor
from fallguard.settings_store import (
    DEFAULT_CONTACTS,
    DEFAULT_SETTINGS,
    ContactStore,
    SettingsStore,
)


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


class TestCareStores(unittest.TestCase):
    def test_contact_store_seeds_adds_and_deletes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contacts.json"
            store = ContactStore(path)
            seeded = store.list()
            self.assertEqual(len(seeded), len(DEFAULT_CONTACTS))
            created = store.add({"name": "Neighbor Pat", "phone": "(555) 100-2000"})
            # A fresh instance reads the persisted file (survives restarts).
            self.assertEqual(len(ContactStore(path).list()), len(seeded) + 1)
            self.assertTrue(ContactStore(path).delete(created["id"]))
            self.assertFalse(ContactStore(path).delete(created["id"]))
            self.assertEqual(len(ContactStore(path).list()), len(seeded))

    def test_contact_store_keeps_empty_list_after_all_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contacts.json"
            store = ContactStore(path)
            for record in list(store.list()):
                self.assertTrue(store.delete(record["id"]))
            # An intentionally empty list must not re-seed the defaults.
            self.assertEqual(ContactStore(path).list(), [])

    def test_settings_store_persists_and_validates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            store = SettingsStore(path)
            self.assertEqual(store.get(), DEFAULT_SETTINGS)
            saved = store.update({"grace_period_sec": 30, "email_alerts": False})
            self.assertEqual(saved["grace_period_sec"], 30)
            self.assertFalse(saved["email_alerts"])
            # Values survive a fresh instance; defaults fill the gaps.
            reloaded = SettingsStore(path).get()
            self.assertEqual(reloaded["grace_period_sec"], 30)
            self.assertEqual(reloaded["chime_volume"], DEFAULT_SETTINGS["chime_volume"])
            with self.assertRaises(ValueError):
                store.update({"grace_period_sec": 999})
            with self.assertRaises(ValueError):
                store.update({"chime_volume": "loud"})
            with self.assertRaises(ValueError):
                store.update({"email_alerts": "yes"})
            # Unknown keys are ignored rather than persisted.
            self.assertNotIn("bogus", store.update({"bogus": 1}))


class TestVideoSplit(unittest.TestCase):
    """The 80/20 evaluation split must be grouped by whole video."""

    @staticmethod
    def _frame():
        rows = []
        for label, prefix, count in ((0, "adl", 40), (1, "fall", 30)):
            for i in range(1, count + 1):
                for window in range(3):
                    rows.append(
                        {
                            "clip_id": f"{prefix}-{i:02d}",
                            "label": label,
                            "window_start": window,
                        }
                    )
        return pd.DataFrame(rows)

    def test_split_is_grouped_stratified_and_complete(self):
        df = self._frame()
        train_df, test_df, train_ids, test_ids = split_by_video(df)

        # No video can appear in both splits (leakage is fatal).
        self.assertEqual(set(train_ids) & set(test_ids), set())
        # Every video lands in exactly one split.
        self.assertEqual(set(train_ids) | set(test_ids), set(df["clip_id"]))
        # 80/20 stratified: 40 ADL -> 32/8, 30 falls -> 24/6.
        self.assertEqual(len(train_ids), 56)
        self.assertEqual(len(test_ids), 14)
        self.assertEqual(
            test_df["clip_id"].nunique(), 14
        )
        self.assertEqual(set(test_df["label"]), {0, 1})
        self.assertEqual(set(train_df["label"]), {0, 1})
        # All windows are accounted for.
        self.assertEqual(len(train_df) + len(test_df), len(df))

    def test_split_is_deterministic(self):
        df = self._frame()
        first = split_by_video(df)
        second = split_by_video(df)
        self.assertEqual(first[2], second[2])
        self.assertEqual(first[3], second[3])


if __name__ == "__main__":
    unittest.main()
