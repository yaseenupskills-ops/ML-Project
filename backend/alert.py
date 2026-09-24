"""
Alert Module
------------
Handles sending alerts via email (and SMS stretch goal).
Only alert metadata (text) is transmitted - no video or images.
"""

import smtplib
import ssl
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional
import yaml
import time
from pathlib import Path
import json

# Try to import Twilio for SMS (stretch goal)
try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Twilio not available - SMS alerts disabled")

logger = logging.getLogger(__name__)

class AlertManager:
    """Manages alerting via email and SMS."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with configuration."""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.email_config = self.config['email']
        self._validate_email_config()
        
        # SMS configuration (stretch goal)
        self.sms_config = self.config.get('sms', {
            'enabled': False,
            'account_sid': '',
            'auth_token': '',
            'from_number': '',
            'to_number': ''
        })
        
        # Alert log file (local only)
        self.alert_log = Path(self.config['paths']['logs_dir']) / "alerts.jsonl"
        self.alert_log.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info("AlertManager initialized")
        if self.email_config['sender'] and self.email_config['app_password']:
            logger.info("Email alerts configured")
        else:
            logger.warning("Email not fully configured - check config.yaml")
        
        if TWILIO_AVAILABLE and self.sms_config.get('enabled', False):
            logger.info("SMS alerts configured (stretch goal)")
        else:
            logger.info("SMS alerts not configured")
    
    def _validate_email_config(self):
        """Validate email configuration."""
        required_fields = ['smtp_host', 'smtp_port', 'sender', 'app_password', 'recipient']
        for field in required_fields:
            if not self.email_config.get(field):
                logger.warning(f"Email config missing or empty: {field}")
    
    def send_email_alert(self, 
                        fall_event: dict, 
                        grace_result: dict,
                        custom_message: Optional[str] = None,
                        log_alert: bool = True) -> bool:
        """
        Send email alert for fall detection.
        
        Args:
            fall_event: Dictionary with fall event details
            grace_result: Dictionary from grace period processing
            custom_message: Optional custom message body
            log_alert: Whether to write an entry to the local alert log
            
        Returns:
            True if email sent successfully, False otherwise
        """
        # Check if email is configured
        if not self.email_config['sender'] or not self.email_config['app_password']:
            logger.error("Email not configured - cannot send alert")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_config['sender']
            msg['To'] = self.email_config['recipient']
            
            # Determine subject based on outcome
            if grace_result['outcome'] == 'cancelled':
                msg['Subject'] = "ℹ️ Fall Detection Alert - User Responded (False Alarm)"
            else:
                msg['Subject'] = "⚠️ URGENT: Fall Detection Alert - Possible Fall Detected"
            
            # Create message body
            if custom_message is None:
                body = self._format_alert_message(fall_event, grace_result)
            else:
                body = custom_message
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            context = ssl.create_default_context()
            # Try to use certifi for SSL certificates (handles macOS cert issues)
            try:
                import certifi
                context.load_verify_locations(certifi.where())
            except ImportError:
                # If certifi not available, try to use system certs
                # If that fails, we'll use an unverified context (not ideal but works for testing)
                try:
                    context.load_default_certs()
                except Exception:
                    logger.warning("Could not load SSL certificates, using unverified context")
                    context = ssl._create_unverified_context()
            
            with smtplib.SMTP(self.email_config['smtp_host'], self.email_config['smtp_port']) as server:
                server.starttls(context=context)
                server.login(self.email_config['sender'], self.email_config['app_password'])
                text = msg.as_string()
                server.sendmail(self.email_config['sender'], self.email_config['recipient'], text)
            
            logger.info(f"Email alert sent to {self.email_config['recipient']}")
            
            # Log alert locally
            self._log_alert(fall_event, grace_result, 'email', True)
            
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("Email authentication failed - check app password")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            return False
    
    def send_sms_alert(self,
                      fall_event: dict,
                      grace_result: dict,
                      custom_message: Optional[str] = None) -> bool:
        """
        Send SMS alert via Twilio (stretch goal).
        
        Args:
            fall_event: Dictionary with fall event details
            grace_result: Dictionary from grace period processing
            custom_message: Optional custom message body
            
        Returns:
            True if SMS sent successfully, False otherwise
        """
        if not TWILIO_AVAILABLE:
            logger.error("Twilio not available - SMS alerts disabled")
            return False
        
        if not self.sms_config.get('enabled', False):
            logger.warning("SMS alerts not enabled in config")
            return False
        
        # Check SMS configuration
        required_fields = ['account_sid', 'auth_token', 'from_number', 'to_number']
        missing_fields = [f for f in required_fields if not self.sms_config.get(f)]
        if missing_fields:
            logger.error(f"SMS config missing fields: {missing_fields}")
            return False
        
        try:
            # Initialize Twilio client
            client = Client(self.sms_config['account_sid'], self.sms_config['auth_token'])
            
            # Create message body
            if custom_message is None:
                body = self._format_alert_message(fall_event, grace_result, is_sms=True)
            else:
                body = custom_message
            
            # Truncate to SMS length if needed
            if len(body) > 160:
                body = body[:157] + "..."
            
            # Send message
            message = client.messages.create(
                body=body,
                from_=self.sms_config['from_number'],
                to=self.sms_config['to_number']
            )
            
            logger.info(f"SMS alert sent: SID {message.sid}")
            
            # Log alert locally
            self._log_alert(fall_event, grace_result, 'sms', True)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send SMS alert: {e}")
            return False
    
    def _format_alert_message(self, fall_event: dict, grace_result: dict, is_sms: bool = False) -> str:
        """
        Format alert message for email or SMS.
        
        Args:
            fall_event: Fall event dictionary
            grace_result: Grace period result dictionary
            is_sms: True if formatting for SMS (shorter)
            
        Returns:
            Formatted message string
        """
        # Extract information
        timestamp = fall_event.get('timestamp', time.time())
        subject_id = fall_event.get('subject_id', 'unknown')
        clip_id = fall_event.get('clip_id', 'unknown')
        confidence = fall_event.get('confidence', 0.0)
        tier = fall_event.get('tier', 'low')
        
        # Format timestamp
        try:
            dt_string = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
        except:
            dt_string = str(timestamp)
        
        # Determine alert type
        if grace_result['outcome'] == 'cancelled':
            alert_type = "FALSE ALARM CANCELLED"
            urgency = "Low"
            action = "No action needed - user confirmed they are okay"
        else:
            alert_type = "POSSIBLE FALL DETECTED"
            urgency = "High"
            action = "Please check on the individual immediately"
        
        if is_sms:
            # Short format for SMS
            msg = f"{alert_type} at {dt_string}\n"
            msg += f"Confidence: {tier} ({confidence:.0%})\n"
            msg += f"User: {action}\n"
            if grace_result['outcome'] != 'cancelled':
                msg += "ALERT SENT - NO RESPONSE RECEIVED"
            else:
                msg += "FALSE ALARM - USER RESPONDED"
        else:
            # Full format for email
            msg = f"FALL DETECTION SYSTEM ALERT\n"
            msg += "=" * 40 + "\n\n"
            msg += f"ALERT TYPE: {alert_type}\n"
            msg += f"TIMESTAMP: {dt_string}\n"
            msg += f"SUBJECT ID: {subject_id}\n"
            msg += f"CLIP ID: {clip_id}\n"
            msg += f"CONFIDENCE: {tier} ({confidence:.1%})\n"
            msg += f"GRACE PERIOD OUTCOME: {grace_result['outcome']}\n"
            if grace_result['response_time'] is not None:
                msg += f"RESPONSE TIME: {grace_result['response_time']:.1f} seconds\n"
            msg += "\n"
            msg += "RECOMMENDED ACTION:\n"
            msg += f"  {action}\n\n"
            msg += "ADDITIONAL CONTEXT:\n"
            msg += "- This is an automated alert from a fall detection system\n"
            msg += "- The system processes pose keypoints only - no video is stored or transmitted\n"
            msg += "- False alarms can occur during rapid sitting/lying down\n"
            msg += "- If this is a true fall, please check on the individual immediately\n"
            msg += "- If unable to reach them, consider calling emergency services\n\n"
            msg += "SYSTEM INFORMATION:\n"
            msg += "- Alert sent by: Fall Detection System\n"
            msg += "- This message was generated automatically\n"
            msg += "- Do not reply to this automated message\n"
        
        return msg
    
    def _log_alert(self, fall_event: dict, grace_result: dict, 
                  alert_type: str, success: bool):
        """Log alert attempt to local file."""
        try:
            log_entry = {
                'timestamp': time.time(),
                'fall_event_timestamp': fall_event.get('timestamp'),
                'fall_event_subject': fall_event.get('subject_id'),
                'fall_event_clip': fall_event.get('clip_id'),
                'fall_event_confidence': fall_event.get('confidence'),
                'fall_event_tier': fall_event.get('tier'),
                'alert_type': alert_type,
                'alert_success': success,
                'grace_period_outcome': grace_result.get('outcome'),
                'grace_period_response_time': grace_result.get('response_time'),
                'video_clip_path': fall_event.get('video_clip_path', ''),
                'status': 'pending',
                'acknowledged_by': None,
                'acknowledged_at': None,
                'acknowledged_by_role': None,
                'logged_locally_only': True
            }
            
            with open(self.alert_log, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
            logger.debug(f"Logged alert attempt to {self.alert_log}")
            
        except Exception as e:
            logger.error(f"Failed to log alert: {e}")
    
    @staticmethod
    def acknowledge_alert(log_file: Path, alert_timestamp: float, 
                         user: str, role: str, action: str = 'acknowledged') -> bool:
        """Update an alert with acknowledgment details.
        
        Args:
            log_file: Path to alerts.jsonl
            alert_timestamp: Timestamp of the alert to update
            user: Username who acknowledged
            role: Role of the user (admin/caregiver)
            action: 'acknowledged', 'dismissed', or 'escalated'
            
        Returns:
            True if updated successfully
        """
        try:
            lines = []
            updated = False
            with open(log_file, 'r') as f:
                for line in f:
                    entry = json.loads(line.strip())
                    if abs(entry.get('timestamp', 0) - alert_timestamp) < 0.01:
                        entry['status'] = action
                        entry['acknowledged_by'] = user
                        entry['acknowledged_at'] = time.time()
                        entry['acknowledged_by_role'] = role
                        updated = True
                    lines.append(json.dumps(entry))
            
            if updated:
                with open(log_file, 'w') as f:
                    f.write('\n'.join(lines) + '\n')
                logger.info(f"Alert {alert_timestamp} {action} by {user} ({role})")
            return updated
            
        except Exception as e:
            logger.error(f"Failed to acknowledge alert: {e}")
            return False
    
    @staticmethod
    def bulk_update_alerts(log_file: Path, alert_timestamps: list, user: str,
                           role: str, action: str = 'acknowledged') -> list:
        """Update multiple alerts with acknowledgment details in one pass.

        Args:
            log_file: Path to alerts.jsonl
            alert_timestamps: List of timestamps of the alerts to update
            user: Username who performed the action
            role: Role of the user (admin/caregiver)
            action: 'acknowledged', 'dismissed', or 'escalated'

        Returns:
            List of timestamps that were successfully updated
        """
        if not alert_timestamps:
            return []
        targets = set(round(float(ts), 4) for ts in alert_timestamps)
        updated = []
        try:
            lines = []
            with open(log_file, 'r') as f:
                for line in f:
                    entry = json.loads(line.strip())
                    key = round(float(entry.get('timestamp', 0)), 4)
                    if key in targets:
                        entry['status'] = action
                        entry['acknowledged_by'] = user
                        entry['acknowledged_at'] = time.time()
                        entry['acknowledged_by_role'] = role
                        updated.append(entry.get('timestamp'))
                    lines.append(json.dumps(entry))
            if updated:
                with open(log_file, 'w') as f:
                    f.write('\n'.join(lines) + '\n')
                logger.info(f"{len(updated)} alerts {action} by {user} ({role})")
            return updated
        except Exception as e:
            logger.error(f"Failed to bulk update alerts: {e}")
            return []

    @staticmethod
    def read_alerts(log_file: Path) -> list:
        """Read all alerts from log file."""
        if not log_file.exists():
            return []
        alerts = []
        with open(log_file, 'r') as f:
            for line in f:
                try:
                    alerts.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
        return alerts

    def _read_alert_entry(self, log_file: Path, alert_timestamp: float) -> Optional[dict]:
        """Read a single alert entry by timestamp."""
        if not log_file.exists():
            return None
        with open(log_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
                if abs(float(entry.get('timestamp', 0)) - float(alert_timestamp)) < 0.01:
                    return entry
        return None

    def send_escalation_email(self, log_file: Path, alert_timestamp: float) -> bool:
        """Send an urgent follow-up email when an alert is escalated.

        Re-notifies the caregiver for alerts that could not be resolved in time.
        Only alert metadata (text) is transmitted - no video or images.

        Args:
            log_file: Path to alerts.jsonl
            alert_timestamp: Timestamp of the escalated alert

        Returns:
            True if email sent successfully
        """
        entry = self._read_alert_entry(log_file, alert_timestamp)
        if not entry or entry.get('status') != 'escalated':
            logger.warning("Cannot send escalation email - alert entry not escalated")
            return False
        if not self.email_config['sender'] or not self.email_config['app_password']:
            logger.warning("Email not configured - cannot send escalation alert")
            return False

        fall_event = {
            'timestamp': entry.get('fall_event_timestamp') or entry.get('timestamp'),
            'subject_id': entry.get('fall_event_subject', 'unknown'),
            'clip_id': entry.get('fall_event_clip', 'unknown'),
            'confidence': entry.get('fall_event_confidence', 0.0),
            'tier': entry.get('fall_event_tier', 'low'),
            'video_clip_path': entry.get('video_clip_path', ''),
        }
        grace_result = {
            'alert_triggered': True,
            'outcome': 'timeout',
            'response_time': None,
            'timestamp': entry.get('timestamp'),
        }
        custom = (
            "ESCALATED FALL ALERT - ACTION REQUIRED\n"
            "=" * 40 + "\n\n"
            "This alert was escalated because no response was recorded in time.\n"
            f"Subject: {fall_event['subject_id']}\n"
            f"Clip: {fall_event['clip_id']}\n"
            f"Confidence: {fall_event['tier']} ({fall_event['confidence']:.1%})\n\n"
            "PLEASE CHECK ON THE INDIVIDUAL IMMEDIATELY.\n"
            "If you are unable to reach them, consider calling emergency services."
        )
        return self.send_email_alert(fall_event, grace_result, custom_message=custom,
                                     log_alert=False)

    @staticmethod
    def auto_escalate_stale(log_file: Path, max_age_sec: float,
                            user: str = 'system', role: str = 'system') -> list:
        """Escalate pending alerts older than the given age.

        Args:
            log_file: Path to alerts.jsonl
            max_age_sec: Age threshold (seconds) after which a pending alert escalates
            user: Username to record as the escalator
            role: Role to record

        Returns:
            List of timestamps that were escalated
        """
        if max_age_sec <= 0:
            return []
        now = time.time()
        stale = []
        if log_file.exists():
            with open(log_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                    except json.JSONDecodeError:
                        continue
                    if entry.get('status') == 'pending' and now - float(entry.get('timestamp', 0)) > float(max_age_sec):
                        stale.append(entry.get('timestamp'))
        return AlertManager.bulk_update_alerts(log_file, stale, user, role, 'escalated')
    
    def send_alert(self, 
                  fall_event: dict,
                  grace_result: dict,
                  method: str = 'email',
                  custom_message: Optional[str] = None) -> bool:
        """
        Send alert via specified method.
        
        Args:
            fall_event: Fall event dictionary
            grace_result: Grace period result dictionary
            method: 'email' or 'sms'
            custom_message: Optional custom message body
            
        Returns:
            True if alert sent successfully, False otherwise
        """
        if method.lower() == 'email':
            return self.send_email_alert(fall_event, grace_result, custom_message)
        elif method.lower() == 'sms':
            return self.send_sms_alert(fall_event, grace_result, custom_message)
        else:
            logger.error(f"Unknown alert method: {method}")
            return False

def send_fall_alert(fall_event: dict,
                   grace_result: dict,
                   config_path: str = "config.yaml",
                   method: str = 'email') -> bool:
    """
    Convenience function to send fall alert.
    
    Args:
        fall_event: Fall event dictionary
        grace_result: Grace period result dictionary
        config_path: Path to configuration file
        method: 'email' or 'sms'
        
    Returns:
        True if alert sent successfully, False otherwise
    """
    manager = AlertManager(config_path)
    return manager.send_alert(fall_event, grace_result, method)

def test_email_connection(config_path: str = "config.yaml") -> bool:
    """
    Test email connection and authentication.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        True if connection successful, False otherwise
    """
    try:
        manager = AlertManager(config_path)
        
        if not manager.email_config['sender'] or not manager.email_config['app_password']:
            print("Email not configured - please set sender and app_password in config.yaml")
            return False
        
        # Try to connect and authenticate
        context = ssl.create_default_context()
        with smtplib.SMTP(manager.email_config['smtp_host'], manager.email_config['smtp_port']) as server:
            server.starttls(context=context)
            server.login(manager.email_config['sender'], manager.email_config['app_password'])
        
        print(f"✓ Successfully connected to {manager.email_config['smtp_host']}")
        print(f"✓ Authenticated as {manager.email_config['sender']}")
        return True
        
    except Exception as e:
        print(f"✗ Email connection failed: {e}")
        return False

if __name__ == "__main__":
    # Example usage
    import sys
    logging.basicConfig(level=logging.INFO)
    
    print("Fall Detection Alert System Test")
    print("=" * 40)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            # Test email connection
            success = test_email_connection()
            sys.exit(0 if success else 1)
        elif sys.argv[1] == "send":
            # Send test alert
            if len(sys.argv) < 4:
                print("Usage: python alert.py send <fall_event_json> <grace_result_json>")
                sys.exit(1)
            
            try:
                fall_event = json.loads(sys.argv[2])
                grace_result = json.loads(sys.argv[3])
                
                success = send_fall_alert(fall_event, grace_result)
                print(f"Alert sent: {success}")
                sys.exit(0 if success else 1)
            except json.JSONDecodeError as e:
                print(f"Invalid JSON: {e}")
                sys.exit(1)
            except Exception as e:
                print(f"Error: {e}")
                sys.exit(1)
        else:
            print("Usage:")
            print("  python alert.py test          # Test email connection")
            print("  python alert.py send <fall_event_json> <grace_result_json>  # Send test alert")
            sys.exit(1)
    else:
        # Demo mode
        print("Running in demo mode...")
        
        # Test email connection first
        if test_email_connection():
            print("\nSending test alert...")
            
            # Example fall event
            fall_event = {
                'timestamp': time.time(),
                'subject_id': 'test_subject',
                'clip_id': 'demo_clip',
                'confidence': 0.87,
                'tier': 'high'
            }
            
            # Example grace period result (no response)
            grace_result = {
                'alert_triggered': True,
                'outcome': 'timeout',
                'response_time': None,
                'timestamp': time.time() - 20
            }
            
            success = send_fall_alert(fall_event, grace_result)
            print(f"Test alert sent: {success}")
        else:
            print("Please configure email in config.yaml first")