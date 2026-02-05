import logging
from datetime import datetime
from pathlib import Path

from .paths import get_logs_dir


def configure_file_logging(base_dir: Path | None = None, log_folder_name: str = "logs") -> Path:
    """
    Configure application-wide logging to a timestamped log file.

    Each app session gets its own log file named with the current date and time.
    Format: app_YYYY-MM-DD_HH-MM-SS.log

    Logs are written under:
        <base_dir>/<log_folder_name>/app_YYYY-MM-DD_HH-MM-SS.log

    Returns the path to the log file.
    """
    # base_dir is kept for backward-compatibility but ignored in favor of utils.paths
    log_dir = get_logs_dir()

    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file_path = log_dir / f"app_{timestamp}.log"
    log_file_path_resolved = log_file_path.resolve()

    # Dedicated application logger (avoid root to prevent duplicates)
    logger = logging.getLogger("leads_gen")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Avoid adding duplicate handlers if called multiple times
    # Compare resolved absolute paths to ensure accurate detection
    existing_paths = {
        Path(h.baseFilename).resolve()
        for h in logger.handlers
        if hasattr(h, "baseFilename")
    }
    
    if log_file_path_resolved not in existing_paths:
        # Use regular FileHandler since each session gets its own file
        file_handler = logging.FileHandler(
            log_file_path,
            mode="w",  # Create new file for each session
            encoding="utf-8",
            delay=False,
        )
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)

    return log_file_path

