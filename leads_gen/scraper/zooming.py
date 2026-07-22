import logging

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

logger = logging.getLogger("leads_gen")


def enable_update_results_checkbox(driver):
    """
    Enables the 'Update results when map moves' checkbox if it's not already checked.
    """
    try:

        logger.info("Checking if 'Update results when map moves' is enabled...")

        checkbox = driver.find_element(
            By.XPATH, "//div[@class='DuI1J Hk4XGb fontBodyMedium']/button[@aria-checked]"
        )

        aria_checked = checkbox.get_attribute("aria-checked")

        if aria_checked == "false":

            checkbox.click()

            logger.info("Checked 'Update results when map moves'.")

        else:

            logger.info("'Update results when map moves' is already checked.")

    except NoSuchElementException:

        logger.warning("'Update results when map moves' checkbox not found.")

    except Exception as e:

        logger.error(f"Error enabling update checkbox: {e}")
