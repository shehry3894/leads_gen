import logging
import os
import sys

from selenium import webdriver
from selenium.common.exceptions import (
    SessionNotCreatedException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from leads_gen.config.settings import HEADLESS_MODE

logger = logging.getLogger("leads_gen")


def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for PyInstaller executable."""
    # sys._MEIPASS is injected by PyInstaller at runtime; not present in dev.
    base_path = getattr(sys, "_MEIPASS", None) or os.path.abspath("")
    return os.path.join(base_path, relative_path)


class DriverInitError(RuntimeError):
    """Raised when we can't build a Chrome WebDriver — carries a human message."""


def _diagnose_webdriver_error(exc: Exception) -> str:
    """Convert a raw Selenium exception into an actionable message."""
    text = str(exc).lower()
    if (
        "chrome not reachable" in text
        or "cannot find chrome" in text
        or "chrome was not found" in text
    ):
        return (
            "Google Chrome does not appear to be installed on this machine. "
            "Please install Chrome from https://www.google.com/chrome and try again."
        )
    if "version" in text and ("mismatch" in text or "session not created" in text):
        return (
            "Chrome and ChromeDriver versions are incompatible. "
            "Update Chrome to the latest version, or set the CHROMEDRIVER_PATH environment "
            "variable to a driver matching your Chrome version."
        )
    if "user data directory" in text or "already in use" in text:
        return (
            "Chrome's user-data directory is in use by another process. "
            "Close all Chrome windows (including background processes) and try again."
        )
    return f"Failed to start Chrome ({type(exc).__name__}): {exc}"


def start_driver(headless: bool = False) -> webdriver.Chrome:
    """
    Build a Chrome WebDriver honoring HEADLESS_MODE and (optional) CHROMEDRIVER_PATH.

    Raises DriverInitError with a user-facing message on failure — callers can
    surface ``str(e)`` directly in the UI.
    """
    options = Options()

    if HEADLESS_MODE:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
    else:
        options.add_argument("--start-maximized")

    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    logger.info("Initializing local ChromeDriver with headless=%s...", HEADLESS_MODE)

    driver_path = os.environ.get("CHROMEDRIVER_PATH")
    if driver_path:
        logger.info("Using CHROMEDRIVER_PATH override: %s", driver_path)
    else:
        try:
            driver_path = ChromeDriverManager().install()
            logger.info("ChromeDriver installed at: %s", driver_path)
        except Exception as e:
            # webdriver_manager touches the network + filesystem; either can fail.
            logger.exception("ChromeDriver download/install failed")
            raise DriverInitError(
                "Could not download ChromeDriver. Check your internet connection, or "
                "set CHROMEDRIVER_PATH to a locally installed driver. Details: "
                f"{type(e).__name__}: {e}"
            ) from e

    try:
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)
    except SessionNotCreatedException as e:
        logger.error("Chrome/ChromeDriver version mismatch: %s", e)
        raise DriverInitError(_diagnose_webdriver_error(e)) from e
    except WebDriverException as e:
        logger.error("WebDriver failed to start: %s", e)
        raise DriverInitError(_diagnose_webdriver_error(e)) from e
    except Exception as e:
        logger.exception("Unexpected error initializing ChromeDriver")
        raise DriverInitError(_diagnose_webdriver_error(e)) from e

    logger.info("ChromeDriver initialized successfully.")
    return driver
