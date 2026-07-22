"""
Filesystem-path helpers used throughout the app.

Every ``get_*_dir()`` function attempts to create its target directory. If the
primary location is not writable (read-only volume, permission denied, disk
full), we fall back to a per-user temp directory so the app can still run —
users just lose logs/output in the ideal spot rather than crashing at import.
"""

from __future__ import annotations

import contextlib
import logging
import sys
import tempfile
from pathlib import Path

logger = logging.getLogger("leads_gen")


def get_base_dir() -> Path:
    """
    Return the base directory for the application.

    In frozen (PyInstaller) mode this is the folder containing the executable.
    In development mode this is the project root (directory containing this file's parent).
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent

    # utils/paths.py -> utils -> project root
    return Path(__file__).resolve().parent.parent


def _ensure_dir(primary: Path, fallback_name: str) -> Path:
    """
    Create ``primary`` if possible, else fall back to a tempdir named
    ``leads_gen_<fallback_name>`` under the OS temp root.
    """
    try:
        primary.mkdir(parents=True, exist_ok=True)
        return primary
    except (PermissionError, OSError) as e:
        fallback = Path(tempfile.gettempdir()) / f"leads_gen_{fallback_name}"
        # If even the tempdir fails we return it anyway — callers will surface
        # a clearer error when they attempt to write.
        with contextlib.suppress(OSError):
            fallback.mkdir(parents=True, exist_ok=True)
        logger.warning(
            "Could not create %s (%s: %s); falling back to %s",
            primary,
            type(e).__name__,
            e,
            fallback,
        )
        return fallback


def get_logs_dir() -> Path:
    return _ensure_dir(get_base_dir() / "logs", "logs")


def get_output_dir() -> Path:
    return _ensure_dir(get_base_dir() / "output", "output")


def get_ui_output_dir() -> Path:
    """Default UI output directory (separate from CLI 'output')."""
    return _ensure_dir(get_base_dir() / "leads_gen_output", "ui_output")


def get_license_dir() -> Path:
    return _ensure_dir(get_base_dir() / "license", "license")
