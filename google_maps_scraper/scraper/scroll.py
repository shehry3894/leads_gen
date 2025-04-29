import time
import logging
from selenium.webdriver.common.by import By

# Configure logging for this module
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def scroll_results(driver, max_results):
    logging.info('Starting the scroll process.')
    scrollable_div = driver.find_element(By.XPATH, '//div[@role="feed"]')

    collected = 0
    last_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)

    while True:
        logging.info(f"Scrolling... Current collected results: {collected}")
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
        time.sleep(3)

        new_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)

        results = driver.find_elements(By.XPATH, '//div[contains(@class, "Nv2PK")]')
        
        collected = len(results)
        # Check if the maximum number of results is reached
        if max_results is not None and len(results) >= max_results:
            logging.info(f"Reached the maximum number of results: {max_results}. Stopping scroll.")
            break


        if new_height == last_height:
            logging.info("No more results to load. Reached the bottom of the page.")
            break

        last_height = new_height
    logging.info(f"Scrolling finished. Total results collected: {collected}")