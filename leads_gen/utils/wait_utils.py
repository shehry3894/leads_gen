"""
Smart wait utilities for reliable Selenium operations.

Provides configurable wait and retry logic to handle slow connections,
dynamic content loading, and element availability checks.
"""

import logging
import time
from collections.abc import Callable
from typing import Any

from selenium.common.exceptions import (
    ElementNotInteractableException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from leads_gen.config.settings import WAIT_CONFIG

logger = logging.getLogger("leads_gen")


class SmartWait:
    """
    Smart wait utility with configurable retries and exponential backoff.
    """

    def __init__(self, driver: WebDriver, config: dict | None = None):
        """
        Initialize SmartWait with driver and optional custom config.

        Args:
            driver: Selenium WebDriver instance
            config: Optional custom wait configuration (overrides WAIT_CONFIG)
        """
        self.driver = driver
        self.config = config or WAIT_CONFIG
        self.base_wait: float = float(self.config.get("base_wait", 1.0))
        self.max_retries: int = int(self.config.get("max_retries", 10))
        self.exponential_backoff: bool = bool(self.config.get("exponential_backoff", False))

    def wait_for_element(
        self, by: str, value: str, timeout: float | None = None, condition: str = "presence"
    ) -> WebElement | None:
        """
        Wait for element with smart retry logic.

        Args:
            by: Selenium By locator type
            value: Locator value
            timeout: Maximum wait time (uses config default if not specified)
            condition: Type of wait condition ('presence', 'visibility', 'clickable')

        Returns:
            WebElement if found, None otherwise
        """
        timeout = timeout or self.config.get("max_wait", 20)

        # Map condition string to EC method
        conditions = {
            "presence": EC.presence_of_element_located,
            "visibility": EC.visibility_of_element_located,
            "clickable": EC.element_to_be_clickable,
        }

        condition_func = conditions.get(condition, EC.presence_of_element_located)

        try:
            logger.debug(
                f"Waiting for element: {by}='{value}' (condition: {condition}, timeout: {timeout}s)"
            )
            element = WebDriverWait(self.driver, timeout).until(condition_func((by, value)))
            logger.debug(f"✓ Element found: {by}='{value}'")
            return element
        except TimeoutException:
            logger.warning(f"✗ Timeout waiting for element: {by}='{value}' after {timeout}s")
            return None
        except Exception as e:
            logger.error(f"✗ Error waiting for element {by}='{value}': {e}")
            return None

    def wait_for_elements(
        self, by: str, value: str, timeout: float | None = None, min_count: int = 1
    ) -> list:
        """
        Wait for multiple elements to appear.

        Args:
            by: Selenium By locator type
            value: Locator value
            timeout: Maximum wait time
            min_count: Minimum number of elements expected

        Returns:
            List of WebElements found
        """
        timeout = timeout or self.config.get("max_wait", 20)

        try:
            logger.debug(f"Waiting for {min_count}+ elements: {by}='{value}'")
            WebDriverWait(self.driver, timeout).until(
                lambda d: len(d.find_elements(by, value)) >= min_count
            )
            elements = self.driver.find_elements(by, value)
            logger.debug(f"✓ Found {len(elements)} elements: {by}='{value}'")
            return elements
        except TimeoutException:
            logger.warning(f"✗ Timeout waiting for {min_count}+ elements: {by}='{value}'")
            return []
        except Exception as e:
            logger.error(f"✗ Error waiting for elements {by}='{value}': {e}")
            return []

    def retry_with_backoff(
        self, func: Callable, *args, max_attempts: int | None = None, **kwargs
    ) -> tuple[bool, Any]:
        """
        Retry a function with exponential backoff.

        Args:
            func: Function to retry
            *args: Positional arguments for func
            max_attempts: Maximum retry attempts (uses config default if not specified)
            **kwargs: Keyword arguments for func

        Returns:
            Tuple of (success: bool, result: Any)
        """
        attempts: int = max_attempts or self.max_retries
        wait_time = self.base_wait

        for attempt in range(1, attempts + 1):
            try:
                logger.debug(f"Attempt {attempt}/{attempts}: {func.__name__}")
                result = func(*args, **kwargs)
                logger.debug(f"✓ Success on attempt {attempt}")
                return True, result
            except (
                StaleElementReferenceException,
                NoSuchElementException,
                ElementNotInteractableException,
            ) as e:
                if attempt < attempts:
                    logger.debug(
                        f"Attempt {attempt} failed: {e.__class__.__name__}. Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    if self.exponential_backoff:
                        wait_time *= 2
                else:
                    logger.error(f"✗ All {attempts} attempts failed for {func.__name__}")
                    return False, None
            except Exception as e:
                logger.error(f"✗ Unexpected error in {func.__name__}: {e}")
                return False, None

        return False, None

    def wait_and_click(self, by: str, value: str, timeout: float | None = None) -> bool:
        """
        Wait for element to be clickable and click it with retry logic.

        Args:
            by: Selenium By locator type
            value: Locator value
            timeout: Maximum wait time

        Returns:
            True if clicked successfully, False otherwise
        """
        element = self.wait_for_element(by, value, timeout, condition="clickable")
        if not element:
            return False

        def click_element():
            element.click()
            return True

        success, _ = self.retry_with_backoff(click_element, max_attempts=3)
        if success:
            logger.debug(f"✓ Clicked element: {by}='{value}'")
        else:
            logger.warning(f"✗ Failed to click element: {by}='{value}'")

        return success

    def wait_for_page_load(self, timeout: float | None = None) -> bool:
        """
        Wait for page to finish loading.

        Args:
            timeout: Maximum wait time

        Returns:
            True if page loaded, False otherwise
        """
        timeout = timeout or self.config.get("page_load", 10)

        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            logger.debug("✓ Page loaded")
            return True
        except TimeoutException:
            logger.warning(f"✗ Page load timeout after {timeout}s")
            return False

    def wait_for_element_to_disappear(
        self, by: str, value: str, timeout: float | None = None
    ) -> bool:
        """
        Wait for an element to disappear (e.g., loading spinner).

        Args:
            by: Selenium By locator type
            value: Locator value
            timeout: Maximum wait time

        Returns:
            True if element disappeared, False if still present
        """
        timeout = timeout or self.config.get("max_wait", 20)

        try:
            WebDriverWait(self.driver, timeout).until_not(
                EC.presence_of_element_located((by, value))
            )
            logger.debug(f"✓ Element disappeared: {by}='{value}'")
            return True
        except TimeoutException:
            logger.debug(f"Element still present: {by}='{value}'")
            return False


def create_smart_wait(driver: WebDriver, config: dict | None = None) -> SmartWait:
    """
    Factory function to create SmartWait instance.

    Args:
        driver: Selenium WebDriver instance
        config: Optional custom wait configuration

    Returns:
        SmartWait instance
    """
    return SmartWait(driver, config)


# Convenience functions for backward compatibility
def wait_for_element(
    driver: WebDriver,
    by: str,
    value: str,
    timeout: float | None = None,
    condition: str = "presence",
) -> WebElement | None:
    """Convenience function to wait for a single element."""
    smart_wait = SmartWait(driver)
    return smart_wait.wait_for_element(by, value, timeout, condition)


def wait_for_elements(
    driver: WebDriver,
    by: str,
    value: str,
    timeout: float | None = None,
    min_count: int = 1,
) -> list:
    """Convenience function to wait for multiple elements."""
    smart_wait = SmartWait(driver)
    return smart_wait.wait_for_elements(by, value, timeout, min_count)
