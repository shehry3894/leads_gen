import os
import sys
import logging
import argparse

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


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=f'{__app_name__} - Scrape business leads from Google Maps',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (default)
  python main.py

  # CLI mode with arguments
  python main.py --query "gyms in New York" --max-results 20

  # Skip license check (for testing)
  python main.py --query "cafes in Paris" --max-results 10 --no-license

  # Scrape all available results
  python main.py --query "restaurants in London" --max-results all
        """
    )
    
    parser.add_argument(
        '--query',
        '-q',
        type=str,
        help='Search query (e.g., "gyms in New York")'
    )
    
    parser.add_argument(
        '--max-results',
        '-m',
        type=str,
        help='Maximum number of results to scrape (or "all" for no limit)'
    )
    
    parser.add_argument(
        '--no-license',
        action='store_true',
        help='Skip license validation (for testing purposes only)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'{__app_name__} v{__version__}'
    )
    
    return parser.parse_args()


def main():
    # Parse command-line arguments
    args = parse_arguments()
    
    log_file = configure_file_logging()
    logger = logging.getLogger("leads_gen")
    logger.info(f"{__app_name__} v{__version__} started (CLI mode). Logs: {log_file}")

    # Determine if we're using command-line arguments or interactive mode
    use_cli_args = args.query is not None or args.max_results is not None
    
    if use_cli_args:
        logger.info("Running in CLI argument mode")
    else:
        logger.info("Running in interactive mode")

    # Initialize licensing system (skip if --no-license flag is set)
    license_manager = None
    if not args.no_license:
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
            print("")
            print("Step 1: Get your machine fingerprint")
            print('  uv run python -c "from leads_gen.licensing.fingerprint import generate_machine_fingerprint; print(generate_machine_fingerprint())"')
            print("")
            print("Step 2: Send the fingerprint to the developer/administrator")
            print("")
            print("Step 3: Activate the license key you received")
            print('  echo "YOUR_LICENSE_KEY_HERE" > leads_gen/license.key')
            print("")
            print("Step 4: Run the application again")
            print("")
            print("For testing without license, use: --no-license flag")
            print("  python main.py --query 'test' --max-results 3 --no-license")
            print("="*60)
            sys.exit(1)

        # Display license info
        license_info = license_manager.get_license_info()
        logger.info(f"License type: {license_info['type']}")
        logger.info(f"Days remaining: {license_info['days_remaining']}")
        logger.info(f"Max results per run: {license_info['max_results']}")
    else:
        logger.warning("License check bypassed (--no-license flag used)")
        print("\n⚠️  WARNING: Running without license validation (testing mode)")

    # Get query and max_results from CLI args or interactive prompts
    if use_cli_args:
        query = args.query if args.query else input('Enter the search term (e.g., "gyms in New York"): ').strip()
        
        if args.max_results:
            if args.max_results.lower() == 'all':
                max_results = None
            else:
                try:
                    max_results = int(args.max_results)
                except ValueError:
                    logger.error(f"Invalid --max-results value: {args.max_results}. Must be a number or 'all'")
                    print(f"❌ Error: --max-results must be a number or 'all', got: {args.max_results}")
                    sys.exit(1)
        else:
            max_results_input = input('Enter the number of businesses to scrape (type "all" for no limit): ').strip()
            max_results = None if max_results_input.lower() == 'all' else int(max_results_input)
    else:
        query, max_results = get_user_inputs()
    
    logger.info(f"User input: query=%r, max_results=%s", query, max_results if max_results is not None else "all")

    # Enforce license limits (only if license validation is enabled)
    if license_manager:
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
