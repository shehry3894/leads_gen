"""
End-to-end pipeline test using main.main() with TESTING=True.

Setting TESTING=True in settings.py causes main.main() to skip Selenium
entirely and use ``get_demo_leads()`` as the "scraped" data. That lets
us exercise argparse → licensing bypass → normalize → dedupe → Excel
write in a single fast test, no browser required.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import openpyxl
import pytest


@pytest.fixture
def testing_mode(monkeypatch):
    """Flip TESTING=True and reload main so its module-level import picks
    up the new value."""
    import leads_gen.config.settings as s

    monkeypatch.setattr(s, "TESTING", True)
    # main.py binds TESTING at import time, so wipe it and reimport.
    monkeypatch.delitem(sys.modules, "main", raising=False)
    yield
    monkeypatch.delitem(sys.modules, "main", raising=False)


class TestFullPipelineTestingMode:
    def test_end_to_end_produces_canonical_xlsx(self, testing_mode, tmp_output_dir, monkeypatch):
        # Point main.py at the tmp output dir for this run.
        from leads_gen.utils import paths

        monkeypatch.setattr(paths, "get_output_dir", lambda: tmp_output_dir)

        # main.py imports get_output_dir directly, so patch its binding too.
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "main.py",
                "--query",
                "gyms in Testville",
                "--max-results",
                "3",
                "--no-license",
            ],
        )

        import main

        # Force reimport so its `from leads_gen.utils.paths import get_output_dir`
        # picks up our monkeypatched version.
        importlib.reload(main)
        main.main()

        out_file = tmp_output_dir / "gyms_in_Testville.xlsx"
        assert out_file.exists(), f"Expected {out_file} to be written"

        ws = openpyxl.load_workbook(out_file).active
        from leads_gen.core.data_normalization import CANONICAL_COLUMNS

        assert [c.value for c in ws[1]] == CANONICAL_COLUMNS
        # Header + 3 demo rows
        assert ws.max_row == 4

    def test_rerun_same_query_deduplicates(self, testing_mode, tmp_output_dir, monkeypatch):
        from leads_gen.utils import paths

        monkeypatch.setattr(paths, "get_output_dir", lambda: tmp_output_dir)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "main.py",
                "--query",
                "rerun_query",
                "--max-results",
                "3",
                "--no-license",
            ],
        )

        import main

        importlib.reload(main)
        main.main()

        # Re-run — same demo data. Website-based dedupe should keep row
        # count identical.
        main.main()

        out_file = tmp_output_dir / "rerun_query.xlsx"
        ws = openpyxl.load_workbook(out_file).active
        assert ws.max_row == 4, (
            f"After re-run, expected 4 rows (header + 3 unique), " f"got {ws.max_row}"
        )
