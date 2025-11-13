import logging

from logger.abstract import AbstractLogger


class ConsoleLogger(AbstractLogger):
    def __init__(self, name: str, level: int | str):
        # init logger object
        self._logger = logging.getLogger(name)
        self._level = level
        self._logger.setLevel(level)

        # set handlers
        self._set_console_handler()

    def critical(self, msg: object, request_id: str = '-'):
        self._logger.critical(msg)

    def fatal(self, msg: object, request_id: str = '-'):
        self._logger.fatal(msg)

    def error(self, msg: object, request_id: str = '-'):
        self._logger.error(msg)

    def warning(self, msg: object, request_id: str = '-'):
        self._logger.warning(msg)

    def info(self, msg: object, request_id: str = '-'):
        self._logger.info(msg)

    def debug(self, msg: object, request_id: str = '-'):
        self._logger.debug(msg)

    def _set_console_handler(self):
        # set console formatter
        self._formatter = logging.Formatter(
            '%(asctime)s  %(levelname)-5s %(process)d --- [%(threadName)s] %(name)s   : %(message)s',
            '%Y-%m-%dT%H:%M:%S%z'
        )

        # init console handler
        self._console_handler = logging.StreamHandler()
        self._console_handler.setFormatter(self._formatter)
        self._console_handler.setLevel(self._level)

        # register handler
        self._logger.addHandler(self._console_handler)
