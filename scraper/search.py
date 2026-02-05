import time
import logging
from scraper.zooming import zoom_out, enable_update_results_checkbox
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

logger = logging.getLogger(__name__)

import time
from selenium.webdriver.common.keys import Keys


def set_browser_zoom(driver):
    zoom_levels = [90, 80, 75, 67]

    for zoom_level in zoom_levels:
        driver.execute_script(f"document.body.style.zoom='{zoom_level}%'")
        time.sleep(0.3)


def search_maps(driver, query):
    try:
        logger.info(f'Searching for: {query} on Google Maps')

        driver.get('https://www.google.com/maps')

        time.sleep(5)  # wait for Maps to fully load

        set_browser_zoom(driver)

        search_box = driver.find_element(By.ID, 'searchboxinput')
        search_box.send_keys(query)
        search_box.send_keys(Keys.ENTER)
        time.sleep(5)

        logger.info(f'Search for "{query}" completed.')

        enable_update_results_checkbox(driver)

        time.sleep(1.5)  # Wait for the map to load


    except Exception as e:
        logger.error(f"Error occurred during search for '{query}': {str(e)}")
        raise
