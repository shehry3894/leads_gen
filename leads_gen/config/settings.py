import logging
import os

# Configure logging for this module
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Add headless mode configuration
# Read from environment variable, default to True (headless mode)
# Chrome runs visibly by default — Google Maps' bot detection throttles
# headless sessions (smaller scroll feed, "limited view" panel), so leaving
# the browser visible produces ~2-3x more results per query. Set
# HEADLESS_MODE=true to hide Chrome for automated / server runs where the
# yield drop is acceptable.
HEADLESS_MODE = os.getenv("HEADLESS_MODE", "false").lower() in ("true", "1", "yes")
# Developer fast-cap: forces the scroll stage to stop at 3 results regardless
# of license or user input. Env-controlled, default OFF. NEVER ship a customer
# build with this on — customers rely on their license cap being respected.
# Enable locally with: LEADS_GEN_TRIAL=true make ui
TRIAL = os.getenv("LEADS_GEN_TRIAL", "false").lower() in ("true", "1", "yes")
# TESTING=True short-circuits Selenium and returns demo data. Env override
# lets pytest flip it on in a spawned Streamlit subprocess without editing
# this file.
TESTING = os.getenv("LEADS_GEN_TESTING", "false").lower() in ("true", "1", "yes")

# Smart Wait Configuration
# Configure wait times and retry logic for reliable scraping
WAIT_CONFIG = {
    # Base wait time between retries (in seconds)
    "base_wait": 1.0,
    # Maximum wait time for any single element (in seconds)
    "max_wait": 20,
    # Number of retry attempts for finding elements
    "max_retries": 10,
    # Use exponential backoff (doubles wait time after each retry)
    "exponential_backoff": False,
    # Specific timeouts for different operations
    "page_load": 10,  # Wait for initial page load
    "search_box": 15,  # Wait for search box to appear
    "search_results": 15,  # Wait for results feed to load
    "business_card": 10,  # Wait for business card to be clickable
    "info_panel": 10,  # Wait for business info panel to load
    "element_visibility": 10,  # Wait for elements to be visible
}


def get_user_inputs() -> tuple[str, int | None]:
    logging.info("Prompting user for search term and max results.")

    query = input('Enter the search term (e.g., "gyms in New York"): ')
    logging.info(f"User entered search term: {query}")

    raw = input('Enter the number of businesses to scrape (type "all" for no limit): ')

    max_results: int | None
    if raw.lower() == "all":
        logging.info('User chose "all" for the number of results.')
        max_results = None
    else:
        logging.info(f"User entered {raw} as the number of results.")
        max_results = int(raw)

    return query, max_results
