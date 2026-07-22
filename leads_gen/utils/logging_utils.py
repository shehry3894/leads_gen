"""
Application-wide logging configuration.

Sessions get a timestamped file handler under ``logs/`` (or a temp fallback
if that directory isn't writable). If the file handler itself can't be
attached, we fall back to a StreamHandler on stderr so the process still
produces logs — silent logging is the worst outcome for a shipped app.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

from .paths import get_logs_dir


def configure_file_logging(base_dir: Path | None = None, log_folder_name: str = "logs") -> Path:
    """
    Configure application-wide logging to a timestamped log file.

    Each app session gets its own log file named with the current date and time.
    Format: app_YYYY-MM-DD_HH-MM-SS.log

    Returns the intended log file path — even if the FileHandler couldn't be
    attached (in which case logs go to stderr and a warning is emitted).
    """
    # base_dir is kept for backward-compatibility but ignored in favor of utils.paths
    log_dir = get_logs_dir()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file_path = log_dir / f"app_{timestamp}.log"

    # Dedicated application logger (avoid root to prevent duplicates)
    logger = logging.getLogger("leads_gen")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    try:
        log_file_path_resolved = log_file_path.resolve()
    except OSError:
        # Path.resolve() can raise on missing parents on some OSes; treat as new.
        log_file_path_resolved = log_file_path

    # Avoid adding duplicate handlers if called multiple times.
    existing_paths = set()
    for h in logger.handlers:
        base = getattr(h, "baseFilename", None)
        if base:
            try:
                existing_paths.add(Path(base).resolve())
            except OSError:
                existing_paths.add(Path(base))

    if log_file_path_resolved in existing_paths:
        return log_file_path

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")

    try:
        file_handler: logging.Handler = logging.FileHandler(
            log_file_path,
            mode="w",
            encoding="utf-8",
            delay=False,
        )
    except (PermissionError, OSError) as e:
        # Disk full, permission denied, path too long — degrade to stderr so
        # the app still produces logs instead of silently losing them.
        file_handler = logging.StreamHandler(stream=sys.stderr)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.warning(
            "Could not open log file %s (%s: %s); falling back to stderr.",
            log_file_path,
            type(e).__name__,
            e,
        )
        return log_file_path

    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    return log_file_path
