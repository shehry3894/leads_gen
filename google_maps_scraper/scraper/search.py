import time
import logging
from scraper.zooming import zoom_out, enable_update_results_checkbox 
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

logger = logging.getLogger(__name__)

def search_maps(driver, query):
    try:
        logger.info(f'Searching for: {query} on Google Maps')

        driver.get('https://www.google.com/maps')
        time.sleep(3)

        search_box = driver.find_element(By.ID, 'searchboxinput')
        search_box.send_keys(query)
        search_box.send_keys(Keys.ENTER)
        time.sleep(5)

        logger.info(f'Search for "{query}" completed.')
        
        enable_update_results_checkbox(driver)
        
        time.sleep(1.5)  # Wait for the map to load
               
        zoom_out(driver)  # Call zoom function 
       
        
    except Exception as e:
        logger.error(f"Error occurred during search for '{query}': {str(e)}")
        raise
