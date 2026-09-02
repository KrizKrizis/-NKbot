# admin/project_leadership/handlers/team.py
# Обработчики управления командой для руководства.

import logging
from vkbottle.bot import Blueprint, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text
from db.database import db
from utils.permissions import get_admin_info
from admin.team_management import (
    get_team_list,
    format_team_list,
    assign_role,
    remove_role,
    promote_user,
    give_warning,
    award_admin_coins,
    get_team_statistics,
)

logger = logging.getLogger(__name__)

bp = Blueprint("founder_team")


@bp.on.message(payload={"cmd": "team_management"})
async def team_management(message: Message):
    team = await get_team_list()
    text = await format_team_list(team)
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("Назначить роль", payload={"cmd": "team_assign_role"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Снять роль", payload={"cmd": "team_remove_role"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Повысить/Понизить", payload={"cmd": "team_promote"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Выдать выговор", payload={"cmd": "team_warning"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "founder_team"}), color=KeyboardButtonColor.SECONDARY)
    await message.answer(text, keyboard=keyboard)


@bp.on.message(payload={"cmd": "team_assign_role"})
async def team_assign_role(message: Message):
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'team_assign_id_input', '{}')",
        message.from_id
    )
    await message.answer("Введите игровой ID игрока, которому хотите назначить роль:")


@bp.on.message(payload={"cmd": "team_remove_role"})
async def team_remove_role(message: Message):
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'team_remove_id_input', '{}')",
        message.from_id
    )
    await message.answer("Введите игровой ID игрока, у которого хотите снять роль:")


@bp.on.message(payload={"cmd": "team_promote"})
async def team_promote(message: Message):
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'team_promote_id_input', '{}')",
        message.from_id
    )
    await message.answer("Введите игровой ID игрока для повышения/понижения:")


@bp.on.message(payload={"cmd": "team_warning"})
async def team_warning(message: Message):
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'team_warning_id_input', '{}')",
        message.from_id
    )
    await message.answer("Введите игровой ID игрока для выдачи выговора:")


@bp.on.message(payload={"cmd": "team_rewards"})
async def team_rewards(message: Message):
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'team_reward_id_input', '{}')",
        message.from_id
    )
    await message.answer("Введите игровой ID игрока для начисления админ-койнов:")


@bp.on.message(payload={"cmd": "team_statistics"})
async def team_statistics(message: Message):
    stats = await get_team_statistics()
    await message.answer(stats)


@bp.on.message()
async def handle_team_text(message: Message):
    state_row = await db.fetchone("SELECT state, data FROM user_states WHERE user_id = ?", message.from_id)
    if not state_row:
        return
    state = state_row["state"]
    text = message.text.strip()

    if state.startswith("team_"):
        if not text.isdigit():
            await message.answer("ID должен быть числом.")
            return
        target_game_id = int(text)
        user = await db.fetchone("SELECT vk_id FROM users WHERE game_id = ?", target_game_id)
        if not user:
            await message.answer("Игрок не найден.")
            await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
            return
        target_vk_id = user["vk_id"]

        if state == "team_assign_id_input":
            # Показать список ролей для назначения
            keyboard = Keyboard(one_time=False, inline=True)
            roles = [
                ("Хелпер", 1, "1.1"),
                ("Администратор", 2, "2.1"),
                ("Старший администратор", 2, "2.2"),
                ("ЗГА", 2, "2.3"),
                ("ГА", 2, "2.4"),
                ("Куратор", 3, "3.1"),
                ("Тестировщик", 3, "3.2"),
                ("Зам. основателя", 3, "3.3"),
            ]
            for name, cat, pos in roles:
                keyboard.add(Text(name, payload={"cmd": "team_assign_confirm", "target_id": target_vk_id, "category": cat, "position": pos}), color=KeyboardButtonColor.PRIMARY)
            keyboard.row()
            keyboard.add(Text("🔙 Отмена", payload={"cmd": "team_management"}), color=KeyboardButtonColor.SECONDARY)
            await message.answer("Выберите роль для назначения:", keyboard=keyboard)
            await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)

        elif state == "team_remove_id_input":
            success, msg = await remove_role(message.from_id, target_vk_id)
            await message.answer(msg)
            await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
            await team_management(message)

        elif state == "team_promote_id_input":
            # Показать список ролей для повышения/понижения (аналогично назначению)
            # Для простоты используем тот же список
            keyboard = Keyboard(one_time=False, inline=True)
            roles = [
                ("Хелпер", 1, "1.1"),
                ("Администратор", 2, "2.1"),
                ("Старший администратор", 2, "2.2"),
                ("ЗГА", 2, "2.3"),
                ("ГА", 2, "2.4"),
                ("Куратор", 3, "3.1"),
                ("Тестировщик", 3, "3.2"),
                ("Зам. основателя", 3, "3.3"),
            ]
            for name, cat, pos in roles:
                keyboard.add(Text(name, payload={"cmd": "team_promote_confirm", "target_id": target_vk_id, "category": cat, "position": pos}), color=KeyboardButtonColor.PRIMARY)
            keyboard.row()
            keyboard.add(Text("🔙 Отмена", payload={"cmd": "team_management"}), color=KeyboardButtonColor.SECONDARY)
            await message.answer("Выберите новую роль:", keyboard=keyboard)
            await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)

        elif state == "team_warning_id_input":
            await db.execute(
                "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'team_warning_reason_input', ?)",
                message.from_id, json.dumps({"target_id": target_vk_id})
            )
            await message.answer("Введите причину выговора:")
            return

        elif state == "team_reward_id_input":
            await db.execute(
                "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'team_reward_amount_input', ?)",
                message.from_id, json.dumps({"target_id": target_vk_id})
            )
            await message.answer("Введите сумму админ-койнов:")
            return

    elif state == "team_warning_reason_input":
        target_id = json.loads(state_row["data"])["target_id"]
        reason = text
        success, msg = await give_warning(message.from_id, target_id, reason)
        await message.answer(msg)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        await team_management(message)

    elif state == "team_reward_amount_input":
        target_id = json.loads(state_row["data"])["target_id"]
        if not text.isdigit():
            await message.answer("Сумма должна быть числом.")
            return
        amount = int(text)
        success, msg = await award_admin_coins(message.from_id, target_id, amount)
        await message.answer(msg)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        await team_management(message)

    else:
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)


# Обработчики подтверждения назначения/повышения
@bp.on.message(payload={"cmd": "team_assign_confirm"})
async def team_assign_confirm(message: Message):
    payload = message.get_payload_json()
    target_id = int(payload["target_id"])
    category = int(payload["category"])
    position = payload["position"]
    success, msg = await assign_role(message.from_id, target_id, category, position)
    await message.answer(msg)
    await team_management(message)


@bp.on.message(payload={"cmd": "team_promote_confirm"})
async def team_promote_confirm(message: Message):
    payload = message.get_payload_json()
    target_id = int(payload["target_id"])
    category = int(payload["category"])
    position = payload["position"]
    success, msg = await promote_user(message.from_id, target_id, category, position)
    await message.answer(msg)
    await team_management(message)