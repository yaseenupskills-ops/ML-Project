"""Project-wide configuration and path helpers.

The application historically opened configuration and runtime paths relative to
whatever directory the process happened to be launched from.  This module makes
paths deterministic and provides lightweight validation for configuration values
that affect safety or correctness.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"


class ConfigError(ValueError):
    """Raised when a configuration file is missing or invalid."""


def resolve_config_path(config_path: str | Path | None = None) -> Path:
    """Resolve a config path without making callers depend on their cwd.

    The default ``config.yaml`` is always resolved relative to the project root.
    Explicit relative paths retain normal cwd-relative semantics, which keeps
    temporary config files straightforward to use in tests and tools.
    """

    if config_path is None or str(config_path) == "config.yaml":
        return DEFAULT_CONFIG_PATH
    return Path(config_path).expanduser().resolve()


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load a YAML configuration file and return a dictionary."""

    path = resolve_config_path(config_path)
    if not path.exists():
        raise ConfigError(f"Configuration file not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Configuration root must be a mapping: {path}")
    return data


def resolve_path(value: str | Path | None, base: str | Path | None = None) -> Path | None:
    """Resolve a configured path relative to ``base`` or the project root."""

    if value is None or str(value).strip() == "":
        return None
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    root = Path(base).expanduser().resolve() if base is not None else PROJECT_ROOT
    return (root / path).resolve()


def validate_config(config: dict[str, Any]) -> list[str]:
    """Return human-readable configuration validation errors.

    Missing optional sections are allowed for compatibility with the original
    example config; callers can merge defaults or use the returned errors to
    decide whether startup should be blocked.
    """

    errors: list[str] = []

    pose = config.get("pose", {}) or {}
    features = config.get("features", {}) or {}
    decision = config.get("decision", {}) or {}
    grace = config.get("grace_period", {}) or {}
    streaming = config.get("streaming", {}) or {}
    camera = config.get("camera", {}) or {}

    def positive_int(section: dict[str, Any], key: str, label: str) -> None:
        value = section.get(key)
        if value is not None and (not isinstance(value, (int, float)) or int(value) < 1):
            errors.append(f"{label} must be a positive integer")

    def nonnegative_number(section: dict[str, Any], key: str, label: str) -> None:
        value = section.get(key)
        if value is not None and (not isinstance(value, (int, float)) or value < 0):
            errors.append(f"{label} must be non-negative")

    positive_int(pose, "frame_stride", "pose.frame_stride")
    positive_int(pose, "smooth_window", "pose.smooth_window")
    min_confidence = pose.get("min_confidence")
    if min_confidence is not None and (
        not isinstance(min_confidence, (int, float)) or not 0 <= min_confidence <= 1
    ):
        errors.append("pose.min_confidence must be between 0 and 1")
    positive_int(features, "fps", "features.fps")
    positive_int(camera, "frame_stride", "camera.frame_stride")
    positive_int(camera, "width", "camera.width")
    positive_int(camera, "height", "camera.height")
    positive_int(decision, "vote_windows", "decision.vote_windows")

    window_sec = features.get("window_sec")
    if window_sec is not None and (not isinstance(window_sec, (int, float)) or window_sec <= 0):
        errors.append("features.window_sec must be greater than zero")

    overlap = features.get("overlap")
    if overlap is not None and (
        not isinstance(overlap, (int, float)) or not 0 <= overlap < 1
    ):
        errors.append("features.overlap must be in the range [0, 1)")

    low_conf = decision.get("low_conf")
    high_conf = decision.get("high_conf")
    for name, value in (("decision.low_conf", low_conf), ("decision.high_conf", high_conf)):
        if value is not None and (not isinstance(value, (int, float)) or not 0 <= value <= 1):
            errors.append(f"{name} must be between 0 and 1")
    if isinstance(low_conf, (int, float)) and isinstance(high_conf, (int, float)):
        if low_conf > high_conf:
            errors.append("decision.low_conf cannot exceed decision.high_conf")

    nonnegative_number(grace, "timeout_sec", "grace_period.timeout_sec")

    port = streaming.get("port")
    if port is not None and (not isinstance(port, int) or not 1 <= port <= 65535):
        errors.append("streaming.port must be an integer between 1 and 65535")

    max_fps = streaming.get("max_fps")
    if max_fps is not None and (not isinstance(max_fps, (int, float)) or max_fps <= 0):
        errors.append("streaming.max_fps must be greater than zero")

    if streaming.get("allow_remote"):
        errors.append(
            "streaming.allow_remote requires an authenticated reverse proxy; "
            "direct remote binding is not permitted by the privacy policy"
        )

    auth = config.get("auth", {}) or {}
    if auth.get("enabled"):
        secret = auth.get("jwt_secret") or auth.get("secret_key")
        if not secret and not os.getenv("FALLGUARD_AUTH_SECRET"):
            errors.append("auth.jwt_secret or FALLGUARD_AUTH_SECRET is required when auth is enabled")

    return errors


def load_validated_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load configuration and raise :class:`ConfigError` if it is unsafe."""

    config = load_config(config_path)
    errors = validate_config(config)
    if errors:
        raise ConfigError("Invalid configuration:\n- " + "\n- ".join(errors))
    return config
