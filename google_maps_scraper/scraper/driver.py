import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def start_driver(headless=False):  # ✅ Added headless parameter
    try:
        options = Options()
        if headless:
            options.add_argument("--headless=new")  # ✅ Use `--headless=new` for modern Chrome
            options.add_argument("--window-size=1920,1080")
        else:
            options.add_argument("--start-maximized")

        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        logger.info(f'Initializing ChromeDriver with headless={headless}...')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        logger.info('ChromeDriver initialized successfully.')
        return driver

    except Exception as e:
        logger.error(f"Error occurred while initializing ChromeDriver: {str(e)}")
        raise