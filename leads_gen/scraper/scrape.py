import logging
import re
import time
from datetime import datetime

import requests
from selenium.webdriver.common.by import By

from leads_gen.config.settings import TRIAL, WAIT_CONFIG
from leads_gen.utils.wait_utils import SmartWait

logger = logging.getLogger("leads_gen")

SOCIAL_PLATFORMS = (
    "Facebook",
    "Instagram",
    "Twitter",
    "LinkedIn",
    "YouTube",
    "Pinterest",
    "TikTok",
    "Threads",
    "Snapchat",
)


def empty_social_links() -> dict:
    """Fresh dict with a None slot per platform plus an empty Emails list."""
    links = dict.fromkeys(SOCIAL_PLATFORMS)
    links["Emails"] = []
    return links


def generate_whatsapp_link(phone_number):
    if phone_number and phone_number != "N/A":
        wa_number = phone_number.replace("+", "").replace(" ", "").replace("-", "")
        return f"https://wa.me/{wa_number}"
    return "N/A"


# --- Interleaved scrape+scroll loop constants ---
# Instead of "scroll everything, then scrape everything" (which loses late results
# if Google throttles halfway), we interleave: scrape a card, scroll for more
# when the DOM runs out, keep going until data starts repeating or the feed is
# genuinely exhausted.
_INTERLEAVED_MAX_DUPLICATE_STREAK = 5
_INTERLEAVED_MAX_SCROLL_STALL_STREAK = 3
# Slightly longer than WAIT_CONFIG.base_wait: Google Maps often takes 1.5-3s to
# render the next batch of cards after a scroll, especially with a visible
# browser on a home connection.
_INTERLEAVED_SCROLL_WAIT_SECONDS = 1.8


def _scroll_feed_to_bottom(driver) -> None:
    """Scroll the Google Maps results feed to trigger lazy-load of more cards."""
    driver.execute_script("""
        const feed = document.querySelector('div[role="feed"]');
        if (feed) feed.scrollTop = feed.scrollHeight;
        """)


def _is_end_of_list_marker_visible(driver) -> bool:
    """Detect Google Maps' 'You've reached the end of the list' message.

    When present, this is Google's authoritative signal that the feed is
    exhausted — we can stop immediately without waiting through the stall
    detector. The exact copy/class churns; we match on visible text.
    """
    try:
        markers = driver.find_elements(
            By.XPATH,
            '//p[contains(., "You\'ve reached the end") ' "or contains(., 'end of the list')]",
        )
        return any(m.is_displayed() for m in markers)
    except Exception:
        return False


_MAPS_CID_HEX_RE = re.compile(r"!1s0x[0-9a-f]+:0x([0-9a-f]+)", re.IGNORECASE)

# Parenthesized number like "(1,234)" — the format Google Maps uses to display
# review count next to the rating in the .F7nice container.
_PARENTHESIZED_NUMBER_RE = re.compile(r"\((\d[\d,]*)\)")


# Review count is best-effort — Google Maps often serves a "limited view" that
# omits it entirely. Keep the poll short (1s max) so businesses without a
# visible count don't cost us 5s each; the rating still comes through fine.
_REVIEW_COUNT_POLL_SECONDS = 1.0
_REVIEW_COUNT_POLL_INTERVAL = 0.25

# Read the parent of .F7nice, not F7nice itself: on many place panels the count
# renders as a sibling span (or a link a few nodes over), not inside F7nice.
_REVIEW_COUNT_JS_SNIPPET = (
    "const el = document.querySelector('.F7nice');"
    "if (!el) return '';"
    "return (el.parentElement || el).innerText;"
)


def _extract_review_count_via_js(driver) -> str:
    # Poll rather than block: some place panels render the count immediately,
    # others hydrate it lazily after the rating stars. Bail out quickly when it
    # doesn't appear at all (small businesses often don't display a count).
    deadline = time.monotonic() + _REVIEW_COUNT_POLL_SECONDS
    while True:
        try:
            container_text = driver.execute_script(_REVIEW_COUNT_JS_SNIPPET)
        except Exception as exc:
            logger.debug("JS review-count extraction failed: %s", exc)
            return "N/A"
        if container_text:
            match = _PARENTHESIZED_NUMBER_RE.search(container_text)
            if match:
                review_count = match.group(1).replace(",", "")
                logger.debug("Found review count via F7nice-parent innerText: %s", review_count)
                return review_count
        if time.monotonic() >= deadline:
            return "N/A"
        time.sleep(_REVIEW_COUNT_POLL_INTERVAL)


def canonicalize_maps_place_url(current_browser_url: str) -> str:
    # driver.current_url embeds the viewport ``@lat,lng,zoom`` plus session tracking
    # (``entry=ttu``, ``g_ep=…``) — reopening it re-centers on the search area at a
    # wide zoom instead of the pin. The CID share-link Google's own "Share" button
    # produces (``maps.google.com/?cid=<decimal>``) opens the exact place every time.
    match = _MAPS_CID_HEX_RE.search(current_browser_url)
    if not match:
        return current_browser_url
    try:
        place_cid_decimal = int(match.group(1), 16)
    except ValueError:
        return current_browser_url
    return f"https://maps.google.com/?cid={place_cid_decimal}"


_DUMMY_DOMAIN_LABELS = frozenset(
    {
        "example",
        "test",
        "dummy",
        "yourdomain",
        "abc",
        "xyz",
    }
)
_DUMMY_LOCAL_TOKENS = (
    "noreply",
    "no-reply",
    "ed436f5053144538958ad06a5005e99a",
    "c183baa23371454f99f417f6616b724d",
)
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


def _is_dummy_email(email_lower: str) -> bool:
    local, _, domain = email_lower.partition("@")
    if not domain:
        return True
    # Reject if any domain label exactly matches a dummy token
    # (real@example.co.uk rejected; owner@myexample.com accepted).
    if any(label in _DUMMY_DOMAIN_LABELS for label in domain.split(".")):
        return True
    # Local-part tokens: substring match is intentional for these
    # (they're specific enough to not false-positive).
    return any(tok in local for tok in _DUMMY_LOCAL_TOKENS)


def clean_emails(emails):
    cleaned = set()
    for email in emails:
        if not _EMAIL_RE.fullmatch(email):
            continue
        email_lower = email.lower()
        if _is_dummy_email(email_lower):
            continue
        cleaned.add(email_lower)
    return list(cleaned)


_SOCIAL_URL_REGEX_PATTERNS = {
    "Facebook": r"https?://(?:www\.|m\.|mobile\.|touch\.)?(?:facebook|fb)\.com/(?:pages/|profile\.php\?id=)?[^\s\"'<>){}\[\]]+",
    "Instagram": r"https?://(?:www\.|m\.)?instagram\.com/(?:p/|reel/|tv/)?[^\s\"'<>){}\[\]]+",
    "Twitter": r"https?://(?:www\.|m\.|mobile\.)?(?:twitter|x)\.com/(?:#!/)?[^\s\"'<>){}\[\]]+",
    "LinkedIn": r"https?://(?:www\.)?linkedin\.com/(?:in/|company/|school/)?[^\s\"'<>){}\[\]]+",
    "YouTube": r"https?://(?:www\.|m\.)?(?:youtube\.com/(?:channel/|c/|user/|@)?|youtu\.be/)[^\s\"'<>){}\[\]]+",
    "Pinterest": r"https?://(?:www\.)?(?:pinterest\.com|pin\.it)/[^\s\"'<>){}\[\]]+",
    "TikTok": r"https?://(?:www\.|vm\.|vt\.)?tiktok\.com/(?:@)?[^\s\"'<>){}\[\]]+",
    "Threads": r"https?://(?:www\.)?threads\.net/(?:@)?[^\s\"'<>){}\[\]]+",
    "Snapchat": r"https?://(?:www\.)?(?:snapchat\.com/(?:add/|t/)|story\.snapchat\.com/)[^\s\"'<>){}\[\]]+",
}

# URL fragments that identify non-profile pages we should discard:
#   - pixel trackers (facebook.com/tr?id=…), embed players (youtube.com/embed/…),
#   - share/intent dialogs (twitter.com/intent/tweet), individual posts/pins,
#     hashtag pages, and reference paths.
# The regexes above are broad on purpose (permissive prefix) — this filter is
# the safety net that rejects the non-profile matches.
_NON_PROFILE_URL_FRAGMENTS_BY_PLATFORM: dict[str, tuple[str, ...]] = {
    # `/2008/fbml` = OpenGraph XML namespace URL (`xmlns:fb="http://www.facebook.com/2008/fbml"`)
    # sites embed in <html> tags — it's not a profile page.
    "Facebook": ("/tr?", "/tr/", "/plugins/", "/sharer", "/dialog/", "/2008/"),
    "Instagram": ("/p/", "/reel/", "/tv/", "/embed", "/tags/", "/explore/"),
    "Twitter": ("/intent/", "/share", "/i/", "/hashtag/"),
    "LinkedIn": ("/sharing/", "/sharearticle", "/shareArticle"),
    "YouTube": ("/embed/", "/watch", "/vi/", "/vi_webp/", "/tr?", "/oembed"),
    "Pinterest": ("/pin/", "/pin-builder/"),
    "TikTok": ("/embed", "/share"),
    "Threads": ("/embed",),
    "Snapchat": (),
}


def _is_profile_url(platform: str, url: str) -> bool:
    non_profile_fragments = _NON_PROFILE_URL_FRAGMENTS_BY_PLATFORM.get(platform, ())
    url_lower = url.lower()
    return not any(fragment in url_lower for fragment in non_profile_fragments)


def extract_social_and_email_links(website_url, retries=2, delay=3):
    social_links = empty_social_links()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    }

    for attempt in range(retries):
        try:
            logger.info(
                f"Attempting to scrape social and email links from: {website_url} (attempt {attempt + 1}/{retries})"
            )
            # Split connect/read timeouts: some business sites are slow to respond
            # to the initial handshake but fine once streaming, or vice versa.
            response = requests.get(website_url, headers=headers, timeout=(5, 15))
            if response.status_code >= 400:
                logger.info(
                    "Website %s returned HTTP %s; skipping social/email extraction",
                    website_url,
                    response.status_code,
                )
                break
            if response.status_code == 200:
                html = response.text
                found_links = []

                # Iterate matches per platform and pick the first that looks like a
                # profile page (see `_is_profile_url`) — otherwise pixel trackers and
                # embed players win because they appear first in the HTML.
                for platform, pattern in _SOCIAL_URL_REGEX_PATTERNS.items():
                    for raw_match in re.findall(pattern, html, re.IGNORECASE):
                        candidate_url = raw_match.rstrip(".,;:!?)}]")
                        if _is_profile_url(platform, candidate_url):
                            social_links[platform] = candidate_url
                            found_links.append(platform)
                            logger.debug(f"Found {platform}: {candidate_url}")
                            break

                # Extract email addresses
                raw_emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", html)
                social_links["Emails"] = clean_emails(raw_emails)

                if found_links or social_links["Emails"]:
                    logger.info(
                        f'Successfully scraped from {website_url}: {", ".join(found_links) if found_links else "no social links"}, {len(social_links["Emails"])} emails'
                    )
                else:
                    logger.info(f"No social media links or emails found on {website_url}")
                break
        except requests.Timeout:
            logger.warning(f"Timeout scraping {website_url} (attempt {attempt + 1}/{retries})")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                logger.error(
                    "Giving up on %s after %s attempts (all timed out)", website_url, retries
                )
        except requests.RequestException as e:
            logger.warning(
                f"Request error scraping {website_url}: {str(e)} (attempt {attempt + 1}/{retries})"
            )
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                logger.error("Giving up on %s after %s attempts: %s", website_url, retries, e)
        except Exception as e:
            logger.warning(
                f"Error scraping {website_url}: {str(e)} (attempt {attempt + 1}/{retries})"
            )
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                logger.error(
                    "Giving up on %s after %s attempts (unexpected error): %s",
                    website_url,
                    retries,
                    e,
                )

    return social_links


def detect_social_media_from_url(url):
    """
    Detects if a URL is a social media link and returns (platform_name, cleaned_url) or (None, None)
    """
    if not url or url == "N/A":
        return None, None

    url_lower = url.lower()

    # Check each platform
    if "facebook.com" in url_lower or "fb.com" in url_lower or "fb.me" in url_lower:
        return "Facebook", url
    if "instagram.com" in url_lower:
        return "Instagram", url
    if (
        "twitter.com" in url_lower
        or url_lower.startswith("https://x.com")
        or "/x.com/" in url_lower
    ):
        return "Twitter", url
    if "linkedin.com" in url_lower:
        return "LinkedIn", url
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "YouTube", url
    if "pinterest.com" in url_lower or "pin.it" in url_lower:
        return "Pinterest", url
    if "tiktok.com" in url_lower:
        return "TikTok", url
    if "threads.net" in url_lower:
        return "Threads", url
    if "snapchat.com" in url_lower:
        return "Snapchat", url

    return None, None


def scrape_business_data(driver, max_results):
    data: list[dict] = []
    smart_wait = SmartWait(driver)

    # Wait for initial results to load
    results = smart_wait.wait_for_elements(
        By.XPATH,
        '//div[contains(@class, "Nv2PK")]',
        timeout=WAIT_CONFIG.get("search_results", 15),
        min_count=1,
    )

    if not results:
        logger.error("No business results found")
        return data

    # TRIAL cap moved here from the (now-deleted) scroll_results stage; the
    # interleaved loop compares against len(data), so a max of 3 means "collect
    # 3 records", not "look at 3 cards".
    if TRIAL:
        max_results = 3
        logger.info(f"TRIAL mode: capping max_results at {max_results}")

    logger.info(
        "Starting interleaved scrape (initial cards visible: %s, max_results=%s)",
        len(results),
        max_results if max_results is not None else "unlimited",
    )

    scraped_links = set()  # Track which businesses we've already scraped to avoid duplicates
    i = 0
    duplicate_streak = 0
    scroll_stall_streak = 0

    while True:
        # --- Global exit conditions ---
        if max_results is not None and len(data) >= max_results:
            logger.info(f"Reached the max results limit: {max_results}")
            break
        if duplicate_streak >= _INTERLEAVED_MAX_DUPLICATE_STREAK:
            logger.info(
                "Data has started repeating (%s duplicates in a row). Stopping.",
                duplicate_streak,
            )
            break

        # --- Ensure a card exists at position i (scroll if needed) ---
        results = driver.find_elements(By.XPATH, '//div[contains(@class, "Nv2PK")]')
        while i >= len(results):
            if _is_end_of_list_marker_visible(driver):
                logger.info("Google Maps 'end of list' marker detected. Stopping.")
                return data
            old_len = len(results)
            _scroll_feed_to_bottom(driver)
            time.sleep(_INTERLEAVED_SCROLL_WAIT_SECONDS)
            results = driver.find_elements(By.XPATH, '//div[contains(@class, "Nv2PK")]')
            if len(results) == old_len:
                scroll_stall_streak += 1
                logger.info(
                    "Scroll produced no new cards (%s/%s)",
                    scroll_stall_streak,
                    _INTERLEAVED_MAX_SCROLL_STALL_STREAK,
                )
                if scroll_stall_streak >= _INTERLEAVED_MAX_SCROLL_STALL_STREAK:
                    logger.info("Feed exhausted after multiple scroll stalls. Stopping.")
                    return data
            else:
                scroll_stall_streak = 0
                logger.info("Cards loaded via scroll: %s -> %s", old_len, len(results))

        accepted_before = len(data)
        try:
            # (results was refreshed by the scroll-ensure block above)
            if i >= len(results):
                logger.warning(f"Result {i} no longer available")
                continue

            # STEP 1: Extract the expected business name from the list card BEFORE clicking
            expected_name = None
            try:
                # Try to get business name from the list item
                name_elem = results[i].find_element(By.CSS_SELECTOR, "div.fontHeadlineSmall")
                expected_name = name_elem.text.strip() if name_elem else None
                logger.debug(f"Expected business name from list: {expected_name}")
            except Exception as e:
                logger.debug(f"Could not get expected name from list item: {str(e)}")

            # Get the aria-label or href to identify this business uniquely
            try:
                link_elem = results[i].find_element(By.TAG_NAME, "a")
                business_href = link_elem.get_attribute("href") if link_elem else None
                business_label = results[i].get_attribute("aria-label") or ""

                # If we didn't get expected_name, try from aria-label
                if not expected_name and business_label:
                    expected_name = business_label.split("·")[0].strip()

                # Create a unique identifier
                unique_id = business_href or business_label

                # Skip if we've already scraped this business
                if unique_id and unique_id in scraped_links:
                    logger.info(
                        f"Skipping duplicate business at index {i}: {business_label[:50]}..."
                    )
                    continue

            except Exception as e:
                logger.debug(f"Could not get unique ID for result {i}: {str(e)}")
                unique_id = None

            # Scroll element into view
            driver.execute_script('arguments[0].scrollIntoView({block: "center"});', results[i])
            time.sleep(0.3)  # Brief pause for scroll animation

            # STEP 2: Click the business card
            # Bind loop var via default arg so the closure doesn't drift if this ever
            # gets called after the loop advances (ruff B023).
            def click_business_card(idx: int = i) -> bool:
                # Re-fetch the element to avoid stale reference
                fresh_results = driver.find_elements(By.XPATH, '//div[contains(@class, "Nv2PK")]')
                if idx < len(fresh_results):
                    fresh_results[idx].click()
                    return True
                return False

            success, _ = smart_wait.retry_with_backoff(click_business_card, max_attempts=3)

            if not success:
                logger.warning(f"Failed to click business card {i+1}")
                continue

            # Mark this business as scraped
            if unique_id:
                scraped_links.add(unique_id)

            # STEP 3: Wait for the info panel container to appear
            info_panel = smart_wait.wait_for_element(
                By.XPATH,
                '//div[contains(@class, "m6QErb")]',
                timeout=WAIT_CONFIG.get("info_panel", 10),
                condition="presence",
            )

            if not info_panel:
                logger.warning(f"Info panel did not load for business {i+1}")
                continue

            # STEP 4: Wait for the SPECIFIC business name to appear in the detail panel
            name = "N/A"
            if expected_name:
                logger.debug(
                    f'Waiting for expected name "{expected_name}" to appear in detail panel...'
                )
                # Wait for h1 with the expected name to appear
                max_wait_for_name = 15  # seconds
                name_found = False

                for _attempt in range(max_wait_for_name):
                    try:
                        h1_elements = driver.find_elements(
                            By.XPATH,
                            '//div[contains(@class, "m6QErb")]//h1[contains(@class,"DUwDvf")]',
                        )
                        for h1 in h1_elements:
                            h1_text = h1.text.strip()
                            if (
                                h1_text
                                and h1_text.lower() != "results"
                                and expected_name.lower() in h1_text.lower()
                            ):
                                name = h1_text
                                name_found = True
                                logger.info(f"✓ Expected name found in detail panel: {name}")
                                break

                        if name_found:
                            break

                        time.sleep(1)
                    except Exception as e:
                        logger.debug(f"Error checking for name: {str(e)}")
                        time.sleep(1)

                if not name_found:
                    logger.warning(
                        f'Expected name "{expected_name}" did not appear after {max_wait_for_name}s, proceeding anyway'
                    )

            # STEP 5: If we still don't have the name, try standard extraction
            if name == "N/A":
                name_selectors = [
                    (By.XPATH, '//div[contains(@class, "m6QErb")]//h1[contains(@class,"DUwDvf")]'),
                    (By.XPATH, '//div[@role="main"]//h1[contains(@class,"DUwDvf")]'),
                    (By.CSS_SELECTOR, "h1.DUwDvf.lfPIob"),
                ]
                for by_type, selector in name_selectors:
                    elem = smart_wait.wait_for_element(
                        by_type, selector, timeout=3, condition="visibility"
                    )
                    if elem and elem.text.strip() and elem.text.strip().lower() != "results":
                        name = elem.text.strip()
                        break

            # Final check
            if name in ["N/A", "Results"]:
                logger.warning(f'Business {i+1}: Could not extract valid name, got "{name}"')

            # STEP 6: Wait a bit more to ensure ALL details are loaded
            logger.debug("Name confirmed, waiting for all details to load...")
            time.sleep(2)  # Extra wait for address, phone, website, etc. to load

            # Extract address with multiple fallback selectors
            address = "N/A"
            address_selectors = [
                (By.XPATH, '//button[contains(@aria-label,"Address")]/div/div[2]/div[1]'),
                (
                    By.XPATH,
                    '//button[@data-item-id="address"]//div[contains(@class,"fontBodyMedium")]',
                ),
                (By.XPATH, '//button[@data-tooltip="Copy address"]'),
                (By.XPATH, '//div[contains(@aria-label,"Address:")]'),
            ]
            for by_type, selector in address_selectors:
                elem = smart_wait.wait_for_element(by_type, selector, timeout=2)
                if elem and elem.text.strip():
                    address = elem.text.strip()
                    logger.debug(f"Found address with {by_type}: {selector}")
                    break

            # Extract website
            website = "N/A"
            website_selectors = [
                (By.XPATH, '//a[contains(@data-item-id,"authority")]'),
                (By.XPATH, '//a[@data-item-id="authority"]'),
                (By.XPATH, '//a[contains(@aria-label,"Website:")]'),
            ]
            for by_type, selector in website_selectors:
                elem = smart_wait.wait_for_element(by_type, selector, timeout=2)
                if elem:
                    href = elem.get_attribute("href")
                    if href and href.strip():
                        website = href
                        logger.debug(f"Found website with {by_type}: {selector}")
                        break

            # Extract phone
            phone = "N/A"
            phone_selectors = [
                (
                    By.XPATH,
                    "//button[contains(@data-item-id,'phone')]//div[contains(@class,'fontBodyMedium')]",
                ),
                (By.XPATH, "//button[@data-tooltip='Copy phone number']"),
                (By.XPATH, "//button[contains(@aria-label,'Phone:')]"),
            ]
            for by_type, selector in phone_selectors:
                elem = smart_wait.wait_for_element(by_type, selector, timeout=2)
                if elem and elem.text.strip():
                    phone = elem.text.strip()
                    logger.debug(f"Found phone with {by_type}: {selector}")
                    break

            # Extract rating and review count. Google Maps often embeds BOTH in a single
            # aria-label ("4.6 stars 1,234 Reviews") on the rating widget, so we look
            # there first; the standalone "N reviews" selectors below are fallbacks.
            rating = "N/A"
            review_count = "N/A"
            rating_selectors = [
                (By.XPATH, '//div[contains(@class,"F7nice")]//span[@role="img"]'),
                (By.XPATH, '//div[contains(@aria-label,"stars")]'),
                (By.XPATH, '//span[contains(@aria-label,"stars")]'),
            ]
            for by_type, selector in rating_selectors:
                elem = smart_wait.wait_for_element(by_type, selector, timeout=2)
                if elem:
                    aria_label = elem.get_attribute("aria-label")
                    if aria_label:
                        rating_match = re.search(r"(\d+\.?\d*)\s+star", aria_label, re.IGNORECASE)
                        if rating_match:
                            rating = rating_match.group(1)
                            logger.debug(f"Found rating in aria-label: {rating}")
                        reviews_match = re.search(
                            r"(\d+(?:,\d+)*)\s+reviews?", aria_label, re.IGNORECASE
                        )
                        if reviews_match:
                            review_count = reviews_match.group(1).replace(",", "")
                            logger.debug(f"Found review count in rating aria-label: {review_count}")
                        if rating != "N/A":
                            break
                    if elem.text.strip():
                        rating = elem.text.strip()
                        logger.debug(f"Found rating text: {rating}")
                        break

            if review_count == "N/A":
                # DOM archaeology (2026-07): Google Maps stopped exposing review
                # count in aria-labels — the rating widget only carries "4.9 stars".
                # When shown at all, the count renders as visible text like "(1,234)"
                # inside the .F7nice container. We read innerText via JS (faster and
                # more resilient to DOM class churn than iterating XPath selectors)
                # and regex the parenthesized number out of it.
                review_count = _extract_review_count_via_js(driver)

            place_url = canonicalize_maps_place_url(driver.current_url)

            # Double-check: Skip if we've already scraped this URL
            if place_url in scraped_links:
                logger.warning(f"Duplicate detected by URL: {place_url} - skipping")
                continue

            # Mark this URL as scraped
            scraped_links.add(place_url)

            # Check if the "website" is actually a social media link
            platform, social_url = detect_social_media_from_url(website)

            social_links = empty_social_links()

            # If website is a social media link, move it to the appropriate column
            if platform:
                social_links[platform] = social_url
                logger.info(
                    f"Website is a {platform} link - moved to {platform} column: {social_url}"
                )
                actual_website = "N/A"  # Set website to N/A since it's actually a social media link
            else:
                actual_website = website
                # Only scrape social links from the website if it's not a social media URL itself
                if website != "N/A":
                    scraped_social = extract_social_and_email_links(website)
                    # Merge scraped social links (don't overwrite if platform was already detected from website URL)
                    for key, value in scraped_social.items():
                        if value and not social_links.get(key):
                            social_links[key] = value

            scraped_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            whatsapp_link = generate_whatsapp_link(phone)

            data.append(
                {
                    "Name": name,
                    "Google Maps Link": place_url,
                    "Address": address,
                    "Phone": phone,
                    "WhatsApp": whatsapp_link,
                    "Website": actual_website,  # Use actual_website (N/A if it was a social media link)
                    "Rating": rating,
                    "Review Count": review_count,
                    "Facebook": social_links["Facebook"],
                    "Instagram": social_links["Instagram"],
                    "Twitter": social_links["Twitter"],
                    "LinkedIn": social_links["LinkedIn"],
                    "YouTube": social_links["YouTube"],
                    "Pinterest": social_links["Pinterest"],
                    "TikTok": social_links["TikTok"],
                    "Threads": social_links["Threads"],
                    "Snapchat": social_links["Snapchat"],
                    "Emails": ", ".join(social_links["Emails"]),
                    "Scraped Time": scraped_time,
                }
            )

            # Log detailed business information
            logger.info(f"✓ Scraped business {i + 1}/{len(results)}: {name}")
            logger.info(f"  └─ Google Maps: {place_url}")
            logger.info(f"  └─ Address: {address}")
            logger.info(f"  └─ Phone: {phone}")
            logger.info(f"  └─ Website: {actual_website}")
            logger.info(f"  └─ Rating: {rating} ({review_count} reviews)")
        except Exception as e:
            logger.error(f"{i + 1}. Failed to scrape business due to: {str(e)}")
        finally:
            # Duplicate streak = "iterations that didn't add a new record".
            # Covers both explicit duplicates (`continue` inside body) and
            # errors — 5 in a row of either means we're not making progress.
            if len(data) > accepted_before:
                duplicate_streak = 0
            else:
                duplicate_streak += 1
            i += 1

    logger.info(f"Scraping completed. Total businesses scraped: {len(data)}")
    return data
