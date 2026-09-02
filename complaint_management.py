# admin/complaint_management.py
# Работа с жалобами: просмотр, принятие, отклонение, наказания.

import json
import logging
from datetime import datetime, timezone
from vkbottle import Keyboard, KeyboardButtonColor, Text
from db.database import db
from utils.permissions import has_permission

logger = logging.getLogger(__name__)


async def get_complaints(status: str = "active") -> list:
    """Возвращает список жалоб из admin_log с action='complaint'."""
    rows = await db.fetchall(
        "SELECT id, admin_id, details, timestamp FROM admin_log WHERE action='complaint' ORDER BY id DESC"
    )
    return rows


async def format_complaints(complaints: list) -> str:
    """Форматирует список жалоб."""
    if not complaints:
        return "Жалоб нет."
    lines = ["📋 Жалобы:"]
    for c in complaints:
        lines.append(f"  • #{c['id']} от {c['admin_id']}: {c['details']} ({c['timestamp']})")
    return "\n".join(lines)


async def get_complaint_keyboard(complaint_id: int) -> str:
    """Клавиатура для конкретной жалобы."""
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("✅ Принять", payload={"cmd": "complaint_accept", "id": complaint_id}), color=KeyboardButtonColor.POSITIVE)
    keyboard.add(Text("❌ Отклонить", payload={"cmd": "complaint_reject", "id": complaint_id}), color=KeyboardButtonColor.NEGATIVE)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "complaints_list"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


async def accept_complaint(admin_id: int, complaint_id: int) -> tuple:
    """Принимает жалобу."""
    if not await has_permission(admin_id, "complaints.resolve"):
        return False, "Недостаточно прав."
    await db.execute(
        "INSERT INTO admin_log (admin_id, action, details) VALUES (?, 'complaint_accept', ?)",
        admin_id, f"complaint_id={complaint_id}"
    )
    return True, "Жалоба принята. Теперь выберите наказание."


async def reject_complaint(admin_id: int, complaint_id: int) -> tuple:
    """Отклоняет жалобу."""
    if not await has_permission(admin_id, "complaints.resolve"):
        return False, "Недостаточно прав."
    await db.execute(
        "INSERT INTO admin_log (admin_id, action, details) VALUES (?, 'complaint_reject', ?)",
        admin_id, f"complaint_id={complaint_id}"
    )
    return True, "Жалоба отклонена."