#!/usr/bin/env python3
"""Verify local runtime prerequisites without modifying project data."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from project_config import ConfigError, load_config, validate_config  # noqa: E402


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        config = load_config(ROOT / "config.yaml")
        errors.extend(validate_config(config))
    except (ConfigError, OSError) as exc:
        errors.append(str(exc))
        config = {}

    pose_model = ROOT / "models" / "pose_landmarker_lite.task"
    if not pose_model.exists():
        errors.append(
            f"Missing MediaPipe model: {pose_model}. Download/provision it before running live detection."
        )

    rf_model = ROOT / str(config.get("model", {}).get("rf_path", "models/rf_baseline.joblib"))
    if not rf_model.is_absolute():
        rf_model = ROOT / rf_model
    if not rf_model.exists():
        warnings.append(f"RF model not found: {rf_model}. Training or model restore is required.")

    for package in ("cv2", "mediapipe", "numpy", "pandas", "sklearn", "streamlit"):
        if importlib.util.find_spec(package) is None:
            errors.append(f"Missing Python package: {package}")

    if config.get("email", {}).get("app_password"):
        warnings.append(
            "Email app password is present in config.yaml; move it to "
            "FALLGUARD_EMAIL_APP_PASSWORD and rotate it if this file was shared."
        )

    recording_enabled = bool(config.get("recording", {}).get("enabled", False))
    if recording_enabled:
        warnings.append("Recording is enabled; verify retention and local-only access before use.")

    if config.get("auth", {}).get("enabled") is False:
        warnings.append("Authentication is disabled; use only for local development.")

    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")

    if errors:
        print(f"Setup verification failed with {len(errors)} error(s).")
        return 1
    print("Setup verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
