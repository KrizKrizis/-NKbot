# admin/team_management.py
# Управление командой: назначение/снятие ролей, повышение/понижение, выговоры, вознаграждения, статистика.

import json
import logging
from datetime import datetime, timezone, timedelta
from vkbottle import Keyboard, KeyboardButtonColor, Text
from db.database import db
from utils.permissions import has_permission, get_admin_info, get_admin_category, reload_admin_cache

logger = logging.getLogger(__name__)

ROLE_HIERARCHY = {
    "4.2": "Основатель проекта",
    "4.1": "Технический администратор",
    "3.3": "Заместитель основателя",
    "3.2": "Тестировщик",
    "3.1": "Куратор проекта",
    "2.4": "Главный администратор",
    "2.3": "Заместитель главного администратора",
    "2.2": "Старший администратор",
    "2.1": "Администратор",
    "1.1": "Хелпер",
}

# Кто кого может назначать/снимать (по категориям)
PROMOTE_RIGHTS = {
    4: [4, 3, 2, 1],     # Руководство может всех
    3: [3, 2, 1],        # Спец-администрация: до 2
    2: [2, 1],           # ГА и ЗГА: до 2 (кроме себя выше), но есть нюансы
}

async def get_team_list() -> list:
    """Возвращает список всех членов команды с их должностями."""
    rows = await db.fetchall(
        """
        SELECT ar.user_id, ar.category, ar.position, u.first_name, u.last_name, u.game_id
        FROM admin_roles ar
        JOIN users u ON ar.user_id = u.vk_id
        ORDER BY ar.category DESC, ar.position
        """
    )
    return rows


async def format_team_list(team: list) -> str:
    """Форматирует список команды."""
    if not team:
        return "Команда пуста."
    lines = ["👥 Команда проекта:"]
    current_category = None
    for member in team:
        if member["category"] != current_category:
            current_category = member["category"]
            lines.append(f"\nКатегория {current_category}:")
        lines.append(f"  • {ROLE_HIERARCHY.get(member['position'], member['position'])} — {member['first_name']} {member['last_name']} (ID: {member['game_id']})")
    return "\n".join(lines)


async def can_assign_role(admin_id: int, target_category: int, target_position: str) -> bool:
    """Проверяет, может ли администратор назначить данную роль."""
    admin_info = await get_admin_info(admin_id)
    if not admin_info:
        return False

    admin_cat = admin_info["category"]
    admin_pos = admin_info["position"]

    # Руководство может всё
    if admin_cat == 4:
        return True

    # Ограничения по категориям
    if admin_cat >= target_category:
        # ГА (2.4) может назначать только хелперов и надзирателей, но не ЗГА и не себя
        if admin_cat == 2 and admin_pos == "2.4":
            if target_category == 2 and target_position not in ("2.2", "2.3"):
                return False
            if target_category == 2 and target_position == "2.4":
                return False
        # ЗГА (2.3) может назначать хелперов и админов 2.1, но не выше
        elif admin_cat == 2 and admin_pos == "2.3":
            if target_category == 2 and target_position != "2.1":
                return False
        # Старший админ и ниже не назначают
        elif admin_cat == 2 and admin_pos in ("2.2", "2.1"):
            return False
        # Спец-администрация: куратор и зам.основателя могут, тестер нет
        if admin_cat == 3:
            if admin_pos == "3.2":
                return False
            if admin_pos == "3.1" and target_category > 2:
                return False
            if admin_pos == "3.3" and target_category > 3:
                return False
        return True
    return False


async def assign_role(admin_id: int, target_user_id: int, category: int, position: str) -> tuple:
    """Назначает роль игроку."""
    if not await can_assign_role(admin_id, category, position):
        return False, "Недостаточно прав для назначения этой роли."

    # Проверяем, существует ли уже роль
    existing = await db.fetchone("SELECT id FROM admin_roles WHERE user_id = ?", target_user_id)
    if existing:
        return False, "У игрока уже есть роль. Сначала снимите текущую."

    # Устанавливаем роль
    permissions = get_default_permissions(category, position)
    await db.execute(
        "INSERT INTO admin_roles (user_id, category, position, permissions, assigned_by) VALUES (?, ?, ?, ?, ?)",
        target_user_id, category, position, json.dumps(permissions), admin_id
    )
    await reload_admin_cache()
    await db.execute(
        "INSERT INTO admin_log (admin_id, action, details) VALUES (?, 'assign_role', ?)",
        admin_id, f"target={target_user_id}, category={category}, position={position}"
    )
    return True, f"Роль {position} выдана игроку {target_user_id}."


async def remove_role(admin_id: int, target_user_id: int) -> tuple:
    """Снимает роль у игрока."""
    target = await db.fetchone("SELECT category, position FROM admin_roles WHERE user_id = ?", target_user_id)
    if not target:
        return False, "У игрока нет роли."

    if not await can_assign_role(admin_id, target["category"], target["position"]):
        return False, "Недостаточно прав для снятия этой роли."

    await db.execute("DELETE FROM admin_roles WHERE user_id = ?", target_user_id)
    await reload_admin_cache()
    await db.execute(
        "INSERT INTO admin_log (admin_id, action, details) VALUES (?, 'remove_role', ?)",
        admin_id, f"target={target_user_id}, old_position={target['position']}"
    )
    return True, f"Роль снята у игрока {target_user_id}."


async def promote_user(admin_id: int, target_user_id: int, new_category: int, new_position: str) -> tuple:
    """Повышает или понижает игрока (снимает старую роль и выдаёт новую)."""
    if not await can_assign_role(admin_id, new_category, new_position):
        return False, "Недостаточно прав."

    await db.execute("DELETE FROM admin_roles WHERE user_id = ?", target_user_id)
    permissions = get_default_permissions(new_category, new_position)
    await db.execute(
        "INSERT INTO admin_roles (user_id, category, position, permissions, assigned_by) VALUES (?, ?, ?, ?, ?)",
        target_user_id, new_category, new_position, json.dumps(permissions), admin_id
    )
    await reload_admin_cache()
    await db.execute(
        "INSERT INTO admin_log (admin_id, action, details) VALUES (?, 'promote', ?)",
        admin_id, f"target={target_user_id}, new_category={new_category}, new_position={new_position}"
    )
    return True, f"Игрок {target_user_id} теперь {ROLE_HIERARCHY.get(new_position, new_position)}."


def get_default_permissions(category: int, position: str) -> dict:
    """Возвращает JSON-права для роли по умолчанию."""
    perms = {
        1: {
            "players.view": True,
            "players.view_extended": False,
            "players.freeze": False,
            "players.target_block": False,
            "players.full_ban": False,
            "players.unblock": False,
            "players.give_item": False,
            "players.take_item": False,
            "players.give_money": False,
            "players.take_money": False,
            "complaints.view": False,
            "complaints.resolve": False,
            "team.view": False,
            "team.manage": False,
            "project.manage": False,
            "system.manage": False,
        },
        2: {
            "players.view": True,
            "players.view_extended": True,
            "players.freeze": True,
            "players.target_block": True,
            "players.full_ban": True,
            "players.unblock": True,
            "players.give_item": False,
            "players.take_item": False,
            "players.give_money": False,
            "players.take_money": False,
            "complaints.view": True,
            "complaints.resolve": True,
            "team.view": True,
            "team.manage": False,
            "project.manage": False,
            "system.manage": False,
        },
        3: {
            "players.view": True,
            "players.view_extended": True,
            "players.freeze": True,
            "players.target_block": True,
            "players.full_ban": True,
            "players.unblock": True,
            "players.give_item": True,
            "players.take_item": True,
            "players.give_money": True,
            "players.take_money": True,
            "complaints.view": True,
            "complaints.resolve": True,
            "team.view": True,
            "team.manage": True,
            "project.manage": True,
            "system.manage": False,
        },
        4: {
            # У руководства права не нужны, т.к. has_permission возвращает True
        }
    }
    # Уточняем для отдельных позиций
    if category == 2:
        if position == "2.1":
            perms[2]["players.full_ban"] = False
            perms[2]["players.give_item"] = False
            perms[2]["players.take_item"] = False
            perms[2]["players.give_money"] = False
            perms[2]["players.take_money"] = False
        elif position == "2.2":
            perms[2]["players.full_ban"] = True
            perms[2]["players.give_money"] = False
            perms[2]["players.take_money"] = False
        elif position in ("2.3", "2.4"):
            perms[2]["players.give_money"] = True
            perms[2]["players.take_money"] = True
            perms[2]["team.manage"] = True
    elif category == 3:
        if position == "3.2":  # Тестировщик
            perms[3] = {
                "players.view": False,
                "players.view_extended": False,
                "players.freeze": False,
                "players.target_block": False,
                "players.full_ban": False,
                "players.unblock": False,
                "players.give_item": False,
                "players.take_item": False,
                "players.give_money": False,
                "players.take_money": False,
                "complaints.view": False,
                "complaints.resolve": False,
                "team.view": True,
                "team.manage": False,
                "project.manage": False,
                "system.manage": False,
                "test_panel": True,
            }
        elif position == "3.1":  # Куратор
            perms[3]["team.manage"] = True
            perms[3]["players.give_money"] = False
            perms[3]["players.take_money"] = False
        elif position == "3.3":  # Зам. основателя
            perms[3]["system.manage"] = False  # Не имеет доступа к системе
    return perms.get(category, {})


async def give_warning(admin_id: int, target_user_id: int, reason: str) -> tuple:
    """Выдаёт выговор члену команды."""
    if not await has_permission(admin_id, "team.manage"):
        return False, "Недостаточно прав."

    # Храним выговоры в admin_log
    await db.execute(
        "INSERT INTO admin_log (admin_id, action, details) VALUES (?, 'warning', ?)",
        admin_id, f"target={target_user_id}, reason={reason}"
    )
    return True, f"Выговор выдан игроку {target_user_id}: {reason}"


async def get_team_statistics() -> str:
    """Возвращает статистику по команде (кто сколько обращений/жалоб обработал)."""
    # Упрощённая версия: считаем из admin_log
    stats = await db.fetchall(
        """
        SELECT admin_id, COUNT(*) as actions
        FROM admin_log
        WHERE timestamp >= datetime('now', '-7 days')
        GROUP BY admin_id
        ORDER BY actions DESC
        """
    )
    if not stats:
        return "За последнюю неделю действий не было."
    lines = ["📊 Статистика команды за неделю:"]
    for s in stats:
        user = await db.fetchone("SELECT first_name, last_name FROM users WHERE vk_id = ?", s["admin_id"])
        name = f"{user['first_name']} {user['last_name']}".strip() if user else str(s["admin_id"])
        lines.append(f"  • {name}: {s['actions']} действий")
    return "\n".join(lines)


async def award_admin_coins(admin_id: int, target_user_id: int, amount: int) -> tuple:
    """Начисляет админ-койны (вознаграждение)."""
    if not await has_permission(admin_id, "team.manage"):
        return False, "Недостаточно прав."

    # Поле admin_coins не было создано; для простоты логируем в admin_log
    await db.execute(
        "INSERT INTO admin_log (admin_id, action, details) VALUES (?, 'award', ?)",
        admin_id, f"target={target_user_id}, amount={amount}"
    )
    return True, f"Начислено {amount} админ-койнов игроку {target_user_id}."