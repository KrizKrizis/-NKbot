# admin/spec_administration/handlers/curator.py
# Обработчики куратора (категория 3, роль 3.1).

import json
import logging
from vkbottle.bot import Blueprint, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text
from db.database import db
from utils.permissions import has_permission, get_admin_info
from admin.player_management import (
    get_player_page, get_total_pages, get_player_profile, search_player, format_search_results,
)
from admin.team_management import get_team_list, format_team_list
from admin.administration.keyboards.players_keyboards import get_admin_players_keyboard
from admin.administration.keyboards.team_keyboards import get_team_management_keyboard

logger = logging.getLogger(__name__)

bp = Blueprint("curator")


async def _get_permissions(user_id: int) -> dict:
    info = await get_admin_info(user_id)
    return info["permissions"] if info else {}


@bp.on.message(payload={"cmd": "spec_players"})
async def spec_players(message: Message):
    permissions = await _get_permissions(message.from_id)
    if not permissions.get("players.view", False):
        await message.answer("Недостаточно прав.")
        return
    page = 1
    players = await get_player_page(page)
    total_pages = await get_total_pages()
    lines = [f"Страница {page}"]
    for p in players:
        status = "🔴" if p["is_blocked"] else "🟢"
        lines.append(f"{status} {p['game_id']} | {p['first_name']} {p['last_name']} | LVL {p['level']}")
    text = "\n".join(lines)
    keyboard = get_admin_players_keyboard(page, total_pages, permissions)
    await message.answer(text, keyboard=keyboard)


@bp.on.message(payload={"cmd": "spec_players_page"})
async def spec_players_page(message: Message):
    permissions = await _get_permissions(message.from_id)
    payload = message.get_payload_json()
    page = int(payload.get("page", 1))
    players = await get_player_page(page)
    total_pages = await get_total_pages()
    lines = [f"Страница {page}"]
    for p in players:
        status = "🔴" if p["is_blocked"] else "🟢"
        lines.append(f"{status} {p['game_id']} | {p['first_name']} {p['last_name']} | LVL {p['level']}")
    text = "\n".join(lines)
    keyboard = get_admin_players_keyboard(page, total_pages, permissions)
    await message.answer(text, keyboard=keyboard)


@bp.on.message(payload={"cmd": "spec_team"})
async def spec_team(message: Message):
    if not await has_permission(message.from_id, "team.view"):
        await message.answer("Недостаточно прав.")
        return
    team = await get_team_list()
    text = await format_team_list(team)
    permissions = await _get_permissions(message.from_id)
    keyboard = get_team_management_keyboard(permissions)
    await message.answer(text, keyboard=keyboard)


@bp.on.message(payload={"cmd": "spec_statistics"})
async def spec_statistics(message: Message):
    if not await has_permission(message.from_id, "team.manage"):
        await message.answer("Недостаточно прав.")
        return
    # Вызываем общую статистику
    from admin.team_management import get_team_statistics
    stats = await get_team_statistics()
    await message.answer(stats)


@bp.on.message(payload={"cmd": "spec_audit"})
async def spec_audit(message: Message):
    if not await has_permission(message.from_id, "team.manage"):
        await message.answer("Недостаточно прав.")
        return
    # Аудит - просто логи администраторов (кратко)
    logs = await db.fetchall("SELECT * FROM admin_log ORDER BY id DESC LIMIT 30")
    lines = ["📋 Аудит действий:"]
    for l in logs:
        lines.append(f"  • {l['admin_id']}: {l['action']} ({l['timestamp']})")
    await message.answer("\n".join(lines))