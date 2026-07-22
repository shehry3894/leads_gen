#!/usr/bin/env python3
"""
License Key Generator (Offline Tool)

This script is NOT bundled with the application.
It is used by the developer to generate license keys for customers.

The license key is an encrypted, base64-encoded string that contains:
- Machine fingerprint
- Expiry date
- Maximum results per run
- Feature flags

Usage:
    python generate_license.py --fingerprint <hash> --days <days> --max-results <number>
    python generate_license.py --fingerprint <hash> --months <months> --max-results <number>
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path to import the leads_gen package when this
# tool is run standalone.
sys.path.insert(0, str(Path(__file__).parent.parent))

from leads_gen.licensing.license_codec import decode_license, encode_license
from leads_gen.licensing.license_model import create_full_license, create_trial_license

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def validate_fingerprint(fingerprint: str) -> bool:
    """Validate that fingerprint is a valid SHA-256 hash."""
    if len(fingerprint) != 64:
        return False
    try:
        int(fingerprint, 16)  # Check if it's valid hex
        return True
    except ValueError:
        return False


def generate_trial_license_key(fingerprint: str, days: int, max_results: int) -> str:
    """Generate a trial license key."""
    license_data = create_trial_license(fingerprint, days, max_results)
    return encode_license(license_data)


def generate_full_license_key(fingerprint: str, months: int, max_results: int) -> str:
    """Generate a full license key."""
    license_data = create_full_license(fingerprint, months, max_results)
    return encode_license(license_data)


def save_license_to_file(license_key: str, fingerprint: str, output_dir: str = "licenses"):
    """Save license key to a file."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Create filename from fingerprint prefix
    filename = f"license_{fingerprint[:16]}.txt"
    filepath = output_path / filename

    with open(filepath, "w") as f:
        f.write(license_key)

    logger.info(f"License saved to: {filepath}")
    return filepath


def main():
    parser = argparse.ArgumentParser(
        description="Generate license keys for Google Maps Lead Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 7-day trial license
  python generate_license.py --fingerprint abc123... --days 7 --max-results 50

  # Generate 12-month full license
  python generate_license.py --fingerprint abc123... --months 12 --max-results 5000

  # Generate license with specific expiry date (recommended)
  python generate_license.py --fingerprint abc123... --expiry-date 2026-12-31 --max-results 1000

  # Generate license and save to file
  python generate_license.py --fingerprint abc123... --expiry-date 2027-06-30 --max-results 1000 --save
        """,
    )

    parser.add_argument(
        "--fingerprint", required=True, help="Machine fingerprint (64-character SHA-256 hash)"
    )

    # Time period (mutually exclusive)
    time_group = parser.add_mutually_exclusive_group(required=True)
    time_group.add_argument(
        "--days", type=int, help="License duration in days (for trial licenses)"
    )
    time_group.add_argument(
        "--months", type=int, help="License duration in months (for full licenses)"
    )
    time_group.add_argument(
        "--expiry-date",
        type=str,
        help="License expiry date in YYYY-MM-DD format (e.g., 2026-12-31)",
    )

    parser.add_argument(
        "--max-results",
        type=int,
        required=True,
        help="Maximum number of results per scraping session",
    )

    parser.add_argument("--save", action="store_true", help="Save license key to file")

    parser.add_argument(
        "--test-decode", action="store_true", help="Test decoding the generated license"
    )

    args = parser.parse_args()

    # Validate fingerprint
    if not validate_fingerprint(args.fingerprint):
        logger.error("Invalid fingerprint format. Must be a 64-character SHA-256 hash (hex)")
        sys.exit(1)

    # Validate max results
    if args.max_results <= 0:
        logger.error("max-results must be greater than 0")
        sys.exit(1)

    # Generate license key
    print("=" * 60)
    print("License Key Generator")
    print("=" * 60)

    # Handle expiry date parameter
    if args.expiry_date:
        from datetime import datetime

        try:
            # Parse the expiry date
            expiry_date = datetime.strptime(args.expiry_date, "%Y-%m-%d").date()
            today = datetime.now().date()

            # Validate expiry date is in the future
            if expiry_date <= today:
                logger.error(
                    f"Expiry date must be in the future. Given: {expiry_date}, Today: {today}"
                )
                sys.exit(1)

            # Calculate days until expiry
            days_until_expiry = (expiry_date - today).days

            # Determine license type based on duration
            if days_until_expiry <= 30:
                # Trial license (30 days or less)
                print("\nGenerating TRIAL license:")
                print(f"  Fingerprint: {args.fingerprint[:16]}...")
                print(f"  Expiry Date: {expiry_date}")
                print(f"  Duration: {days_until_expiry} days")
                print(f"  Max Results: {args.max_results}")
                license_key = generate_trial_license_key(
                    args.fingerprint, days_until_expiry, args.max_results
                )
            else:
                # Full license (more than 30 days)
                months = days_until_expiry // 30  # Approximate months
                print("\nGenerating FULL license:")
                print(f"  Fingerprint: {args.fingerprint[:16]}...")
                print(f"  Expiry Date: {expiry_date}")
                print(f"  Duration: {days_until_expiry} days (~{months} months)")
                print(f"  Max Results: {args.max_results}")
                license_key = generate_full_license_key(args.fingerprint, months, args.max_results)
        except ValueError as e:
            logger.error(f"Invalid date format. Use YYYY-MM-DD (e.g., 2026-12-31). Error: {e}")
            sys.exit(1)
    elif args.days:
        print("\nGenerating TRIAL license:")
        print(f"  Fingerprint: {args.fingerprint[:16]}...")
        print(f"  Duration: {args.days} days")
        print(f"  Max Results: {args.max_results}")
        license_key = generate_trial_license_key(args.fingerprint, args.days, args.max_results)
    else:
        print("\nGenerating FULL license:")
        print(f"  Fingerprint: {args.fingerprint[:16]}...")
        print(f"  Duration: {args.months} months")
        print(f"  Max Results: {args.max_results}")
        license_key = generate_full_license_key(args.fingerprint, args.months, args.max_results)

    print(f"\n{'='*60}")
    print("LICENSE KEY:")
    print(f"{'='*60}")
    print(license_key)
    print(f"{'='*60}")

    # Test decoding
    if args.test_decode:
        print("\nTesting decode...")
        try:
            decoded = decode_license(license_key)
            print(f"✓ License decoded successfully: {decoded}")
            print(f"  Days remaining: {decoded.days_remaining()}")
            print(f"  Is expired: {decoded.is_expired()}")
        except Exception as e:
            print(f"✗ Decode failed: {e}")
            sys.exit(1)

    # Save to file
    if args.save:
        filepath = save_license_to_file(license_key, args.fingerprint)
        print(f"\n✓ License saved to: {filepath}")

    print("\n" + "=" * 60)
    print("Instructions for user:")
    print("  1. Copy the LICENSE KEY above")
    print("  2. Paste it into the application's license field")
    print("  3. Or save it to a file named 'license.key'")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Interactive mode for testing
        print("=" * 60)
        print("License Key Generator - Interactive Mode")
        print("=" * 60)

        # Example usage
        test_fingerprint = "0578690205f040f6d8a88f43d567915696d395380faec3ad41c1da049a8532d7"

        print("\nExample 1: Trial License")
        trial_key = generate_trial_license_key(test_fingerprint, 14, 100)
        print(f"Key: {trial_key}")
        print(f"Length: {len(trial_key)} characters")

        print("\nExample 2: Full License")
        full_key = generate_full_license_key(test_fingerprint, 12, 5000)
        print(f"Key: {full_key}")
        print(f"Length: {len(full_key)} characters")

        print("\nExample 3: Decode Trial License")
        decoded = decode_license(trial_key)
        print(f"Decoded: {decoded}")
        print(f"Days remaining: {decoded.days_remaining()}")

        print("\n" + "=" * 60)
        print("Run with --help for command-line usage")
        print("=" * 60)
    else:
        main()
