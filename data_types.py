import enum


class WebDrivers(enum.Enum):
    firefox = 0
    chrome = 1
    firefox_proxy_server = 2
    chrome_proxy_server = 3

    none = 4


class LoggingTypes(enum.Enum):
    info = 0
    warning = 1
    error = 2
    critical = 3
