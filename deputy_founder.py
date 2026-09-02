# admin/spec_administration/handlers/deputy_founder.py
# Обработчики заместителя основателя (категория 3, роль 3.3).

import json
import logging
from vkbottle.bot import Blueprint, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text
from db.database import db
from utils.permissions import has_permission, get_admin_info
from admin.player_management import (
    get_player_page, get_total_pages, get_player_profile, search_player, format_search_results,
    block_player, unblock_player, give_item, take_item, give_money, take_money,
)
from admin.administration.keyboards.players_keyboards import get_admin_players_keyboard, get_admin_player_manage_keyboard
from admin.administration.keyboards.team_keyboards import get_team_management_keyboard
from admin.team_management import get_team_list, format_team_list, assign_role, remove_role, promote_user
from admin.project_management import list_project_settings, get_project_settings_keyboard

logger = logging.getLogger(__name__)

bp = Blueprint("deputy")


async def _get_permissions(user_id: int) -> dict:
    info = await get_admin_info(user_id)
    return info["permissions"] if info else {}


# Игроки (то же, что у администрации, но с полными правами)
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


# Команда
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


# Проект
@bp.on.message(payload={"cmd": "spec_project"})
async def spec_project(message: Message):
    if not await has_permission(message.from_id, "project.manage"):
        await message.answer("Недостаточно прав.")
        return
    text = await list_project_settings()
    keyboard = await get_project_settings_keyboard()
    await message.answer(text, keyboard=keyboard)


@bp.on.message(payload={"cmd": "spec_project_stats"})
async def spec_project_stats(message: Message):
    users_count = await db.fetchone("SELECT COUNT(*) as cnt FROM users")
    businesses_count = await db.fetchone("SELECT COUNT(*) as cnt FROM businesses WHERE owner_id IS NOT NULL")
    text = f"📊 Статистика проекта:\nИгроков: {users_count['cnt']}\nБизнесов владеют: {businesses_count['cnt']}"
    await message.answer(text)