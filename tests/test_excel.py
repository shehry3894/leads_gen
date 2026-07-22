"""
Excel output: Streamlit's ``create_excel_with_links`` helper and the
raw ``DataFrame.to_excel`` round-trip used by the CLI.

We use openpyxl for cell-level inspection because xlsxwriter (used to
write hyperlinks) doesn't expose a read API.
"""

from __future__ import annotations

import importlib.util
from io import BytesIO
from pathlib import Path

import openpyxl
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def app_module():
    """Load app.py as a module so we can call its helpers without invoking
    Streamlit. Session-scoped because importing app.py is expensive."""
    spec = importlib.util.spec_from_file_location("app_mod", PROJECT_ROOT / "app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestCreateExcelWithLinks:
    def test_returns_nonempty_bytes(self, app_module):
        df = pd.DataFrame([{"Name": "A", "Website": "https://a.com"}])
        data = app_module.create_excel_with_links(df)
        assert isinstance(data, (bytes, bytearray))
        assert len(data) > 0

    def test_header_row_matches_columns(self, app_module):
        cols = ["Name", "Website", "Phone", "Facebook"]
        df = pd.DataFrame(columns=cols)
        data = app_module.create_excel_with_links(df)
        ws = openpyxl.load_workbook(BytesIO(data)).active
        assert [c.value for c in ws[1]] == cols

    def test_urls_get_hyperlinks(self, app_module):
        df = pd.DataFrame(
            [
                {"Name": "A", "Website": "https://a.com", "Facebook": "https://fb.com/a"},
            ]
        )
        ws = openpyxl.load_workbook(BytesIO(app_module.create_excel_with_links(df))).active
        assert ws.cell(row=2, column=2).hyperlink.target == "https://a.com"
        assert ws.cell(row=2, column=3).hyperlink.target == "https://fb.com/a"

    def test_non_url_values_are_not_hyperlinked(self, app_module):
        df = pd.DataFrame([{"Name": "A", "Website": "not-a-url"}])
        ws = openpyxl.load_workbook(BytesIO(app_module.create_excel_with_links(df))).active
        assert ws.cell(row=2, column=2).hyperlink is None

    def test_none_and_empty_values_do_not_crash(self, app_module):
        df = pd.DataFrame(
            [
                {"Name": "A", "Website": None},
                {"Name": "B", "Website": ""},
                {"Name": "C", "Website": "not-a-url"},
            ]
        )
        # Just verify no exception is raised
        app_module.create_excel_with_links(df)

    def test_all_none_column_does_not_crash(self, app_module):
        df = pd.DataFrame([{"Website": None}, {"Website": None}])
        app_module.create_excel_with_links(df)

    def test_empty_dataframe_does_not_crash(self, app_module):
        df = pd.DataFrame(columns=["Name", "Website"])
        app_module.create_excel_with_links(df)


class TestExcelRoundTrip:
    """
    Sanity check the openpyxl round-trip used by main.py so an accidental
    dtype coercion (e.g. phone numbers becoming floats) is caught early.
    """

    def test_phone_stays_string(self, tmp_path):
        from leads_gen.core.data_normalization import process_scraped_data
        from leads_gen.core.demo_data import get_demo_leads

        out = tmp_path / "out.xlsx"
        process_scraped_data(get_demo_leads()).to_excel(out, index=False)

        ws = openpyxl.load_workbook(out).active
        # Column 4 is Phone in CANONICAL_COLUMNS
        for row in range(2, ws.max_row + 1):
            val = ws.cell(row=row, column=4).value
            assert val is None or isinstance(val, str), (
                f"Phone at row {row} was {type(val).__name__}={val!r}, " "expected str or None"
            )
