import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def start_driver():
    try:
        options = Options()
        options.add_argument("--start-maximized") 
        # options.add_argument("--headless")  # Add this line for headless mode
        options.add_argument("--disable-gpu")
        logger.info('Initializing ChromeDriver...')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        logger.info('ChromeDriver initialized successfully.')
        return driver

    except Exception as e:
        logger.error(f"Error occurred while initializing ChromeDriver: {str(e)}")
        raise