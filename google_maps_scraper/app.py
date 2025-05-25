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
st.set_page_config(page_title='Google Maps Business Scraper', layout='wide')
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


def perform_scraping(query, max_results, headless=True, progress_callback=None):
    driver = start_driver(headless=headless)
    try:
        logging.info(f'Searching for: {query}')
        if progress_callback: progress_callback(0.1, 'Searching Google Maps...') 
        search_maps(driver, query)
        
        if progress_callback: progress_callback(0.4, 'Scrolling through results...') 
        scroll_results(driver, max_results)
        
        if progress_callback: progress_callback(0.7, 'Scraping business data...')   
        data = scrape_business_data(driver, max_results)
        
        if progress_callback: progress_callback(1.0, 'Scraping complete.')  
    finally:
        driver.quit()
        logging.info('Driver closed.')
    return data


def handle_result_display(data, query, button_label='Prepare Download'):
    df = pd.DataFrame(data)
    
    # Render clickable WhatsApp links in Streamlit
    df_display = df.copy()
    
    for col in df_display.columns:
        if df_display[col].dtype == 'object' and df_display[col].str.startswith('http').any():
            df_display[col] = df_display[col].apply(
                lambda x: f'<a href="{x}" target="_blank">{x}</a>' if pd.notna(x) and str(x).startswith('http') else ''
            )

    render_dataframe(df_display)


    # Prepare in-memory Excel file with clickable hyperlinks
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

    excel_data = output.getvalue()

    # Download button
    st.download_button(
        label='Download Excel File',
        data=excel_data,
        file_name=f'{query.replace(' ', '_')}.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    
    
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
             # Progress UI elements
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            data = perform_scraping(query, max_results, progress_callback=update_progress)
            handle_result_display(data, query)

            status_text.text("✅ Finished successfully.")
            progress_bar.empty()
            
    elif scrape_option == 'Append to Existing Data':
        uploaded_file = st.file_uploader('Upload an existing file', type=['xlsx'])
        if uploaded_file:
            df_existing = pd.read_excel(uploaded_file)
            st.write('Existing Data:')
            render_dataframe(df_existing)

            query, max_results = get_query_and_limit()

            if st.button('Start Scraping') and query:
                
                # Progress UI elements
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                new_data = perform_scraping(query, max_results, progress_callback=update_progress)
                df_new = pd.DataFrame(new_data)
                df_combined = pd.concat([df_existing, df_new], ignore_index=True)

                handle_result_display(df_combined, query, 'Download Updated Excel')

                status_text.text("✅ Updated file ready.")
                progress_bar.empty()

if __name__ == '__main__':
    main()
