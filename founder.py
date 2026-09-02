# admin/project_leadership/handlers/founder.py
# Главное меню руководства проекта (категория 4).
# Вход по паролю, навигация по всем разделам.

import json
import logging
from vkbottle.bot import Blueprint, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text
from db.database import db
from utils.permissions import get_admin_info
from admin.player_management import format_player_list_page
from admin.team_management import get_team_list, format_team_list
from admin.project_management import list_project_settings, list_works, format_auction_businesses
from admin.system_management import get_recent_logs
from admin.project_leadership.keyboards.leadership_menu import (
    get_founder_main_keyboard,
    get_players_menu_keyboard,
    get_project_menu_keyboard,
    get_team_menu_keyboard,
    get_business_accounts_keyboard,
)

logger = logging.getLogger(__name__)

bp = Blueprint("founder")

FOUNDER_PASSWORD = "5651234565"


async def show_founder_menu(message: Message):
    """Показывает главное меню основателя."""
    keyboard = get_founder_main_keyboard()
    await message.answer("👑 Меню основателя", keyboard=keyboard)


# Обработчики входа с проверкой пароля
@bp.on.message(text="/logosnovpan")
async def founder_login(message: Message):
    # Проверяем, что пользователь является руководством
    admin_info = await get_admin_info(message.from_id)
    if not admin_info or admin_info["category"] != 4:
        await message.answer("Недостаточно прав.")
        return
    # Устанавливаем состояние ожидания пароля
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'founder_password', '{}')",
        message.from_id
    )
    await message.answer("Введите пароль:")


@bp.on.message()
async def handle_password(message: Message):
    state_row = await db.fetchone("SELECT state FROM user_states WHERE user_id = ?", message.from_id)
    if not state_row or state_row["state"] != "founder_password":
        return
    password = message.text.strip()
    if password == FOUNDER_PASSWORD:
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        await show_founder_menu(message)
    else:
        await message.answer("Неверный пароль. Попробуйте ещё раз или отмените.")


# Основные разделы
@bp.on.message(payload={"cmd": "founder_players"})
async def founder_players(message: Message):
    text, keyboard = await format_player_list_page(1)
    await message.answer(text, keyboard=keyboard)


@bp.on.message(payload={"cmd": "founder_project"})
async def founder_project(message: Message):
    await message.answer("⚙️ Проект", keyboard=get_project_menu_keyboard())


@bp.on.message(payload={"cmd": "founder_team"})
async def founder_team(message: Message):
    team = await get_team_list()
    text = await format_team_list(team)
    await message.answer(text, keyboard=get_team_menu_keyboard())


@bp.on.message(payload={"cmd": "founder_business_accounts"})
async def founder_business_accounts(message: Message):
    # Бизнес основателя: шесть счетов
    accounts = await db.fetchall("SELECT * FROM system_accounts ORDER BY id")
    lines = ["💼 Бизнес основателя"]
    for acc in accounts:
        lines.append(f"  {acc['account_name']}: {acc['balance']} NK")
    text = "\n".join(lines)
    await message.answer(text, keyboard=get_business_accounts_keyboard())


@bp.on.message(payload={"cmd": "founder_main"})
async def founder_main(message: Message):
    await show_founder_menu(message)


@bp.on.message(payload={"cmd": "admin_main_menu"})
async def admin_main_menu(message: Message):
    # Возврат в главное меню руководства
    admin_info = await get_admin_info(message.from_id)
    if admin_info and admin_info["category"] == 4:
        await show_founder_menu(message)
    else:
        # Для других категорий будет свой обработчик, но здесь просто ответ
        await message.answer("Главное меню")