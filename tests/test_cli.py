"""
CLI-surface behavior of main.py — argument parsing and licensing gate.

We use subprocess so we get the real argparse + sys.exit code paths.
None of these tests launch a browser; the licensing gate rejects the
run before Selenium is ever invoked.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from leads_gen.licensing.license_codec import encode_license
from leads_gen.licensing.license_model import create_trial_license

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _run(args, timeout=30):
    return subprocess.run(
        [sys.executable, "main.py", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class TestArgparseSurface:
    def test_version_flag(self):
        result = _run(["--version"])
        assert result.returncode == 0
        assert "Google Maps Lead Generator" in result.stdout
        assert "1.0.0" in result.stdout

    def test_help_flag(self):
        result = _run(["--help"])
        assert result.returncode == 0
        assert "--query" in result.stdout
        assert "--max-results" in result.stdout
        assert "--no-license" in result.stdout

    def test_unknown_flag_exit_2(self):
        result = _run(["--totally-unknown-flag"])
        assert result.returncode == 2
        assert "unrecognized arguments" in result.stderr

    def test_invalid_max_results_exit_1(self):
        result = _run(["--query", "x", "--max-results", "banana", "--no-license"])
        assert result.returncode == 1
        assert "must be a number or 'all'" in result.stdout


class TestLicenseGate:
    def test_no_license_file_rejected(self, real_license_key_file):
        if real_license_key_file.exists():
            real_license_key_file.unlink()

        result = _run(["--query", "x", "--max-results", "3"])
        assert result.returncode == 1
        assert "LICENSE REQUIRED" in result.stdout
        assert "No license file found" in result.stdout

    def test_garbage_license_rejected(self, real_license_key_file):
        real_license_key_file.write_text("GARBAGE_NOT_A_VALID_KEY_$$$$$$$$$$$$")

        result = _run(["--query", "x", "--max-results", "3"])
        assert result.returncode == 1
        assert "LICENSE REQUIRED" in result.stdout
        assert "Invalid license" in result.stdout

    def test_wrong_machine_license_rejected(self, real_license_key_file, wrong_fingerprint):
        wrong = create_trial_license(wrong_fingerprint, days=7, max_results=10)
        real_license_key_file.write_text(encode_license(wrong))

        result = _run(["--query", "x", "--max-results", "3"])
        assert result.returncode == 1
        assert "not valid for this machine" in result.stdout

    def test_over_limit_rejected_with_valid_license(
        self, real_license_key_file, machine_fingerprint
    ):
        lic = create_trial_license(machine_fingerprint, days=7, max_results=5)
        real_license_key_file.write_text(encode_license(lic))

        result = _run(["--query", "x", "--max-results", "999"])
        assert result.returncode == 1
        assert "LICENSE LIMIT EXCEEDED" in result.stdout
        assert "999" in result.stdout
        assert "5" in result.stdout

    def test_no_license_flag_bypasses_gate(self, real_license_key_file, tmp_path):
        # We can't actually run the browser here, but --no-license should
        # get us past the licensing gate. The invalid-max-results test
        # already proves the parse+bypass path works end-to-end without
        # a browser; here we just check the warning appears.
        result = _run(["--query", "x", "--max-results", "banana", "--no-license"])
        assert "Running without license validation" in result.stdout
