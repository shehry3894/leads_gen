from scraper.driver import start_driver
from scraper.search import search_maps
from scraper.scroll import scroll_results
from scraper.scrape import scrape_business_data
from input.config import get_user_inputs
import pandas as pd
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == '__main__':
    driver = start_driver()
    try:
        query, max_results = get_user_inputs()
        logging.info(f'Searching for: {query}')
        search_maps(driver, query)

        scroll_results(driver, max_results)

        data = scrape_business_data(driver, max_results)

        # Create output directory if it doesn't exist
        output_dir = 'output'
        os.makedirs(output_dir, exist_ok=True)

        # Save file inside the output folder
        filename = os.path.join(output_dir, f'{query.replace(" ", "_")}.xlsx')

        df_new = pd.DataFrame(data)

        if os.path.exists(filename):
            df_old = pd.read_excel(filename)

            # Merge using Name + Address as unique identifier
            df_combined = pd.concat([df_old, df_new])
            df_combined.drop_duplicates(subset=['Name', 'Address'], keep='last', inplace=True)

            df_combined.to_excel(filename, index=False)
            logging.info(f'Merged with existing file and saved to {filename}')
        else:
            df_new.to_excel(filename, index=False)
            logging.info(f'Saved new file to {filename}')
    finally:
        driver.quit()
        logging.info('Driver closed.')
