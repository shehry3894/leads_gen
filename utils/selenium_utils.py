import os
import platform

from typing import Tuple
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver import Firefox, Chrome, ChromeOptions, FirefoxOptions

from data_types import WebDrivers
from inputs.config import SeleniumConfig
from utils.printing_and_logging import print_and_log

LIB_NAME_GECKO = 'geckodriver' if platform.system() == 'Linux' else 'geckodriver.exe'
LIB_NAME_CHROME = 'chromedriver' if platform.system() == 'Linux' else 'chromedriver.exe'

curr_dir_path = os.path.dirname(os.path.abspath(__file__))
FIREFOX_DRIVER_PATH = r'{}'.format(os.path.abspath(os.path.join(curr_dir_path, '..', 'libs', LIB_NAME_GECKO)))
CHROME_DRIVER_PATH = r'{}'.format(os.path.abspath(os.path.join('libs', LIB_NAME_CHROME)))


def setup_driver(proxy: Tuple[str, int] = (None, None),
                 driver_type: WebDrivers = WebDrivers.firefox.value):
    if driver_type == WebDrivers.firefox.value:
        return setup_firefox_driver(proxy)
    elif driver_type == WebDrivers.chrome:
        return setup_chrome_driver(proxy)
    else:
        print_and_log('UTILS_#setup_driver-NONE')


def setup_chrome_driver(proxy: Tuple[str, int] = (None, None)) -> Chrome:
    print_and_log('UTILS_#_setup_chrome_driver-DEPRECATED')

    chrome_options = ChromeOptions()
    chrome_options.add_argument("--start-maximized")

    if proxy is not None:
        proxy_with_port = str(proxy[0] + ':' + str(proxy[1]))
        chrome_options.add_argument('--proxy-server=%s' % proxy_with_port)

    chrome_options.add_argument(f'user-agent={UserAgent().random}')

    return Chrome(executable_path=CHROME_DRIVER_PATH, chrome_options=chrome_options)


def setup_firefox_driver(proxy: Tuple[str, int] = (None, None)) -> Firefox:
    print_and_log('UTILS_#_setup_firefox_driver')

    options = FirefoxOptions()

    if SeleniumConfig.HEADLESS:
        options.add_argument("--headless")

    profile = get_base_firefox_profile()

    if proxy[0] is not None:
        proxy_addr = proxy[0]
        proxy_port = proxy[1]

        profile.set_preference("network.proxy.type", 1)
        profile.set_preference("network.proxy.http", proxy_addr)
        profile.set_preference("network.proxy.http_port", proxy_port)
        profile.set_preference("network.proxy.ssl", proxy_addr)
        profile.set_preference("network.proxy.ssl_port", proxy_port)

        print_and_log('UTILS_#_firing up the browser with {}:{}'.format(proxy_addr, proxy_port))
    else:
        print_and_log('UTILS_#_firing up the browser with System Proxy.')

    profile.update_preferences()
    return Firefox(executable_path=FIREFOX_DRIVER_PATH, options=options, firefox_profile=profile)


def get_base_firefox_profile():
    profile = webdriver.FirefoxProfile()
    if SeleniumConfig.USE_CUSTOM_PROFILE:
        profile = webdriver.FirefoxProfile('profiles/firefox_profile')

    profile.set_preference("javascript.enabled", True)
    profile.set_preference("network.cookie.cookieBehavior", 0)

    # Disable WebRTC
    profile.set_preference("media.peerconnection.enabled", False)
    profile.set_preference("beacon.enabled", False)

    # Update automation settings
    profile.set_preference("dom.webdriver.enabled", False)
    profile.set_preference('useAutomationExtension', False)

    user_agent = UserAgent().random
    profile.set_preference("general.useragent.override", user_agent)

    return profile
