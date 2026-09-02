# admin/system_management.py
# Системные функции: бэкапы, логи, управление чатами, планировщик, перезагрузка конфигурации.

import json
import logging
import os
import shutil
import importlib
from datetime import datetime, timezone
from vkbottle import Keyboard, KeyboardButtonColor, Text
from db.database import db
from utils.permissions import has_permission
from config import SQLITE_PATH, DB_TYPE
import config as app_config

logger = logging.getLogger(__name__)


async def create_backup() -> tuple:
    if DB_TYPE != "sqlite":
        return False, "Бэкап поддерживается только для SQLite."
    if not os.path.exists(SQLITE_PATH):
        return False, "Файл базы данных не найден."
    backup_dir = os.path.join(os.path.dirname(SQLITE_PATH), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"nikskriz_backup_{timestamp}.db")
    shutil.copy2(SQLITE_PATH, backup_path)
    return True, f"Бэкап создан: {backup_path}"


async def get_recent_logs(limit: int = 50) -> str:
    """Возвращает последние записи из admin_log."""
    rows = await db.fetchall(
        "SELECT admin_id, action, details, timestamp FROM admin_log ORDER BY id DESC LIMIT ?",
        limit
    )
    if not rows:
        return "Логи пусты."
    lines = ["📋 Последние действия:"]
    for r in rows:
        user = await db.fetchone("SELECT first_name, last_name FROM users WHERE vk_id = ?", r["admin_id"])
        name = f"{user['first_name']} {user['last_name']}".strip() if user else str(r["admin_id"])
        lines.append(f"  • {name}: {r['action']} ({r['details']}) в {r['timestamp']}")
    return "\n".join(lines)


async def get_chat_config() -> list:
    return await db.fetchall("SELECT * FROM chat_config ORDER BY chat_mode")


async def format_chat_config(chats: list) -> str:
    if not chats:
        return "Чаты не настроены."
    lines = ["💬 Чаты:"]
    for c in chats:
        lines.append(f"  Режим {c['chat_mode']}: ID {c['chat_id']} ({c['description']})")
    return "\n".join(lines)


async def set_chat_id(mode: int, chat_id: int) -> tuple:
    valid_modes = {2: "Чат хелперов", 3: "Чат администрации", 4: "Чат статистики", 5: "Общий чат команды", 6: "Чат тестировщиков", 7: "Полный лог"}
    if mode not in valid_modes:
        return False, "Неверный режим."
    await db.execute(
        "INSERT OR REPLACE INTO chat_config (chat_mode, chat_id, description) VALUES (?, ?, ?)",
        mode, chat_id, valid_modes[mode]
    )
    return True, f"Чат режима {mode} установлен на ID {chat_id}."


async def get_scheduler_status() -> str:
    from services.scheduler import scheduler
    jobs = scheduler.get_jobs()
    if not jobs:
        return "Планировщик не запущен или нет задач."
    lines = ["⏰ Задачи планировщика:"]
    for job in jobs:
        lines.append(f"  • {job.id}: следующий запуск {job.next_run_time}")
    return "\n".join(lines)


async def run_scheduler_job(job_id: str) -> tuple:
    from services.scheduler import scheduler
    job = scheduler.get_job(job_id)
    if not job:
        return False, "Задача не найдена."
    job.func()
    return True, f"Задача {job_id} запущена вручную."


async def reload_config() -> tuple:
    importlib.reload(app_config)
    return True, "Конфигурация перезагружена (некоторые параметры могут требовать рестарта)."