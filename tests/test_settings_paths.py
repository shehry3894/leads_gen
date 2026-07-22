"""
Configuration + path utilities: HEADLESS_MODE env parsing, WAIT_CONFIG
shape, base/logs/output/license dir resolution.
"""

from __future__ import annotations

import importlib

import pytest

from leads_gen.utils import paths


class TestHeadlessModeParsing:
    """
    HEADLESS_MODE is read at module import; we reload settings after each
    monkeypatch so each parametrized case sees a clean read.
    """

    @pytest.mark.parametrize(
        "env_value,expected",
        [
            ("true", True),
            ("TRUE", True),
            ("True", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("0", False),
            ("no", False),
            ("bogus", False),  # safe default: anything unknown → False (visible browser)
        ],
    )
    def test_env_values(self, env_value, expected, monkeypatch):
        monkeypatch.setenv("HEADLESS_MODE", env_value)
        import leads_gen.config.settings as s

        importlib.reload(s)
        try:
            assert s.HEADLESS_MODE is expected
        finally:
            monkeypatch.delenv("HEADLESS_MODE", raising=False)
            importlib.reload(s)

    def test_unset_defaults_to_true(self, monkeypatch):
        monkeypatch.delenv("HEADLESS_MODE", raising=False)
        import leads_gen.config.settings as s

        importlib.reload(s)
        assert s.HEADLESS_MODE is True


class TestWaitConfig:
    REQUIRED_KEYS = {
        "base_wait",
        "max_wait",
        "max_retries",
        "exponential_backoff",
        "page_load",
        "search_box",
        "search_results",
        "business_card",
        "info_panel",
        "element_visibility",
    }

    def test_all_required_keys_present(self):
        from leads_gen.config.settings import WAIT_CONFIG

        assert self.REQUIRED_KEYS.issubset(WAIT_CONFIG.keys())

    def test_timeouts_are_positive(self):
        from leads_gen.config.settings import WAIT_CONFIG

        for key in (
            "page_load",
            "search_box",
            "search_results",
            "business_card",
            "info_panel",
            "element_visibility",
        ):
            assert WAIT_CONFIG[key] > 0, f"{key} must be positive"


class TestPaths:
    def test_base_dir_is_leads_gen_package(self):
        assert paths.get_base_dir().name == "leads_gen"

    def test_dirs_are_created_on_demand(self, tmp_path, monkeypatch):
        monkeypatch.setattr(paths, "get_base_dir", lambda: tmp_path)
        assert paths.get_logs_dir().exists()
        assert paths.get_output_dir().exists()
        assert paths.get_ui_output_dir().exists()
        assert paths.get_license_dir().exists()

    def test_output_and_ui_output_are_distinct(self, tmp_path, monkeypatch):
        monkeypatch.setattr(paths, "get_base_dir", lambda: tmp_path)
        assert paths.get_output_dir() != paths.get_ui_output_dir()
