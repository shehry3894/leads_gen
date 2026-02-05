"""
License Manager for Google Maps Lead Generator.

This module handles:
- Loading and storing license keys
- Validating licenses against machine fingerprint
- Checking expiry and limits
- Enforcing licensing rules
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

try:
    from leads_gen.licensing.license_model import LicenseData
    from leads_gen.licensing.fingerprint import generate_machine_fingerprint
    from leads_gen.utils.paths import get_base_dir
except ImportError:
    # For running as standalone script
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from leads_gen.licensing.license_model import LicenseData
    from leads_gen.licensing.fingerprint import generate_machine_fingerprint
    from leads_gen.utils.paths import get_base_dir

logger = logging.getLogger("leads_gen")

# Import the decode function from generate_license
# In production, this would be in a shared module
try:
    from tools.generate_license import decode_license
except ImportError:
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from tools.generate_license import decode_license
    except ImportError:
        logger.warning("Could not import decode_license from generate_license module")
        decode_license = None


class LicenseManager:
    """
    Manages license validation and storage for the application.
    """
    
    def __init__(self, license_file: str = "license.key"):
        """
        Initialize the license manager.
        
        Args:
            license_file: Name of the license key file
        """
        self.license_file = license_file
        self.license_data: Optional[LicenseData] = None
        self.license_key: Optional[str] = None
        self.machine_fingerprint = generate_machine_fingerprint()
        
        logger.info(f"License Manager initialized")
        logger.info(f"Machine fingerprint: {self.machine_fingerprint}")
    
    def get_license_path(self) -> Path:
        """Get the path to the license file."""
        app_dir = get_base_dir()
        return app_dir / self.license_file
    
    def load_license_from_file(self) -> bool:
        """
        Load license key from file.
        
        Returns:
            True if license file exists and was loaded, False otherwise
        """
        license_path = self.get_license_path()
        
        if not license_path.exists():
            logger.warning(f"License file not found: {license_path}")
            return False
        
        try:
            with open(license_path, 'r') as f:
                self.license_key = f.read().strip()
            
            logger.info(f"License key loaded from {license_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to read license file: {e}")
            return False
    
    def load_license_from_string(self, license_key: str) -> bool:
        """
        Load license key from a string.
        
        Args:
            license_key: License key string
        
        Returns:
            True if license key was set, False if empty
        """
        if not license_key or not license_key.strip():
            logger.warning("Empty license key provided")
            return False
        
        self.license_key = license_key.strip()
        logger.info("License key loaded from string")
        return True
    
    def save_license_to_file(self, license_key: Optional[str] = None) -> bool:
        """
        Save license key to file.
        
        Args:
            license_key: License key to save (uses self.license_key if not provided)
        
        Returns:
            True if saved successfully, False otherwise
        """
        key_to_save = license_key or self.license_key
        
        if not key_to_save:
            logger.error("No license key to save")
            return False
        
        try:
            license_path = self.get_license_path()
            license_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(license_path, 'w') as f:
                f.write(key_to_save)
            
            logger.info(f"License key saved to {license_path}")
            self.license_key = key_to_save
            return True
        except Exception as e:
            logger.error(f"Failed to save license file: {e}")
            return False
    
    def validate_license(self) -> Tuple[bool, str]:
        """
        Validate the current license key.
        
        Returns:
            Tuple of (is_valid, error_message)
            - (True, "") if license is valid
            - (False, reason) if license is invalid
        """
        if not self.license_key:
            return False, "No license key provided"
        
        if decode_license is None:
            return False, "License validation not available (decode_license not imported)"
        
        # Decode the license key
        try:
            self.license_data = decode_license(self.license_key)
            logger.info(f"License decoded successfully: {self.license_data}")
        except Exception as e:
            logger.error(f"Failed to decode license: {e}")
            return False, f"Invalid license key: {str(e)}"
        
        # Check fingerprint match
        if not self.license_data.matches_fingerprint(self.machine_fingerprint):
            logger.error("License fingerprint does not match machine")
            logger.error(f"Expected: {self.license_data.fingerprint[:16]}...")
            logger.error(f"Got:      {self.machine_fingerprint[:16]}...")
            return False, "License is not valid for this machine"
        
        # Check expiry
        if self.license_data.is_expired():
            days_expired = abs(self.license_data.days_remaining())
            logger.error(f"License expired {days_expired} days ago")
            return False, f"License expired {days_expired} days ago"
        
        # All checks passed
        days_remaining = self.license_data.days_remaining()
        logger.info(f"✓ License is valid ({days_remaining} days remaining)")
        return True, ""
    
    def get_max_results(self) -> int:
        """
        Get the maximum results allowed by the license.
        
        Returns:
            Maximum results per run, or 0 if no valid license
        """
        if not self.license_data:
            return 0
        
        return self.license_data.max_results_per_run
    
    def can_scrape(self, requested_results: int) -> Tuple[bool, str]:
        """
        Check if scraping is allowed with the requested number of results.
        
        Args:
            requested_results: Number of results user wants to scrape
        
        Returns:
            Tuple of (allowed, message)
        """
        if not self.license_data:
            return False, "No valid license. Please activate a license key."
        
        max_allowed = self.license_data.max_results_per_run
        
        if requested_results > max_allowed:
            return False, f"Requested {requested_results} results, but license allows maximum {max_allowed}"
        
        return True, f"Allowed: {requested_results} results (max: {max_allowed})"
    
    def get_license_info(self) -> dict:
        """
        Get license information for display.
        
        Returns:
            Dictionary with license information
        """
        if not self.license_data:
            return {
                'valid': False,
                'status': 'No license',
                'message': 'No valid license key found'
            }
        
        is_trial = self.license_data.features.get('trial', False)
        days_remaining = self.license_data.days_remaining()
        
        return {
            'valid': True,
            'type': 'Trial' if is_trial else 'Full',
            'expiry_date': self.license_data.expiry_date,
            'days_remaining': days_remaining,
            'max_results': self.license_data.max_results_per_run,
            'features': self.license_data.features,
            'machine_fingerprint': self.machine_fingerprint[:16] + "...",
            'status': 'Active' if days_remaining > 0 else 'Expired'
        }
    
    def initialize(self) -> Tuple[bool, str]:
        """
        Initialize and validate license.
        
        This method should be called at app startup.
        It tries to load a license from file and validates it.
        
        Returns:
            Tuple of (success, message)
        """
        logger.info("Initializing license system...")
        
        # Try to load from file
        if self.load_license_from_file():
            is_valid, error = self.validate_license()
            if is_valid:
                info = self.get_license_info()
                return True, f"License active: {info['type']} ({info['days_remaining']} days remaining)"
            else:
                return False, error
        else:
            return False, "No license file found. Please activate a license key."


def get_machine_fingerprint_for_licensing() -> str:
    """
    Utility function to get machine fingerprint for sharing with developer.
    
    Returns:
        Machine fingerprint string
    """
    fingerprint = generate_machine_fingerprint()
    logger.info(f"Machine fingerprint for licensing: {fingerprint}")
    return fingerprint


if __name__ == '__main__':
    """Test the license manager."""
    import argparse
    
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
    
    parser = argparse.ArgumentParser(description="License Manager Test")
    parser.add_argument('--show-fingerprint', action='store_true', help='Show machine fingerprint')
    parser.add_argument('--test-license', type=str, help='Test a license key')
    parser.add_argument('--save-license', type=str, help='Save a license key to file')
    
    args = parser.parse_args()
    
    if args.show_fingerprint:
        print("=" * 60)
        print("MACHINE FINGERPRINT")
        print("=" * 60)
        fingerprint = get_machine_fingerprint_for_licensing()
        print(f"\n{fingerprint}\n")
        print("=" * 60)
        print("Send this fingerprint to the developer to get a license key.")
        print("=" * 60)
    
    elif args.test_license:
        print("=" * 60)
        print("Testing License Key")
        print("=" * 60)
        
        manager = LicenseManager()
        manager.load_license_from_string(args.test_license)
        is_valid, message = manager.validate_license()
        
        if is_valid:
            print(f"\n✓ License is VALID\n")
            info = manager.get_license_info()
            for key, value in info.items():
                print(f"  {key}: {value}")
        else:
            print(f"\n✗ License is INVALID\n")
            print(f"  Reason: {message}")
        
        print("=" * 60)
    
    elif args.save_license:
        print("=" * 60)
        print("Saving License Key")
        print("=" * 60)
        
        manager = LicenseManager()
        if manager.save_license_to_file(args.save_license):
            print(f"\n✓ License saved to: {manager.get_license_path()}\n")
            
            # Test loading and validation
            manager2 = LicenseManager()
            success, message = manager2.initialize()
            print(f"Validation: {message}")
        else:
            print(f"\n✗ Failed to save license\n")
        
        print("=" * 60)
    
    else:
        # Default: Initialize and show status
        print("=" * 60)
        print("License Manager Status")
        print("=" * 60)
        
        manager = LicenseManager()
        success, message = manager.initialize()
        
        print(f"\nStatus: {message}\n")
        
        if success:
            info = manager.get_license_info()
            print("License Details:")
            for key, value in info.items():
                print(f"  {key}: {value}")
        
        print("\n" + "=" * 60)
        print("Run with --help for more options")
        print("=" * 60)
