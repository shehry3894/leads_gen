# --- FIX FOR PYINSTALLER METADATA ISSUES ---
import os
import sys
import subprocess
import time
from pathlib import Path

from leads_gen.config.settings import TESTING, TRIAL

# Disable pip version checks
os.environ["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

# Workaround for PyInstaller metadata issue
if getattr(sys, 'frozen', False):
    # Monkey-patch importlib.metadata
    import importlib.metadata
    import types


    # Create patched version function
    def _patched_version(package_name):
        if package_name == 'streamlit':
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
            self.metadata = {'Name': 'streamlit', 'Version': '1.45.1'}

        def read_text(self, filename):
            return None


    # Monkey-patch distribution
    def _patched_distribution(package_name):
        if package_name == 'streamlit':
            return FakeDistribution()
        return importlib.metadata.distribution(package_name)


    importlib.metadata.distribution = _patched_distribution
    sys.modules['importlib.metadata'] = importlib.metadata

# Set Streamlit environment variables
os.environ["STREAMLIT_RUNNING_IN_PYINSTALLER"] = "true"
os.environ["STREAMLIT_SERVER_ENABLE_STATIC"] = "true"
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
# --- END FIX ---


import streamlit as st
import pandas as pd
import logging
from io import BytesIO

from leads_gen.scraper.driver import start_driver
from leads_gen.scraper.search import search_maps
from leads_gen.scraper.scroll import scroll_results
from leads_gen.scraper.scrape import scrape_business_data
from leads_gen.utils.logging_utils import configure_file_logging
from leads_gen.core.demo_data import get_demo_leads
from leads_gen.utils.paths import get_ui_output_dir
from leads_gen.core.data_normalization import process_scraped_data
from leads_gen.version import __version__, __app_name__
from leads_gen.licensing.license_manager import LicenseManager

import sys

# --- Streamlit and Logging Configuration ---
st.set_page_config(page_title='Google Maps Business Scraper', layout='wide')

# Configure logging ONCE per session (not on every rerun)
if "log_file_path" not in st.session_state:
    st.session_state.log_file_path = configure_file_logging()

LOG_FILE_PATH = st.session_state.log_file_path
OUTPUT_DIR = get_ui_output_dir()

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

logger = logging.getLogger("leads_gen")

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
    log_once("app_started", "info", "%s v%s started (UI mode). Logs: %s", __app_name__, __version__, LOG_FILE_PATH)
    st.session_state.logged_start = True


# --- Utilities ---
def get_query_and_limit():
    query = st.text_input('Enter Search Query', 'gyms in New York')
    max_input = st.text_input('Max Results (Enter "all" for no limit)', '10')
    max_results = None if max_input.lower() == 'all' else int(max_input) if max_input.isdigit() else None

    if max_input and max_results is None and max_input.lower() != 'all':
        st.error('Please enter a valid number or "all".')
        log_once(f"invalid_max:{max_input}", "warning", "Invalid max results input: %s", max_input)
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
            progress_callback(i / 10, 'Scarping...')

        demo = get_demo_leads()
        logger.info("TESTING=True, using demo leads instead of live scraping (rows=%s)", len(demo))
        return demo

    logger.info("Initializing WebDriver (headless=%s) for query=%r, max_results=%s",
                headless, query, max_results if max_results is not None else "all")
    driver = start_driver(headless=headless)

    if TRIAL:
        st.info("⚠️ Scraping 3 results only as you are using trial version")
    try:
        if progress_callback: progress_callback(0.1, 'Searching Google Maps...')
        logger.info("Starting search in Google Maps for query=%r", query)
        search_maps(driver, query)

        if progress_callback: progress_callback(0.4, 'Scrolling through results...')
        logger.info("Starting scroll through results (max_results=%s)",
                    max_results if max_results is not None else "all")
        scroll_results(driver, max_results)

        if progress_callback: progress_callback(0.7, 'Scraping business data...')
        logger.info("Starting scrape of business data")
        data = scrape_business_data(driver, max_results)
        logger.info("Scraping complete. Rows scraped: %s", len(data) if data is not None else 0)

        if progress_callback: progress_callback(1.0, 'Scraping complete.')
    except Exception as e:
        logger.exception("Error during scraping run: %s", e)
        raise
    finally:
        logger.info("Shutting down WebDriver")
        driver.quit()
    return data


def render_clickable_links(df):
    df_display = df.copy()
    for col in df_display.columns:
        # Check if column contains any HTTP links
        # Use try-except to handle cases where .str accessor might fail
        try:
            if df_display[col].dtype == 'object':
                # Convert to string type first to ensure .str accessor works
                col_as_str = df_display[col].astype(str)
                if col_as_str.str.contains('http', na=False, case=False).any():
                    df_display[col] = df_display[col].apply(
                        lambda x: f'<a href="{x}" target="_blank">{x}</a>' if pd.notna(x) and str(x).startswith('http') else x
                    )
        except (AttributeError, TypeError):
            # If we can't process the column, just skip it
            continue
    return df_display


def render_dataframe(df):
    st.markdown("""
        <style>
            table { font-size: 14px; border-collapse: collapse; }
            th, td { padding: 4px 8px !important; white-space: nowrap; max-width: 200px; overflow: hidden; text-overflow: ellipsis; }
        </style>
    """, unsafe_allow_html=True)
    st.markdown(f"""<div style="overflow-x: auto">{df.to_html(escape=False, index=False)}</div>""",
                unsafe_allow_html=True)


def create_excel_with_links(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Sheet1', index=False)
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        link_format = workbook.add_format({'font_color': 'blue', 'underline': 1})

        for col in df.columns:
            if df[col].dtype == 'object' and df[col].str.startswith('http').any():
                col_idx = df.columns.get_loc(col)
                for row_num, val in enumerate(df[col], start=1):
                    if pd.notna(val) and str(val).startswith('http'):
                        worksheet.write_url(row_num, col_idx, val, link_format, val)
    return output.getvalue()


def start_scraping_callback():
    st.session_state.is_scraping = True
    st.session_state.workflow_locked = True


def open_folder(path: str):
    abs_path = os.path.abspath(str(path))

    # Debugging: This will show up in your terminal/command prompt
    print(f"DEBUG: open_folder called for {abs_path}")

    if not path.exists():
        raise st.error(f"Folder does not exist: {path}")

    if sys.platform.startswith("darwin"):  # macOS
        subprocess.Popen(["open", path])
    elif sys.platform.startswith("win"):  # Windows
        os.startfile(path)
    elif sys.platform.startswith("linux"):  # Linux
        subprocess.Popen(["xdg-open", path])
    else:
        raise RuntimeError("Unsupported OS")


def handle_result_display(df):
    render_dataframe(render_clickable_links(df))


def save_excel(df, file_path):
    # df = create_excel_with_links(df)
    if not os.path.exists(st.session_state.output_dir):
        st.info('{st.session_state.output_dir} does not exist! Creating dir...')
        st.session_state.output_dir.mkdir(exist_ok=True)
    df.to_excel(file_path, index=False)


# --- Main Application ---
def main():
    st.title('Business Leads Generator')

    # --- Sidebar: License Information ---
    st.sidebar.header("📋 License Information")
    
    # Initialize license manager and get info
    try:
        if "license_manager" not in st.session_state:
            st.session_state.license_manager = LicenseManager()
            st.session_state.license_manager.initialize()
        
        license_manager = st.session_state.license_manager
        license_info = license_manager.get_license_info()
        
        # Display license details
        if license_info['is_valid']:
            license_type = license_info['type']
            days_remaining = license_info['days_remaining']
            max_results = license_info['max_results']
            expiry_date = license_info['expiry_date']
            
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
            st.sidebar.error("❌ No Valid License")
            st.sidebar.markdown("Contact support for license key.")
    except Exception as e:
        st.sidebar.warning("⚠️ License check skipped")
        log_once("license_error", "warning", f"License check error: {str(e)}")
    
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
        st.sidebar.info("🔒 Workflow locked. Refresh your browser to change modes.")

    # Placeholders for progress feedback, reused in both flows
    progress_bar = st.empty()
    status_text = st.empty()

    def update_progress(pct, msg: str):
        progress_bar.progress(pct)
        status_text.text(msg)

    if scrape_option == 'new':
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

        st.info(f'New data will be saved to: {file_path}')
        log_once(
            f"new_output_file:{file_path}",
            "info",
            "Planned output file for new mode: %s",
            file_path,
        )

        if st.button("Start Scraping",
                     disabled=st.session_state.is_scraping,
                     on_click=start_scraping_callback) and query:
            log_once(
                f"start_new:{query}",
                "info",
                "Start Scraping button clicked (new mode) for query=%r",
                query,
            )
            st.session_state.scraped_df = None

            progress_bar = st.progress(0)
            status_text = st.empty()

            try:
                data_raw = perform_scraping(query, max_results, progress_callback=update_progress)
                # Process and normalize scraped data
                data = process_scraped_data(data_raw)
            except Exception:
                st.error("An unexpected error occurred during scraping. Please check the logs.")
                logger.error("Scraping failed in new mode for query=%r", query)
                st.session_state.is_scraping = False
                return

            st.session_state.scraped_df = data
            st.session_state.query = query

            status_text.success("✅ Finished successfully.")
            progress_bar.empty()

            st.session_state.is_scraping = False

            save_excel(st.session_state.scraped_df, file_path)
            logger.info(
                "New Excel file saved: %s (rows=%s)",
                file_path,
                len(st.session_state.scraped_df.index),
            )

            file_name = Path(file_path).name
            st.code(f"New file created: {file_name}\nLocation: {file_path}", language="text")

    elif scrape_option == 'append':
        st.subheader("Append new leads to an existing file")
        file_path = None

        uploaded_file = st.file_uploader('Upload an existing Excel file (.xlsx)', type=['xlsx'])
        
        # If file is uploaded, save it to OUTPUT_DIR and show the path
        uploaded_file_path = ""
        if uploaded_file is not None:
            # Save uploaded file to OUTPUT_DIR (same location where we save new files)
            uploaded_file_path = str(OUTPUT_DIR / uploaded_file.name)
            
            # Write the uploaded file to disk
            with open(uploaded_file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            logger.info(f"Uploaded file saved to: {uploaded_file_path}")

        path_input = st.text_input(
            "Or provide the full path to an existing local Excel file",
            value=uploaded_file_path if uploaded_file is not None else "",
            placeholder="C:/Users/Name/Documents/leads.xlsx",
            disabled=uploaded_file is not None,
            help="If you don't upload a file above, this local path will be used.",
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
            try:
                df_existing = pd.read_excel(path_input)
                logger.info("Existing file loaded from %s (rows=%s)", path_input, len(df_existing.index))
            except Exception:
                st.error("Failed to read the existing Excel file. Please verify the file and try again.")
                logger.exception("Failed to read existing Excel file")
                return

            st.write('Existing Data...')
            render_dataframe(render_clickable_links(df_existing))

            query, max_results = get_query_and_limit()
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

            if st.button("Start Scraping",
                         disabled=st.session_state.is_scraping,
                         on_click=start_scraping_callback) and query:
                log_once(
                    f"start_append:{query}",
                    "info",
                    "Start Scraping button clicked (append mode) for query=%r",
                    query,
                )
                st.session_state.scraped_df = None

                progress_bar = st.progress(0)
                status_text = st.empty()

                try:
                    new_data_raw = perform_scraping(query, max_results, progress_callback=update_progress)
                    # Process and normalize new scraped data
                    new_data = process_scraped_data(new_data_raw)
                except Exception:
                    st.error("An unexpected error occurred during scraping. Please check the logs.")
                    logger.error("Scraping failed in append mode for query=%r", query)
                    st.session_state.is_scraping = False
                    return

                # Combine existing and new data, then deduplicate
                data = pd.concat([df_existing, new_data], ignore_index=True)
                # Re-deduplicate the combined dataset
                from utils.data_normalization import deduplicate_dataframe
                data = deduplicate_dataframe(data)
                logger.info(
                    "Append mode: existing rows=%s, new rows=%s, combined rows=%s",
                    len(df_existing.index),
                    len(new_data.index),
                    len(data.index),
                )

                st.session_state.scraped_df = data
                st.session_state.query = query

                status_text.text("✅ Updated file ready.")
                progress_bar.empty()

                st.session_state.is_scraping = False

                save_excel(st.session_state.scraped_df, file_path)
                logger.info(
                    "Existing Excel file updated: %s (rows=%s)",
                    file_path,
                    len(st.session_state.scraped_df.index),
                )

                file_name = Path(file_path).name
                st.code(
                    f"Existing file updated: {file_name}\nLocation: {file_path}",
                    language="text",
                )

    if file_path and (st.session_state.scraped_df is not None):
        st.subheader("Result")
        st.markdown("---")

        handle_result_display(st.session_state.scraped_df)

        # Use on_click to trigger the function BEFORE the script reruns
        st.button(
            "📂 Open Output Folder",
            on_click=open_folder,
            args=(st.session_state.output_dir,),
            help="Click to open the folder containing your Excel files"
        )


if __name__ == '__main__':
    main()
