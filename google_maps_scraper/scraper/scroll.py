import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configure logging for this module
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def scroll_results(driver, max_results):
    logging.info('Starting the scroll process.')

    try:
        # Wait for the scrollable div to be present on the page
        scrollable_div = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[@role="feed"]'))
        )
        logging.info('Scrollable feed found.')

        collected = 0
        last_height = driver.execute_script('return arguments[0].scrollHeight', scrollable_div)

        while True:
            logging.info(f'Scrolling... Current collected results: {collected}')
            driver.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', scrollable_div)
            time.sleep(3)

            new_height = driver.execute_script('return arguments[0].scrollHeight', scrollable_div)

            # Find all business results
            try:
                results = driver.find_elements(By.XPATH, '//div[contains(@class, "Nv2PK")]')
            except NoSuchElementException:
                logging.error('Error: Could not find the elements for results.')
                break

            collected = len(results)
            logging.info(f'Found {collected} results so far.')

            # Check if the maximum number of results is reached
            if max_results is not None and collected >= max_results:
                logging.info(f'Reached the maximum number of results: {max_results}. Stopping scroll.')
                break

            # If no new results are loaded, stop scrolling
            if new_height == last_height:
                logging.info('No more results to load. Reached the bottom of the page.')
                break

            last_height = new_height

        logging.info(f'Scrolling finished. Total results collected: {collected}')
    except TimeoutException:
        logging.error('Timed out waiting for the scrollable feed to load.')
    except Exception as e:
        logging.error(f'An unexpected error occurred: {str(e)}')
