import os
import sys
import logging

import pandas as pd

from leads_gen.scraper.driver import start_driver
from leads_gen.scraper.search import search_maps
from leads_gen.scraper.scroll import scroll_results
from leads_gen.scraper.scrape import scrape_business_data
from leads_gen.utils.logging_utils import configure_file_logging
from leads_gen.core.demo_data import get_demo_leads
from leads_gen.utils.paths import get_output_dir
from leads_gen.core.data_normalization import process_scraped_data, deduplicate_dataframe
from leads_gen.licensing.license_manager import LicenseManager
from leads_gen.version import __version__, __app_name__

from leads_gen.config.settings import get_user_inputs, HEADLESS_MODE, TESTING


def main():
    log_file = configure_file_logging()
    logger = logging.getLogger("leads_gen")
    logger.info(f"{__app_name__} v{__version__} started (CLI mode). Logs: {log_file}")

    # Initialize licensing system
    license_manager = LicenseManager()
    success, message = license_manager.initialize()
    logger.info(f"License status: {message}")
    
    if not success:
        logger.error("="*60)
        logger.error("LICENSE REQUIRED")
        logger.error("="*60)
        logger.error(message)
        logger.error("\nTo get a license:")
        logger.error("1. Run: python utils/license_manager.py --show-fingerprint")
        logger.error("2. Send the fingerprint to the developer")
        logger.error("3. Save the license key: python utils/license_manager.py --save-license <key>")
        logger.error("="*60)
        print("\n" + "="*60)
        print("LICENSE REQUIRED")
        print("="*60)
        print(f"{message}\n")
        print("To get a license:")
        print("1. Run: python utils/license_manager.py --show-fingerprint")
        print("2. Send the fingerprint to the developer")
        print("3. Save the license key: python utils/license_manager.py --save-license <key>")
        print("="*60)
        sys.exit(1)

    # Display license info
    license_info = license_manager.get_license_info()
    logger.info(f"License type: {license_info['type']}")
    logger.info(f"Days remaining: {license_info['days_remaining']}")
    logger.info(f"Max results per run: {license_info['max_results']}")

    query, max_results = get_user_inputs()
    logger.info(f"User input (CLI): query=%r, max_results=%s", query, max_results if max_results is not None else "all")

    # Enforce license limits
    if max_results is None:
        max_results = license_manager.get_max_results()
        logger.info(f"No max results specified, using license limit: {max_results}")
    else:
        can_scrape, msg = license_manager.can_scrape(max_results)
        if not can_scrape:
            logger.error("="*60)
            logger.error("LICENSE LIMIT EXCEEDED")
            logger.error("="*60)
            logger.error(msg)
            logger.error(f"\nYour license allows maximum {license_manager.get_max_results()} results per run")
            logger.error("="*60)
            print("\n" + "="*60)
            print("LICENSE LIMIT EXCEEDED")
            print("="*60)
            print(f"{msg}")
            print(f"\nYour license allows maximum {license_manager.get_max_results()} results per run")
            print("="*60)
            sys.exit(1)
        else:
            logger.info(msg)

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
