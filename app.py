# --- FIX FOR PYINSTALLER METADATA ISSUES ---
import os
import subprocess
import sys
import time
from pathlib import Path

from leads_gen.config.settings import TESTING, TRIAL

# Disable pip version checks
os.environ["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

# Workaround for PyInstaller metadata issue
if getattr(sys, "frozen", False):
    # Monkey-patch importlib.metadata
    import importlib.metadata

    # Create patched version function
    def _patched_version(package_name):
        if package_name == "streamlit":
            return "1.45.1"  # Replace with your actual Streamlit version
        try:
            return importlib.metadata.version(package_name)
        except importlib.metadata.PackageNotFoundError:
            return "0.0.0"

    # Apply the patch
    importlib.metadata.version = _patched_version

    # Set fake distribution for Streamlit
    class FakeDistribution:
        def __init__(self):
            self.metadata = {"Name": "streamlit", "Version": "1.45.1"}

        def read_text(self, filename):
            return None

    # Monkey-patch distribution
    def _patched_distribution(package_name):
        if package_name == "streamlit":
            return FakeDistribution()
        return importlib.metadata.distribution(package_name)

    importlib.metadata.distribution = _patched_distribution
    sys.modules["importlib.metadata"] = importlib.metadata

# Set Streamlit environment variables
os.environ["STREAMLIT_RUNNING_IN_PYINSTALLER"] = "true"
os.environ["STREAMLIT_SERVER_ENABLE_STATIC"] = "true"
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
# --- END FIX ---


import logging
import sys
from io import BytesIO

import pandas as pd
import streamlit as st

from leads_gen.core.data_normalization import process_scraped_data
from leads_gen.core.demo_data import get_demo_leads
from leads_gen.licensing.fingerprint import generate_machine_fingerprint
from leads_gen.licensing.license_manager import LicenseManager
from leads_gen.scraper.driver import start_driver
from leads_gen.scraper.scrape import scrape_business_data
from leads_gen.scraper.scroll import scroll_results
from leads_gen.scraper.search import search_maps
from leads_gen.utils.logging_utils import configure_file_logging
from leads_gen.utils.paths import get_ui_output_dir
from leads_gen.version import __app_name__, __version__

# --- Streamlit and Logging Configuration ---
st.set_page_config(page_title="Google Maps Business Scraper", layout="wide")

# Configure logging ONCE per session (not on every rerun)
if "log_file_path" not in st.session_state:
    st.session_state.log_file_path = configure_file_logging()

LOG_FILE_PATH = st.session_state.log_file_path
OUTPUT_DIR = get_ui_output_dir()

# Initialize session state variables
if "output_dir" not in st.session_state:
    st.session_state.output_dir = OUTPUT_DIR

if "scraped_df" not in st.session_state:
    st.session_state.scraped_df = None

if "query" not in st.session_state:
    st.session_state.query = None

if "is_scraping" not in st.session_state:
    st.session_state.is_scraping = False

if "workflow_locked" not in st.session_state:
    st.session_state.workflow_locked = False

if "trial_mode" not in st.session_state:
    st.session_state.trial_mode = False

if "scraping_complete" not in st.session_state:
    st.session_state.scraping_complete = False  # Track if scraping finished successfully

if "uploaded_file_processed" not in st.session_state:
    st.session_state.uploaded_file_processed = {}  # Track which files have been written to disk

logger = logging.getLogger("leads_gen")


def reset_app_state():
    """
    Reset the application state to initial values.
    Keeps log file and license info intact, but clears scraping data and workflow state.
    """
    logger.info("=" * 60)
    logger.info("🔄 APP RESET - User clicked reset button")
    logger.info("=" * 60)

    # Count what's being cleared
    cleared_items = []

    # Clear scraping-related state
    if st.session_state.scraped_df is not None:
        cleared_items.append("scraped data")
        st.session_state.scraped_df = None

    if st.session_state.query:
        cleared_items.append(f"query: '{st.session_state.query}'")
        st.session_state.query = None

    if st.session_state.is_scraping:
        cleared_items.append("scraping flag")
        st.session_state.is_scraping = False

    if st.session_state.workflow_locked:
        cleared_items.append("workflow lock")
        st.session_state.workflow_locked = False

    if st.session_state.trial_mode:
        cleared_items.append("trial mode")
        st.session_state.trial_mode = False

    if st.session_state.scraping_complete:
        cleared_items.append("scraping complete flag")
        st.session_state.scraping_complete = False

    if st.session_state.uploaded_file_processed:
        cleared_items.append("uploaded file tracking")
        st.session_state.uploaded_file_processed = {}

    st.session_state.output_dir = OUTPUT_DIR

    # Keep these intact:
    # - log_file_path (same log file for entire browser session)
    # - license_manager (keep license validation)
    # - logged_start (don't re-log app start)
    # - _logged_keys (keep track of what's been logged to avoid duplicates)

    if cleared_items:
        logger.info("Cleared: %s", ", ".join(cleared_items))
    else:
        logger.info("No active state to clear")

    logger.info("App state reset to initial values")
    logger.info("Log file continues: %s", LOG_FILE_PATH)
    logger.info("License info preserved")
    logger.info("=" * 60)

    st.rerun()


def log_once(key: str, level: str, msg: str, *args):
    """
    Log a message only once per session for a given key.
    This helps avoid noisy duplicates caused by Streamlit reruns.
    """
    # Use a list to keep things JSON-serializable for Streamlit session_state
    if "_logged_keys" not in st.session_state:
        st.session_state._logged_keys = []

    cache = st.session_state._logged_keys
    if key in cache:
        return
    cache.append(key)
    if level == "info":
        logger.info(msg, *args)
    elif level == "warning":
        logger.warning(msg, *args)
    elif level == "error":
        logger.error(msg, *args)
    else:
        logger.log(logging.INFO, msg, *args)


# Only log app start once per browser session
if "logged_start" not in st.session_state:
    log_once(
        "app_started",
        "info",
        "%s v%s started (UI mode). Logs: %s",
        __app_name__,
        __version__,
        LOG_FILE_PATH,
    )
    st.session_state.logged_start = True


# --- Utilities ---
def get_query_and_limit(disabled=False):
    query = st.text_input("Enter Search Query", "gyms in New York", disabled=disabled)

    # In trial mode, always use 3 results
    if st.session_state.trial_mode:
        st.info("🧪 **Trial Mode Active** - Limited to 3 results per search")
        max_results = 3
        log_once(
            f"trial_mode_query:{query}",
            "info",
            "Trial mode: query=%r, max_results=3 (fixed)",
            query,
        )
    else:
        max_input = st.text_input('Max Results (Enter "all" for no limit)', "10", disabled=disabled)
        max_results = (
            None if max_input.lower() == "all" else int(max_input) if max_input.isdigit() else None
        )

        if max_input and max_results is None and max_input.lower() != "all":
            st.error('Please enter a valid number or "all".')
            log_once(
                f"invalid_max:{max_input}", "warning", "Invalid max results input: %s", max_input
            )
        log_once(
            f"query:{query}|max:{max_results if max_results is not None else 'all'}",
            "info",
            "User input: query=%r, max_results=%s",
            query,
            max_results if max_results is not None else "all",
        )

    return query, max_results


def perform_scraping(query, max_results, headless=True, progress_callback=None):
    if TESTING:
        st.info("⚠️ Testing Enabled!")
        for i in range(10):
            time.sleep(0.2)
            if progress_callback:
                progress_callback(i / 10, "Scraping...")

        demo = get_demo_leads()
        logger.info("TESTING=True, using demo leads instead of live scraping (rows=%s)", len(demo))
        return demo

    logger.info(
        "Initializing WebDriver (headless=%s) for query=%r, max_results=%s",
        headless,
        query,
        max_results if max_results is not None else "all",
    )
    from leads_gen.scraper.driver import DriverInitError

    try:
        driver = start_driver(headless=headless)
    except DriverInitError as e:
        # start_driver already logged; re-raise as ScrapingError with a UI-friendly message.
        raise RuntimeError(str(e)) from e

    if TRIAL:
        st.info("⚠️ Scraping 3 results only as you are using trial version")

    data: list = []
    try:
        if progress_callback:
            progress_callback(0.1, "Searching Google Maps...")
        logger.info("Starting search in Google Maps for query=%r", query)
        search_maps(driver, query)

        if progress_callback:
            progress_callback(0.4, "Scrolling through results...")
        logger.info(
            "Starting scroll through results (max_results=%s)",
            max_results if max_results is not None else "all",
        )
        scroll_results(driver, max_results)

        if progress_callback:
            progress_callback(0.7, "Scraping business data...")
        logger.info("Starting scrape of business data")
        data = scrape_business_data(driver, max_results) or []
        logger.info("Scraping complete. Rows scraped: %s", len(data))

        if progress_callback:
            progress_callback(1.0, "Scraping complete.")
    except Exception:
        logger.exception("Error during scraping run")
        raise
    finally:
        logger.info("Shutting down WebDriver")
        try:
            driver.quit()
        except Exception:
            # Chrome may already be dead; don't mask the original exception.
            logger.warning("driver.quit() failed during teardown", exc_info=True)
    return data


def render_clickable_links(df):
    df_display = df.copy()
    for col in df_display.columns:
        # Check if column contains any HTTP links
        # Use try-except to handle cases where .str accessor might fail
        try:
            if df_display[col].dtype == "object":
                # Convert to string type first to ensure .str accessor works
                col_as_str = df_display[col].astype(str)
                if col_as_str.str.contains("http", na=False, case=False).any():
                    df_display[col] = df_display[col].apply(
                        lambda x: (
                            f'<a href="{x}" target="_blank">{x}</a>'
                            if pd.notna(x) and str(x).startswith("http")
                            else x
                        )
                    )
        except (AttributeError, TypeError):
            # If we can't process the column, just skip it
            continue
    return df_display


def render_dataframe(df):
    st.markdown(
        """
        <style>
            table { font-size: 14px; border-collapse: collapse; }
            th, td { padding: 4px 8px !important; white-space: nowrap; max-width: 200px; overflow: hidden; text-overflow: ellipsis; }
        </style>
    """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""<div style="overflow-x: auto">{df.to_html(escape=False, index=False)}</div>""",
        unsafe_allow_html=True,
    )


def create_excel_with_links(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Sheet1", index=False)
        workbook = writer.book
        worksheet = writer.sheets["Sheet1"]
        link_format = workbook.add_format({"font_color": "blue", "underline": 1})

        for col in df.columns:
            if df[col].dtype != "object":
                continue
            col_as_str = df[col].astype(str)
            if not col_as_str.str.startswith("http").any():
                continue
            col_idx = df.columns.get_loc(col)
            for row_num, val in enumerate(df[col], start=1):
                if pd.notna(val) and str(val).startswith("http"):
                    worksheet.write_url(row_num, col_idx, val, link_format, val)
    return output.getvalue()


def start_scraping_callback():
    st.session_state.is_scraping = True
    st.session_state.workflow_locked = True


def open_folder(path):
    folder = Path(path)
    abs_path = str(folder.resolve())
    logger.info("open_folder called for %s", abs_path)

    if not folder.exists():
        st.error(f"Folder does not exist: {abs_path}")
        return

    try:
        if sys.platform.startswith("darwin"):  # macOS
            subprocess.Popen(
                ["open", abs_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif sys.platform.startswith("win"):  # Windows
            os.startfile(abs_path)  # noqa: S606 — Windows-only, path is validated above
        elif sys.platform.startswith("linux"):  # Linux
            subprocess.Popen(
                ["xdg-open", abs_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            st.error("Unsupported OS for opening folders")
    except FileNotFoundError:
        # e.g., xdg-open not installed on a minimal Linux, or `open` missing on stripped macOS.
        logger.error("Folder-open helper not found for platform %s", sys.platform)
        st.error(
            "Could not launch the file manager. Please open this folder manually:\n" f"{abs_path}"
        )
    except OSError as e:
        logger.exception("Failed to open folder %s", abs_path)
        st.error(f"Could not open folder: {e}. Please open manually:\n{abs_path}")


def handle_result_display(df):
    render_dataframe(render_clickable_links(df))


def save_excel(df, file_path) -> bool:
    """
    Write ``df`` to Excel at ``file_path``. Surfaces disk-full, permission-denied,
    and file-locked errors as user-visible ``st.error`` calls. Returns True on
    success, False on any handled failure.
    """
    try:
        output_dir = Path(st.session_state.output_dir)
        if not output_dir.exists():
            st.info(f"{output_dir} does not exist! Creating dir...")
            output_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        logger.error("Permission denied creating output dir: %s", st.session_state.output_dir)
        st.error(f"Permission denied creating folder: {st.session_state.output_dir}")
        return False
    except OSError as e:
        logger.exception("Could not create output dir")
        st.error(f"Could not create output folder: {e}")
        return False

    logger.info("Saving DataFrame to %s: %s rows, %s columns", file_path, len(df), len(df.columns))

    try:
        df.to_excel(file_path, index=False, engine="openpyxl")
    except PermissionError:
        logger.exception("Permission denied writing Excel to %s", file_path)
        st.error(
            "Could not save the Excel file — permission denied. "
            "The file may be open in Excel, or the folder is read-only.\n\n"
            f"Path: {file_path}"
        )
        return False
    except OSError as e:
        # Disk full, path-too-long, invalid characters, etc.
        msg = str(e).lower()
        hint = ""
        if "no space" in msg or "enospc" in msg:
            hint = " The disk appears to be full."
        elif "file name too long" in msg or "enametoolong" in msg:
            hint = " The file name/path is too long — try a shorter query."
        logger.exception("Excel save failed for %s", file_path)
        st.error(f"Could not save Excel file to {file_path}.{hint} Details: {e}")
        return False

    # Verify the save by reading back.
    try:
        verify_df = pd.read_excel(file_path)
        logger.info("Save verified: %s rows written to %s", len(verify_df), file_path)
        if len(verify_df) != len(df):
            logger.error(
                "SAVE MISMATCH: expected %s rows but file has %s rows", len(df), len(verify_df)
            )
            st.warning(
                f"Save verification mismatch: expected {len(df)} rows, "
                f"file has {len(verify_df)}. Data may be truncated."
            )
    except Exception:
        # Verification is best-effort; don't fail the save on read-back errors.
        logger.warning("Could not verify save for %s", file_path, exc_info=True)

    return True


# --- Main Application ---
def main():
    st.title("Business Leads Generator")

    # --- Sidebar: License Information ---
    st.sidebar.header("📋 License Information")

    # Initialize license manager and get info
    license_valid = False
    license_message = ""

    try:
        if "license_manager" not in st.session_state:
            st.session_state.license_manager = LicenseManager()
            success, message = st.session_state.license_manager.initialize()
            st.session_state.license_init_success = success
            st.session_state.license_init_message = message

        license_manager = st.session_state.license_manager
        license_info = license_manager.get_license_info()

        # Display license details
        if license_info["valid"]:
            license_valid = True
            license_type = license_info["type"]
            days_remaining = license_info["days_remaining"]
            max_results = license_info["max_results"]
            expiry_date = license_info["expiry_date"]

            # Color-code based on days remaining
            if days_remaining > 30:
                status_emoji = "✅"
                status_color = "green"
            elif days_remaining > 7:
                status_emoji = "⚠️"
                status_color = "orange"
            else:
                status_emoji = "🔴"
                status_color = "red"

            st.sidebar.markdown(f"**License Type:** {license_type}")
            st.sidebar.markdown(f"**Status:** {status_emoji} Active")
            st.sidebar.markdown(f"**Expires:** {expiry_date}")
            st.sidebar.markdown(f"**Days Remaining:** :{status_color}[{days_remaining} days]")
            st.sidebar.markdown(f"**Max Results:** {max_results} per run")

            # Warning if expiring soon
            if days_remaining <= 7:
                st.sidebar.warning(f"⚠️ License expiring in {days_remaining} days!")
        else:
            license_valid = False
            license_message = st.session_state.get("license_init_message", "No license file found")
            st.sidebar.error("❌ No Valid License")
            st.sidebar.markdown("**Action Required:** Activate license to unlock the limitations")
    except Exception as e:
        license_valid = False
        license_message = str(e)
        st.sidebar.error("❌ License Error")
        st.sidebar.markdown("Unable to validate license")
        log_once("license_error", "error", f"License check error: {str(e)}")

    st.sidebar.markdown("---")

    # --- Check license before allowing any operations ---
    # Allow trial mode to bypass license check
    if not license_valid and not st.session_state.trial_mode:
        st.error("🔒 License Required")
        st.markdown("### Application Locked - Valid License Required")
        st.markdown(f"""
        This application requires a valid license to operate. Your current license status:

        **Status:** ❌ Invalid or Missing

        **Error:** {license_message}
        """)

        st.markdown("---")

        # Generate and display machine fingerprint
        st.markdown("### 🔑 Your Machine Fingerprint")
        st.markdown(
            "**Copy the fingerprint below and send it to your administrator to get a license key:**"
        )

        try:
            machine_fingerprint = generate_machine_fingerprint()
            st.code(machine_fingerprint, language=None)
            st.success(
                "✅ Fingerprint generated successfully. Copy the code above and send it to get your license."
            )
        except Exception as e:
            st.error(f"❌ Could not generate fingerprint: {str(e)}")
            st.markdown("Please contact your administrator for assistance.")

        st.markdown("---")

        st.markdown("""
        ### 📋 How to Activate Your License

        **Step 1:** Copy your machine fingerprint shown above (click the copy button)

        **Step 2:** Send the fingerprint to your administrator or support team

        **Step 3:** You will receive a license key from the administrator

        **Step 4:** Give the license key to your administrator to activate it on this machine

        **Step 5:** Refresh this page after activation

        ---

        ### 📞 Need Help?

        Contact your system administrator or support team with your fingerprint to get a license key.
        """)

        st.markdown("---")

        # Trial Mode Option
        st.markdown("### 🧪 Try Without License (Trial Mode)")
        st.markdown("**Want to test the app with limited features?**")
        st.markdown("Trial mode allows you to scrape up to 3 results per search without a license.")

        if st.button(
            "🧪 Start Trial Mode (3 Results Max)", type="primary", use_container_width=True
        ):
            st.session_state.trial_mode = True
            license_valid = True  # Bypass license check for trial
            logger.info("User activated Trial Mode without license - limited to 3 results")
            st.rerun()

        # Stop execution here - don't show any other UI elements
        st.stop()

    # --- Sidebar: App Control ---
    st.sidebar.header("🔄 App Control")

    # Trial Mode Toggle
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button(
            "🧪 Trial Mode",
            use_container_width=True,
            type="primary" if st.session_state.trial_mode else "secondary",
        ):
            st.session_state.trial_mode = not st.session_state.trial_mode
            logger.info(
                f"Trial mode {'ENABLED' if st.session_state.trial_mode else 'DISABLED'} by user"
            )
            st.rerun()
    with col2:
        if st.button("🔄 Reset", use_container_width=True, type="secondary"):
            reset_app_state()

    # Show trial mode status
    if st.session_state.trial_mode:
        st.sidebar.success("🧪 Trial Mode: ON (3 results max)")
    else:
        st.sidebar.caption("Trial Mode: OFF")

    st.sidebar.caption("Reset: Clear app state, keep logs")

    st.sidebar.markdown("---")

    # --- Sidebar: high-level workflow selection ---
    st.sidebar.header("Workflow")
    st.sidebar.markdown(
        "- **Start fresh**: create a brand new Excel file from a new search query.\n"
        "- **Append to existing**: add new leads into an existing Excel file you already have."
    )

    mode_options = {
        "Start fresh (new Excel file)": "new",
        "Append to existing Excel file": "append",
    }
    selected_mode_label = st.sidebar.radio(
        "What would you like to do?",
        list(mode_options.keys()),
        index=0,
        disabled=st.session_state.workflow_locked,
    )
    scrape_option = mode_options[selected_mode_label]
    log_once(f"mode:{scrape_option}", "info", "User selected workflow mode: %s", scrape_option)

    # Show message when workflow is locked
    if st.session_state.workflow_locked:
        st.sidebar.info("🔒 Workflow locked. Press Reset Button to change modes.")

    # Placeholders for progress feedback, reused in both flows
    progress_bar = st.empty()
    status_text = st.empty()

    def update_progress(pct, msg: str):
        # Streamlit reruns can invalidate the underlying placeholder DeltaGenerator
        # (e.g., session refresh mid-scrape). Log and continue instead of crashing
        # the whole scrape run.
        try:
            progress_bar.progress(pct)
            status_text.text(msg)
        except Exception:
            logger.debug("progress_callback skipped (session likely reloaded)", exc_info=True)

    if scrape_option == "new":
        st.subheader("Start fresh with a new search")
        st.session_state.output_dir = OUTPUT_DIR

        query, max_results = get_query_and_limit()

        # Let the user control where the new Excel file will be saved
        default_folder = str(st.session_state.output_dir)
        folder_input = st.text_input(
            "Folder where the new Excel file will be saved",
            value=default_folder,
            help="Change this to any existing folder on your system.",
        )
        if folder_input:
            st.session_state.output_dir = Path(folder_input)
            log_once(
                f"new_output_dir:{st.session_state.output_dir}",
                "info",
                "User set output folder (new mode) to: %s",
                st.session_state.output_dir,
            )

        file_name = f'{query.replace(" ", "_")}.xlsx' if query else "leads.xlsx"
        file_path = os.path.join(st.session_state.output_dir, file_name)

        st.info(f"New data will be saved to: {file_path}")
        log_once(
            f"new_output_file:{file_path}",
            "info",
            "Planned output file for new mode: %s",
            file_path,
        )

        # Disable start button when scraping is in progress OR when scraping is complete
        start_button_disabled = st.session_state.is_scraping or st.session_state.scraping_complete

        # Show info message if scraping is complete
        if st.session_state.scraping_complete:
            st.success("✅ Scraping completed! Use the Reset button below to start a new scrape.")

        # Show status message if scraping is in progress
        if st.session_state.is_scraping and not st.session_state.scraping_complete:
            st.warning("🔄 Scraping in progress... Please wait.")

        start_clicked = st.button(
            "Start Scraping",
            disabled=start_button_disabled,
            on_click=start_scraping_callback,
            use_container_width=True,
        )

        if start_clicked and query:
            log_once(
                f"start_new:{query}",
                "info",
                "Start Scraping button clicked (new mode) for query=%r",
                query,
            )
            st.session_state.scraped_df = None
            st.session_state.scraping_complete = False  # Reset completion flag

            progress_bar = st.progress(0)
            status_text = st.empty()

            try:
                data_raw = perform_scraping(query, max_results, progress_callback=update_progress)

                # Process and normalize scraped data
                data = process_scraped_data(data_raw)

                # Save data to session state
                st.session_state.scraped_df = data
                st.session_state.query = query

            except Exception as e:
                logger.error("Scraping failed in new mode for query=%r: %s", query, str(e))
                st.error("An unexpected error occurred during scraping. Please check the logs.")
                st.session_state.is_scraping = False
                return

            # Reset flags
            st.session_state.is_scraping = False
            st.session_state.scraping_complete = True

            # Save results to Excel
            if len(data) > 0:
                save_excel(st.session_state.scraped_df, file_path)
                logger.info(
                    "Excel file saved: %s (rows=%s)",
                    file_path,
                    len(st.session_state.scraped_df.index),
                )
                st.success("✅ Scraping completed successfully!")

                file_name = Path(file_path).name
                st.code(f"File created: {file_name}\nLocation: {file_path}", language="text")
            else:
                st.warning("No data was collected.")

    elif scrape_option == "append":
        st.subheader("Append new leads to an existing file")
        file_path = None

        # Show info if inputs are disabled
        if st.session_state.scraping_complete:
            st.info(
                "✅ Scraping complete! File selection is locked. Use the Reset button to start a new scrape."
            )

        # Disable file upload if scraping is complete to prevent overwriting merged file
        uploaded_file = st.file_uploader(
            "Upload an existing Excel file (.xlsx)",
            type=["xlsx"],
            disabled=st.session_state.scraping_complete,
            help=(
                "Upload disabled after scraping completes. Use Reset to upload a new file."
                if st.session_state.scraping_complete
                else None
            ),
        )

        # If file is uploaded, save it to OUTPUT_DIR and show the path
        uploaded_file_path = ""
        if uploaded_file is not None:
            # Save uploaded file to OUTPUT_DIR (same location where we save new files)
            uploaded_file_path = str(OUTPUT_DIR / uploaded_file.name)

            # Create a unique key for this upload (filename + size)
            upload_key = f"{uploaded_file.name}_{uploaded_file.size}"

            # Only write the uploaded file ONCE and not after scraping completes
            # This prevents overwriting the merged file after scraping
            if (
                upload_key not in st.session_state.uploaded_file_processed
                and not st.session_state.scraping_complete
            ):
                # Write the uploaded file to disk. If this fails partway (disk full,
                # permission denied), we surface the error and abort — otherwise
                # downstream read_excel would blame the "corrupt" file, hiding the
                # real cause.
                try:
                    with open(uploaded_file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                except PermissionError:
                    logger.exception("Permission denied writing upload to %s", uploaded_file_path)
                    st.error(
                        f"Permission denied saving the upload to {uploaded_file_path}. "
                        "Try uploading to a different folder or run the app with write access."
                    )
                    return
                except OSError as e:
                    logger.exception("Failed to save uploaded file to %s", uploaded_file_path)
                    st.error(f"Could not save the uploaded file: {e}")
                    return

                st.session_state.uploaded_file_processed[upload_key] = True
                logger.info("Uploaded file saved to: %s", uploaded_file_path)
            else:
                logger.debug("Skipping file upload write - already processed or scraping complete")

        path_input = st.text_input(
            "Or provide the full path to an existing local Excel file",
            value=uploaded_file_path if uploaded_file is not None else "",
            placeholder="C:/Users/Name/Documents/leads.xlsx",
            disabled=uploaded_file is not None or st.session_state.scraping_complete,
            help=(
                "Input disabled after scraping completes. Use Reset to select a new file."
                if st.session_state.scraping_complete
                else "If you don't upload a file above, this local path will be used."
            ),
        )

        # Logic to decide which path to use
        error = False
        if path_input:
            if os.path.exists(path_input):
                if uploaded_file:
                    st.info(f"Using uploaded file: {uploaded_file.name}")
                    log_once(
                        f"upload:{uploaded_file.name}",
                        "info",
                        "User uploaded existing Excel file: %s (saved to: %s)",
                        uploaded_file.name,
                        path_input,
                    )
                else:
                    st.success(f"Using local path: {path_input}")
                    log_once(
                        f"path:{path_input}",
                        "info",
                        "User selected existing Excel file via path: %s",
                        path_input,
                    )
            else:
                st.error("Invalid local path.")
                error = True
                log_once(
                    f"invalid_path:{path_input}",
                    "warning",
                    "User provided invalid path for existing Excel file: %s",
                    path_input,
                )

        if (not error) and path_input:
            # Only load the file if we don't already have scraped data from append mode
            # This prevents reloading the original file after we've saved the merged data
            if st.session_state.scraped_df is None or not st.session_state.scraping_complete:
                try:
                    df_existing = pd.read_excel(path_input)
                    logger.info(
                        "Existing file loaded from %s (rows=%s)", path_input, len(df_existing.index)
                    )
                except Exception:
                    st.error(
                        "Failed to read the existing Excel file. Please verify the file and try again."
                    )
                    logger.exception("Failed to read existing Excel file")
                    return
            else:
                # If scraping is complete, reload the merged file to show updated data
                try:
                    df_existing = pd.read_excel(path_input)
                    logger.info(
                        "Reloading updated file after append: %s (rows=%s)",
                        path_input,
                        len(df_existing.index),
                    )
                except Exception:
                    logger.error("Failed to reload updated file, using session state data")
                    df_existing = st.session_state.scraped_df

            # Show current data - merged if available, otherwise original
            if st.session_state.scraped_df is not None and st.session_state.scraping_complete:
                st.write("Current Data (After Merge)...")
                st.info(f"Showing merged results: {len(st.session_state.scraped_df)} total rows")
                render_dataframe(render_clickable_links(st.session_state.scraped_df))
            else:
                st.write("Existing Data (Before Scraping)...")
                render_dataframe(render_clickable_links(df_existing))

            # Disable query/max inputs if scraping is complete
            query, max_results = get_query_and_limit(disabled=st.session_state.scraping_complete)
            file_name = f'{query.replace(" ", "_")}.xlsx'
            file_path = os.path.join(OUTPUT_DIR, file_name)
            if path_input:
                file_path = path_input
                st.session_state.output_dir = Path(file_path).parent
            log_once(
                f"append_output_file:{file_path}",
                "info",
                "Planned output file for append mode: %s",
                file_path,
            )

            # Disable start button when scraping is in progress OR when scraping is complete
            start_button_disabled_append = (
                st.session_state.is_scraping or st.session_state.scraping_complete
            )

            # Show info message if scraping is complete
            if st.session_state.scraping_complete:
                st.success(
                    "✅ Scraping completed! Use the Reset button below to start a new scrape."
                )

            # Show status message if scraping is in progress
            if st.session_state.is_scraping and not st.session_state.scraping_complete:
                st.warning("🔄 Scraping in progress... Please wait.")

            start_clicked_append = st.button(
                "Start Scraping",
                disabled=start_button_disabled_append,
                on_click=start_scraping_callback,
                use_container_width=True,
                key="start_append_btn",
            )

            if start_clicked_append and query:
                log_once(
                    f"start_append:{query}",
                    "info",
                    "Start Scraping button clicked (append mode) for query=%r",
                    query,
                )
                st.session_state.scraped_df = None
                st.session_state.scraping_complete = False  # Reset completion flag

                progress_bar = st.progress(0)
                status_text = st.empty()

                # Initialize variables
                new_data = pd.DataFrame()
                data = pd.DataFrame()

                try:
                    new_data_raw = perform_scraping(
                        query, max_results, progress_callback=update_progress
                    )

                    # Process and normalize new scraped data
                    new_data = process_scraped_data(new_data_raw)

                    # Combine existing and new data, then deduplicate
                    data = pd.concat([df_existing, new_data], ignore_index=True)
                    from leads_gen.core.data_normalization import deduplicate_dataframe

                    data = deduplicate_dataframe(data)
                    logger.info(
                        "Append mode: existing rows=%s, new rows=%s, combined rows=%s",
                        len(df_existing.index),
                        len(new_data.index),
                        len(data.index),
                    )

                    # Save data to session state
                    st.session_state.scraped_df = data
                    st.session_state.query = query

                except Exception as e:
                    logger.error("Scraping failed in append mode for query=%r: %s", query, str(e))
                    st.error("An unexpected error occurred during scraping. Please check the logs.")
                    st.session_state.is_scraping = False
                    return

                # Reset flags
                st.session_state.is_scraping = False
                st.session_state.scraping_complete = True

                # Save the combined data
                if st.session_state.scraped_df is not None and len(st.session_state.scraped_df) > 0:
                    save_excel(st.session_state.scraped_df, file_path)
                    logger.info(
                        "Existing Excel file updated: %s (total rows=%s, new rows=%s)",
                        file_path,
                        len(st.session_state.scraped_df),
                        len(new_data),
                    )
                    st.success(
                        f"✅ Scraping completed successfully! Added {len(new_data)} new rows (total: {len(st.session_state.scraped_df)} rows)."
                    )

                    file_name = Path(file_path).name
                    st.code(
                        f"Existing file updated: {file_name}\nLocation: {file_path}",
                        language="text",
                    )
                else:
                    st.warning("No new data was collected.")

    if file_path and (st.session_state.scraped_df is not None):
        st.subheader("Result")
        st.markdown("---")

        handle_result_display(st.session_state.scraped_df)

        # Use on_click to trigger the function BEFORE the script reruns
        st.button(
            "📂 Open Output Folder",
            on_click=open_folder,
            args=(st.session_state.output_dir,),
            help="Click to open the folder containing your Excel files",
        )


if __name__ == "__main__":
    main()
