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
import uuid
from pathlib import Path

# Add parent directory to path to import the leads_gen package when this
# tool is run standalone.
sys.path.insert(0, str(Path(__file__).parent.parent))

from leads_gen.licensing.license_codec import decode_license, encode_license
from leads_gen.licensing.license_model import create_full_license, create_trial_license

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def validate_fingerprint(fingerprint: str) -> bool:
    """Validate that fingerprint is a valid UUID (in any accepted form)."""
    try:
        uuid.UUID(fingerprint)
    except (ValueError, AttributeError, TypeError):
        return False
    return True


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

    # Create filename from fingerprint prefix (strip hyphens for a
    # filesystem-friendly slice).
    filename = f"license_{fingerprint.replace('-', '')[:16]}.txt"
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
  python generate_license.py --fingerprint 5172A6D1-D8D1-525D-B275-C891BB687412 --days 7 --max-results 50

  # Generate 12-month full license
  python generate_license.py --fingerprint 5172A6D1-D8D1-525D-B275-C891BB687412 --months 12 --max-results 5000

  # Generate license with specific expiry date (recommended)
  python generate_license.py --fingerprint 5172A6D1-D8D1-525D-B275-C891BB687412 --expiry-date 2026-12-31 --max-results 1000

  # Generate license and save to file
  python generate_license.py --fingerprint 5172A6D1-D8D1-525D-B275-C891BB687412 --expiry-date 2027-06-30 --max-results 1000 --save
        """,
    )

    parser.add_argument(
        "--fingerprint",
        required=True,
        help="Machine fingerprint — the customer's hardware UUID "
        "(e.g. '5172A6D1-D8D1-525D-B275-C891BB687412'). Accepts any "
        "case / with or without hyphens; normalized internally.",
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
        logger.error(
            "Invalid fingerprint format. Must be a valid UUID "
            "(e.g. '5172A6D1-D8D1-525D-B275-C891BB687412')."
        )
        sys.exit(1)

    # Validate max results
    if args.max_results <= 0:
        logger.error("max-results must be greater than 0")
        sys.exit(1)

    # Generate license key
    print("=" * 60)
    print("License Key Generator")
    print("=" * 60)

    # Normalise all three input modes (--days, --months, --expiry-date) to a
    # single day count, then classify TRIAL vs FULL by duration inside
    # `create_license_from_days`. Old behaviour classified by which flag was
    # used, so `--days 365` was labelled Trial and `--months 1` was labelled
    # Full — misleading for the customer's sidebar display.
    from datetime import datetime

    if args.expiry_date:
        try:
            expiry_date = datetime.strptime(args.expiry_date, "%Y-%m-%d").date()
        except ValueError as e:
            logger.error(f"Invalid date format. Use YYYY-MM-DD (e.g., 2026-12-31). Error: {e}")
            sys.exit(1)
        today = datetime.now().date()
        if expiry_date <= today:
            logger.error(f"Expiry date must be in the future. Given: {expiry_date}, Today: {today}")
            sys.exit(1)
        total_days = (expiry_date - today).days
        duration_summary = f"{total_days} days (until {expiry_date})"
    elif args.days:
        total_days = args.days
        duration_summary = f"{args.days} days"
    else:
        # `create_full_license` uses months*30, and we keep that convention
        # here so --months output is byte-identical to the historic behaviour.
        total_days = args.months * 30
        duration_summary = f"{args.months} months (~{total_days} days)"

    from leads_gen.licensing.license_codec import encode_license
    from leads_gen.licensing.license_model import (
        TRIAL_LICENSE_DAY_CUTOFF,
        create_license_from_days,
    )

    license_label = "TRIAL" if total_days <= TRIAL_LICENSE_DAY_CUTOFF else "FULL"
    print(f"\nGenerating {license_label} license:")
    print(f"  Fingerprint: {args.fingerprint[:16]}...")
    print(f"  Duration: {duration_summary}")
    print(f"  Max Results: {args.max_results}")

    license_data = create_license_from_days(args.fingerprint, total_days, args.max_results)
    license_key = encode_license(license_data)

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
        test_fingerprint = "5172A6D1-D8D1-525D-B275-C891BB687412"

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
