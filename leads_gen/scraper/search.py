import time
import logging
from leads_gen.scraper.zooming import zoom_out, enable_update_results_checkbox
from leads_gen.utils.wait_utils import SmartWait
from leads_gen.config.settings import WAIT_CONFIG
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

logger = logging.getLogger("leads_gen")

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
        smart_wait = SmartWait(driver)

        driver.get('https://www.google.com/maps')
        logger.info('Navigated to Google Maps')

        # Wait for page to load completely
        smart_wait.wait_for_page_load(timeout=WAIT_CONFIG.get('page_load', 10))

        # Try to handle any consent/cookie dialogs
        try:
            # Try to accept cookies if dialog appears (don't wait too long)
            accept_buttons = driver.find_elements(By.XPATH, '//button[contains(., "Accept") or contains(., "Agree") or contains(., "I agree")]')
            if accept_buttons:
                accept_buttons[0].click()
                logger.info('Accepted cookie consent dialog')
                time.sleep(0.5)  # Brief pause after clicking
        except Exception as e:
            logger.debug(f'No cookie dialog found or error dismissing it: {e}')

        set_browser_zoom(driver)

        # Try multiple selectors for the search box with smart wait
        search_box = None
        selectors = [
            (By.ID, 'searchboxinput'),
            (By.NAME, 'q'),
            (By.CSS_SELECTOR, 'input[aria-label*="Search"]'),
            (By.CSS_SELECTOR, 'input[placeholder*="Search"]'),
            (By.XPATH, '//input[@id="searchboxinput"]'),
        ]
        
        timeout = WAIT_CONFIG.get('search_box', 15)
        for by_type, selector in selectors:
            logger.debug(f'Trying to find search box with {by_type}: {selector}')
            search_box = smart_wait.wait_for_element(
                by_type, 
                selector, 
                timeout=timeout,
                condition='visibility'
            )
            if search_box:
                logger.info(f'Found search box using {by_type}: {selector}')
                break
        
        if not search_box:
            logger.error('Could not find search box with any known selector')
            logger.info(f'Current URL: {driver.current_url}')
            logger.info(f'Page title: {driver.title}')
            raise Exception('Search box element not found after trying multiple selectors')
        
        # Type query and submit
        search_box.send_keys(query)
        search_box.send_keys(Keys.ENTER)
        
        # Wait for search results to load (looking for results feed)
        logger.info('Waiting for search results to load...')
        results_timeout = WAIT_CONFIG.get('search_results', 15)
        results_loaded = smart_wait.wait_for_element(
            By.XPATH,
            '//div[@role="feed"]',
            timeout=results_timeout,
            condition='presence'
        )
        
        if results_loaded:
            logger.info(f'Search for "{query}" completed - results loaded')
        else:
            logger.warning(f'Search results may not have loaded properly')

        enable_update_results_checkbox(driver)

        # Brief wait for map animations to settle
        time.sleep(0.5)


    except Exception as e:
        logger.error(f"Error occurred during search for '{query}': {str(e)}")
        raise
