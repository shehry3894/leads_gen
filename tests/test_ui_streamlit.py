"""
Streamlit UI end-to-end tests — spawn `streamlit run app.py`, drive it
with headless Chrome, assert on rendered DOM.

Marked ``ui`` so they're excluded from the default fast suite. Run with:

    uv run pytest -m ui
    # or
    make test-ui

Uses LEADS_GEN_TESTING=true (baked into ``streamlit_server`` fixture) so
"scrape" returns demo data — we're testing the UI wiring, not Google Maps
(that's what ``test-live`` is for).
"""

from __future__ import annotations

import re

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

pytestmark = pytest.mark.ui

HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _wait_text(driver, text, timeout=30):
    """Wait until any visible element contains ``text``."""
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located(
            (By.XPATH, f"//*[contains(normalize-space(.), {repr(text)})]")
        )
    )


def _click_button_with_text(driver, text, timeout=15):
    """Streamlit buttons wrap their label in a <p> inside a <button>."""
    btn = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable(
            (By.XPATH, f"//button[.//p[contains(normalize-space(.), {repr(text)})]]")
        )
    )
    btn.click()


class TestLicenseLandingPage:
    def test_shows_fingerprint_and_trial_button_when_no_license(
        self, streamlit_server, ui_browser, real_license_key_file
    ):
        # Guarantee the landing page renders (no license file present).
        if real_license_key_file.exists():
            real_license_key_file.unlink()

        ui_browser.get(streamlit_server)
        _wait_text(ui_browser, "License Required")

        # Fingerprint block: st.code renders 64 hex chars inside <code>.
        code_els = WebDriverWait(ui_browser, 15).until(
            lambda d: [
                el
                for el in d.find_elements(By.TAG_NAME, "code")
                if HEX64.match(el.text.strip().lower())
            ]
            or False
        )
        assert code_els, "Expected a 64-char hex fingerprint on the landing page"

        # Trial Mode button should be present and clickable.
        WebDriverWait(ui_browser, 5).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[.//p[contains(., 'Start Trial Mode')]]")
            )
        )


class TestTrialModeEndToEnd:
    def test_trial_mode_scrapes_demo_and_renders_results(
        self, streamlit_server, ui_browser, real_license_key_file
    ):
        # Force the trial-mode landing page path.
        if real_license_key_file.exists():
            real_license_key_file.unlink()

        ui_browser.get(streamlit_server)
        _wait_text(ui_browser, "License Required")

        # Enter trial mode.
        _click_button_with_text(ui_browser, "Start Trial Mode")

        # Post-rerun: main UI + "Trial Mode Active" info banner.
        _wait_text(ui_browser, "Trial Mode Active", timeout=20)
        _wait_text(ui_browser, "Enter Search Query")

        # Kick off the scrape. TESTING=true → returns demo data in ~2s.
        _click_button_with_text(ui_browser, "Start Scraping")

        _wait_text(ui_browser, "Scraping completed successfully", timeout=30)

        # render_dataframe writes an HTML <table>. It must have rows beyond
        # the header — otherwise we're rendering an empty frame.
        table = WebDriverWait(ui_browser, 10).until(
            EC.presence_of_element_located((By.XPATH, "//table"))
        )
        body_rows = table.find_elements(By.XPATH, ".//tbody/tr")
        assert body_rows, "Results table has no body rows"

        # Sanity: a canonical column header should be in the table.
        headers = [th.text.strip() for th in table.find_elements(By.XPATH, ".//thead//th")]
        assert "Name" in headers, f"Expected 'Name' header, got {headers!r}"


@pytest.fixture
def valid_license_installed(real_license_key_file, machine_fingerprint):
    """
    Write a valid, machine-bound license file so the UI renders the
    normal (unlocked) main page instead of the trial landing page.
    """
    from leads_gen.licensing.license_codec import encode_license
    from leads_gen.licensing.license_model import create_trial_license

    lic = create_trial_license(machine_fingerprint, days=30, max_results=100)
    real_license_key_file.write_text(encode_license(lic))
    yield real_license_key_file


class TestLicenseSidebar:
    def test_valid_license_unlocks_main_ui_and_shows_sidebar(
        self, streamlit_server, ui_browser, valid_license_installed
    ):
        ui_browser.get(streamlit_server)

        # Sidebar should show License Information block, not the lock screen.
        _wait_text(ui_browser, "License Information", timeout=20)
        _wait_text(ui_browser, "Days Remaining:")
        _wait_text(ui_browser, "Max Results:")

        # Main UI is reachable — the Start Scraping button exists.
        WebDriverWait(ui_browser, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//button[.//p[contains(., 'Start Scraping')]]")
            )
        )

        # The locked-landing-page heading must NOT be on this page.
        assert not ui_browser.find_elements(
            By.XPATH, "//*[contains(normalize-space(.), 'Application Locked')]"
        ), "Landing page 'Application Locked' should not appear with a valid license"


class TestInputValidation:
    def test_invalid_max_results_shows_error(
        self, streamlit_server, ui_browser, valid_license_installed
    ):
        ui_browser.get(streamlit_server)
        _wait_text(ui_browser, "Enter Search Query", timeout=20)

        # Streamlit sets aria-label to match the input's label.
        max_input = WebDriverWait(ui_browser, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//input[contains(@aria-label, 'Max Results')]")
            )
        )
        max_input.clear()
        max_input.send_keys("banana")
        # Blur / commit to trigger Streamlit's rerun.
        max_input.send_keys("\t")

        _wait_text(ui_browser, "Please enter a valid number", timeout=10)


class TestResetButton:
    def test_reset_re_enables_start_after_scrape(
        self, streamlit_server, ui_browser, valid_license_installed
    ):
        ui_browser.get(streamlit_server)
        _wait_text(ui_browser, "Enter Search Query", timeout=20)

        _click_button_with_text(ui_browser, "Start Scraping")
        _wait_text(ui_browser, "Scraping completed successfully", timeout=30)

        # Post-scrape, Start Scraping is disabled (workflow lock).
        btn_locator = (By.XPATH, "//button[.//p[contains(., 'Start Scraping')]]")
        btn = ui_browser.find_element(*btn_locator)
        assert not btn.is_enabled(), "Start button should be disabled after scrape"

        # Reset lives in the sidebar.
        _click_button_with_text(ui_browser, "Reset")

        # Success banner should be gone, Start button clickable again.
        WebDriverWait(ui_browser, 10).until(lambda d: d.find_element(*btn_locator).is_enabled())
        assert not ui_browser.find_elements(
            By.XPATH,
            "//*[contains(normalize-space(.), 'Scraping completed successfully')]",
        ), "Success banner should clear after reset"


class TestAppendModeToggle:
    def test_selecting_append_mode_reveals_file_uploader(
        self, streamlit_server, ui_browser, real_license_key_file
    ):
        # Trial mode is enough for this UI-toggle check.
        if real_license_key_file.exists():
            real_license_key_file.unlink()

        ui_browser.get(streamlit_server)
        _wait_text(ui_browser, "License Required")
        _click_button_with_text(ui_browser, "Start Trial Mode")
        _wait_text(ui_browser, "Enter Search Query", timeout=20)

        # Uploader should NOT be visible yet (default mode is "Start fresh").
        assert not ui_browser.find_elements(
            By.XPATH, "//*[contains(., 'Upload an existing Excel file')]"
        )

        # Switch mode via the sidebar radio.
        append_label = WebDriverWait(ui_browser, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//label[contains(., 'Append to existing Excel file')]")
            )
        )
        append_label.click()

        _wait_text(ui_browser, "Upload an existing Excel file", timeout=10)
        _wait_text(ui_browser, "Or provide the full path to an existing local Excel file")


class TestSidebarTrialToggle:
    def test_sidebar_trial_button_activates_trial_mode(
        self, streamlit_server, ui_browser, valid_license_installed
    ):
        ui_browser.get(streamlit_server)
        _wait_text(ui_browser, "License Information", timeout=20)

        # Sidebar starts with Trial Mode off.
        _wait_text(ui_browser, "Trial Mode: OFF")
        assert not ui_browser.find_elements(
            By.XPATH, "//*[contains(normalize-space(.), 'Trial Mode Active')]"
        ), "Trial banner should not be shown before toggle"

        # Click the sidebar Trial Mode toggle. When the license landing page
        # isn't rendered, this is the only 'Trial Mode' button on the page.
        _click_button_with_text(ui_browser, "Trial Mode")

        _wait_text(ui_browser, "Trial Mode: ON", timeout=10)
        _wait_text(ui_browser, "Trial Mode Active")

        # Max Results input disappears in trial mode (fixed at 3).
        assert not ui_browser.find_elements(
            By.XPATH, "//input[contains(@aria-label, 'Max Results')]"
        )


class TestWorkflowLock:
    def test_mode_radio_locked_after_scrape_starts(
        self, streamlit_server, ui_browser, valid_license_installed
    ):
        ui_browser.get(streamlit_server)
        _wait_text(ui_browser, "Enter Search Query", timeout=20)

        # Pre-scrape: no lock notice.
        assert not ui_browser.find_elements(
            By.XPATH, "//*[contains(normalize-space(.), 'Workflow locked')]"
        )

        _click_button_with_text(ui_browser, "Start Scraping")
        _wait_text(ui_browser, "Scraping completed successfully", timeout=30)

        # Post-scrape: sidebar shows workflow-lock notice, Reset restores it.
        _wait_text(ui_browser, "Workflow locked", timeout=10)


class TestOpenOutputFolderButton:
    def test_open_output_folder_button_appears_after_scrape(
        self, streamlit_server, ui_browser, valid_license_installed
    ):
        ui_browser.get(streamlit_server)
        _wait_text(ui_browser, "Enter Search Query", timeout=20)

        # Not present before scraping.
        assert not ui_browser.find_elements(
            By.XPATH, "//button[.//p[contains(., 'Open Output Folder')]]"
        )

        _click_button_with_text(ui_browser, "Start Scraping")
        _wait_text(ui_browser, "Scraping completed successfully", timeout=30)

        WebDriverWait(ui_browser, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//button[.//p[contains(., 'Open Output Folder')]]")
            )
        )


class TestAppendUploadRoundTrip:
    def test_upload_existing_file_and_scrape_produces_merged_output(
        self, streamlit_server, ui_browser, real_license_key_file, tmp_path
    ):
        """
        Full append flow: upload xlsx → existing data renders → scrape (demo) →
        merged file is written with rows from both sources.

        The uploaded file lands in ``leads_gen/leads_gen_output/`` because
        ``OUTPUT_DIR`` is baked into the running Streamlit subprocess. We use
        a UUID-tagged filename so no other test / real run can collide, and
        we delete it on teardown.
        """
        import uuid

        import openpyxl
        import pandas as pd

        from leads_gen.core.data_normalization import (
            CANONICAL_COLUMNS,
            process_scraped_data,
        )
        from leads_gen.utils.paths import get_ui_output_dir

        # Two unique rows with websites that will NOT collide with demo data
        # (so dedupe keeps them all).
        existing = pd.DataFrame(
            [
                {
                    "Name": "Pre-existing Gym A",
                    "Website": "https://pre-existing-a.test",
                    "Address": "1 Preloaded Way",
                    "Phone": "+1 555-9001",
                },
                {
                    "Name": "Pre-existing Gym B",
                    "Website": "https://pre-existing-b.test",
                    "Address": "2 Preloaded Way",
                    "Phone": "+1 555-9002",
                },
            ]
        )
        canonical = process_scraped_data(existing.to_dict("records"))

        # Unique filename to isolate this test from any other run.
        upload_name = f"pytest_upload_{uuid.uuid4().hex[:8]}.xlsx"
        upload_src = tmp_path / upload_name
        canonical.to_excel(upload_src, index=False)

        # Where the app will save the merged file.
        merged_path = get_ui_output_dir() / upload_name

        # Trial mode path — no license.
        if real_license_key_file.exists():
            real_license_key_file.unlink()

        try:
            ui_browser.get(streamlit_server)
            _wait_text(ui_browser, "License Required")
            _click_button_with_text(ui_browser, "Start Trial Mode")
            _wait_text(ui_browser, "Enter Search Query", timeout=20)

            # Switch to append mode.
            WebDriverWait(ui_browser, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//label[contains(., 'Append to existing Excel file')]")
                )
            ).click()
            _wait_text(ui_browser, "Upload an existing Excel file", timeout=10)

            # Streamlit's file uploader hides its <input type=file>; send_keys
            # to it directly bypasses the click-to-open dialog.
            file_input = WebDriverWait(ui_browser, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
            )
            file_input.send_keys(str(upload_src))

            # Existing data should render before scrape.
            _wait_text(ui_browser, "Existing Data", timeout=20)

            _click_button_with_text(ui_browser, "Start Scraping")
            _wait_text(ui_browser, "Scraping completed successfully", timeout=30)

            # Merged file exists and has header + more rows than we uploaded.
            assert merged_path.exists(), f"Expected merged file at {merged_path}"
            ws = openpyxl.load_workbook(merged_path).active
            assert [c.value for c in ws[1]] == CANONICAL_COLUMNS
            # 2 existing + demo rows (5 in trial-capped output), all unique.
            assert ws.max_row > 3, f"Merged file has only {ws.max_row} rows; expected > 3"
        finally:
            if merged_path.exists():
                merged_path.unlink()
