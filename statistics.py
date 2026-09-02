# admin/administration/handlers/statistics.py
# Статистика для администрации (ЗГА/ГА).

import logging
from vkbottle.bot import Blueprint, Message
from db.database import db
from utils.permissions import has_permission
from admin.team_management import get_team_statistics

logger = logging.getLogger(__name__)

bp = Blueprint("admin_statistics")


@bp.on.message(payload={"cmd": "admin_statistics"})
async def admin_statistics(message: Message):
    if not await has_permission(message.from_id, "team.manage"):
        await message.answer("Недостаточно прав.")
        return
    stats = await get_team_statistics()
    await message.answer(stats)