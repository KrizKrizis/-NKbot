# nkbot.py
# Точка входа в бота NiksKriz Corporation.
# Автоматически находит и загружает все Blueprint'ы из папок-модулей.

import logging
import importlib
import pkgutil
from pathlib import Path

from vkbottle.bot import Bot, Blueprint, Message
from vkbottle.polling import BotPolling

from config import VK_TOKEN, LOG_LEVEL, GROUP_ID
from db.database import db
from db.migrations import init_db
from middlewares.input_dispatcher import InputDispatcher
from services.scheduler import init_scheduler

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Создаём бота
bot = Bot(token=VK_TOKEN)
bot.labeler.message_view.register_middleware(InputDispatcher)

MODULE_DIRS = [
    "player", "city", "jobs", "bank", "business", "casino",
    "nkvito", "craft", "mars", "lottery", "housing", "transport",
    "shop", "gas_station", "auction", "admin"
]

def discover_and_load_blueprints():
    """Обходит папки модулей, импортирует файлы и загружает Blueprint'ы через bp.load(bot)."""
    for module_dir in MODULE_DIRS:
        package_path = Path(__file__).parent / module_dir / "handlers"
        if not package_path.exists():
            continue

        for module_info in pkgutil.iter_modules([str(package_path)]):
            module_name = f"{module_dir}.handlers.{module_info.name}"
            try:
                module = importlib.import_module(module_name)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    # Загружаем только экземпляры Blueprint, а не сам класс
                    if isinstance(attr, Blueprint):
                        attr.load(bot)
                        logger.info(f"Загружен Blueprint '{attr_name}' из {module_name}")
            except Exception as e:
                logger.error(f"Ошибка загрузки модуля {module_name}: {e}")

    # Отдельно обрабатываем admin/base.py
    try:
        import admin.base as admin_base
        for attr_name in dir(admin_base):
            attr = getattr(admin_base, attr_name)
            if isinstance(attr, Blueprint):
                attr.load(bot)
                logger.info(f"Загружен Blueprint '{attr_name}' из admin/base.py")
    except Exception as e:
        logger.error(f"Ошибка загрузки admin/base.py: {e}")

async def on_startup():
    try:
        logger.info("Запуск NiksKriz Corporation...")
        await db.initialize()
        await init_db()
        init_scheduler()
        discover_and_load_blueprints()
        logger.info("Бот готов.")
    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}", exc_info=True)
        raise

async def on_shutdown():
    logger.info("Завершение работы...")
    await db.close()
    logger.info("Бот остановлен.")

# ============================================================
# ВРЕМЕННЫЙ ОБРАБОТЧИК — закомментирован, чтобы не мешал работе.
# Раскомментируй только для отладки.
# ============================================================
# @bot.on.message()
# async def debug_any_message(message: Message):
#     logger.info(f"=== ПОЛУЧЕНО сообщение: from_id={message.from_id}, text={message.text}, chat_id={message.chat_id}, peer_id={message.peer_id}")
#     await message.answer(f"Бот работает! Ты написал: {message.text}")
# ============================================================

if __name__ == "__main__":
    # ВАЖНО: передаём КОРУТИНУ (результат вызова), а не функцию
    bot.loop_wrapper.on_startup.append(on_startup())
    bot.loop_wrapper.on_shutdown.append(on_shutdown())
    bot.run_forever()