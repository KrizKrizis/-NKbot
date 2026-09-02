# admin/administration/handlers/administration.py
# Главное меню администрации, вход и выход.

import logging
from vkbottle.bot import Blueprint, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text
from db.database import db
from utils.permissions import get_admin_info
from admin.administration.keyboards.administration_menu import get_administration_main_keyboard

logger = logging.getLogger(__name__)

bp = Blueprint("administration")


async def show_administration_menu(message: Message):
    """Показывает главное меню администрации."""
    admin_info = await get_admin_info(message.from_id)
    if not admin_info or admin_info["category"] != 2:
        await message.answer("Недостаточно прав.")
        return
    keyboard = get_administration_main_keyboard(message.from_id, admin_info["permissions"])
    await message.answer("🛡 Меню администрации", keyboard=keyboard)


@bp.on.message(payload={"cmd": "admin_main_menu"})
async def admin_main_menu(message: Message):
    await show_administration_menu(message)