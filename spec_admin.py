# admin/spec_administration/handlers/spec_admin.py
# Общее меню спец-администрации.

import logging
from vkbottle.bot import Blueprint, Message
from db.database import db
from utils.permissions import get_admin_info
from admin.spec_administration.keyboards.spec_admin_menu import get_spec_admin_main_keyboard

logger = logging.getLogger(__name__)

bp = Blueprint("spec_admin")


async def show_spec_admin_menu(message: Message):
    admin_info = await get_admin_info(message.from_id)
    if not admin_info or admin_info["category"] != 3:
        await message.answer("Недостаточно прав.")
        return
    keyboard = get_spec_admin_main_keyboard(message.from_id, admin_info["permissions"])
    await message.answer("🛠 Меню спец-администрации", keyboard=keyboard)


@bp.on.message(payload={"cmd": "admin_main_menu"})
async def admin_main_menu(message: Message):
    await show_spec_admin_menu(message)