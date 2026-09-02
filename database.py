# db/database.py
# Асинхронное подключение к SQLite через aiosqlite.
# Поддерживает передачу параметров как кортеж, список или отдельные значения.

import aiosqlite
from config import SQLITE_PATH

class Database:
    def __init__(self):
        self._conn = None

    async def initialize(self):
        self._conn = await aiosqlite.connect(SQLITE_PATH)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    @property
    def conn(self):
        if self._conn is None:
            raise RuntimeError("База не инициализирована. Вызови await db.initialize()")
        return self._conn

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    # Универсальный метод для выполнения запросов
    async def execute(self, sql, *params):
        # Если params пуст, используем None
        if not params:
            cursor = await self.conn.execute(sql)
        elif len(params) == 1 and isinstance(params[0], (tuple, list)):
            # Если передан один параметр и это список/кортеж, используем его
            cursor = await self.conn.execute(sql, params[0])
        else:
            # Иначе собираем все параметры в кортеж
            cursor = await self.conn.execute(sql, params)
        await self.conn.commit()
        return cursor

    async def fetchall(self, sql, *params):
        if not params:
            cursor = await self.conn.execute(sql)
        elif len(params) == 1 and isinstance(params[0], (tuple, list)):
            cursor = await self.conn.execute(sql, params[0])
        else:
            cursor = await self.conn.execute(sql, params)
        return await cursor.fetchall()

    async def fetchone(self, sql, *params):
        if not params:
            cursor = await self.conn.execute(sql)
        elif len(params) == 1 and isinstance(params[0], (tuple, list)):
            cursor = await self.conn.execute(sql, params[0])
        else:
            cursor = await self.conn.execute(sql, params)
        return await cursor.fetchone()

# Единый экземпляр для всего проекта
db = Database()