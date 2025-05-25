import time
import logging
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

logger = logging.getLogger(__name__)

        
def zoom_out(driver):
    """
    Zooms out on Google Maps 3 times.
    """
    logger.info('Starting to zoom out on Google Maps.')

    try:
        # Try to hide the survey iframe
        try:
            iframe = driver.find_element(By.CSS_SELECTOR, "iframe[title*='Survey']")
            driver.execute_script("arguments[0].style.display = 'none';", iframe)
            logger.info("Survey iframe hidden.")
        except NoSuchElementException:
            logger.info("No survey iframe found.")

        for i in range(3):
            zoom_out_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Zoom out']")

            if 'disabled' in zoom_out_button.get_attribute('class'):
                logger.info(f'Zoom out button disabled at iteration {i+1}.')
                break

            driver.execute_script("arguments[0].scrollIntoView(true);", zoom_out_button)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", zoom_out_button)
            
            logger.info(f'Zoomed out {i+1}/3 times.')
            time.sleep(1.5)

        logger.info('Finished zooming out.')

    except Exception as e:
        logger.warning(f'Zoom out operation failed: {e}')



def enable_update_results_checkbox(driver):
    """
    Enables the 'Update results when map moves' checkbox if it's not already checked.
    """
    try:
        
        logger.info("Checking if 'Update results when map moves' is enabled...")
        
        checkbox = driver.find_element(By.XPATH, "//div[@class='DuI1J Hk4XGb fontBodyMedium']/button[@aria-checked]")
        
        aria_checked = checkbox.get_attribute('aria-checked')
        
        if aria_checked == 'false':
        
            checkbox.click()
        
            logger.info("Checked 'Update results when map moves'.")
        
        else:
        
            logger.info("'Update results when map moves' is already checked.")
    
    except NoSuchElementException:
    
        logger.warning("'Update results when map moves' checkbox not found.")
    
    except Exception as e:
    
        logger.error(f"Error enabling update checkbox: {e}")