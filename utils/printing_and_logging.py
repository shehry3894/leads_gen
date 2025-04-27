import logging
import os

from logging.handlers import RotatingFileHandler

from data_types import LoggingTypes

output_log_folder_path = os.path.join('outputs', 'logs')
if not os.path.exists(output_log_folder_path):
    os.makedirs(output_log_folder_path, mode=0o777)
log_file_path = os.path.join(output_log_folder_path, "log.log")
print(log_file_path)

log_handler = RotatingFileHandler(log_file_path, mode='w', maxBytes=100 * 1024 * 1024,
                                  backupCount=5, encoding=None, delay=0)
log_formatter = logging.Formatter('%(asctime)-15s %(threadName)-10s %(levelname)-8s %(message)s')
log_handler.setFormatter(log_formatter)
log_handler.setLevel(logging.INFO)

logger = logging.getLogger('root')
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)


def print_and_log(msg: str, logging_type: LoggingTypes = LoggingTypes.info):
    print(msg)

    if logging_type == LoggingTypes.info:
        logger.info(msg)
    elif logging_type == LoggingTypes.warning:
        logger.warning(msg)
    elif logging_type == LoggingTypes.error:
        logger.error(msg)
    elif logging_type == LoggingTypes.critical:
        logger.critical(msg)
