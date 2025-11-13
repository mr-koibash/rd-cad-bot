from abc import ABC, abstractmethod
from typing import Any


class AbstractDatabaseManager(ABC):
    @abstractmethod
    def execute_query(self, query: str, params=None) -> list[Any]:
        pass

    @abstractmethod
    def close(self) -> None:
        pass
