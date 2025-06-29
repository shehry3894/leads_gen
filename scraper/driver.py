import logging
import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from input.config import HEADLESS_MODE

logger = logging.getLogger(__name__)


def resource_path(relative_path):
    """Get absolute path to resource, works for PyInstaller executable."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath("")
    return os.path.join(base_path, relative_path)


def start_driver(headless=False):  # ✅ Added headless parameter

    try:
        options = Options()

        if HEADLESS_MODE:
            options.add_argument('--headless=new')  # modern headless
            options.add_argument('--window-size=1920,1080')
        else:
            options.add_argument('--start-maximized')

        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        logger.info(f'Initializing local ChromeDriver with headless={HEADLESS_MODE}...')
        # Step 2: Install ChromeDriver and get its path
        try:
            driver_path = ChromeDriverManager().install()
            print(f"ChromeDriver installed at: {driver_path}")
        except Exception as e:
            print("Error during ChromeDriver installation:", e)
            raise

        # Step 3: Create a Service object with the path
        try:
            service = Service(driver_path)
            print("Service object created.")
        except Exception as e:
            print("Error creating Service object:", e)
            raise

        # Step 4: Create the Chrome WebDriver
        try:
            driver = webdriver.Chrome(service=service, options=options)
            print("WebDriver initialized successfully.")
        except Exception as e:
            print("Error initializing WebDriver:", e)
            raise
        # driver_path = resource_path("scraper/chromedriver.exe")
        # service = Service(executable_path=driver_path)
        # driver = webdriver.Chrome(service=service, options=options)

        logger.info('ChromeDriver initialized successfully.')
        return driver

    except Exception as e:
        logger.error(f'Error occurred while initializing ChromeDriver: {str(e)}')
        raise
