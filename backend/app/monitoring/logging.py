"""Structured JSON logging (PRD §13): timestamp, service, device_id, event_id,
request_id, level, message, error_code."""

import json
import logging
import sys
from datetime import datetime, timezone

SERVICE_NAME = "fallguard-backend"

_EXTRA_FIELDS = ("device_id", "event_id", "request_id", "error_code")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "service": SERVICE_NAME,
            "level": record.levelname,
            "message": record.getMessage(),
        }
        for field in _EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
