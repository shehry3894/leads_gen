import os
import sys
import logging

import pandas as pd

from scraper.driver import start_driver
from scraper.search import search_maps
from scraper.scroll import scroll_results
from scraper.scrape import scrape_business_data
from utils.logging_utils import configure_file_logging
from utils.demo_data import get_demo_leads
from utils.paths import get_output_dir
from utils.data_normalization import process_scraped_data, deduplicate_dataframe
from version import __version__, __app_name__

from input.config import get_user_inputs, HEADLESS_MODE, TESTING


def main():
    log_file = configure_file_logging()
    logger = logging.getLogger("leads_gen")
    logger.info(f"{__app_name__} v{__version__} started (CLI mode). Logs: {log_file}")

    query, max_results = get_user_inputs()
    logger.info(f"User input (CLI): query=%r, max_results=%s", query, max_results if max_results is not None else "all")

    if TESTING:
        logger.info("TESTING=True, using demo leads instead of live scraping")
        data = get_demo_leads()
    else:
        driver = start_driver()
        try:
            logger.info(f"Searching for: {query}")
            search_maps(driver, query)

            scroll_results(driver, max_results)

            data = scrape_business_data(driver, max_results)
        finally:
            driver.quit()
            logger.info("Driver closed.")

    # Process and normalize scraped data
    df_new = process_scraped_data(data)
    
    # Create output directory if it doesn't exist
    output_dir = get_output_dir()

    # Save file inside the output folder
    filename = output_dir / f'{query.replace(" ", "_")}.xlsx'

    if filename.exists():
        df_old = pd.read_excel(filename)
        logger.info(f"Existing file found: {filename} ({len(df_old)} rows)")

        # Combine old and new data, then deduplicate
        df_combined = pd.concat([df_old, df_new], ignore_index=True)
        df_combined = deduplicate_dataframe(df_combined)

        df_combined.to_excel(filename, index=False)
        logger.info(f"Merged with existing file and saved to {filename} ({len(df_combined)} rows)")
    else:
        df_new.to_excel(filename, index=False)
        logger.info(f"Saved new file to {filename} ({len(df_new)} rows)")


if __name__ == '__main__':
    main()
