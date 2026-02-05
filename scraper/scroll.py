import time
import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from input.config import TRIAL

logger = logging.getLogger("leads_gen")


def scroll_results(driver, max_results):
    if TRIAL:
        max_results = 3
        logger.info(f'Setting max results to {max_results} since you are using trial version')

    logger.info('Starting the scroll process.')

    try:
        # Wait for the scrollable results feed to be present
        scrollable_div = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//div[@role="feed"]'))
        )
        logger.info('Scrollable feed found.')

        collected = 0
        same_count_retries = 0
        max_retries = 5

        while True:
            # Scroll to bottom of scrollable_div
            driver.execute_script(
                'arguments[0].scrollTop = arguments[0].scrollHeight', scrollable_div
            )
            logger.debug('Scrolled to bottom.')

            time.sleep(2.5)  # Wait for new results to load

            results = driver.find_elements(By.XPATH, '//div[contains(@class, "Nv2PK")]')
            current_count = len(results)

            if current_count > collected:
                collected = current_count
                same_count_retries = 0
                logger.info(f'Collected {collected} results so far.')
            else:
                same_count_retries += 1
                logger.info(f'No new results. Retry {same_count_retries}/{max_retries}')
                if same_count_retries >= max_retries:
                    logger.info('No more results to load or max retries reached.')
                    break

            if max_results and collected >= max_results:
                logger.info(f'Reached requested max results: {max_results}')
                break

        logger.info(f'Scrolling finished. Total results collected: {collected}')

    except TimeoutException:
        logger.error('Timed out waiting for scrollable feed.')
    except Exception as e:
        logger.error(f'Unexpected error during scroll: {e}')
