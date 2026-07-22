"""
Machine fingerprint generation for licensing.

This module generates a unique, hashed fingerprint for the machine
running the application. The fingerprint is based on hardware identifiers
and is used for machine-bound licensing.
"""

import hashlib
import logging
import platform
import uuid

logger = logging.getLogger("leads_gen")


def get_mac_address() -> str | None:
    """
    Get the MAC address of the machine.

    Returns:
        MAC address as a string, or None if not available
    """
    try:
        # Get the MAC address as a 48-bit integer
        mac_int = uuid.getnode()

        # Convert to MAC address format (XX:XX:XX:XX:XX:XX)
        mac_hex = ":".join(
            [f"{(mac_int >> elements) & 0xFF:02x}" for elements in range(0, 8 * 6, 8)][::-1]
        )

        logger.debug("Retrieved MAC address (will be hashed)")
        return mac_hex
    except Exception as e:
        logger.error(f"Failed to retrieve MAC address: {e}")
        return None


def generate_machine_fingerprint() -> str:
    """
    Generate a hashed machine fingerprint.

    The fingerprint is generated from:
    - MAC address (primary identifier)
    - System UUID (if available)
    - Hostname (as fallback)

    The raw identifiers are never exposed or logged.
    Only the final hash is returned and logged.

    Returns:
        A SHA-256 hash of the machine identifiers (64 hex characters)
    """
    identifiers = []

    # Get MAC address
    mac = get_mac_address()
    if mac:
        identifiers.append(mac)

    # Get system/machine ID if available
    try:
        system_uuid = uuid.UUID(int=uuid.getnode())
        identifiers.append(str(system_uuid))
    except Exception:
        pass

    # Get hostname as additional identifier
    try:
        hostname = platform.node()
        if hostname:
            identifiers.append(hostname)
    except Exception:
        pass

    # If no identifiers found, use a random UUID (not ideal for licensing)
    if not identifiers:
        logger.warning("No hardware identifiers found, generating random fingerprint")
        identifiers.append(str(uuid.uuid4()))

    # Combine all identifiers
    combined = "|".join(identifiers)

    # Generate SHA-256 hash
    fingerprint = hashlib.sha256(combined.encode("utf-8")).hexdigest()

    logger.info(f"Generated machine fingerprint: {fingerprint}")
    logger.debug(f"Fingerprint based on {len(identifiers)} identifier(s)")

    return fingerprint


def get_machine_info() -> dict:
    """
    Get machine information for licensing purposes.

    Returns:
        Dictionary containing:
        - fingerprint: Hashed machine fingerprint
        - system: Operating system
        - platform: Platform details
        - hostname: Machine hostname (not sensitive)
    """
    info = {
        "fingerprint": generate_machine_fingerprint(),
        "system": platform.system(),
        "platform": platform.platform(),
        "hostname": platform.node(),
        "python_version": platform.python_version(),
    }

    logger.info(f"Machine Info - System: {info['system']}, Platform: {info['platform']}")

    return info


if __name__ == "__main__":
    """Test the fingerprint generation."""
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("Machine Fingerprint Test")
    print("=" * 60)

    # Generate fingerprint
    fingerprint = generate_machine_fingerprint()
    print(f"\nMachine Fingerprint: {fingerprint}")
    print(f"Length: {len(fingerprint)} characters")

    # Get full machine info
    print("\nFull Machine Info:")
    info = get_machine_info()
    for key, value in info.items():
        print(f"  {key}: {value}")

    # Test consistency
    print("\nTesting consistency (should be identical):")
    fp1 = generate_machine_fingerprint()
    fp2 = generate_machine_fingerprint()
    print(f"  First:  {fp1}")
    print(f"  Second: {fp2}")
    print(f"  Match:  {fp1 == fp2}")

    print("\n" + "=" * 60)
