# Licensing guide

Machine-bound, time-limited, offline licensing. No internet, no phone-home, no license server. A license issued for machine A will not validate on machine B.

## How it works

1. **Fingerprint** — [leads_gen/licensing/fingerprint.py](../../leads_gen/licensing/fingerprint.py) hashes MAC + system UUID + hostname into a 64-char SHA-256.
2. **Issuance** — [tools/generate_license.py](../../tools/generate_license.py) (developer-only, holds `SECRET_KEY`) serializes a `LicenseData` dataclass, appends a checksum, XOR-encrypts with `SHA256(SECRET_KEY)`, base64-encodes.
3. **Activation** — the user writes the license key to `leads_gen/license.key`.
4. **Validation** — [leads_gen/licensing/license_manager.py](../../leads_gen/licensing/license_manager.py) decodes on startup, checks fingerprint match + expiry + result limit.

Both the CLI (`main.py`) and the Streamlit UI (`app.py`) enforce the license. The UI additionally surfaces the fingerprint and offers a 3-result Trial-mode button when no license is present.

## User flow

**Get your fingerprint.**
```bash
make fingerprint
```
Or from Streamlit: launch `make ui` — if no license is installed, the sidebar shows the fingerprint with a copy button.

**Send it to the license issuer.** They return a license key (a base64 blob).

**Activate.**
```bash
echo "YOUR_LICENSE_KEY" > leads_gen/license.key
```

**Verify.**
```bash
uv run python -m leads_gen.licensing.license_manager
```
Prints active status, days remaining, and max-results cap. Or launch the UI — the sidebar shows license type, expiry, and days remaining, colour-coded.

## Developer flow: issuing licenses

`tools/generate_license.py` requires a fingerprint, one of `--days` / `--months` / `--expiry-date` (mutually exclusive), and `--max-results`.

```bash
# 30-day trial, 50 max results
uv run python tools/generate_license.py \
  --fingerprint <64-char-hash> --days 30 --max-results 50

# 12-month full license, 5000 max results
uv run python tools/generate_license.py \
  --fingerprint <64-char-hash> --months 12 --max-results 5000

# Explicit expiry date
uv run python tools/generate_license.py \
  --fingerprint <64-char-hash> --expiry-date 2027-06-30 --max-results 1000

# Add --test-decode to verify the key round-trips before sending
```

Send the printed license key to the user. Do **not** ship `tools/generate_license.py` — it holds the shared secret.

## Validation checks (in order)

1. Base64 decode + checksum
2. Fingerprint match against the current machine
3. Expiry date > today
4. Requested `max_results` ≤ license cap

Any failure blocks the run.

## Error messages users will see

| Message | Cause | Fix |
|---|---|---|
| **LICENSE REQUIRED — No license file found** | `leads_gen/license.key` missing | Follow the User flow above |
| **License expired N days ago** | Past expiry date | Renew via the issuer |
| **License is not valid for this machine** | Fingerprint mismatch | New machine → new license needed. VMs can produce unstable fingerprints. |
| **LICENSE LIMIT EXCEEDED** | `--max-results` > license cap | Request higher cap or lower `--max-results` |
| **License Check Failed** (Streamlit sidebar) | Corrupt/tampered `license.key` | Re-save the key |

## Bypass for local development

`main.py` accepts `--no-license` which skips the entire licensing subsystem. Local dev only — do not distribute a binary built with this default.

```bash
uv run python main.py --query "gyms in NYC" --max-results 10 --no-license
```

## Threat model — what's protected, what isn't

**Protected**
- License keys are opaque (encrypted + checksummed) — users can't hand-craft valid keys without `SECRET_KEY`.
- Fingerprints are SHA-256 hashes — raw MAC/hostname is never logged or transmitted.
- License data includes an integrity checksum — bit-flipping produces a hard failure, not silent misuse.
- The `SECRET_KEY` never ships with the app.

**Not protected**
- This is symmetric-crypto security-by-obscurity, not cryptographic strength. A determined attacker with the binary can reverse-engineer the validator.
- License files can be copied between machines but won't validate against a different fingerprint.
- No revocation. Once issued, a license is valid until expiry.

## Files

| Path | Role |
|---|---|
| [leads_gen/licensing/fingerprint.py](../../leads_gen/licensing/fingerprint.py) | Fingerprint generation (SHA-256 of MAC + UUID + hostname) |
| [leads_gen/licensing/license_model.py](../../leads_gen/licensing/license_model.py) | `LicenseData` dataclass + validation |
| [leads_gen/licensing/license_codec.py](../../leads_gen/licensing/license_codec.py) | `encode_license` / `decode_license` (XOR + base64) |
| [leads_gen/licensing/license_manager.py](../../leads_gen/licensing/license_manager.py) | `LicenseManager` — loads, validates, enforces |
| [tools/generate_license.py](../../tools/generate_license.py) | Developer-only issuer — **do not distribute** |
| `leads_gen/license.key` | User's activated license (created at activation) |
