"""
Scraper helper functions: social media URL detection, email cleaning,
WhatsApp link generation, and the empty-social-links factory.

These functions run inside the Selenium loop but have no browser
dependency themselves, so we can test them in isolation.
"""

from __future__ import annotations

import pytest

from leads_gen.scraper.scrape import (
    SOCIAL_PLATFORMS,
    clean_emails,
    detect_social_media_from_url,
    empty_social_links,
    generate_whatsapp_link,
)


class TestDetectSocialMedia:
    @pytest.mark.parametrize(
        "url,expected_platform",
        [
            ("https://facebook.com/foo", "Facebook"),
            ("https://www.fb.com/bar", "Facebook"),
            ("https://instagram.com/handle", "Instagram"),
            ("https://twitter.com/handle", "Twitter"),
            ("https://x.com/handle", "Twitter"),
            ("https://linkedin.com/in/x", "LinkedIn"),
            ("https://youtube.com/@channel", "YouTube"),
            ("https://youtu.be/abc123", "YouTube"),
            ("https://pinterest.com/x", "Pinterest"),
            ("https://tiktok.com/@user", "TikTok"),
            ("https://threads.net/@user", "Threads"),
            ("https://snapchat.com/add/x", "Snapchat"),
        ],
    )
    def test_detects_platform(self, url, expected_platform):
        platform, returned = detect_social_media_from_url(url)
        assert platform == expected_platform
        assert returned == url

    @pytest.mark.parametrize("url", [None, "N/A", "https://example.com", ""])
    def test_non_social_returns_none(self, url):
        assert detect_social_media_from_url(url) == (None, None)


class TestCleanEmails:
    def test_lowercases_and_dedupes(self):
        result = clean_emails(["Owner@ACME.io", "owner@acme.io"])
        assert result == ["owner@acme.io"]

    def test_rejects_dummy_domain_label(self):
        # 'example', 'test', 'dummy' etc as any DOMAIN LABEL → reject.
        assert clean_emails(["real@example.co.uk"]) == []
        assert clean_emails(["a@test.com"]) == []
        assert clean_emails(["b@dummy.io"]) == []

    def test_accepts_domain_containing_dummy_substring(self):
        # Regression: substring match was too aggressive — 'myexample.com'
        # should NOT be rejected just because it contains 'example'.
        result = clean_emails(["owner@myexample.com"])
        assert "owner@myexample.com" in result

    def test_rejects_noreply_variants(self):
        assert clean_emails(["noreply@site.com"]) == []
        assert clean_emails(["no-reply@site.com"]) == []

    def test_rejects_malformed(self):
        assert (
            clean_emails(["not-an-email", "@missing-local.com", "missing-domain@", "no-at-symbol"])
            == []
        )

    def test_mixed_input(self):
        result = clean_emails(
            [
                "good@real-business.co",
                "test@example.com",  # dummy domain
                "noreply@real.com",  # noreply
                "GOOD@real-business.co",  # dup (case)
                "malformed",
            ]
        )
        assert result == ["good@real-business.co"]


class TestGenerateWhatsappLink:
    def test_valid_phone_becomes_wa_link(self):
        assert generate_whatsapp_link("+1 555-123-4567") == "https://wa.me/15551234567"

    def test_strips_all_formatting(self):
        assert generate_whatsapp_link("+1-800-555-9999") == "https://wa.me/18005559999"

    @pytest.mark.parametrize("value", [None, "N/A"])
    def test_missing_becomes_na(self, value):
        assert generate_whatsapp_link(value) == "N/A"


class TestEmptySocialLinks:
    def test_has_all_platforms_plus_emails(self):
        result = empty_social_links()
        assert set(result.keys()) == set(SOCIAL_PLATFORMS) | {"Emails"}

    def test_platforms_are_none_emails_is_empty_list(self):
        result = empty_social_links()
        assert result["Emails"] == []
        for platform in SOCIAL_PLATFORMS:
            assert result[platform] is None

    def test_returns_fresh_dict_each_call(self):
        # No shared mutable default (a common Python footgun).
        first = empty_social_links()
        first["Emails"].append("mutated@test.com")
        second = empty_social_links()
        assert second["Emails"] == []
