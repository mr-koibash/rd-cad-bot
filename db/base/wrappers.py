import functools
import logging
import inspect

from psycopg2 import DatabaseError
from psycopg2.pool import PoolError

from logger.console import ConsoleLogger


def repository(exclude_methods=None):
    exclude_methods = set(exclude_methods or [])

    def class_decorator(cls):
        original_init = cls.__init__

        @functools.wraps(original_init)
        def new_init(self, *args, **kwargs):
            # get args
            name = kwargs.pop('name', cls.__name__)
            level = kwargs.pop('level', logging.DEBUG)

            # init logger (logstash or default)
            self._logger = ConsoleLogger(name, level)

            original_init(self, *args, **kwargs)
        cls.__init__ = new_init

        def exception_handler(func):
            @functools.wraps(func)
            def wrapper(self, *args, **kwargs):
                request_id = kwargs.pop('request_id', '-')
                try:
                    return func(self, *args, **kwargs)
                except PoolError as e:
                    self._logger.error(f"Database pool connection error: {e}", request_id=request_id)
                except DatabaseError as e:
                    self._logger.error(f"Database error: {e}", request_id=request_id)
                except ValueError as e:
                    self._logger.error(f"Incorrect value: {e}", request_id=request_id)
                except Exception as e:
                    self._logger.critical(f"Unexpected error: {e}", request_id=request_id)

            return wrapper

        for name, method in inspect.getmembers(cls, inspect.isfunction):
            if not name.startswith('_') and name not in exclude_methods:
                setattr(cls, name, exception_handler(method))

        return cls

    return class_decorator
