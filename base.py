# db/backends/base.py
# Абстрактный базовый класс для бэкендов базы данных.

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple


class DatabaseBackend(ABC):
    @abstractmethod
    async def connect(self) -> None:
        """Устанавливает соединение с базой данных."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Закрывает соединение."""
        pass

    @abstractmethod
    async def execute(self, query: str, *params: Any) -> None:
        """Выполняет запрос без возврата строк."""
        pass

    @abstractmethod
    async def fetchone(self, query: str, *params: Any) -> Optional[Tuple]:
        """Возвращает одну строку."""
        pass

    @abstractmethod
    async def fetchall(self, query: str, *params: Any) -> List[Tuple]:
        """Возвращает все строки."""
        pass

    @abstractmethod
    async def execute_many(self, query: str, params_list: List[Tuple]) -> None:
        """Выполняет один запрос с разными параметрами."""
        pass

    @abstractmethod
    async def execute_script(self, script: str) -> None:
        """Выполняет скрипт, содержащий несколько SQL-запросов."""
        pass