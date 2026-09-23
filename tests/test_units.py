"""
Unit Tests for Core Components
------------------------------
Simple tests to verify the correctness of individual functions.
"""

import unittest
import numpy as np
import pandas as pd
from pathlib import Path
import tempfile
import os

# Import modules to test
from pose_extraction import PoseExtractor
from features import FeatureEngineer
from decision_logic import DecisionLogic, FallEvent
from grace_period import GracePeriodManager

class TestPoseExtractor(unittest.TestCase):
    """Test pose extraction functionality."""
    
    def setUp(self):
        self.extractor = PoseExtractor()
    
    def test_initialization(self):
        """Test that PoseExtractor initializes correctly."""
        self.assertIsNotNone(self.extractor.pose)
        self.assertEqual(self.extractor.frame_stride, 2)
        self.assertEqual(self.extractor.smooth_window, 3)
        self.assertEqual(self.extractor.min_confidence, 0.5)
    
    def test_confidence_tier(self):
        """Test confidence tier mapping."""
        # Test high confidence
        self.assertEqual(self.extractor.confidence_tier(0.9), "high")
        self.assertEqual(self.extractor.confidence_tier(0.8), "high")
        
        # Test medium confidence
        self.assertEqual(self.extractor.confidence_tier(0.7), "medium")
        self.assertEqual(self.extractor.confidence_tier(0.5), "medium")
        
        # Test low confidence
        self.assertEqual(self.extractor.confidence_tier(0.4), "low")
        self.assertEqual(self.extractor.confidence_tier(0.0), "low")

class TestFeatureEngineer(unittest.TestCase):
    """Test feature engineering functionality."""
    
    def setUp(self):
        self.engineer = FeatureEngineer()
    
    def test_aspect_ratio_calculation(self):
        """Test aspect ratio calculation."""
        # Create a simple keypoint array representing a standing person
        # Tall and narrow shape
        keypoints = np.zeros((33, 3))
        # Set some points to create a tall narrow bounding box
        keypoints[11, :2] = [0.4, 0.8]  # Left shoulder
        keypoints[12, :2] = [0.6, 0.8]  # Right shoulder
        keypoints[23, :2] = [0.45, 0.2] # Left hip
        keypoints[24, :2] = [0.55, 0.2] # Right hip
        keypoints[:, 2] = 0.9  # High visibility
        
        ratio = self.engineer.compute_aspect_ratio(keypoints)
        # Should be tall/narrow: height > width
        self.assertGreater(ratio, 1.0)
    
    def test_torso_orientation(self):
        """Test torso orientation calculation."""
        # Upright torso
        keypoints = np.zeros((33, 3))
        keypoints[11, :2] = [0.4, 0.8]  # Left shoulder
        keypoints[12, :2] = [0.6, 0.8]  # Right shoulder
        keypoints[23, :2] = [0.45, 0.2] # Left hip
        keypoints[24, :2] = [0.55, 0.2] # Right hip
        keypoints[:, 2] = 0.9
        
        angle = self.engineer.compute_torso_orientation(keypoints)
        # Should be close to 0 degrees (vertical)
        self.assertLess(angle, 30.0)
        
        # Horizontal torso (lying down)
        keypoints[11, :2] = [0.2, 0.5]  # Left shoulder
        keypoints[12, :2] = [0.8, 0.5]  # Right shoulder
        keypoints[23, :2] = [0.25, 0.5] # Left hip
        keypoints[24, :2] = [0.75, 0.5] # Right hip
        
        angle = self.engineer.compute_torso_orientation(keypoints)
        # Should be close to 90 degrees (horizontal)
        self.assertGreater(angle, 60.0)

class TestDecisionLogic(unittest.TestCase):
    """Test decision logic functionality."""
    
    def setUp(self):
        self.dec_logic = DecisionLogic()
    
    def test_confidence_tier(self):
        """Test confidence tier mapping."""
        self.assertEqual(self.dec_logic.confidence_tier(0.9), "high")
        self.assertEqual(self.dec_logic.confidence_tier(0.8), "high")
        self.assertEqual(self.dec_logic.confidence_tier(0.7), "medium")
        self.assertEqual(self.dec_logic.confidence_tier(0.5), "medium")
        self.assertEqual(self.dec_logic.confidence_tier(0.4), "low")
        self.assertEqual(self.dec_logic.confidence_tier(0.0), "low")
    
    def test_majority_vote(self):
        """Test majority voting logic."""
        # Not enough windows
        is_fall, conf, tier = self.dec_logic.majority_vote([0.9], [0])
        self.assertFalse(is_fall)
        
        # Enough windows but not all above threshold
        probs = [0.4, 0.4, 0.4]  # All below low threshold
        is_fall, conf, tier = self.dec_logic.majority_vote(probs, [0,1,2])
        self.assertFalse(is_fall)
        
        # Enough windows above medium threshold
        probs = [0.9, 0.9, 0.4]  # Two above high threshold
        is_fall, conf, tier = self.dec_logic.majority_vote(probs, [0,1,2])
        self.assertTrue(is_fall)
        self.assertEqual(tier, "high")
        
        # Mixed case
        probs = [0.6, 0.7, 0.8]  # All above low, two above medium
        is_fall, conf, tier = self.dec_logic.majority_vote(probs, [0,1,2])
        self.assertTrue(is_fall)
        self.assertEqual(tier, "medium")  # Average is 0.7

class TestGracePeriodManager(unittest.TestCase):
    """Test grace period functionality."""
    
    def setUp(self):
        self.manager = GracePeriodManager()
    
    def test_initialization(self):
        """Test that GracePeriodManager initializes correctly."""
        self.assertEqual(self.manager.timeout_sec, 20)
        self.assertTrue(self.manager.log_file.parent.exists())

if __name__ == '__main__':
    unittest.main()