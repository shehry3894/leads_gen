"""
utils/wait_utils.SmartWait — mock-based tests, no real Selenium.

We patch ``WebDriverWait`` at the module level so we can control its
return value / raised exception without spinning up a browser. Sleeps
are patched to no-ops so retry tests run instantly.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from selenium.common.exceptions import (
    ElementNotInteractableException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By


@pytest.fixture
def patched_wait(monkeypatch):
    """Replace WebDriverWait with a MagicMock so tests can drive .until()."""
    from leads_gen.utils import wait_utils

    mock = MagicMock(name="WebDriverWait")
    monkeypatch.setattr(wait_utils, "WebDriverWait", mock)
    return mock


@pytest.fixture
def no_sleep(monkeypatch):
    """Skip time.sleep in retry_with_backoff for fast tests."""
    from leads_gen.utils import wait_utils

    calls: list[float] = []
    monkeypatch.setattr(wait_utils.time, "sleep", calls.append)
    return calls


class TestWaitForElement:
    def test_returns_element_on_success(self, patched_wait):
        from leads_gen.utils.wait_utils import SmartWait

        fake_el = MagicMock(name="element")
        patched_wait.return_value.until.return_value = fake_el

        result = SmartWait(MagicMock()).wait_for_element(By.ID, "foo", timeout=5)
        assert result is fake_el

    def test_returns_none_on_timeout(self, patched_wait):
        from leads_gen.utils.wait_utils import SmartWait

        patched_wait.return_value.until.side_effect = TimeoutException()
        assert SmartWait(MagicMock()).wait_for_element(By.ID, "foo") is None

    def test_returns_none_on_unexpected_error(self, patched_wait):
        from leads_gen.utils.wait_utils import SmartWait

        patched_wait.return_value.until.side_effect = RuntimeError("boom")
        assert SmartWait(MagicMock()).wait_for_element(By.ID, "foo") is None

    def test_unknown_condition_defaults_to_presence(self, patched_wait):
        """Passing an unknown condition string shouldn't raise — falls back to presence."""
        from leads_gen.utils.wait_utils import SmartWait

        patched_wait.return_value.until.return_value = MagicMock()
        # Shouldn't raise KeyError
        SmartWait(MagicMock()).wait_for_element(By.ID, "foo", condition="totally-not-a-condition")


class TestWaitForElements:
    def test_returns_all_elements_on_success(self, patched_wait):
        from leads_gen.utils.wait_utils import SmartWait

        driver = MagicMock()
        driver.find_elements.return_value = [MagicMock(), MagicMock(), MagicMock()]
        patched_wait.return_value.until.return_value = True

        result = SmartWait(driver).wait_for_elements(By.CSS_SELECTOR, ".x")
        assert len(result) == 3

    def test_returns_empty_list_on_timeout(self, patched_wait):
        from leads_gen.utils.wait_utils import SmartWait

        patched_wait.return_value.until.side_effect = TimeoutException()
        assert SmartWait(MagicMock()).wait_for_elements(By.CSS_SELECTOR, ".x") == []


def _mock_fn(name="fn", **kwargs) -> MagicMock:
    """
    MagicMock with __name__ set — needed because retry_with_backoff logs
    ``func.__name__`` and bare MagicMocks raise AttributeError on that
    access.
    """
    m = MagicMock(**kwargs)
    m.__name__ = name
    return m


class TestRetryWithBackoff:
    def test_success_on_first_try_does_not_sleep(self, no_sleep):
        from leads_gen.utils.wait_utils import SmartWait

        fn = _mock_fn(return_value="ok")
        sw = SmartWait(MagicMock(), config={"base_wait": 1.0, "max_retries": 5})

        ok, result = sw.retry_with_backoff(fn)

        assert (ok, result) == (True, "ok")
        assert fn.call_count == 1
        assert no_sleep == []

    @pytest.mark.parametrize(
        "exc",
        [
            StaleElementReferenceException,
            NoSuchElementException,
            ElementNotInteractableException,
        ],
    )
    def test_retries_on_transient_selenium_errors(self, no_sleep, exc):
        from leads_gen.utils.wait_utils import SmartWait

        fn = _mock_fn(side_effect=[exc(), exc(), "final"])
        sw = SmartWait(MagicMock(), config={"base_wait": 0.5, "max_retries": 5})

        ok, result = sw.retry_with_backoff(fn)

        assert (ok, result) == (True, "final")
        assert fn.call_count == 3

    def test_gives_up_after_max_attempts(self, no_sleep):
        from leads_gen.utils.wait_utils import SmartWait

        fn = _mock_fn(side_effect=StaleElementReferenceException())
        sw = SmartWait(MagicMock(), config={"base_wait": 0.5, "max_retries": 3})

        ok, result = sw.retry_with_backoff(fn)

        assert (ok, result) == (False, None)
        assert fn.call_count == 3

    def test_unknown_exception_bails_immediately(self, no_sleep):
        """Only known Selenium transients should be retried."""
        from leads_gen.utils.wait_utils import SmartWait

        def raiser():
            raise RuntimeError("nope")

        sw = SmartWait(MagicMock(), config={"base_wait": 0.5, "max_retries": 5})
        ok, result = sw.retry_with_backoff(raiser)

        assert (ok, result) == (False, None)
        # No retries and (importantly) no sleeps.
        assert no_sleep == []

    def test_exponential_backoff_doubles_wait(self, no_sleep):
        from leads_gen.utils.wait_utils import SmartWait

        fn = _mock_fn(side_effect=StaleElementReferenceException())
        sw = SmartWait(
            MagicMock(),
            config={
                "base_wait": 1.0,
                "max_retries": 4,
                "exponential_backoff": True,
            },
        )

        sw.retry_with_backoff(fn)

        # 4 attempts → sleeps between attempts 1→2, 2→3, 3→4. Not after the last.
        assert no_sleep == [1.0, 2.0, 4.0]

    def test_linear_backoff_keeps_wait_constant(self, no_sleep):
        from leads_gen.utils.wait_utils import SmartWait

        fn = _mock_fn(side_effect=StaleElementReferenceException())
        sw = SmartWait(
            MagicMock(),
            config={
                "base_wait": 0.5,
                "max_retries": 4,
                "exponential_backoff": False,
            },
        )

        sw.retry_with_backoff(fn)

        assert no_sleep == [0.5, 0.5, 0.5]


class TestWaitAndClick:
    def test_returns_false_when_element_not_found(self, patched_wait, no_sleep):
        from leads_gen.utils.wait_utils import SmartWait

        patched_wait.return_value.until.side_effect = TimeoutException()
        assert SmartWait(MagicMock()).wait_and_click(By.ID, "foo") is False

    def test_clicks_element_when_found(self, patched_wait, no_sleep):
        from leads_gen.utils.wait_utils import SmartWait

        fake_el = MagicMock(name="button")
        patched_wait.return_value.until.return_value = fake_el

        ok = SmartWait(MagicMock()).wait_and_click(By.ID, "foo")

        assert ok is True
        fake_el.click.assert_called_once()
