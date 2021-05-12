# See https://www.toptal.com/python/in-depth-python-logging


import logging
import sys

# from logging.handlers import TimedRotatingFileHandler
FORMATTER = logging.Formatter("%(asctime)s — %(name)s — %(levelname)s — %(message)s")


# LOG_FILE = "my_app.log"


def class_fullname(obj):
    # o.__module__ + "." + o.__class__.__qualname__ is an example in
    # this context of H.L. Mencken's "neat, plausible, and wrong."
    # Python makes no guarantees as to whether the __module__ special
    # attribute is defined, so we take a more circumspect approach.
    # Alas, the module name is explicitly excluded from __qualname__
    # in Python 3.

    module = obj.__class__.__module__
    if module is None or module == str.__class__.__module__:
        return obj.__class__.__name__  # Avoid reporting __builtin__
    else:
        return module + '.' + obj.__class__.__name__


def get_console_handler():
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(FORMATTER)
    return console_handler


# def get_file_handler():
#    file_handler = TimedRotatingFileHandler(LOG_FILE, when='midnight')
#    file_handler.setFormatter(FORMATTER)
#    return file_handler


def get_logger(logger_name):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)  # better to have too much log than not enough
    if not logger.hasHandlers():
        logger.addHandler(get_console_handler())
        # logger.addHandler(get_file_handler())
    # with this pattern, it's rarely necessary to propagate the error up to parent
    logger.propagate = False
    return logger
