from abc import ABC, abstractmethod


class AbstractLogger(ABC):
    @abstractmethod
    def critical(self, msg: object, request_id: str = '-'):
        pass

    @abstractmethod
    def fatal(self, msg: object, request_id: str = '-'):
        pass

    @abstractmethod
    def error(self, msg: object, request_id: str = '-'):
        pass

    @abstractmethod
    def warning(self, msg: object, request_id: str = '-'):
        pass

    @abstractmethod
    def info(self, msg: object, request_id: str = '-'):
        pass

    @abstractmethod
    def debug(self, msg: object, request_id: str = '-'):
        pass