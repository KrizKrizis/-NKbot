# admin/project_leadership/handlers/system.py
# Обработчики системных функций для руководства.

import logging
from vkbottle.bot import Blueprint, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text
from db.database import db
from utils.permissions import get_admin_info
from admin.system_management import (
    get_system_menu_keyboard,
    create_backup,
    get_recent_logs,
    get_chat_config,
    format_chat_config,
    set_chat_id,
    get_scheduler_status,
    run_scheduler_job,
    reload_config,
)

logger = logging.getLogger(__name__)

bp = Blueprint("founder_system")


@bp.on.message(payload={"cmd": "system_menu"})
async def system_menu(message: Message):
    keyboard = await get_system_menu_keyboard(message.from_id)
    if keyboard:
        await message.answer("💻 Система", keyboard=keyboard)
    else:
        await message.answer("Недостаточно прав.")


@bp.on.message(payload={"cmd": "system_reload_cache"})
async def system_reload_cache(message: Message):
    from utils.permissions import reload_admin_cache
    await reload_admin_cache()
    await message.answer("Кеш ролей сброшен.")


@bp.on.message(payload={"cmd": "system_backup"})
async def system_backup(message: Message):
    success, msg = await create_backup()
    await message.answer(msg)


@bp.on.message(payload={"cmd": "system_logs"})
async def system_logs(message: Message):
    logs = await get_recent_logs(50)
    await message.answer(logs)


@bp.on.message(payload={"cmd": "system_chats"})
async def system_chats(message: Message):
    chats = await get_chat_config()
    text = await format_chat_config(chats)
    keyboard = Keyboard(one_time=False, inline=True)
    for c in chats:
        keyboard.add(Text(f"Режим {c['chat_mode']}", payload={"cmd": "system_chat_set", "mode": c["chat_mode"]}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "system_menu"}), color=KeyboardButtonColor.SECONDARY)
    await message.answer(text, keyboard=keyboard)


@bp.on.message(payload={"cmd": "system_chat_set"})
async def system_chat_set(message: Message):
    payload = message.get_payload_json()
    mode = int(payload.get("mode"))
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'system_chat_id_input', ?)",
        message.from_id, json.dumps({"mode": mode})
    )
    await message.answer("Введите новый ID чата:")


@bp.on.message(payload={"cmd": "system_scheduler"})
async def system_scheduler(message: Message):
    status = await get_scheduler_status()
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("🔄 Обновить", payload={"cmd": "system_scheduler"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "system_menu"}), color=KeyboardButtonColor.SECONDARY)
    await message.answer(status, keyboard=keyboard)


@bp.on.message(payload={"cmd": "system_reload_config"})
async def system_reload_config(message: Message):
    success, msg = await reload_config()
    await message.answer(msg)


@bp.on.message()
async def handle_system_text(message: Message):
    state_row = await db.fetchone("SELECT state, data FROM user_states WHERE user_id = ?", message.from_id)
    if not state_row:
        return
    state = state_row["state"]
    if state == "system_chat_id_input":
        text = message.text.strip()
        if not text.isdigit():
            await message.answer("ID чата должен быть числом.")
            return
        chat_id = int(text)
        data = json.loads(state_row["data"])
        mode = data["mode"]
        success, msg = await set_chat_id(mode, chat_id)
        await message.answer(msg)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        await system_chats(message)
    else:
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)