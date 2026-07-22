import argparse
import logging
import sys

import pandas as pd

from leads_gen.config.settings import TESTING, get_user_inputs
from leads_gen.core.data_normalization import deduplicate_dataframe, process_scraped_data
from leads_gen.core.demo_data import get_demo_leads
from leads_gen.licensing.license_manager import LicenseManager
from leads_gen.scraper.driver import start_driver
from leads_gen.scraper.scrape import scrape_business_data
from leads_gen.scraper.scroll import scroll_results
from leads_gen.scraper.search import search_maps
from leads_gen.utils.logging_utils import configure_file_logging
from leads_gen.utils.paths import get_output_dir
from leads_gen.version import __app_name__, __version__

logger = logging.getLogger("leads_gen")


def _emit_block(title: str, body_lines):
    """Log AND print a titled block once, so users and log files stay in sync."""
    banner = "=" * 60
    lines = [banner, title, banner, *body_lines, banner]
    text = "\n".join(lines)
    logger.error(text)
    print("\n" + text)


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=f"{__app_name__} - Scrape business leads from Google Maps",
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
        """,
    )

    parser.add_argument("--query", "-q", type=str, help='Search query (e.g., "gyms in New York")')

    parser.add_argument(
        "--max-results",
        "-m",
        type=str,
        help='Maximum number of results to scrape (or "all" for no limit)',
    )

    parser.add_argument(
        "--no-license",
        action="store_true",
        help="Skip license validation (for testing purposes only)",
    )

    parser.add_argument("--version", action="version", version=f"{__app_name__} v{__version__}")

    return parser.parse_args()


def main():
    # Parse command-line arguments
    args = parse_arguments()

    log_file = configure_file_logging()
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
            _emit_block(
                "LICENSE REQUIRED",
                [
                    message,
                    "",
                    "Step 1: Get your machine fingerprint",
                    '  uv run python -c "from leads_gen.licensing.fingerprint import generate_machine_fingerprint; print(generate_machine_fingerprint())"',
                    "",
                    "Step 2: Send the fingerprint to the developer/administrator",
                    "",
                    "Step 3: Activate the license key you received",
                    '  echo "YOUR_LICENSE_KEY_HERE" > leads_gen/license.key',
                    "",
                    "Step 4: Run the application again",
                    "",
                    "For testing without license, use: --no-license flag",
                    "  python main.py --query 'test' --max-results 3 --no-license",
                ],
            )
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
        query = (
            args.query
            if args.query
            else input('Enter the search term (e.g., "gyms in New York"): ').strip()
        )

        if args.max_results:
            if args.max_results.lower() == "all":
                max_results = None
            else:
                try:
                    max_results = int(args.max_results)
                except ValueError:
                    logger.error(
                        f"Invalid --max-results value: {args.max_results}. Must be a number or 'all'"
                    )
                    print(
                        f"❌ Error: --max-results must be a number or 'all', got: {args.max_results}"
                    )
                    sys.exit(1)
        else:
            max_results_input = input(
                'Enter the number of businesses to scrape (type "all" for no limit): '
            ).strip()
            max_results = None if max_results_input.lower() == "all" else int(max_results_input)
    else:
        query, max_results = get_user_inputs()

    logger.info(
        "User input: query=%r, max_results=%s",
        query,
        max_results if max_results is not None else "all",
    )

    # Enforce license limits (only if license validation is enabled)
    if license_manager:
        if max_results is None:
            max_results = license_manager.get_max_results()
            logger.info(f"No max results specified, using license limit: {max_results}")
        else:
            can_scrape, msg = license_manager.can_scrape(max_results)
            if not can_scrape:
                _emit_block(
                    "LICENSE LIMIT EXCEEDED",
                    [
                        msg,
                        "",
                        f"Your license allows maximum {license_manager.get_max_results()} results per run",
                    ],
                )
                sys.exit(1)
            else:
                logger.info(msg)

    if TESTING:
        logger.info("TESTING=True, using demo leads instead of live scraping")
        data = get_demo_leads()
    else:
        from leads_gen.scraper.driver import DriverInitError

        try:
            driver = start_driver()
        except DriverInitError as e:
            _emit_block("BROWSER STARTUP FAILED", [str(e)])
            sys.exit(2)

        try:
            logger.info(f"Searching for: {query}")
            search_maps(driver, query)
            scroll_results(driver, max_results)
            data = scrape_business_data(driver, max_results)
        except Exception:
            logger.exception("Scraping failed")
            _emit_block(
                "SCRAPING FAILED",
                [
                    "The scraper hit an unexpected error. See log file for details:",
                    str(log_file),
                ],
            )
            sys.exit(3)
        finally:
            try:
                driver.quit()
            except Exception:
                logger.warning("driver.quit() failed during teardown", exc_info=True)
            logger.info("Driver closed.")

    # Process and normalize scraped data
    df_new = process_scraped_data(data)

    # Create output directory (uses tempdir fallback if primary isn't writable).
    output_dir = get_output_dir()
    filename = output_dir / f'{query.replace(" ", "_")}.xlsx'

    try:
        if filename.exists():
            df_old = pd.read_excel(filename)
            logger.info(f"Existing file found: {filename} ({len(df_old)} rows)")

            df_combined = pd.concat([df_old, df_new], ignore_index=True)
            df_combined = deduplicate_dataframe(df_combined)

            df_combined.to_excel(filename, index=False)
            logger.info(
                f"Merged with existing file and saved to {filename} ({len(df_combined)} rows)"
            )
        else:
            df_new.to_excel(filename, index=False)
            logger.info(f"Saved new file to {filename} ({len(df_new)} rows)")
    except PermissionError:
        logger.exception("Permission denied writing Excel to %s", filename)
        _emit_block(
            "COULD NOT SAVE OUTPUT",
            [
                f"Permission denied writing to: {filename}",
                "Close the file if it's open in Excel, or run from a folder you can write to.",
            ],
        )
        sys.exit(4)
    except OSError as e:
        logger.exception("OS error saving Excel to %s", filename)
        hint = ""
        msg = str(e).lower()
        if "no space" in msg or "enospc" in msg:
            hint = "  The disk appears to be full."
        _emit_block("COULD NOT SAVE OUTPUT", [f"Error writing {filename}: {e}", hint])
        sys.exit(4)


if __name__ == "__main__":
    main()
