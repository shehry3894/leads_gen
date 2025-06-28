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
        base_path = os.path.abspath(".")
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
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        # driver_path = resource_path("scraper/chromedriver.exe")
        # service = Service(executable_path=driver_path)
        # driver = webdriver.Chrome(service=service, options=options)

        logger.info('ChromeDriver initialized successfully.')
        return driver

    except Exception as e:
        logger.error(f'Error occurred while initializing ChromeDriver: {str(e)}')
        raise