import os
import sys
from pathlib import Path


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


def get_logs_dir() -> Path:
    base = get_base_dir()
    logs_dir = base / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_output_dir() -> Path:
    base = get_base_dir()
    out_dir = base / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def get_ui_output_dir() -> Path:
    """
    Default UI output directory (separate from CLI 'output' if desired).
    """
    base = get_base_dir()
    out_dir = base / "leads_gen_output"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def get_license_dir() -> Path:
    base = get_base_dir()
    lic_dir = base / "license"
    lic_dir.mkdir(parents=True, exist_ok=True)
    return lic_dir

