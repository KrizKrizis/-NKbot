# db/backends/sqlite.py
# Бэкенд SQLite с использованием aiosqlite, WAL и busy_timeout.

import aiosqlite
from typing import Any, List, Optional, Tuple
from .base import DatabaseBackend


class SQLiteBackend(DatabaseBackend):
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        self.conn = await aiosqlite.connect(self.db_path)
        await self.conn.execute("PRAGMA journal_mode=WAL;")
        await self.conn.execute("PRAGMA busy_timeout=5000;")
        await self.conn.execute("PRAGMA foreign_keys=ON;")
        self.conn.row_factory = aiosqlite.Row

    async def disconnect(self) -> None:
        if self.conn:
            await self.conn.close()

    async def execute(self, query: str, *params: Any) -> None:
        await self.conn.execute(query, params)
        await self.conn.commit()

    async def fetchone(self, query: str, *params: Any) -> Optional[Tuple]:
        cursor = await self.conn.execute(query, params)
        row = await cursor.fetchone()
        await cursor.close()
        return row

    async def fetchall(self, query: str, *params: Any) -> List[Tuple]:
        cursor = await self.conn.execute(query, params)
        rows = await cursor.fetchall()
        await cursor.close()
        return rows

    async def execute_many(self, query: str, params_list: List[Tuple]) -> None:
        await self.conn.executemany(query, params_list)
        await self.conn.commit()

    async def execute_script(self, script: str) -> None:
        await self.conn.executescript(script)
        await self.conn.commit()