"""
License data model for the Google Maps Lead Generator.

This module defines the structure of license data and provides
validation logic for license parameters.
"""

import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger("leads_gen")


@dataclass
class LicenseData:
    """
    License data structure for machine-bound, time-limited licensing.

    Attributes:
        fingerprint: Hashed machine fingerprint (SHA-256, 64 chars)
        expiry_date: License expiration date (ISO format: YYYY-MM-DD)
        max_results_per_run: Maximum number of results allowed per scraping session
        version: License format version for future compatibility
        issued_date: Date when license was issued (ISO format)
        features: Optional dictionary of feature flags
    """

    fingerprint: str
    expiry_date: str  # ISO format: YYYY-MM-DD
    max_results_per_run: int
    version: str = "1.0"
    issued_date: str = ""  # ISO format: YYYY-MM-DD
    features: dict[str, bool] | None = None

    def __post_init__(self):
        """Validate license data after initialization."""
        if not self.issued_date:
            self.issued_date = datetime.now().strftime("%Y-%m-%d")

        if self.features is None:
            self.features = {}

        # Validate fingerprint
        if not self.fingerprint or len(self.fingerprint) != 64:
            raise ValueError("Fingerprint must be a 64-character SHA-256 hash")

        # Validate dates
        try:
            expiry = datetime.strptime(self.expiry_date, "%Y-%m-%d")
            issued = datetime.strptime(self.issued_date, "%Y-%m-%d")

            if expiry <= issued:
                raise ValueError("Expiry date must be after issued date")
        except ValueError as e:
            raise ValueError(f"Invalid date format: {e}") from e

        # Validate max results
        if self.max_results_per_run <= 0:
            raise ValueError("max_results_per_run must be greater than 0")

    def to_dict(self) -> dict[str, Any]:
        """Convert license data to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LicenseData":
        """Create LicenseData from dictionary."""
        return cls(**data)

    def is_expired(self, check_date: datetime | None = None) -> bool:
        """
        Check if license is expired.

        Args:
            check_date: Date to check against (defaults to today)

        Returns:
            True if license is expired, False otherwise
        """
        if check_date is None:
            check_date = datetime.now()

        expiry = datetime.strptime(self.expiry_date, "%Y-%m-%d")
        return check_date.date() > expiry.date()

    def days_remaining(self) -> int:
        """
        Get number of days remaining until expiry.

        Returns:
            Number of days remaining (negative if expired)
        """
        expiry = datetime.strptime(self.expiry_date, "%Y-%m-%d")
        today = datetime.now()
        delta = expiry.date() - today.date()
        return delta.days

    def matches_fingerprint(self, fingerprint: str) -> bool:
        """
        Check if provided fingerprint matches license fingerprint.

        Args:
            fingerprint: Machine fingerprint to check

        Returns:
            True if fingerprints match, False otherwise
        """
        return self.fingerprint == fingerprint

    def __repr__(self) -> str:
        """String representation (safe for logging)."""
        return (
            f"LicenseData(fingerprint={self.fingerprint[:16]}..., "
            f"expiry={self.expiry_date}, max_results={self.max_results_per_run}, "
            f"version={self.version})"
        )


def create_trial_license(fingerprint: str, days: int = 7, max_results: int = 50) -> LicenseData:
    """
    Create a trial license for testing.

    Args:
        fingerprint: Machine fingerprint
        days: Number of days the trial is valid
        max_results: Maximum results per run

    Returns:
        LicenseData object for trial license
    """
    expiry_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

    return LicenseData(
        fingerprint=fingerprint,
        expiry_date=expiry_date,
        max_results_per_run=max_results,
        features={
            "trial": True,
            "social_media_scraping": True,
            "email_extraction": True,
        },
    )


def create_full_license(fingerprint: str, months: int = 12, max_results: int = 1000) -> LicenseData:
    """
    Create a full/paid license.

    Args:
        fingerprint: Machine fingerprint
        months: Number of months the license is valid
        max_results: Maximum results per run

    Returns:
        LicenseData object for full license
    """
    expiry_date = (datetime.now() + timedelta(days=months * 30)).strftime("%Y-%m-%d")

    return LicenseData(
        fingerprint=fingerprint,
        expiry_date=expiry_date,
        max_results_per_run=max_results,
        features={
            "trial": False,
            "social_media_scraping": True,
            "email_extraction": True,
            "unlimited_exports": True,
        },
    )


TRIAL_LICENSE_DAY_CUTOFF = 30


def create_license_from_days(fingerprint: str, total_days: int, max_results: int) -> LicenseData:
    # Classify by actual duration rather than which CLI flag the issuer used.
    # Also preserves exact day-count in expiry: `create_full_license` uses a
    # months*30 approximation that drifts by up to a week for arbitrary day counts.
    if total_days <= TRIAL_LICENSE_DAY_CUTOFF:
        return create_trial_license(fingerprint, days=total_days, max_results=max_results)
    expiry_date = (datetime.now() + timedelta(days=total_days)).strftime("%Y-%m-%d")
    return LicenseData(
        fingerprint=fingerprint,
        expiry_date=expiry_date,
        max_results_per_run=max_results,
        features={
            "trial": False,
            "social_media_scraping": True,
            "email_extraction": True,
            "unlimited_exports": True,
        },
    )


if __name__ == "__main__":
    """Test the license data model."""
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("License Data Model Test")
    print("=" * 60)

    # Test fingerprint (example)
    test_fingerprint = "a" * 64

    # Create trial license
    print("\n1. Creating Trial License:")
    trial = create_trial_license(test_fingerprint, days=14, max_results=100)
    print(f"   {trial}")
    print(f"   Days remaining: {trial.days_remaining()}")
    print(f"   Is expired: {trial.is_expired()}")
    print(f"   Features: {trial.features}")

    # Create full license
    print("\n2. Creating Full License:")
    full = create_full_license(test_fingerprint, months=12, max_results=5000)
    print(f"   {full}")
    print(f"   Days remaining: {full.days_remaining()}")
    print(f"   Is expired: {full.is_expired()}")
    print(f"   Features: {full.features}")

    # Test serialization
    print("\n3. Testing Serialization:")
    license_dict = trial.to_dict()
    print(f"   Dict keys: {list(license_dict.keys())}")
    reconstructed = LicenseData.from_dict(license_dict)
    print(f"   Reconstructed: {reconstructed}")
    print(f"   Match: {trial == reconstructed}")

    # Test validation
    print("\n4. Testing Validation:")
    try:
        invalid = LicenseData(
            fingerprint="short",  # Invalid: too short
            expiry_date="2025-12-31",
            max_results_per_run=100,
        )
    except ValueError as e:
        print(f"   ✓ Caught invalid fingerprint: {e}")

    try:
        invalid = LicenseData(
            fingerprint=test_fingerprint,
            expiry_date="2020-01-01",  # Invalid: in the past
            max_results_per_run=100,
        )
    except ValueError as e:
        print(f"   ✓ Caught invalid date: {e}")

    print("\n" + "=" * 60)
