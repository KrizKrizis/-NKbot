# admin/project_leadership/handlers/project.py
# Обработчики управления проектом для руководства.

import logging
from vkbottle.bot import Blueprint, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text
from db.database import db
from utils.permissions import get_admin_info
from admin.project_management import (
    list_project_settings,
    get_project_settings_keyboard,
    get_setting_category_keyboard,
    edit_setting_value,
    list_works,
    format_auction_businesses,
    list_promocodes,
    create_promocode,
    delete_promocode,
)

logger = logging.getLogger(__name__)

bp = Blueprint("founder_project")


@bp.on.message(payload={"cmd": "project_settings"})
async def project_settings(message: Message):
    text = await list_project_settings()
    keyboard = await get_project_settings_keyboard()
    await message.answer(text, keyboard=keyboard)


@bp.on.message(payload={"cmd": "project_setting_category"})
async def project_setting_category(message: Message):
    payload = message.get_payload_json()
    category = payload.get("category")
    keyboard = await get_setting_category_keyboard(category)
    await message.answer(f"Настройки категории {category}:", keyboard=keyboard)


@bp.on.message(payload={"cmd": "project_setting_edit"})
async def project_setting_edit(message: Message):
    payload = message.get_payload_json()
    key = payload.get("key")
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'project_setting_value_input', ?)",
        message.from_id, json.dumps({"key": key})
    )
    await message.answer(f"Введите новое значение для {key}:")


@bp.on.message(payload={"cmd": "project_promocodes"})
async def project_promocodes(message: Message):
    promos = await list_promocodes()
    lines = ["🎁 Промокоды:"]
    for p in promos:
        lines.append(f"  • {p['code']} (осталось: {p['uses_left']})")
    text = "\n".join(lines) if promos else "Промокодов нет."
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("Создать промокод", payload={"cmd": "project_promocode_create"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Удалить промокод", payload={"cmd": "project_promocode_delete"}), color=KeyboardButtonColor.NEGATIVE)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "founder_project"}), color=KeyboardButtonColor.SECONDARY)
    await message.answer(text, keyboard=keyboard)


@bp.on.message(payload={"cmd": "project_statistics"})
async def project_statistics(message: Message):
    # Упрощённая статистика проекта
    users_count = await db.fetchone("SELECT COUNT(*) as cnt FROM users")
    businesses_count = await db.fetchone("SELECT COUNT(*) as cnt FROM businesses WHERE owner_id IS NOT NULL")
    text = f"📊 Статистика проекта:\nИгроков: {users_count['cnt']}\nБизнесов владеют: {businesses_count['cnt']}"
    await message.answer(text)


@bp.on.message()
async def handle_project_text(message: Message):
    state_row = await db.fetchone("SELECT state, data FROM user_states WHERE user_id = ?", message.from_id)
    if not state_row:
        return
    state = state_row["state"]
    text = message.text.strip()

    if state == "project_setting_value_input":
        key = json.loads(state_row["data"])["key"]
        success, msg = await edit_setting_value(message.from_id, key, text)
        await message.answer(msg)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        await project_settings(message)

    else:
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)


# Обработчики создания/удаления промокодов
@bp.on.message(payload={"cmd": "project_promocode_create"})
async def project_promocode_create(message: Message):
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'promocode_code_input', '{}')",
        message.from_id
    )
    await message.answer("Введите код промокода:")


@bp.on.message(payload={"cmd": "project_promocode_delete"})
async def project_promocode_delete(message: Message):
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'promocode_delete_input', '{}')",
        message.from_id
    )
    await message.answer("Введите код промокода для удаления:")


@bp.on.message()
async def handle_promocode_text(message: Message):
    state_row = await db.fetchone("SELECT state, data FROM user_states WHERE user_id = ?", message.from_id)
    if not state_row:
        return
    state = state_row["state"]
    text = message.text.strip()

    if state == "promocode_code_input":
        code = text
        await db.execute(
            "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'promocode_reward_type_input', ?)",
            message.from_id, json.dumps({"code": code})
        )
        await message.answer("Введите тип награды (money/item/business):")
    elif state == "promocode_reward_type_input":
        reward_type = text
        data = json.loads(state_row["data"])
        data["reward_type"] = reward_type
        await db.execute(
            "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'promocode_reward_id_input', ?)",
            message.from_id, json.dumps(data)
        )
        await message.answer("Введите ID награды (для предмета или бизнеса), для денег введите 0:")
    elif state == "promocode_reward_id_input":
        reward_id = text
        data = json.loads(state_row["data"])
        data["reward_id"] = reward_id
        await db.execute(
            "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'promocode_amount_input', ?)",
            message.from_id, json.dumps(data)
        )
        await message.answer("Введите сумму/количество награды:")
    elif state == "promocode_amount_input":
        if not text.isdigit():
            await message.answer("Сумма должна быть числом.")
            return
        reward_amount = int(text)
        data = json.loads(state_row["data"])
        data["reward_amount"] = reward_amount
        await db.execute(
            "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'promocode_uses_input', ?)",
            message.from_id, json.dumps(data)
        )
        await message.answer("Введите количество использований:")
    elif state == "promocode_uses_input":
        if not text.isdigit():
            await message.answer("Количество должно быть числом.")
            return
        uses_left = int(text)
        data = json.loads(state_row["data"])
        code = data["code"]
        reward_type = data["reward_type"]
        reward_id = data.get("reward_id", "")
        reward_amount = data["reward_amount"]
        success, msg = await create_promocode(message.from_id, code, reward_type, reward_id, reward_amount, uses_left)
        await message.answer(msg)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        await project_promocodes(message)
    elif state == "promocode_delete_input":
        code = text
        success, msg = await delete_promocode(message.from_id, code)
        await message.answer(msg)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        await project_promocodes(message)
    else:
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)