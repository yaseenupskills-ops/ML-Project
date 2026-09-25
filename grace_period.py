"""
Grace Period Module
-------------------
Implements the confirmation window to reduce false alarms.
Allows user to cancel alerts within a timeout period.
"""

import time
import json
import logging
from typing import Optional, Callable
from pathlib import Path
from dataclasses import dataclass

from project_config import load_config, resolve_config_path, resolve_path

logger = logging.getLogger(__name__)

@dataclass
class GracePeriodResult:
    """Result of grace period processing."""
    alert_triggered: bool  # True if alert should be sent
    outcome: str           # "cancelled" or "timeout"
    response_time: Optional[float]  # Seconds until response, None if timeout
    timestamp: float       # Unix timestamp of grace period start
    video_clip_path: str = ""  # Path to video clip around detection time

class GracePeriodManager:
    """Manages the grace period confirmation window."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with configuration."""
        config_file = resolve_config_path(config_path)
        self.config = load_config(config_file)
        
        grace_config = self.config['grace_period']
        self.timeout_sec = grace_config['timeout_sec']
        
        # File for logging false positives (locally only)
        logs_dir = resolve_path(
            self.config.get('paths', {}).get('logs_dir', 'logs'),
            base=config_file.parent,
        )
        self.log_file = (logs_dir or Path('logs')) / "false_positives.jsonl"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"GracePeriodManager initialized: timeout={self.timeout_sec}s")
    
    def confirm_fall(self, 
                     fall_event: dict,
                     get_user_input: Optional[Callable[[float], bool]] = None) -> GracePeriodResult:
        """Present grace period and wait for user response.
        
        Args:
            fall_event: Dictionary with fall event details
            get_user_input: Optional callback that returns True if user responded
                           If None, uses console input simulation
         
        Returns:
            GracePeriodResult indicating whether alert should be triggered
        """
        start_time = time.time()
        timeout = self.timeout_sec
        
        logger.info(f"Starting grace period for fall event at {fall_event.get('timestamp', 'unknown')}")
        logger.info(f"User has {timeout} seconds to respond")
        
        # In a real system, this would trigger a UI/audio prompt
        # For simulation, we'll use console input or a callback
        
        try:
            if get_user_input is None:
                # Default: simulate with console input
                print(f"\n⚠️  FALL DETECTED - Respond within {timeout} seconds to cancel alert")
                print("   Press ENTER if you're okay, or wait for alert to be sent...")
                
                # Wait for user input with timeout
                user_responded = False
                start = time.time()
                while time.time() - start < timeout:
                    # Check if input is available
                    import sys, select
                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        line = sys.stdin.readline()
                        if line.strip() == '':
                            user_responded = True
                            break
                    time.sleep(0.1)
            else:
                user_responded = get_user_input(timeout)
            
            if user_responded:
                outcome = "cancelled"
                alert_triggered = False
                response_time = time.time() - start_time
                logger.info(f"User responded after {response_time:.1f}s - alert cancelled")
            else:
                outcome = "timeout"
                alert_triggered = True
                response_time = None
                logger.info(f"No response after {timeout}s - triggering alert")
                
        except Exception as e:
            logger.error(f"Error during grace period: {e}")
            # Default to triggering alert on error
            outcome = "error"
            alert_triggered = True
            response_time = None
        
        # Create result
        result = GracePeriodResult(
            alert_triggered=alert_triggered,
            outcome=outcome,
            response_time=response_time,
            timestamp=start_time
        )
        
        # Log the result locally (for false positive analysis)
        self._log_grace_period_result(fall_event, result)
        
        return result
    
    def _log_grace_period_result(self, fall_event: dict, result: GracePeriodResult):
        """Log grace period result to local file for analysis."""
        try:
            log_entry = {
                'timestamp': result.timestamp,
                'fall_event_timestamp': fall_event.get('timestamp'),
                'fall_event_subject': fall_event.get('subject_id'),
                'fall_event_clip': fall_event.get('clip_id'),
                'fall_event_confidence': fall_event.get('confidence'),
                'fall_event_tier': fall_event.get('tier'),
                'grace_period_outcome': result.outcome,
                'grace_period_response_time': result.response_time,
                'alert_triggered': result.alert_triggered
            }
            
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
            logger.debug(f"Logged grace period result to {self.log_file}")
            
        except Exception as e:
            logger.error(f"Failed to log grace period result: {e}")

# Keep the old simulate_grace_period function for backward compatibility
def simulate_grace_period(fall_event: dict, 
                         timeout_sec: int = 20,
                         auto_respond_after: Optional[float] = None) -> GracePeriodResult:
    """Simulate grace period for testing purposes.
    
    Args:
        fall_event: Dictionary with fall event details
        timeout_sec: Seconds before escalating alert
        auto_respond_after: If not None, automatically respond after this many seconds
        
    Returns:
        GracePeriodResult indicating whether alert should be triggered
    """
    manager = GracePeriodManager()  # Uses default config
    # The explicit argument is part of the public helper API. Do not silently
    # ignore it and wait for the configured production timeout.
    manager.timeout_sec = float(timeout_sec)

    def auto_response(timeout_sec):
        """Auto-respond after auto_respond_after seconds."""
        if auto_respond_after is None:
            return False
        start = time.time()
        while time.time() - start < timeout_sec:
            if time.time() - start >= auto_respond_after:
                return True
            time.sleep(min(0.01, max(0.0, timeout_sec - (time.time() - start))))
        return False
    
    return manager.confirm_fall(fall_event, get_user_input=auto_response)