# Licensing System Guide
**Google Maps Lead Generator**  
**Version:** 1.0  
**Date:** February 5, 2026

---

## Overview

The Google Maps Lead Generator implements a **machine-bound, time-limited, offline licensing system** to control application usage. The licensing system is completely offline and does not require internet connectivity.

### Key Features

- ✅ **Machine-Bound**: Licenses are tied to specific hardware fingerprints
- ✅ **Time-Limited**: Licenses have expiration dates
- ✅ **Result Limits**: Configurable maximum results per scraping session
- ✅ **Feature Flags**: Licenses can enable/disable specific features
- ✅ **Offline**: No internet required for validation
- ✅ **Secure**: License keys are encrypted and non-human-readable
- ✅ **Logging**: All license operations are logged for audit trails

---

## Architecture

### Components

1. **Machine Fingerprint (`utils/fingerprint.py`)**
   - Generates unique hardware identifier
   - Uses MAC address + hostname + system UUID
   - SHA-256 hashed (never exposes raw identifiers)

2. **License Data Model (`utils/license_model.py`)**
   - Defines license structure
   - Validation logic
   - Helper functions for trial/full licenses

3. **License Key Generator (`generate_license.py`)**
   - **OFFLINE TOOL** (not bundled with app)
   - Encrypts license data into opaque keys
   - Uses symmetric encryption with secret key
   - Includes integrity checksum

4. **License Manager (`utils/license_manager.py`)**
   - Loads and stores license keys
   - Validates licenses
   - Enforces limits
   - Provides license information

5. **Enforcement Integration**
   - CLI (`main.py`): Blocks execution if invalid license
   - Streamlit UI (`app.py`): Should display license warnings (not yet integrated)

---

## License Issuance Workflow

### Step 1: User Gets Machine Fingerprint

```bash
# User runs this on their machine
python utils/license_manager.py --show-fingerprint
```

**Output:**
```
============================================================
MACHINE FINGERPRINT
============================================================

0578690205f040f6d8a88f43d567915696d395380faec3ad41c1da049a8532d7

============================================================
Send this fingerprint to the developer to get a license key.
============================================================
```

User sends this fingerprint to you (the developer).

### Step 2: Developer Generates License Key

```bash
# For a 30-day trial license with 500 max results
python generate_license.py --fingerprint <user_fingerprint> --days 30 --max-results 500

# For a 12-month full license with 5000 max results
python generate_license.py --fingerprint <user_fingerprint> --months 12 --max-results 5000
```

**Output:**
```
============================================================
LICENSE KEY:
============================================================
FFsECLK+uqDlkGWwpYMzGLJgg3u5mNWae7KBMwqC7vIKGBUFsLK7+4DUf+alzGhR...
============================================================
```

Send this license key to the user.

### Step 3: User Activates License

**Option A: Command line**
```bash
python utils/license_manager.py --save-license "<license_key>"
```

**Option B: Manual file creation**
Create a file named `license.key` in the application directory and paste the license key.

**Option C: UI (Streamlit) - Not yet implemented**
Paste the license key into the activation field in the UI.

### Step 4: Automatic Validation

The application automatically validates the license on startup:
- Checks machine fingerprint match
- Checks expiration date
- Enforces result limits

---

## License Types

### Trial License

```python
# Characteristics:
- Duration: 7-30 days
- Max Results: 50-500 per run
- Features: All enabled
- Purpose: Evaluation
```

**Generate:**
```bash
python generate_license.py \
  --fingerprint <hash> \
  --days 14 \
  --max-results 100
```

### Full License

```python
# Characteristics:
- Duration: 6-12 months (or longer)
- Max Results: 1000-5000+ per run
- Features: All enabled
- Purpose: Production use
```

**Generate:**
```bash
python generate_license.py \
  --fingerprint <hash> \
  --months 12 \
  --max-results 5000
```

---

## License Validation

### Validation Checks

1. **Format Check**: License key must be valid base64
2. **Decryption**: License must decrypt with secret key
3. **Integrity**: Checksum must match
4. **Fingerprint Match**: Machine fingerprint must match license
5. **Expiration**: Current date must be before expiry date
6. **Result Limit**: Requested results must not exceed license limit

### Validation Flow

```
App Start
    ↓
Load license.key
    ↓
Decode & Decrypt
    ↓
Validate Fingerprint ─→ [FAIL] → Block Execution
    ↓
Check Expiration ──────→ [FAIL] → Block Execution
    ↓
Check Result Limit ────→ [FAIL] → Block Execution
    ↓
✓ Allow Execution
```

---

## Command-Line Usage

### For Users

```bash
# Show machine fingerprint
python utils/license_manager.py --show-fingerprint

# Save license key
python utils/license_manager.py --save-license "<key>"

# Test a license key
python utils/license_manager.py --test-license "<key>"

# Check current license status
python utils/license_manager.py
```

### For Developers

```bash
# Generate license interactively
python generate_license.py

# Generate license with parameters
python generate_license.py \
  --fingerprint <hash> \
  --months 12 \
  --max-results 5000 \
  --test-decode

# Save generated license to file
python generate_license.py \
  --fingerprint <hash> \
  --days 30 \
  --max-results 500 \
  --save
```

---

## Integration Points

### CLI Mode (`main.py`)

```python
# Licensing enforcement implemented:
from utils.license_manager import LicenseManager

def main():
    # Initialize license
    license_manager = LicenseManager()
    success, message = license_manager.initialize()
    
    if not success:
        # Block execution, show error
        sys.exit(1)
    
    # Enforce result limits
    can_scrape, msg = license_manager.can_scrape(max_results)
    if not can_scrape:
        sys.exit(1)
    
    # Proceed with scraping...
```

### Streamlit UI (`app.py`) - **TODO**

```python
# To be implemented:
1. Display license status in sidebar
2. Show days remaining warning
3. Add license activation UI
4. Block scraping if invalid license
5. Show appropriate error messages
```

---

## Error Messages

### No License Found

```
LICENSE REQUIRED
================================================================
No license file found. Please activate a license key.

To get a license:
1. Run: python utils/license_manager.py --show-fingerprint
2. Send the fingerprint to the developer
3. Save the license key: python utils/license_manager.py --save-license <key>
================================================================
```

### License Expired

```
LICENSE REQUIRED
================================================================
License expired 5 days ago

To renew your license, contact the developer with your machine fingerprint.
================================================================
```

### Wrong Machine

```
LICENSE REQUIRED
================================================================
License is not valid for this machine

This license was issued for a different machine fingerprint.
================================================================
```

### Result Limit Exceeded

```
LICENSE LIMIT EXCEEDED
================================================================
Requested 1000 results, but license allows maximum 500

Your license allows maximum 500 results per run
================================================================
```

---

## Security Considerations

### What's Protected

✅ License keys are encrypted with secret key  
✅ Machine fingerprints are hashed (SHA-256)  
✅ Raw MAC addresses never exposed or logged  
✅ License data includes integrity checksum  
✅ Secret key not bundled with application  

### Known Limitations

⚠️ This is **security by obscurity**, not cryptographically unbreakable  
⚠️ Determined users can reverse-engineer the validation  
⚠️ Secret key is in `generate_license.py` (keep this file secure!)  
⚠️ No online activation or phone-home capability  
⚠️ License files can be copied between machines (but won't validate)  

### Best Practices

1. **Keep `generate_license.py` secret** - Don't distribute it with the app
2. **Change the SECRET_KEY** - Use a unique, random key
3. **Log all license validations** - Track usage patterns
4. **Issue time-limited licenses** - Forces periodic renewal
5. **Monitor customer usage** - Watch for suspicious patterns

---

## Troubleshooting

### Issue: License validation fails immediately

**Solution:**
1. Check if `license.key` file exists
2. Verify file is not corrupted
3. Check logs for specific error message
4. Try re-saving the license key

### Issue: "License is not valid for this machine"

**Solution:**
1. Get current machine fingerprint: `python utils/license_manager.py --show-fingerprint`
2. Request new license from developer with correct fingerprint
3. Virtual machines may have unstable fingerprints

### Issue: License file not found after saving

**Solution:**
1. Check you're running from the correct directory
2. Verify file permissions
3. Look for `license.key` in application base directory

### Issue: Results limit lower than expected

**Solution:**
1. Check license info: `python utils/license_manager.py`
2. Verify the correct license was activated
3. Request new license with higher limit

---

## Testing

### Test Scenario 1: Generate and Validate License

```bash
# Get fingerprint
python utils/license_manager.py --show-fingerprint

# Generate license (using the fingerprint from above)
python generate_license.py \
  --fingerprint 0578690205f040f6d8a88f43d567915696d395380faec3ad41c1da049a8532d7 \
  --days 30 \
  --max-results 500 \
  --test-decode

# Save and validate
python utils/license_manager.py --save-license "<generated_key>"

# Check status
python utils/license_manager.py
```

### Test Scenario 2: Enforce Result Limits

```bash
# Run with valid limit (should work)
echo -e "test query\n100" | python main.py

# Run exceeding limit (should fail)
# If license allows 500, try 1000:
echo -e "test query\n1000" | python main.py
```

### Test Scenario 3: Wrong Machine

```bash
# Generate license for different fingerprint
python generate_license.py \
  --fingerprint "aaaa..." \
  --days 30 \
  --max-results 500

# Try to use it (should fail)
python utils/license_manager.py --save-license "<wrong_key>"
python main.py
```

---

## File Locations

```
leads_gen/
├── license.key              # User's license (created after activation)
├── generate_license.py      # License generator (OFFLINE TOOL - NOT DISTRIBUTED)
├── utils/
│   ├── fingerprint.py       # Machine fingerprint generation
│   ├── license_model.py     # License data structure
│   └── license_manager.py   # License validation & enforcement
└── logs/
    └── app_*.log            # Contains license validation logs
```

---

## Future Enhancements

### Planned
- [ ] Streamlit UI integration for license activation
- [ ] License expiry warnings (7 days, 1 day before)
- [ ] Grace period after expiration
- [ ] Multiple machine support (floating licenses)

### Not Planned
- ❌ Online activation (stays offline)
- ❌ Phone-home functionality
- ❌ Cloud license server
- ❌ Subscription management

---

## Support

For licensing issues:

1. Check logs in `logs/app_*.log`
2. Run diagnostic: `python utils/license_manager.py`
3. Get machine fingerprint: `python utils/license_manager.py --show-fingerprint`
4. Contact developer with:
   - Machine fingerprint
   - Error message from logs
   - License type (trial/full)

---

## Changelog

### Version 1.0 (2026-02-05)
- Initial licensing system implementation
- Machine fingerprint generation
- License key encoding/decoding
- CLI enforcement
- License manager with validation
- Offline license generation tool

---

**End of Licensing Guide**
