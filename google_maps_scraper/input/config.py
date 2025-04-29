import logging

# Configure logging for this module
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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