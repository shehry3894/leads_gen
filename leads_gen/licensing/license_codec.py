"""
License key encode/decode primitives.

Runtime code (LicenseManager) and the developer-only key generator
(tools/generate_license.py) both share this module so the encoding
scheme lives in exactly one place. The SECRET_KEY here is what
XORs the payload — it must stay identical between generator and
validator.
"""

import base64
import hashlib
import json
import logging

from leads_gen.licensing.license_model import LicenseData

logger = logging.getLogger("leads_gen")

# Symmetric secret used for the XOR obfuscation of license payloads.
# Not real encryption; the goal is to make casual tampering fail the checksum.
SECRET_KEY = "LEADS_GEN_SECRET_KEY_2026_DO_NOT_SHARE"

_CHECKSUM_MARKER = "|CHECKSUM|"


def _key_stream() -> bytes:
    return hashlib.sha256(SECRET_KEY.encode()).digest()


def _xor(data: bytes) -> bytearray:
    key = _key_stream()
    return bytearray(byte ^ key[i % len(key)] for i, byte in enumerate(data))


def encode_license(license_data: LicenseData) -> str:
    """Serialize + checksum + XOR + base64 a LicenseData into a license key."""
    json_str = json.dumps(license_data.to_dict(), sort_keys=True)
    checksum = hashlib.sha256(json_str.encode()).hexdigest()[:16]
    payload = f"{json_str}{_CHECKSUM_MARKER}{checksum}"

    encrypted = _xor(payload.encode("utf-8"))
    license_key = base64.b64encode(encrypted).decode("utf-8")
    logger.info(f"Encoded license: {len(license_key)} characters")
    return license_key


def decode_license(license_key: str) -> LicenseData:
    """Reverse of encode_license. Raises ValueError on any corruption."""
    try:
        encrypted = base64.b64decode(license_key.encode("utf-8"))
        payload = _xor(encrypted).decode("utf-8")

        if _CHECKSUM_MARKER not in payload:
            raise ValueError("Invalid license format: missing checksum")

        json_str, checksum_part = payload.split(_CHECKSUM_MARKER)
        expected_checksum = hashlib.sha256(json_str.encode()).hexdigest()[:16]

        if checksum_part != expected_checksum:
            raise ValueError("Invalid license: checksum mismatch (corrupted or tampered)")

        license_data = LicenseData.from_dict(json.loads(json_str))
        logger.info(f"Decoded license: {license_data}")
        return license_data
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Invalid license key: {e}") from e
