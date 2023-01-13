import os
import logging.handlers
from datetime import datetime
import time
import json

DEFAULT_FORMATTER = logging.Formatter(fmt='%(asctime)-8s | %(filename)-18s:%(funcName)-22s:%(lineno)-3d | %(levelname)-8s: %(message)s',
                                      datefmt='%H:%M:%S')
HTML_FORMATTER = logging.Formatter(fmt='%(message)s')


class Logger(logging.Logger):
    """
    Logger

    Set some parts automatically, here to expand on with specific methods if needs be
    """
    def __init__(self, name, **kwargs):
        if os.path.exists('config.json'):
            with open('config.json', 'r') as config_file:
                config = json.load(config_file)
        else:
            config = {}

        self.level = 0
        super().__init__(name)
        self.root.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        handler.setFormatter(DEFAULT_FORMATTER)
        handler.setLevel(20)
        self.addHandler(handler)

        self.date = datetime.now().isoformat().split('T')[0]
        if 'dir' in kwargs:
            self.directory = kwargs['dir']
            self.file = os.path.join(self.directory, f"{name}_{self.date}.log")
            try:
                os.mkdir(os.path.split(self.file)[0])
            except FileExistsError:
                pass
            except FileNotFoundError:
                raise self.LoggerCantMakeFileException(r"Can't create nested folders yet")
        else:
            self.directory = 'logs'
            self.file = f"{name}_{self.date}.log"

        if not os.path.exists(self.directory):
            os.makedirs(self.directory)

        for f in os.listdir(self.directory):
            if os.stat(os.path.join(self.directory, f)).st_mtime < time.time() - (config.get('log_lifetime') or 7) * 86400:
                if os.path.isfile(f):
                    os.remove(os.path.join(self.directory, f))

        # Define File Handler
        self.__file_handler = logging.FileHandler(os.path.join(self.directory, self.file),
                                                  mode='a+')
        self.__file_handler.setFormatter(DEFAULT_FORMATTER)
        self.__file_handler.setLevel(0)
        self.addHandler(self.__file_handler)

        self.info("===========================================")
        self.debug(f"{self.name} logger created...")

    class LoggerCantMakeFileException(Exception):
        pass

    def update_file_handler(self):
        if self.date != datetime.now().isoformat().split('T')[0]:
            self.date = datetime.now().isoformat().split('T')[0]
            self.directory = 'logs'
            self.file = f"{self.name}_{self.date}.log"

            self.removeHandler(self.__file_handler)
            self.__file_handler = logging.FileHandler(os.path.join(self.directory, self.file),
                                                      mode='a+')
            self.__file_handler.setFormatter(DEFAULT_FORMATTER)
            self.__file_handler.setLevel(0)
            self.addHandler(self.__file_handler)


def log_wrap(logger):

    """ Wrapper """
    def decorate(func):

        """ Decorator """
        def call(*args, **kwargs):
            """ Actual wrapping """
            logger.debug(func.__name__ + " {")
            logger.level += 1

            result = func(*args, **kwargs)

            logger.level -= 1
            logger.debug("} " + func.__name__)

            return result

        # Return decorator
        return call

    # Return wrapper
    return decorate


