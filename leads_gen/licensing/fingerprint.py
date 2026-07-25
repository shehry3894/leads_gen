"""
Machine fingerprint — the OS hardware UUID.

Reads the OS-native hardware UUID (SMBIOS / motherboard-level) directly
and returns it in canonical UUID form. This value is what the license
system binds against — customers see it in the sidebar, copy it, and
send it to the developer to receive a license key.

Per-OS source:
  - macOS   → IOPlatformUUID via ``ioreg -rd1 -c IOPlatformExpertDevice``
              (identical to the "Hardware UUID" shown in System Information)
  - Windows → SMBIOS system UUID via ``wmic csproduct get UUID``
  - Linux   → SMBIOS system UUID from /sys/class/dmi/id/product_uuid
              (root-only on Ubuntu/Debian; falls back to /etc/machine-id,
              a 128-bit ID set at OS install, stable across reboots)

Output is always the standard UPPERCASE hyphenated form
(e.g. ``5172A6D1-D8D1-525D-B275-C891BB687412``) regardless of source
format. The 32-hex ``/etc/machine-id`` fallback is reshaped into UUID
form for a consistent user-facing representation.

Fails hard (RuntimeError) if no identifier is available. A random
fallback would silently invalidate the customer's license on the next
launch, which is worse than refusing to run.
"""

from __future__ import annotations

import contextlib
import logging
import platform
import re
import subprocess
import uuid
from pathlib import Path

logger = logging.getLogger("leads_gen")


def _read_uuid_macos() -> str | None:
    try:
        out = subprocess.check_output(
            ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
            text=True,
            timeout=5,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None
    m = re.search(r'"IOPlatformUUID"\s*=\s*"([0-9A-Fa-f-]+)"', out)
    return m.group(1) if m else None


def _read_uuid_windows() -> str | None:
    try:
        out = subprocess.check_output(
            ["wmic", "csproduct", "get", "UUID"],
            text=True,
            timeout=5,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None
    # wmic output is "UUID\r\r\n<uuid>\r\r\n" — pick the first non-header line.
    for line in out.splitlines():
        candidate = line.strip()
        if candidate and candidate.lower() != "uuid":
            return candidate
    return None


def _read_uuid_linux() -> str | None:
    # Preferred: SMBIOS system UUID (real hardware UUID).
    # World-readable on Fedora / RHEL; root-only on Ubuntu / Debian.
    with contextlib.suppress(OSError):
        raw = Path("/sys/class/dmi/id/product_uuid").read_text().strip()
        if raw:
            return raw
    # Fallback for distros that gate /sys/class/dmi behind root: use the
    # systemd machine-id (128 bits of hex, no hyphens). Set at OS install
    # and stable across reboots — reformatted into UUID shape downstream.
    with contextlib.suppress(OSError):
        machine_id = Path("/etc/machine-id").read_text().strip()
        if machine_id:
            return machine_id
    return None


def _normalize(raw: str) -> str:
    """
    Parse a UUID string or 32-hex machine-id and return the canonical
    UPPERCASE hyphenated UUID form. Raises ValueError if the input is
    not a 128-bit hex value.
    """
    return str(uuid.UUID(raw)).upper()


def _get_hardware_uuid() -> str:
    system = platform.system()
    reader = {
        "Darwin": _read_uuid_macos,
        "Windows": _read_uuid_windows,
        "Linux": _read_uuid_linux,
    }.get(system)

    raw = reader() if reader else None
    if not raw:
        raise RuntimeError(
            f"Cannot read hardware UUID on {system!r}. This is required "
            "for machine-bound licensing. Contact support."
        )
    try:
        return _normalize(raw)
    except ValueError as e:
        raise RuntimeError(
            f"Hardware UUID from {system!r} is malformed ({raw!r}): {e}. " "Contact support."
        ) from e


def generate_machine_fingerprint() -> str:
    """
    Return this machine's hardware UUID in canonical UPPERCASE form
    (e.g. ``5172A6D1-D8D1-525D-B275-C891BB687412``).

    Raises:
        RuntimeError: if the OS does not expose a hardware machine ID.
    """
    fingerprint = _get_hardware_uuid()
    logger.info(f"Generated machine fingerprint: {fingerprint}")
    return fingerprint


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("Machine Fingerprint")
    print("=" * 60)

    fp = generate_machine_fingerprint()
    print(f"\nFingerprint: {fp}")
    print(f"Length:      {len(fp)} characters")

    assert generate_machine_fingerprint() == fp, "fingerprint not stable!"
    print("Stability:   OK (two consecutive calls returned the same value)")
    print("=" * 60)
