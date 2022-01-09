import logging
import os
import sys
from datetime import datetime


# It means when use: <from logging_utils import *>, it will import all in <__all__> variable.
# If this module has many classes or functions, we need to add more code to import
__all__ = [
    'get_current_time_format',
    'get_logger'
]


def get_current_time_format(fmt='%d_%m_%Y_%H_%M_%S'):
    """
    Get current time according to <fmt> format
    """

    return datetime.now().strftime(fmt)


# Logging formatter supporting colorized output
class _ColorizedLogFormatter(logging.Formatter):
    COLOR_CODES = {
        logging.CRITICAL: "\033[1;35m",  # bright/bold magenta
        logging.ERROR: "\033[1;31m",  # bright/bold red
        logging.WARNING: "\033[1;33m",  # bright/bold yellow
        logging.INFO: "\033[0;37m",  # white / light gray
        logging.DEBUG: "\033[1;30m"  # bright/bold black / dark gray
    }
    
    RESET_CODE = "\033[0m"

    def __init__(self, color=False, *args, **kwargs):
        super(_ColorizedLogFormatter, self).__init__(*args, **kwargs)
        self.color = color

    def format(self, record, *args, **kwargs):
        if self.color and record.levelno in self.COLOR_CODES:
            record.color_on = self.COLOR_CODES[record.levelno]
            record.color_off = self.RESET_CODE
        else:
            record.color_on = record.color_off = ''
        return super(_ColorizedLogFormatter, self).format(record, *args, **kwargs)


def get_logger(name, console_stream='stdout', log_dir=None):
    """
    Logging according to the setting format
    """

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    log_format = '%(color_on)s%(asctime)s.%(msecs)03d ' \
                 '[%(threadName)s] [%(name)s] [%(levelname)s] %(message)s%(color_off)s'
    date_format = '%m/%d/%Y %H:%M:%S'
    if log_dir is not None:
        os.makedirs(log_dir, exist_ok=True)
        logfile = os.path.join(log_dir, get_current_time_format()) + '.log'
        logfile_handler = logging.FileHandler(logfile, mode='w')
        logfile_handler.setFormatter(_ColorizedLogFormatter(fmt=log_format, datefmt=date_format, color=False))
        logger.addHandler(logfile_handler)
    if console_stream:
        stream = getattr(sys, console_stream) if isinstance(console_stream, str) else console_stream
        console_handler = logging.StreamHandler(stream)
        console_handler.setFormatter(_ColorizedLogFormatter(fmt=log_format, datefmt=date_format, color=True))
        logger.addHandler(console_handler)
    return logger


if __name__ == '__main__':
    logger = get_logger(__file__)
    logger.warning('yo!')
