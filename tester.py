# admin/spec_administration/handlers/tester.py
# Обработчики тестировщика (категория 3, роль 3.2).

import json
import logging
from vkbottle.bot import Blueprint, Message
from db.database import db
from utils.permissions import has_permission
from admin.test_panel_management import (
    get_test_menu_keyboard,
    give_test_balance,
    give_test_item,
    reset_test_data,
    get_test_logs,
)

logger = logging.getLogger(__name__)

bp = Blueprint("tester")


@bp.on.message(payload={"cmd": "spec_test_panel"})
async def spec_test_panel(message: Message):
    if not await has_permission(message.from_id, "test_panel"):
        await message.answer("Недостаточно прав.")
        return
    keyboard = await get_test_menu_keyboard(message.from_id)
    if keyboard:
        await message.answer("🛠 Тест-панель", keyboard=keyboard)


@bp.on.message(payload={"cmd": "test_balance"})
async def test_balance(message: Message):
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'test_balance_input', '{}')",
        message.from_id
    )
    await message.answer("Введите виртуальный баланс:")


@bp.on.message(payload={"cmd": "test_level"})
async def test_level(message: Message):
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'test_level_input', '{}')",
        message.from_id
    )
    await message.answer("Введите виртуальный уровень:")


@bp.on.message(payload={"cmd": "test_reset"})
async def test_reset(message: Message):
    success, msg = await reset_test_data(message.from_id)
    await message.answer(msg)
    await spec_test_panel(message)


@bp.on.message(payload={"cmd": "test_logs"})
async def test_logs(message: Message):
    logs = await get_test_logs(message.from_id)
    await message.answer(logs)


@bp.on.message()
async def handle_tester_text(message: Message):
    state_row = await db.fetchone("SELECT state, data FROM user_states WHERE user_id = ?", message.from_id)
    if not state_row:
        return
    state = state_row["state"]
    text = message.text.strip()

    if state == "test_balance_input":
        if not text.isdigit():
            await message.answer("Введите число.")
            return
        success, msg = await give_test_balance(message.from_id, int(text))
        await message.answer(msg)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        await spec_test_panel(message)

    elif state == "test_level_input":
        if not text.isdigit():
            await message.answer("Введите число.")
            return
        # Устанавливаем уровень
        await db.execute(
            "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'test_level', ?)",
            message.from_id, json.dumps({"level": int(text), "exp": 0})
        )
        await message.answer(f"Виртуальный уровень установлен: {text}")
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        await spec_test_panel(message)

    else:
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)