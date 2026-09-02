# db/backends/postgres.py
# Полная реализация бэкенда PostgreSQL с использованием asyncpg.

import re
import asyncpg
from typing import Any, List, Optional, Tuple
from .base import DatabaseBackend


class PostgresBackend(DatabaseBackend):
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    @staticmethod
    def _convert_placeholders(query: str) -> str:
        """
        Заменяет символы '?' на '$1', '$2', ... для совместимости
        с SQL-запросами, написанными для SQLite.
        """
        counter = 0

        def replace(match):
            nonlocal counter
            counter += 1
            return f"${counter}"

        return re.sub(r"\?", replace, query)

    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(dsn=self.dsn)

    async def disconnect(self) -> None:
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def execute(self, query: str, *params: Any) -> None:
        if not self.pool:
            raise RuntimeError("PostgreSQL пул не инициализирован")
        converted_query = self._convert_placeholders(query)
        async with self.pool.acquire() as conn:
            await conn.execute(converted_query, *params)

    async def fetchone(self, query: str, *params: Any) -> Optional[Tuple]:
        if not self.pool:
            raise RuntimeError("PostgreSQL пул не инициализирован")
        converted_query = self._convert_placeholders(query)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(converted_query, *params)
            return tuple(row) if row else None

    async def fetchall(self, query: str, *params: Any) -> List[Tuple]:
        if not self.pool:
            raise RuntimeError("PostgreSQL пул не инициализирован")
        converted_query = self._convert_placeholders(query)
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(converted_query, *params)
            return [tuple(row) for row in rows]

    async def execute_many(self, query: str, params_list: List[Tuple]) -> None:
        if not self.pool:
            raise RuntimeError("PostgreSQL пул не инициализирован")
        converted_query = self._convert_placeholders(query)
        async with self.pool.acquire() as conn:
            await conn.executemany(converted_query, params_list)

    async def execute_script(self, script: str) -> None:
        if not self.pool:
            raise RuntimeError("PostgreSQL пул не инициализирован")
        statements = [s.strip() for s in script.split(";") if s.strip()]
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for statement in statements:
                    converted = self._convert_placeholders(statement)
                    await conn.execute(converted)