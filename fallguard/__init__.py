"""FallGuard — privacy-preserving fall detection for elderly care.

Python package containing the detection pipeline, ML models, evaluation,
alerts, alert store, camera sources, stream server, and config handling.
"""

from .project_config import PROJECT_ROOT, load_config, resolve_path

__all__ = ["PROJECT_ROOT", "load_config", "resolve_path"]