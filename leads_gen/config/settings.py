import logging
import os

# Configure logging for this module
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Add headless mode configuration
# Read from environment variable, default to True (headless mode)
HEADLESS_MODE = os.getenv('HEADLESS_MODE', 'true').lower() in ('true', '1', 'yes')
TRIAL = True  # ✅ Limits to 3 results for quick testing
TESTING = False  # ✅ Disabled to enable real Google Maps scraping

# Smart Wait Configuration
# Configure wait times and retry logic for reliable scraping
WAIT_CONFIG = {
    # Base wait time between retries (in seconds)
    'base_wait': 1.0,
    
    # Maximum wait time for any single element (in seconds)
    'max_wait': 20,
    
    # Number of retry attempts for finding elements
    'max_retries': 10,
    
    # Use exponential backoff (doubles wait time after each retry)
    'exponential_backoff': False,
    
    # Specific timeouts for different operations
    'page_load': 10,        # Wait for initial page load
    'search_box': 15,       # Wait for search box to appear
    'search_results': 15,   # Wait for results feed to load
    'business_card': 10,    # Wait for business card to be clickable
    'info_panel': 10,       # Wait for business info panel to load
    'element_visibility': 10,  # Wait for elements to be visible
}


def get_user_inputs():
    logging.info('Prompting user for search term and max results.')

    query = input('Enter the search term (e.g., "gyms in New York"): ')
    logging.info(f'User entered search term: {query}')

    max_results = input('Enter the number of businesses to scrape (type "all" for no limit): ')

    if max_results.lower() == 'all':
        logging.info('User chose "all" for the number of results.')
        max_results = None
    else:
        logging.info(f'User entered {max_results} as the number of results.')
        max_results = int(max_results)

    return query, max_results
