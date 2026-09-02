# admin/project_leadership/handlers/roles.py
# Обработчики назначения/снятия ролей (дублирует часть из team.py, но для ясности).

import logging
from vkbottle.bot import Blueprint, Message
from db.database import db
from admin.team_management import assign_role, remove_role

logger = logging.getLogger(__name__)

bp = Blueprint("founder_roles")


@bp.on.message(payload={"cmd": "roles_menu"})
async def roles_menu(message: Message):
    # Просто перенаправляем на team_management
    from admin.project_leadership.handlers.team import team_management
    await team_management(message)