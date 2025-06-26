# --- FIX FOR PYINSTALLER METADATA ISSUES ---
import sys
import os

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
import os
import logging
from io import BytesIO
from scraper.driver import start_driver
from scraper.search import search_maps
from scraper.scroll import scroll_results
from scraper.scrape import scrape_business_data

# --- Streamlit and Logging Configuration ---
st.set_page_config(page_title='Google Maps Business Scraper', layout='wide')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')



# --- Utilities ---
def get_query_and_limit():
    query = st.text_input('Enter Search Query', 'gyms in New York')
    max_input = st.text_input('Max Results (Enter "all" for no limit)', '10')
    max_results = None if max_input.lower() == 'all' else int(max_input) if max_input.isdigit() else None

    if max_input and max_results is None and max_input.lower() != 'all':
        st.error('Please enter a valid number or "all".')
    return query, max_results


def perform_scraping(query, max_results, headless=True, progress_callback=None):
    driver = start_driver(headless=headless)
    try:
        if progress_callback: progress_callback(0.1, 'Searching Google Maps...')
        search_maps(driver, query)

        if progress_callback: progress_callback(0.4, 'Scrolling through results...')
        scroll_results(driver, max_results)

        if progress_callback: progress_callback(0.7, 'Scraping business data...')
        data = scrape_business_data(driver, max_results)

        if progress_callback: progress_callback(1.0, 'Scraping complete.')
    finally:
        driver.quit()
    return data


def render_clickable_links(df):
    df_display = df.copy()
    for col in df_display.columns:
        if df_display[col].dtype == 'object' and df_display[col].str.contains('http', na=False).any():
            df_display[col] = df_display[col].apply(
                lambda x: f'<a href="{x}" target="_blank">{x}</a>' if pd.notna(x) and str(x).startswith('http') else ''
            )
    return df_display


def render_dataframe(df):
    st.markdown("""
        <style>
            table { font-size: 14px; border-collapse: collapse; }
            th, td { padding: 4px 8px !important; white-space: nowrap; max-width: 200px; overflow: hidden; text-overflow: ellipsis; }
        </style>
    """, unsafe_allow_html=True)
    st.markdown(f"""<div style="overflow-x: auto">{df.to_html(escape=False, index=False)}</div>""", unsafe_allow_html=True)


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


def handle_result_display(df, query):
    render_dataframe(render_clickable_links(df))
    excel_data = create_excel_with_links(df)
    st.download_button(
        label='Download Excel File',
        data=excel_data,
        file_name=f'{query.replace(" ", "_")}.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


# --- Main Application ---
def main():
    st.title('Google Maps Business Scraper')
    st.sidebar.header("Options")

    scrape_option = st.sidebar.selectbox('Choose an option', ['Scrape New Data', 'Append to Existing Data'])

    def update_progress(pct, msg):
        progress_bar.progress(pct)
        status_text.text(msg)

    if scrape_option == 'Scrape New Data':
        query, max_results = get_query_and_limit()

        if st.button('Start Scraping') and query:
            progress_bar = st.progress(0)
            status_text = st.empty()

            data = perform_scraping(query, max_results, progress_callback=update_progress)
            handle_result_display(pd.DataFrame(data), query)

            status_text.text("✅ Finished successfully.")
            progress_bar.empty()

    elif scrape_option == 'Append to Existing Data':
        uploaded_file = st.file_uploader('Upload an existing file', type=['xlsx'])
        if uploaded_file:
            df_existing = pd.read_excel(uploaded_file)
            st.write('Existing Data:')
            render_dataframe(render_clickable_links(df_existing))

            query, max_results = get_query_and_limit()

            if st.button('Start Scraping') and query:
                progress_bar = st.progress(0)
                status_text = st.empty()

                new_data = perform_scraping(query, max_results, progress_callback=update_progress)
                df_combined = pd.concat([df_existing, pd.DataFrame(new_data)], ignore_index=True)
                handle_result_display(df_combined, query)

                status_text.text("✅ Updated file ready.")
                progress_bar.empty()


if __name__ == '__main__':
    
    main()
