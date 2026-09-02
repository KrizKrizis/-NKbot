# admin/project_leadership/handlers/players.py
# Обработчики управления игроками для руководства.

import json
import logging
from vkbottle.bot import Blueprint, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text
from db.database import db
from utils.permissions import get_admin_info
from admin.player_management import (
    format_player_list_page,
    get_player_profile,
    search_player,
    format_search_results,
    block_player,
    unblock_player,
    give_item,
    take_item,
    give_money,
    take_money,
)
from admin.project_leadership.handlers.founder import founder_players

logger = logging.getLogger(__name__)

bp = Blueprint("founder_players")


@bp.on.message(payload={"cmd": "players_page"})
async def players_page(message: Message):
    payload = message.get_payload_json()
    page = int(payload.get("page", 1))
    text, keyboard = await format_player_list_page(page)
    await message.answer(text, keyboard=keyboard)


@bp.on.message(payload={"cmd": "player_stats_request"})
async def player_stats_request(message: Message):
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'player_stats_id_input', '{}')",
        message.from_id
    )
    await message.answer("Введите игровой ID игрока для просмотра статистики:")


@bp.on.message(payload={"cmd": "player_logs_request"})
async def player_logs_request(message: Message):
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'player_logs_id_input', '{}')",
        message.from_id
    )
    await message.answer("Введите игровой ID игрока для просмотра логов:")


@bp.on.message(payload={"cmd": "player_search_request"})
async def player_search_request(message: Message):
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'player_search_input', '{}')",
        message.from_id
    )
    await message.answer("Введите имя, фамилию, @username или ID игрока:")


@bp.on.message(payload={"cmd": "player_manage_request"})
async def player_manage_request(message: Message):
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'player_manage_id_input', '{}')",
        message.from_id
    )
    await message.answer("Введите игровой ID игрока для управления:")


# Обработчики действий управления
@bp.on.message(payload={"cmd": "manage_freeze"})
async def manage_freeze(message: Message):
    payload = message.get_payload_json()
    target_id = int(payload.get("target_id"))
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'manage_freeze_duration', ?)",
        message.from_id, json.dumps({"target_id": target_id})
    )
    await message.answer("Введите длительность заморозки в днях (0 = навсегда):")


@bp.on.message(payload={"cmd": "manage_target_block"})
async def manage_target_block(message: Message):
    payload = message.get_payload_json()
    target_id = int(payload.get("target_id"))
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'manage_target_duration', ?)",
        message.from_id, json.dumps({"target_id": target_id})
    )
    await message.answer("Введите длительность точечной блокировки в днях (0 = навсегда):")


@bp.on.message(payload={"cmd": "manage_full_ban"})
async def manage_full_ban(message: Message):
    payload = message.get_payload_json()
    target_id = int(payload.get("target_id"))
    success, msg = await block_player(message.from_id, target_id, "full", 0)  # навсегда
    await message.answer(msg)
    await founder_players(message)


@bp.on.message(payload={"cmd": "manage_unblock"})
async def manage_unblock(message: Message):
    payload = message.get_payload_json()
    target_id = int(payload.get("target_id"))
    success, msg = await unblock_player(message.from_id, target_id)
    await message.answer(msg)
    await founder_players(message)


@bp.on.message(payload={"cmd": "manage_give_money"})
async def manage_give_money(message: Message):
    payload = message.get_payload_json()
    target_id = int(payload.get("target_id"))
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'manage_money_amount_give', ?)",
        message.from_id, json.dumps({"target_id": target_id})
    )
    await message.answer("Введите сумму для выдачи:")


@bp.on.message(payload={"cmd": "manage_take_money"})
async def manage_take_money(message: Message):
    payload = message.get_payload_json()
    target_id = int(payload.get("target_id"))
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'manage_money_amount_take', ?)",
        message.from_id, json.dumps({"target_id": target_id})
    )
    await message.answer("Введите сумму для изъятия:")


@bp.on.message(payload={"cmd": "manage_give_item"})
async def manage_give_item(message: Message):
    payload = message.get_payload_json()
    target_id = int(payload.get("target_id"))
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'manage_item_id_give', ?)",
        message.from_id, json.dumps({"target_id": target_id})
    )
    await message.answer("Введите ID предмета для выдачи:")


@bp.on.message(payload={"cmd": "manage_take_item"})
async def manage_take_item(message: Message):
    payload = message.get_payload_json()
    target_id = int(payload.get("target_id"))
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'manage_item_id_take', ?)",
        message.from_id, json.dumps({"target_id": target_id})
    )
    await message.answer("Введите ID предмета для изъятия:")


# Общий обработчик текстовых сообщений для состояний управления игроками
@bp.on.message()
async def handle_player_text(message: Message):
    state_row = await db.fetchone("SELECT state, data FROM user_states WHERE user_id = ?", message.from_id)
    if not state_row:
        return
    state = state_row["state"]
    text = message.text.strip()
    data = json.loads(state_row["data"])
    target_id = data.get("target_id")

    if state == "player_stats_id_input":
        if not text.isdigit():
            await message.answer("ID должен быть числом.")
            return
        target_game_id = int(text)
        user = await db.fetchone("SELECT vk_id FROM users WHERE game_id = ?", target_game_id)
        if not user:
            await message.answer("Игрок не найден.")
            await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
            return
        profile = await get_player_profile(user["vk_id"], message.from_id)
        await message.answer(profile)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)

    elif state == "player_logs_id_input":
        if not text.isdigit():
            await message.answer("ID должен быть числом.")
            return
        target_game_id = int(text)
        user = await db.fetchone("SELECT vk_id FROM users WHERE game_id = ?", target_game_id)
        if not user:
            await message.answer("Игрок не найден.")
            await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
            return
        logs = await db.fetchall("SELECT * FROM admin_log WHERE admin_id = ? ORDER BY id DESC LIMIT 20", user["vk_id"])
        if not logs:
            await message.answer("Логов нет.")
        else:
            lines = ["📋 Логи игрока:"]
            for l in logs:
                lines.append(f"  • {l['action']}: {l['details']} ({l['timestamp']})")
            await message.answer("\n".join(lines))
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)

    elif state == "player_search_input":
        results = await search_player(text)
        formatted = await format_search_results(results)
        await message.answer(formatted)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)

    elif state == "player_manage_id_input":
        if not text.isdigit():
            await message.answer("ID должен быть числом.")
            return
        target_game_id = int(text)
        user = await db.fetchone("SELECT vk_id FROM users WHERE game_id = ?", target_game_id)
        if not user:
            await message.answer("Игрок не найден.")
            await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
            return
        keyboard = Keyboard(one_time=False, inline=True)
        keyboard.add(Text("Заморозить", payload={"cmd": "manage_freeze", "target_id": user["vk_id"]}), color=KeyboardButtonColor.PRIMARY)
        keyboard.add(Text("Точечная блокировка", payload={"cmd": "manage_target_block", "target_id": user["vk_id"]}), color=KeyboardButtonColor.PRIMARY)
        keyboard.add(Text("Полный бан", payload={"cmd": "manage_full_ban", "target_id": user["vk_id"]}), color=KeyboardButtonColor.NEGATIVE)
        keyboard.add(Text("Разблокировать", payload={"cmd": "manage_unblock", "target_id": user["vk_id"]}), color=KeyboardButtonColor.PRIMARY)
        keyboard.add(Text("Выдать деньги", payload={"cmd": "manage_give_money", "target_id": user["vk_id"]}), color=KeyboardButtonColor.PRIMARY)
        keyboard.add(Text("Изъять деньги", payload={"cmd": "manage_take_money", "target_id": user["vk_id"]}), color=KeyboardButtonColor.PRIMARY)
        keyboard.add(Text("Выдать предмет", payload={"cmd": "manage_give_item", "target_id": user["vk_id"]}), color=KeyboardButtonColor.PRIMARY)
        keyboard.add(Text("Изъять предмет", payload={"cmd": "manage_take_item", "target_id": user["vk_id"]}), color=KeyboardButtonColor.PRIMARY)
        keyboard.row()
        keyboard.add(Text("🔙 Назад", payload={"cmd": "founder_players"}), color=KeyboardButtonColor.SECONDARY)
        await message.answer("Выберите действие:", keyboard=keyboard)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)

    elif state == "manage_freeze_duration":
        if not text.isdigit():
            await message.answer("Длительность должна быть числом.")
            return
        days = int(text)
        success, msg = await block_player(message.from_id, target_id, "freeze", days)
        await message.answer(msg)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        await founder_players(message)

    elif state == "manage_target_duration":
        if not text.isdigit():
            await message.answer("Длительность должна быть числом.")
            return
        days = int(text)
        success, msg = await block_player(message.from_id, target_id, "target", days)
        await message.answer(msg)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        await founder_players(message)

    elif state == "manage_money_amount_give":
        if not text.isdigit():
            await message.answer("Сумма должна быть числом.")
            return
        amount = int(text)
        success, msg = await give_money(message.from_id, target_id, amount)
        await message.answer(msg)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        await founder_players(message)

    elif state == "manage_money_amount_take":
        if not text.isdigit():
            await message.answer("Сумма должна быть числом.")
            return
        amount = int(text)
        success, msg = await take_money(message.from_id, target_id, amount)
        await message.answer(msg)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        await founder_players(message)

    elif state == "manage_item_id_give":
        item_id = text
        await db.execute(
            "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'manage_item_qty_give', ?)",
            message.from_id, json.dumps({"target_id": target_id, "item_id": item_id})
        )
        await message.answer("Введите количество:")

    elif state == "manage_item_id_take":
        item_id = text
        await db.execute(
            "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'manage_item_qty_take', ?)",
            message.from_id, json.dumps({"target_id": target_id, "item_id": item_id})
        )
        await message.answer("Введите количество:")

    elif state == "manage_item_qty_give":
        if not text.isdigit():
            await message.answer("Количество должно быть числом.")
            return
        qty = int(text)
        item_id = data.get("item_id")
        success, msg = await give_item(message.from_id, target_id, item_id, qty)
        await message.answer(msg)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        await founder_players(message)

    elif state == "manage_item_qty_take":
        if not text.isdigit():
            await message.answer("Количество должно быть числом.")
            return
        qty = int(text)
        item_id = data.get("item_id")
        success, msg = await take_item(message.from_id, target_id, item_id, qty)
        await message.answer(msg)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        await founder_players(message)

    else:
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)