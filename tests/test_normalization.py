"""
Data normalization + deduplication: canonical schema enforcement, empty/
missing-value handling, phone normalization, Excel sanitization, and
duplicate collapsing.
"""

from __future__ import annotations

import pandas as pd
import pytest

from leads_gen.core.data_normalization import (
    CANONICAL_COLUMNS,
    deduplicate_dataframe,
    normalize_business_record,
    normalize_dataframe,
    normalize_empty_value,
    normalize_phone_number,
    process_scraped_data,
    sanitize_for_excel,
)


class TestNormalizeEmptyValue:
    @pytest.mark.parametrize("value", [None, "N/A", "", float("nan")])
    def test_empty_variants_become_empty_string(self, value):
        assert normalize_empty_value(value) == ""

    def test_int_becomes_str(self):
        assert normalize_empty_value(42) == "42"

    def test_whitespace_stripped(self):
        assert normalize_empty_value("  hi  ") == "hi"


class TestNormalizePhone:
    def test_strips_separators_keeps_plus_and_parens(self):
        assert normalize_phone_number("+1 (555) 123-4567") == "+1(555)1234567"

    def test_strips_letters(self):
        # "ext" and any other letters must be removed.
        result = normalize_phone_number("call: 555-1234 ext.5")
        assert result == "55512345"
        assert "e" not in result and "x" not in result and "t" not in result

    @pytest.mark.parametrize("value", [None, "", "N/A"])
    def test_empty_variants(self, value):
        assert normalize_phone_number(value) == ""


class TestSanitizeForExcel:
    def test_collapses_whitespace(self):
        assert sanitize_for_excel("a   b\t\tc") == "a b c"

    def test_strips_control_chars_completely(self):
        # Regression test: \x1f is both a control char AND matches Python's
        # unicode \s. The strip pass must run BEFORE the collapse pass so
        # \x1f is removed rather than turned into a space.
        assert sanitize_for_excel("hi\x00\x01\x1fworld") == "hiworld"

    def test_preserves_regular_chars(self):
        assert sanitize_for_excel("Normal Business Name") == "Normal Business Name"

    def test_empty_stays_empty(self):
        assert sanitize_for_excel("") == ""


class TestNormalizeBusinessRecord:
    def test_produces_canonical_keys(self):
        rec = normalize_business_record({"Name": "Test"})
        assert set(rec.keys()) == set(CANONICAL_COLUMNS)

    def test_emails_list_joined_by_comma(self):
        rec = normalize_business_record({"Name": "X", "Emails": ["a@b.com", "c@d.io"]})
        assert rec["Emails"] == "a@b.com, c@d.io"

    def test_phone_normalized(self):
        rec = normalize_business_record({"Name": "X", "Phone": "+1-555-0000"})
        assert rec["Phone"] == "+15550000"


class TestNormalizeDataframe:
    def test_empty_df_yields_canonical_columns(self):
        result = normalize_dataframe(pd.DataFrame())
        assert list(result.columns) == CANONICAL_COLUMNS
        assert len(result) == 0

    def test_extra_columns_are_dropped(self):
        df = pd.DataFrame([{"Name": "A", "UnknownField": "junk"}])
        result = normalize_dataframe(df)
        assert list(result.columns) == CANONICAL_COLUMNS
        assert "UnknownField" not in result.columns

    def test_missing_columns_are_filled(self):
        df = pd.DataFrame([{"Name": "A"}])
        result = normalize_dataframe(df)
        assert result.iloc[0]["Phone"] == ""
        assert result.iloc[0]["Website"] == ""


class TestDeduplicate:
    def test_website_dedup_case_insensitive(self):
        df = pd.DataFrame(
            [
                {"Name": "A", "Address": "1 St", "Website": "https://x.com"},
                {"Name": "A copy", "Address": "1 St", "Website": "HTTPS://X.COM"},
                {"Name": "B", "Address": "2 St", "Website": "https://y.com"},
            ]
        )
        assert len(deduplicate_dataframe(df)) == 2

    def test_fallback_to_name_plus_address(self):
        df = pd.DataFrame(
            [
                {"Name": "Same", "Address": "1 St", "Website": ""},
                {"Name": "Same", "Address": "1 St", "Website": "N/A"},
                {"Name": "Same", "Address": "2 St", "Website": ""},
            ]
        )
        assert len(deduplicate_dataframe(df)) == 2

    def test_does_not_mutate_input(self):
        # Regression test: earlier version leaked a '_dedup_key' column
        # into the caller's DataFrame.
        df = pd.DataFrame([{"Name": "A", "Address": "1", "Website": "x"}])
        before = list(df.columns)
        deduplicate_dataframe(df)
        assert list(df.columns) == before

    def test_empty_df_returns_empty(self):
        assert deduplicate_dataframe(pd.DataFrame()).empty

    def test_keeps_first_occurrence(self):
        df = pd.DataFrame(
            [
                {"Name": "First", "Address": "", "Website": "https://x.com"},
                {"Name": "Second", "Address": "", "Website": "https://x.com"},
            ]
        )
        result = deduplicate_dataframe(df)
        assert len(result) == 1
        assert result.iloc[0]["Name"] == "First"


class TestProcessScrapedData:
    def test_demo_data_round_trip(self):
        from leads_gen.core.demo_data import get_demo_leads

        demo = get_demo_leads()
        result = process_scraped_data(demo)
        assert len(result) == len(demo)
        assert list(result.columns) == CANONICAL_COLUMNS

    def test_empty_input_yields_canonical_empty_df(self):
        result = process_scraped_data([])
        assert list(result.columns) == CANONICAL_COLUMNS
        assert len(result) == 0
