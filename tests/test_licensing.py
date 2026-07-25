"""
Licensing subsystem: fingerprint, model, codec, manager.

These tests exercise the offline license flow end-to-end without
touching the real ``leads_gen/license.key`` on disk. Coverage focuses on
the parts a wrong change would break silently:

  - Fingerprint format (must be a canonical hardware UUID).
  - Fingerprint normalization on the license side (any UUID form that
    ``uuid.UUID`` accepts must round-trip and match).
  - License-file opacity (the on-disk blob must never contain plaintext
    fields — that's the whole point of the XOR + base64 layer).
  - Tamper resistance (flipping bytes must fail decode).
  - Manager edge cases (uninitialized state, expired vs wrong-machine
    error distinction, re-issue cycles).
"""

from __future__ import annotations

import uuid

import pytest

from leads_gen.licensing.fingerprint import generate_machine_fingerprint
from leads_gen.licensing.license_codec import decode_license, encode_license
from leads_gen.licensing.license_manager import LicenseManager
from leads_gen.licensing.license_model import (
    LicenseData,
    create_full_license,
    create_license_from_days,
    create_trial_license,
)

# ---------------------------------------------------------------------------
# fingerprint.py — real hardware UUID
# ---------------------------------------------------------------------------


class TestFingerprint:
    def test_returns_canonical_uuid(self):
        fp = generate_machine_fingerprint()
        # Must be parseable as a UUID
        parsed = uuid.UUID(fp)
        # And must be in canonical UPPERCASE hyphenated form
        assert fp == str(parsed).upper()

    def test_is_36_chars_with_hyphens(self):
        fp = generate_machine_fingerprint()
        assert len(fp) == 36
        assert fp[8] == "-"
        assert fp[13] == "-"
        assert fp[18] == "-"
        assert fp[23] == "-"

    def test_all_chars_are_uppercase_hex_or_hyphen(self):
        fp = generate_machine_fingerprint()
        for c in fp:
            assert c in "0123456789ABCDEF-", f"non-canonical char {c!r}"

    def test_stable_across_calls(self):
        assert generate_machine_fingerprint() == generate_machine_fingerprint()


# ---------------------------------------------------------------------------
# license_model.py — validation & normalization
# ---------------------------------------------------------------------------


class TestLicenseDataFingerprintFormats:
    """Whatever the caller passes for a fingerprint, LicenseData must
    normalize it to the canonical UPPERCASE hyphenated form so that
    string comparisons downstream work regardless of input style."""

    def test_accepts_uppercase_hyphenated(self):
        lic = LicenseData(
            fingerprint="5172A6D1-D8D1-525D-B275-C891BB687412",
            expiry_date="2099-01-01",
            max_results_per_run=10,
        )
        assert lic.fingerprint == "5172A6D1-D8D1-525D-B275-C891BB687412"

    def test_accepts_lowercase_hyphenated_and_normalizes(self):
        lic = LicenseData(
            fingerprint="5172a6d1-d8d1-525d-b275-c891bb687412",
            expiry_date="2099-01-01",
            max_results_per_run=10,
        )
        assert lic.fingerprint == "5172A6D1-D8D1-525D-B275-C891BB687412"

    def test_accepts_no_hyphens_and_normalizes(self):
        lic = LicenseData(
            fingerprint="5172A6D1D8D1525DB275C891BB687412",
            expiry_date="2099-01-01",
            max_results_per_run=10,
        )
        assert lic.fingerprint == "5172A6D1-D8D1-525D-B275-C891BB687412"

    def test_accepts_mixed_case(self):
        lic = LicenseData(
            fingerprint="5172a6D1-d8d1-525D-b275-c891bb687412",
            expiry_date="2099-01-01",
            max_results_per_run=10,
        )
        assert lic.fingerprint == "5172A6D1-D8D1-525D-B275-C891BB687412"

    def test_rejects_random_string(self):
        with pytest.raises(ValueError, match="valid UUID"):
            LicenseData(
                fingerprint="not-a-uuid-at-all",
                expiry_date="2099-01-01",
                max_results_per_run=10,
            )

    def test_rejects_old_64_hex_hash(self):
        # 64 hex chars is not a valid UUID (UUID is 32 hex).
        with pytest.raises(ValueError):
            LicenseData(
                fingerprint="a" * 64,
                expiry_date="2099-01-01",
                max_results_per_run=10,
            )

    def test_rejects_short_hex(self):
        with pytest.raises(ValueError):
            LicenseData(
                fingerprint="deadbeef",
                expiry_date="2099-01-01",
                max_results_per_run=10,
            )

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            LicenseData(
                fingerprint="",
                expiry_date="2099-01-01",
                max_results_per_run=10,
            )


class TestLicenseDataValidation:
    def test_rejects_zero_max_results(self, machine_fingerprint):
        with pytest.raises(ValueError):
            LicenseData(
                fingerprint=machine_fingerprint, expiry_date="2099-01-01", max_results_per_run=0
            )

    def test_rejects_negative_max_results(self, machine_fingerprint):
        with pytest.raises(ValueError):
            LicenseData(
                fingerprint=machine_fingerprint, expiry_date="2099-01-01", max_results_per_run=-1
            )

    def test_rejects_expiry_before_issued(self, machine_fingerprint):
        with pytest.raises(ValueError):
            LicenseData(
                fingerprint=machine_fingerprint,
                issued_date="2020-06-01",
                expiry_date="2020-01-01",
                max_results_per_run=10,
            )

    def test_rejects_malformed_date(self, machine_fingerprint):
        with pytest.raises(ValueError):
            LicenseData(
                fingerprint=machine_fingerprint, expiry_date="not-a-date", max_results_per_run=10
            )


class TestLicenseDataBehavior:
    def test_is_expired_true_for_past(self, machine_fingerprint):
        past = LicenseData(
            fingerprint=machine_fingerprint,
            issued_date="2020-01-01",
            expiry_date="2020-06-01",
            max_results_per_run=10,
        )
        assert past.is_expired()
        assert past.days_remaining() < 0

    def test_is_expired_false_for_future(self, machine_fingerprint):
        future = create_trial_license(machine_fingerprint, days=7, max_results=10)
        assert not future.is_expired()
        assert 6 <= future.days_remaining() <= 7

    def test_matches_fingerprint(self, machine_fingerprint, wrong_fingerprint):
        lic = create_trial_license(machine_fingerprint, days=1, max_results=1)
        assert lic.matches_fingerprint(machine_fingerprint)
        assert not lic.matches_fingerprint(wrong_fingerprint)

    def test_matches_fingerprint_is_normalized(self, machine_fingerprint):
        """Callers passing UUID in lowercase / no-hyphens / mixed case
        must still compare equal to the canonical stored form."""
        lic = create_trial_license(machine_fingerprint, days=1, max_results=1)
        assert lic.matches_fingerprint(machine_fingerprint.lower())
        assert lic.matches_fingerprint(machine_fingerprint.replace("-", ""))
        assert lic.matches_fingerprint(machine_fingerprint.lower().replace("-", ""))

    def test_matches_fingerprint_rejects_garbage_input(self, machine_fingerprint):
        """Garbage input must return False, not raise."""
        lic = create_trial_license(machine_fingerprint, days=1, max_results=1)
        assert not lic.matches_fingerprint("not-a-uuid")
        assert not lic.matches_fingerprint("")
        assert not lic.matches_fingerprint("00000000-0000-0000-0000-000000000000")

    def test_features_default_flags(self, machine_fingerprint):
        trial = create_trial_license(machine_fingerprint, 1, 1)
        assert trial.features["trial"] is True
        full = create_full_license(machine_fingerprint, 1, 1)
        assert full.features["trial"] is False


# ---------------------------------------------------------------------------
# license_codec.py — encode/decode, opacity, tamper resistance
# ---------------------------------------------------------------------------


class TestCodec:
    def test_round_trip_preserves_fields(self, machine_fingerprint):
        original = create_trial_license(machine_fingerprint, days=14, max_results=42)
        key = encode_license(original)
        decoded = decode_license(key)

        assert decoded.fingerprint == original.fingerprint
        assert decoded.expiry_date == original.expiry_date
        assert decoded.max_results_per_run == 42
        assert decoded.features == original.features

    def test_full_license_round_trip(self, machine_fingerprint):
        full = create_full_license(machine_fingerprint, months=12, max_results=5000)
        decoded = decode_license(encode_license(full))
        assert decoded.max_results_per_run == 5000
        assert decoded.features["trial"] is False

    def test_uuid_survives_round_trip(self, machine_fingerprint):
        """Round-trip must preserve the canonical UUID form byte-for-byte."""
        lic = create_trial_license(machine_fingerprint, days=1, max_results=1)
        decoded = decode_license(encode_license(lic))
        assert decoded.fingerprint == machine_fingerprint
        assert len(decoded.fingerprint) == 36

    def test_tampered_key_raises(self, machine_fingerprint):
        key = encode_license(create_trial_license(machine_fingerprint, 1, 1))
        tampered = key[:-4] + "AAAA"
        with pytest.raises(ValueError):
            decode_license(tampered)

    def test_garbage_key_raises(self):
        with pytest.raises(ValueError):
            decode_license("this-is-not-a-license")

    def test_empty_key_raises(self):
        with pytest.raises(ValueError):
            decode_license("")


class TestLicenseFileOpacity:
    """The .key file the customer sees on disk must not expose any field
    as plaintext. This is the whole point of the XOR + base64 layer —
    verifying it prevents regressions where someone accidentally logs or
    stores raw JSON."""

    def test_no_plaintext_uuid(self, machine_fingerprint):
        lic = create_full_license(machine_fingerprint, months=12, max_results=500)
        key = encode_license(lic)
        assert machine_fingerprint not in key
        # Also try lowercase / no-hyphen variants (nothing should match).
        assert machine_fingerprint.lower() not in key
        assert machine_fingerprint.replace("-", "") not in key

    def test_no_plaintext_field_names(self, machine_fingerprint):
        lic = create_full_license(machine_fingerprint, months=12, max_results=500)
        key = encode_license(lic)
        for field in ("fingerprint", "expiry_date", "max_results", "features", "leads_gen"):
            assert field not in key, f"plaintext field leaked into key: {field!r}"

    def test_no_plaintext_expiry(self, machine_fingerprint):
        # Use a far-future date the encoding shouldn't happen to contain by chance.
        lic = LicenseData(
            fingerprint=machine_fingerprint,
            expiry_date="2087-04-19",
            max_results_per_run=123456789,
        )
        key = encode_license(lic)
        assert "2087-04-19" not in key
        assert "123456789" not in key


# ---------------------------------------------------------------------------
# license_manager.py
# ---------------------------------------------------------------------------


class TestLicenseManager:
    def test_no_license_file(self, isolated_license_key):
        # tmp key file does not exist yet
        mgr = LicenseManager()
        ok, msg = mgr.initialize()
        assert not ok
        assert "No license file found" in msg

    def test_wrong_machine_rejected(self, isolated_license_key, wrong_fingerprint):
        wrong = create_trial_license(wrong_fingerprint, days=7, max_results=10)
        isolated_license_key.write_text(encode_license(wrong))

        mgr = LicenseManager()
        ok, msg = mgr.initialize()
        assert not ok
        assert "not valid for this machine" in msg

    def test_valid_license_accepted(self, isolated_license_key, machine_fingerprint):
        lic = create_trial_license(machine_fingerprint, days=7, max_results=25)
        isolated_license_key.write_text(encode_license(lic))

        mgr = LicenseManager()
        ok, msg = mgr.initialize()
        assert ok, msg
        info = mgr.get_license_info()
        assert info["valid"] is True
        assert info["type"] == "Trial"
        assert info["status"] == "Active"
        assert info["max_results"] == 25

    def test_expired_license_rejected(self, isolated_license_key, machine_fingerprint):
        expired = LicenseData(
            fingerprint=machine_fingerprint,
            issued_date="2020-01-01",
            expiry_date="2020-06-01",
            max_results_per_run=10,
        )
        isolated_license_key.write_text(encode_license(expired))

        mgr = LicenseManager()
        ok, msg = mgr.initialize()
        assert not ok
        assert "expired" in msg.lower()

    def test_expired_license_reports_expired_not_wrong_machine(
        self, isolated_license_key, machine_fingerprint
    ):
        """An expired-but-otherwise-valid license (fingerprint matches this
        machine) must report 'expired', not 'wrong machine'. Regression
        guard: past bug had the manager checking expiry before fingerprint
        and reporting the wrong error."""
        expired = LicenseData(
            fingerprint=machine_fingerprint,
            issued_date="2020-01-01",
            expiry_date="2020-06-01",
            max_results_per_run=10,
        )
        isolated_license_key.write_text(encode_license(expired))
        mgr = LicenseManager()
        ok, msg = mgr.initialize()
        assert not ok
        assert "expired" in msg.lower()
        assert "not valid for this machine" not in msg

    def test_garbage_license_file_rejected(self, isolated_license_key):
        isolated_license_key.write_text("GARBAGE_NOT_A_VALID_LICENSE_KEY")

        mgr = LicenseManager()
        ok, msg = mgr.initialize()
        assert not ok
        assert "invalid license" in msg.lower()

    def test_can_scrape_within_limit(self, isolated_license_key, machine_fingerprint):
        lic = create_trial_license(machine_fingerprint, days=7, max_results=25)
        isolated_license_key.write_text(encode_license(lic))
        mgr = LicenseManager()
        mgr.initialize()
        ok, msg = mgr.can_scrape(10)
        assert ok, msg

    def test_can_scrape_over_limit(self, isolated_license_key, machine_fingerprint):
        lic = create_trial_license(machine_fingerprint, days=7, max_results=5)
        isolated_license_key.write_text(encode_license(lic))
        mgr = LicenseManager()
        mgr.initialize()
        ok, msg = mgr.can_scrape(999)
        assert not ok
        assert "999" in msg and "5" in msg

    def test_can_scrape_at_exact_limit(self, isolated_license_key, machine_fingerprint):
        lic = create_trial_license(machine_fingerprint, days=7, max_results=5)
        isolated_license_key.write_text(encode_license(lic))
        mgr = LicenseManager()
        mgr.initialize()
        ok, _ = mgr.can_scrape(5)
        assert ok

    def test_load_license_from_string(self, machine_fingerprint):
        # Doesn't touch disk at all
        lic = create_trial_license(machine_fingerprint, days=1, max_results=1)
        mgr = LicenseManager()
        assert mgr.load_license_from_string(encode_license(lic))
        ok, msg = mgr.validate_license()
        assert ok, msg

    def test_load_license_from_string_rejects_empty(self):
        mgr = LicenseManager()
        assert not mgr.load_license_from_string("")
        assert not mgr.load_license_from_string("   ")


class TestLicenseManagerUninitialized:
    """State before any license has been loaded/validated. These paths
    are hit by the Streamlit UI on first launch, so getting them wrong
    would break the sidebar rendering."""

    def test_get_license_info_before_load(self):
        mgr = LicenseManager()
        info = mgr.get_license_info()
        assert info["valid"] is False
        assert info["status"] == "No license"

    def test_get_max_results_before_load(self):
        mgr = LicenseManager()
        assert mgr.get_max_results() == 0

    def test_can_scrape_before_load(self):
        mgr = LicenseManager()
        ok, msg = mgr.can_scrape(5)
        assert not ok
        assert "license" in msg.lower()

    def test_validate_without_key(self):
        mgr = LicenseManager()
        ok, _ = mgr.validate_license()
        assert not ok


class TestLicenseReissueCycle:
    """Simulate a customer being reissued a new license: overwrite the
    key file with a new blob and re-init. This catches state bleeding
    between LicenseManager instances."""

    def test_three_reissue_cycles(self, isolated_license_key, machine_fingerprint):
        for cycle in range(3):
            lic = create_trial_license(machine_fingerprint, days=1, max_results=5 + cycle)
            isolated_license_key.write_text(encode_license(lic))
            mgr = LicenseManager()
            ok, msg = mgr.initialize()
            assert ok, f"cycle {cycle}: {msg}"
            assert mgr.get_license_info()["max_results"] == 5 + cycle

    def test_upgrade_trial_to_full(self, isolated_license_key, machine_fingerprint):
        # Customer starts on trial
        trial = create_trial_license(machine_fingerprint, days=1, max_results=3)
        isolated_license_key.write_text(encode_license(trial))
        mgr1 = LicenseManager()
        mgr1.initialize()
        assert mgr1.get_license_info()["type"] == "Trial"

        # Then upgrades to full
        full = create_full_license(machine_fingerprint, months=12, max_results=1000)
        isolated_license_key.write_text(encode_license(full))
        mgr2 = LicenseManager()
        mgr2.initialize()
        info = mgr2.get_license_info()
        assert info["type"] == "Full"
        assert info["max_results"] == 1000


class TestLicenseClassificationByDuration:
    """create_license_from_days: <=30 days = Trial, >30 = Full."""

    def test_thirty_days_is_trial(self, machine_fingerprint):
        lic = create_license_from_days(machine_fingerprint, total_days=30, max_results=10)
        assert lic.features["trial"] is True

    def test_thirty_one_days_is_full(self, machine_fingerprint):
        lic = create_license_from_days(machine_fingerprint, total_days=31, max_results=10)
        assert lic.features["trial"] is False

    def test_one_year_is_full(self, machine_fingerprint):
        lic = create_license_from_days(machine_fingerprint, total_days=365, max_results=10)
        assert lic.features["trial"] is False
