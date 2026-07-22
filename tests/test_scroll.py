"""
scraper/scroll.scroll_results — mocked-driver tests.

Verifies the two hard-to-eyeball invariants of the scroll loop:
  1. TRIAL=True forces max_results to 3 regardless of caller
  2. Loop terminates on either (a) reaching requested max, (b) 5 consecutive
     scrolls with no new .Nv2PK cards, or (c) missing scrollable feed

We count ``driver.execute_script`` calls (each = one scroll) rather than
inspecting internal state — a stable, refactor-tolerant signal.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def fake_driver():
    return MagicMock(name="driver")


@pytest.fixture
def patched_scroll(monkeypatch):
    """No real sleeps; SmartWait returns a fake scrollable div."""
    from leads_gen.scraper import scroll as scroll_mod

    monkeypatch.setattr(scroll_mod.time, "sleep", lambda _s: None)

    fake_smart_wait = MagicMock(name="SmartWait")
    fake_smart_wait.wait_for_element.return_value = MagicMock(name="scrollable_div")
    monkeypatch.setattr(scroll_mod, "SmartWait", lambda _d: fake_smart_wait)

    return fake_smart_wait


def _cards(n: int) -> list:
    return [MagicMock(name=f"card{i}") for i in range(n)]


class TestTrialCap:
    def test_trial_forces_max_to_3_even_if_caller_asks_more(
        self, fake_driver, patched_scroll, monkeypatch
    ):
        from leads_gen.scraper import scroll as scroll_mod

        monkeypatch.setattr(scroll_mod, "TRIAL", True)

        # First scroll returns 3 cards — should hit the (now-capped) max.
        fake_driver.find_elements.side_effect = [_cards(3)]

        scroll_mod.scroll_results(fake_driver, max_results=100)

        assert fake_driver.execute_script.call_count == 1


class TestStopConditions:
    def test_stops_when_requested_max_reached(self, fake_driver, patched_scroll, monkeypatch):
        from leads_gen.scraper import scroll as scroll_mod

        monkeypatch.setattr(scroll_mod, "TRIAL", False)

        # Growth: 2 → 4 → 6 cards. Requested 5, breaks on iter 3.
        fake_driver.find_elements.side_effect = [_cards(2), _cards(4), _cards(6)]

        scroll_mod.scroll_results(fake_driver, max_results=5)

        assert fake_driver.execute_script.call_count == 3

    def test_stops_after_five_consecutive_no_new_cards(
        self, fake_driver, patched_scroll, monkeypatch
    ):
        from leads_gen.scraper import scroll as scroll_mod

        monkeypatch.setattr(scroll_mod, "TRIAL", False)

        # Iter 1 collects 4; iters 2-6 plateau at 4 → same_count_retries hits 5.
        fake_driver.find_elements.side_effect = [_cards(4)] * 10

        scroll_mod.scroll_results(fake_driver, max_results=100)

        # 1 growth + 5 plateau = 6 scrolls
        assert fake_driver.execute_script.call_count == 6

    def test_none_max_means_scroll_until_plateau(self, fake_driver, patched_scroll, monkeypatch):
        from leads_gen.scraper import scroll as scroll_mod

        monkeypatch.setattr(scroll_mod, "TRIAL", False)

        # 3 → 6, then 5 plateau iters at 6.
        fake_driver.find_elements.side_effect = [
            _cards(3),
            _cards(6),
            _cards(6),
            _cards(6),
            _cards(6),
            _cards(6),
            _cards(6),
        ]

        scroll_mod.scroll_results(fake_driver, max_results=None)

        # 2 growth + 5 plateau = 7 scrolls
        assert fake_driver.execute_script.call_count == 7


class TestMissingFeed:
    def test_missing_feed_returns_without_scrolling(self, fake_driver, patched_scroll, monkeypatch):
        from leads_gen.scraper import scroll as scroll_mod

        monkeypatch.setattr(scroll_mod, "TRIAL", False)

        # SmartWait returns None → feed never found.
        patched_scroll.wait_for_element.return_value = None

        scroll_mod.scroll_results(fake_driver, max_results=10)

        assert fake_driver.execute_script.call_count == 0
