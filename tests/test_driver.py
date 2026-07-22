"""
scraper/driver.py — non-browser-launching tests.

We verify that start_driver() honors the CHROMEDRIVER_PATH env var by
mocking Selenium's Chrome constructor and asserting that when the env
var is set, ChromeDriverManager is NOT invoked (which would need
network) and instead the env-var path flows through to the Service.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestChromedriverPathOverride:
    def test_env_var_short_circuits_manager(self, monkeypatch):
        monkeypatch.setenv("CHROMEDRIVER_PATH", "/fake/path/chromedriver")

        with (
            patch("leads_gen.scraper.driver.ChromeDriverManager") as mgr_cls,
            patch("leads_gen.scraper.driver.Service") as service_cls,
            patch("leads_gen.scraper.driver.webdriver.Chrome") as chrome_cls,
        ):
            fake_driver = MagicMock()
            chrome_cls.return_value = fake_driver

            from leads_gen.scraper.driver import start_driver

            driver = start_driver()

            # ChromeDriverManager should not be instantiated at all
            mgr_cls.assert_not_called()
            # Service should receive the env-var path
            service_cls.assert_called_once_with("/fake/path/chromedriver")
            assert driver is fake_driver

    def test_no_env_var_falls_back_to_manager(self, monkeypatch):
        monkeypatch.delenv("CHROMEDRIVER_PATH", raising=False)

        with (
            patch("leads_gen.scraper.driver.ChromeDriverManager") as mgr_cls,
            patch("leads_gen.scraper.driver.Service") as service_cls,
            patch("leads_gen.scraper.driver.webdriver.Chrome") as chrome_cls,
        ):
            mgr_instance = MagicMock()
            mgr_instance.install.return_value = "/managed/chromedriver"
            mgr_cls.return_value = mgr_instance
            chrome_cls.return_value = MagicMock()

            from leads_gen.scraper.driver import start_driver

            start_driver()

            mgr_cls.assert_called_once()
            mgr_instance.install.assert_called_once()
            service_cls.assert_called_once_with("/managed/chromedriver")
