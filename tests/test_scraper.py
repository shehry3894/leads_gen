"""
Live end-to-end scraper test — needs a real Chrome + internet.

Skipped by default (marked ``live``). Run explicitly with:

    uv run pytest -m live
    # or
    make test-live

Uses ``--no-license`` so it works on any machine without a valid key.
The TRIAL flag in settings caps scroll to 3 results regardless.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

TEST_QUERY = "gyms in New York"
MAX_RESULTS = "3"


@pytest.mark.live
def test_scrape_end_to_end():
    result = subprocess.run(
        [
            sys.executable,
            "main.py",
            "--query",
            TEST_QUERY,
            "--max-results",
            MAX_RESULTS,
            "--no-license",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )

    # Log output on failure so the diagnostic is right there.
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)

    assert result.returncode == 0, f"scraper exited {result.returncode}"

    # A successful run must have written the Excel file for this query.
    expected = PROJECT_ROOT / "leads_gen" / "output" / (TEST_QUERY.replace(" ", "_") + ".xlsx")
    assert expected.exists(), f"Expected output file {expected} not found"
