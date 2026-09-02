# admin/base.py
# Вход в админ-панель, маршрутизация по категориям.

import logging
from vkbottle.bot import Blueprint, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text
from db.database import db
from utils.permissions import get_admin_info, reload_admin_cache
from admin.project_leadership.handlers.founder import show_founder_menu
from admin.spec_administration.handlers.spec_admin import show_spec_admin_menu
from admin.administration.handlers.administration import show_administration_menu
from admin.helpers.handlers.helpers import show_helpers_menu

logger = logging.getLogger(__name__)

bp = Blueprint("admin_base")


async def _is_user_in_db(user_id: int) -> bool:
    row = await db.fetchone("SELECT vk_id FROM users WHERE vk_id = ?", user_id)
    return row is not None


async def show_admin_panel(message: Message):
    """Показывает админ-панель в зависимости от категории пользователя."""
    user_id = message.from_id

    if not await _is_user_in_db(user_id):
        await message.answer("Вы не зарегистрированы.")
        return

    admin_info = await get_admin_info(user_id)
    if not admin_info:
        await message.answer("У вас нет админ-роли.")
        return

    category = admin_info["category"]

    if category == 4:
        await show_founder_menu(message)
    elif category == 3:
        await show_spec_admin_menu(message)
    elif category == 2:
        await show_administration_menu(message)
    elif category == 1:
        await show_helpers_menu(message)
    else:
        await message.answer("Недостаточно прав.")


@bp.on.message(text=["/loghelper", "/logadmin", "/logspecadmin", "/logosnovpan"])
async def admin_login(message: Message):
    user_id = message.from_id

    if not await _is_user_in_db(user_id):
        await message.answer("Вы не зарегистрированы. Напишите /start.")
        return

    command = message.text
    admin_info = await get_admin_info(user_id)

    if command == "/logosnovpan":
        if admin_info and admin_info["category"] == 4:
            # Пароль будет запрошен в founder.py
            await show_founder_menu(message)
        else:
            await message.answer("Недостаточно прав.")
        return

    if not admin_info:
        await message.answer("У вас нет админ-роли.")
        return

    category = admin_info["category"]

    if command == "/loghelper" and category == 1:
        await show_helpers_menu(message)
    elif command == "/logadmin" and category == 2:
        await show_administration_menu(message)
    elif command == "/logspecadmin" and category == 3:
        await show_spec_admin_menu(message)
    else:
        await message.answer("Команда не соответствует вашей категории.")


@bp.on.message(payload={"cmd": "admin_logout"})
async def admin_logout(message: Message):
    await message.answer("Вы вышли из админ-панели.")


@bp.on.message(payload={"cmd": "admin_reload_cache"})
async def admin_reload_cache(message: Message):
    admin_info = await get_admin_info(message.from_id)
    if admin_info and admin_info["category"] == 4:
        await reload_admin_cache()
        await message.answer("Кеш прав сброшен.")
    else:
        await message.answer("Недостаточно прав.")