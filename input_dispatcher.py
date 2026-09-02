# middlewares/input_dispatcher.py
# Мидлварь для обработки входящих сообщений (логирование, фильтрация и т.п.)

import logging
from vkbottle.bot import Message
from vkbottle import BaseMiddleware

logger = logging.getLogger(__name__)

class InputDispatcher(BaseMiddleware[Message]):
    async def pre(self):
        """Выполняется до того, как сообщение попадёт в хендлер."""
        msg = self.event
        logger.debug(f"Входящее сообщение от {msg.from_id}: {msg.text}")
        # Здесь можно добавить фильтры, анти-спам, проверку прав и т.д.
        return True

    async def post(self):
        """Выполняется после обработки сообщения."""
        pass