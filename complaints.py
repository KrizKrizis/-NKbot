# admin/administration/handlers/complaints.py
# Обработчики жалоб для администрации.

import json
import logging
from vkbottle.bot import Blueprint, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text
from db.database import db
from utils.permissions import has_permission
from admin.complaint_management import get_complaints, format_complaints, accept_complaint, reject_complaint
from admin.administration.keyboards.complaints_keyboards import get_complaints_list_keyboard, get_complaint_detail_keyboard

logger = logging.getLogger(__name__)

bp = Blueprint("admin_complaints")


@bp.on.message(payload={"cmd": "admin_complaints"})
async def admin_complaints(message: Message):
    if not await has_permission(message.from_id, "complaints.view"):
        await message.answer("Недостаточно прав.")
        return
    complaints = await get_complaints()
    text = await format_complaints(complaints)
    keyboard = get_complaints_list_keyboard(complaints)
    await message.answer(text, keyboard=keyboard)


@bp.on.message(payload={"cmd": "admin_complaint_detail"})
async def admin_complaint_detail(message: Message):
    payload = message.get_payload_json()
    complaint_id = int(payload["id"])
    if not await has_permission(message.from_id, "complaints.resolve"):
        await message.answer("Недостаточно прав.")
        return
    keyboard = get_complaint_detail_keyboard(complaint_id)
    await message.answer(f"Жалоба #{complaint_id}", keyboard=keyboard)


@bp.on.message(payload={"cmd": "admin_complaint_accept"})
async def admin_complaint_accept(message: Message):
    payload = message.get_payload_json()
    complaint_id = int(payload["id"])
    if not await has_permission(message.from_id, "complaints.resolve"):
        await message.answer("Недостаточно прав.")
        return
    success, msg = await accept_complaint(message.from_id, complaint_id)
    await message.answer(msg)
    await admin_complaints(message)


@bp.on.message(payload={"cmd": "admin_complaint_reject"})
async def admin_complaint_reject(message: Message):
    payload = message.get_payload_json()
    complaint_id = int(payload["id"])
    if not await has_permission(message.from_id, "complaints.resolve"):
        await message.answer("Недостаточно прав.")
        return
    success, msg = await reject_complaint(message.from_id, complaint_id)
    await message.answer(msg)
    await admin_complaints(message)