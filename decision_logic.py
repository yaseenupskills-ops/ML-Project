"""
Decision Logic Module
---------------------
Implements majority voting and confidence tiering for fall detection.
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Optional
import logging

from project_config import load_config
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class FallEvent:
    """Represents a detected fall event."""
    timestamp: float  # Seconds since start of sequence
    confidence: float  # Raw probability [0, 1]
    tier: str         # "high", "medium", "low"
    window_start: int # Start frame index
    window_end: int   # End frame index
    subject_id: str   # Subject identifier
    clip_id: str      # Clip identifier
    features: dict    # Optional: feature values at detection

class DecisionLogic:
    """Handles majority voting and confidence tiering."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with configuration."""
        self.config = load_config(config_path)
        
        dec_config = self.config['decision']
        self.vote_windows = int(dec_config['vote_windows'])
        self.high_conf_thresh = float(dec_config['high_conf'])
        self.low_conf_thresh = float(dec_config['low_conf'])
        if self.vote_windows < 1:
            raise ValueError("decision.vote_windows must be positive")
        if not 0 <= self.low_conf_thresh <= self.high_conf_thresh <= 1:
            raise ValueError("decision thresholds must satisfy 0 <= low_conf <= high_conf <= 1")
        
        logger.info(f"DecisionLogic initialized: "
                   f"vote_windows={self.vote_windows}, "
                   f"high_conf={self.high_conf_thresh}, "
                   f"low_conf={self.low_conf_thresh}")
    
    def confidence_tier(self, probability: float) -> str:
        """
        Map probability to confidence tier.
        
        Args:
            probability: Model probability for fall class [0, 1]
            
        Returns:
            Confidence tier: "high", "medium", or "low"
        """
        if probability >= self.high_conf_thresh:
            return "high"
        elif probability >= self.low_conf_thresh:
            return "medium"
        else:
            return "low"
    
    def majority_vote(self, 
                     probabilities: List[float], 
                     window_indices: Optional[List[int]] = None) -> Tuple[bool, float, str]:
        """
        Apply majority voting across consecutive windows.
        
        Args:
            probabilities: List of fall probabilities for each window
            window_indices: Optional list of window indices (for debugging)
            
        Returns:
            Tuple of (is_fall_detected, avg_confidence, tier)
        """
        if not probabilities:
            return False, 0.0, "low"
        if any(not np.isfinite(float(p)) or not 0 <= float(p) <= 1 for p in probabilities):
            raise ValueError("Probabilities must be finite values in [0, 1]")
        if len(probabilities) < self.vote_windows:
            # Not enough windows for majority vote
            return False, 0.0, "low"
        
        # Check last N consecutive windows
        recent_probs = probabilities[-self.vote_windows:]
        
        # Require a strict majority of the recent windows to meet the high
        # confidence threshold. The average confidence is reported separately.
        high_count = sum(1 for p in recent_probs if p >= self.high_conf_thresh)
        required_high = (self.vote_windows // 2) + 1

        is_candidate = high_count >= required_high
        
        if is_candidate:
            # Use average probability of the voting windows
            avg_confidence = np.mean(recent_probs)
            tier = self.confidence_tier(avg_confidence)
            return True, avg_confidence, tier
        else:
            return False, 0.0, "low"
    
    def process_predictions(self, 
                           df: pd.DataFrame,
                           probability_col: str = 'fall_probability') -> List[FallEvent]:
        """
        Process a DataFrame of window predictions to detect fall events.
        
        Args:
            df: DataFrame with predictions (must have probability_col, subject_id, clip_id)
            probability_col: Column name containing fall probabilities
            
        Returns:
            List of detected FallEvent objects
        """
        if probability_col not in df.columns:
            raise ValueError(f"Column {probability_col} not found in DataFrame")
        required = {
            "subject_id", "clip_id", "window_start", "window_end",
            "window_start_time",
        }
        missing = sorted(required - set(df.columns))
        if missing:
            raise ValueError(f"Missing prediction columns: {missing}")

        # Sort by subject, clip, and time to ensure proper ordering.
        df_sorted = df.sort_values(
            ["subject_id", "clip_id", "window_start_time"]
        ).reset_index(drop=True)
        fall_events = []

        # Process each subject/clip combination separately.
        for (subject_id, clip_id), group in df_sorted.groupby(["subject_id", "clip_id"]):
            group = group.reset_index(drop=True)
            probabilities = group[probability_col].astype(float).tolist()
            window_starts = group["window_start"].values
            window_ends = group["window_end"].values
            window_times = group["window_start_time"].values
            last_event_time = None

            for i in range(len(probabilities)):
                if i + 1 < self.vote_windows:
                    continue
                detected, confidence, tier = self.majority_vote(probabilities[: i + 1])
                if not detected:
                    continue
                event_time = float(window_times[i])
                if last_event_time is not None and event_time - last_event_time <= 5.0:
                    continue
                event = FallEvent(
                    timestamp=event_time,
                    confidence=float(confidence),
                    tier=tier,
                    window_start=int(window_starts[i]),
                    window_end=int(window_ends[i]),
                    subject_id=str(subject_id),
                    clip_id=str(clip_id),
                    features={},
                )
                fall_events.append(event)
                last_event_time = event_time
                logger.info("Fall event detected: %s", event)
        
        logger.info(f"Processed {len(df_sorted)} windows, detected {len(fall_events)} fall events")
        return fall_events
    
    def apply_hysteresis(self, 
                        probabilities: List[float],
                        fall_threshold: float = 0.5,
                        rise_threshold: float = 0.3) -> List[bool]:
        """
        Apply hysteresis thresholding to reduce rapid toggling.
        
        Args:
            probabilities: List of probabilities
            fall_threshold: Threshold to transition TO fall state
            rise_threshold: Threshold to transition FROM fall state
            
        Returns:
            List of boolean fall states
        """
        states = [False] * len(probabilities)
        in_fall_state = False
        
        for i, prob in enumerate(probabilities):
            if not in_fall_state and prob >= fall_threshold:
                # Transition to fall state
                in_fall_state = True
            elif in_fall_state and prob <= rise_threshold:
                # Transition to non-fall state
                in_fall_state = False
            
            states[i] = in_fall_state
        
        return states

def detect_fall_events(predictions_df: pd.DataFrame,
                      config_path: str = "config.yaml") -> List[FallEvent]:
    """
    Convenience function to detect fall events from predictions DataFrame.
    
    Args:
        predictions_df: DataFrame with window predictions
        config_path: Path to configuration file
        
    Returns:
        List of FallEvent objects
    """
    dec_logic = DecisionLogic(config_path)
    return dec_logic.process_predictions(predictions_df)

def majority_vote_probabilities(probabilities: List[float],
                               vote_windows: int = 3,
                               high_conf: float = 0.8,
                               low_conf: float = 0.5) -> Tuple[bool, float, str]:
    """
    Standalone majority voting function.
    
    Args:
        probabilities: List of probabilities
        vote_windows: Number of consecutive windows required
        high_conf: Threshold for high confidence
        low_conf: Threshold for low confidence
        
    Returns:
        Tuple of (is_detected, confidence, tier)
    """
    # Temporary config override
    class TempConfig:
        def __init__(self):
            self.decision = {
                'vote_windows': vote_windows,
                'high_conf': high_conf,
                'low_conf': low_conf
            }
    
    # We'll hack this - in practice, just use the class directly
    dec_logic = DecisionLogic.__new__(DecisionLogic)
    dec_logic.vote_windows = vote_windows
    dec_logic.high_conf_thresh = high_conf
    dec_logic.low_conf_thresh = low_conf
    
    return dec_logic.majority_vote(probabilities)

if __name__ == "__main__":
    # Example usage
    import sys
    import pandas as pd
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1:
        predictions_csv = sys.argv[1]
        
        print(f"Processing predictions from {predictions_csv}")
        df = pd.read_csv(predictions_csv)
        
        events = detect_fall_events(df)
        
        print(f"Detected {len(events)} fall events:")
        for i, event in enumerate(events):
            print(f"  {i+1}. {event}")
    else:
        # Create example data
        print("Creating example predictions...")
        n_windows = 20
        df_example = pd.DataFrame({
            'subject_id': ['subject1'] * n_windows,
            'clip_id': ['clip1'] * n_windows,
            'window_start': list(range(0, n_windows*3, 3)),
            'window_end': list(range(3, n_windows*3+3, 3)),
            'window_start_time': [i*3.0/30 for i in range(n_windows)],  # Assuming 30fps, 3-sec windows
            'fall_probability': [0.1, 0.2, 0.3, 0.7, 0.8, 0.9, 0.8, 0.7, 0.2, 0.1] +
                              [0.1]*10  # Pad to 20
        })
        
        events = detect_fall_events(df_example)
        print(f"Detected {len(events)} fall events in example data:")
        for event in events:
            print(f"  {event}")