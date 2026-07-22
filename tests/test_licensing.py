"""
Licensing subsystem: fingerprint, model, codec, manager.

These tests exercise the offline license flow end-to-end without touching
the real ``leads_gen/license.key`` on disk.
"""

from __future__ import annotations

import pytest

from leads_gen.licensing.fingerprint import generate_machine_fingerprint
from leads_gen.licensing.license_codec import decode_license, encode_license
from leads_gen.licensing.license_manager import LicenseManager
from leads_gen.licensing.license_model import (
    LicenseData,
    create_full_license,
    create_trial_license,
)

# ---------------------------------------------------------------------------
# fingerprint.py
# ---------------------------------------------------------------------------


class TestFingerprint:
    def test_is_64_char_hex(self):
        fp = generate_machine_fingerprint()
        assert len(fp) == 64
        int(fp, 16)  # raises if non-hex

    def test_stable_across_calls(self):
        assert generate_machine_fingerprint() == generate_machine_fingerprint()


# ---------------------------------------------------------------------------
# license_model.py
# ---------------------------------------------------------------------------


class TestLicenseDataValidation:
    def test_rejects_short_fingerprint(self, machine_fingerprint):
        with pytest.raises(ValueError):
            LicenseData(fingerprint="deadbeef", expiry_date="2099-01-01", max_results_per_run=10)

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

    def test_matches_fingerprint(self, machine_fingerprint):
        lic = create_trial_license(machine_fingerprint, days=1, max_results=1)
        assert lic.matches_fingerprint(machine_fingerprint)
        assert not lic.matches_fingerprint("f" * 64)

    def test_features_default_flags(self, machine_fingerprint):
        trial = create_trial_license(machine_fingerprint, 1, 1)
        assert trial.features["trial"] is True
        full = create_full_license(machine_fingerprint, 1, 1)
        assert full.features["trial"] is False


# ---------------------------------------------------------------------------
# license_codec.py
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

    def test_wrong_machine_rejected(self, isolated_license_key):
        wrong = create_trial_license("f" * 64, days=7, max_results=10)
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
