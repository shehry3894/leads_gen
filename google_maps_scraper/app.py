import streamlit as st
import pandas as pd
import os
import logging
from scraper.driver import start_driver
from scraper.search import search_maps
from scraper.scroll import scroll_results
from scraper.scrape import scrape_business_data
from io import BytesIO

# Configure Streamlit and logging
st.set_page_config(page_title="Google Maps Business Scraper", layout="wide")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')



def save_to_excel(data, query):
    
    
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f'{query.replace(" ", "_")}.xlsx')
    pd.DataFrame(data).to_excel(filename, index=False)
    return filename

def display_whatsapp_links(df):
    
    
    if 'WhatsApp' in df.columns:
        df['WhatsApp'] = df['WhatsApp'].apply(lambda x: f'<a href="{x}" target="_blank">{x}</a>' if x else "")
    return df

def render_dataframe(df):
    
    
    st.markdown("""
        <style>
            table { font-size: 14px; border-collapse: collapse; }
            th, td { padding: 4px 8px !important; white-space: nowrap; max-width: 200px; overflow: hidden; text-overflow: ellipsis; }
        </style>
    """, unsafe_allow_html=True)
    st.markdown(f"""<div style="overflow-x: auto">{df.to_html(escape=False, index=False)}</div>""", unsafe_allow_html=True)

def get_query_and_limit():
    
    
    query = st.text_input('Enter Search Query', 'gyms in New York')
    max_input = st.text_input('Max Results (Enter "all" for no limit)', '10')
    max_results = None if max_input.lower() == 'all' else int(max_input) if max_input.isdigit() else None

    if max_input and max_results is None and max_input.lower() != 'all':
        st.error('Please enter a valid number or "all".')
    return query, max_results

def perform_scraping(query, max_results, headless=True):
    driver = start_driver(headless=headless)
    try:
        logging.info(f'Searching for: {query}')
        search_maps(driver, query)
        scroll_results(driver, max_results)
        data = scrape_business_data(driver, max_results)
    finally:
        driver.quit()
        logging.info('Driver closed.')
    return data

def handle_result_display(data, query, button_label='Download Excel'):
    filename = save_to_excel(data, query)
    st.success(f'Scraping completed. Data saved to {filename}')
    st.download_button(button_label, filename, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
    df = pd.read_excel(filename)
    df = display_whatsapp_links(df)
    render_dataframe(df)


# ========= Main Streamlit App =========
def main():
    st.title('Google Maps Business Scraper')
    st.sidebar.header("Options")

    headless_mode = st.sidebar.checkbox('Run in headless mode', value=True)
    scrape_option = st.sidebar.selectbox('Choose an option', ['Scrape New Data', 'Append to Existing Data'])

    if scrape_option == 'Scrape New Data':
        query, max_results = get_query_and_limit()

        if st.button('Start Scraping') and query:
            data = perform_scraping(query, max_results, headless=headless_mode)
            handle_result_display(data, query)

    elif scrape_option == 'Append to Existing Data':
        uploaded_file = st.file_uploader('Upload an existing file', type=['xlsx'])
        if uploaded_file:
            df_existing = pd.read_excel(uploaded_file)
            st.write('Existing Data:')
            render_dataframe(df_existing)

            query, max_results = get_query_and_limit()

            if st.button('Start Scraping') and query:
                new_data = perform_scraping(query, max_results, headless=headless_mode)
                df_new = pd.DataFrame(new_data)
                df_combined = pd.concat([df_existing, df_new], ignore_index=True)

                handle_result_display(df_combined, query, 'Download Updated Excel')


if __name__ == '__main__':
    main()
