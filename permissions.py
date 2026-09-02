# utils/permissions.py
# Проверка прав администраторов, категорий и ролей.

import json
from typing import Optional, Dict
from config import FOUNDER_ID, TECH_ADMIN_ID, CHAT_HELPERS, CHAT_ADMINS, CHAT_GA_STATS, CHAT_TEAM_GENERAL, CHAT_TESTERS, CHAT_FULL_LOG
from db.database import db

# Кэш для быстрой проверки
_admin_cache: Dict[int, Optional[Dict]] = {}


async def get_admin_info(user_id: int) -> Optional[Dict]:
    """
    Возвращает информацию о категории и должности администратора.
    Сначала проверяет руководство из .env, затем таблицу admin_roles.
    Кэширует результат.
    """
    if user_id in _admin_cache:
        return _admin_cache[user_id]

    # Руководство (категория 4)
    if user_id == FOUNDER_ID:
        info = {"category": 4, "position": "Основатель проекта"}
        _admin_cache[user_id] = info
        return info
    if user_id == TECH_ADMIN_ID:
        info = {"category": 4, "position": "Технический администратор"}
        _admin_cache[user_id] = info
        return info

    # Проверяем базу
    row = await db.fetchone(
        "SELECT category, position, permissions FROM admin_roles WHERE user_id = ?",
        user_id
    )
    if row:
        permissions = json.loads(row["permissions"]) if row["permissions"] else {}
        info = {
            "category": row["category"],
            "position": row["position"],
            "permissions": permissions
        }
        _admin_cache[user_id] = info
        return info

    _admin_cache[user_id] = None
    return None


async def reload_admin_cache() -> None:
    """Очищает кеш прав."""
    _admin_cache.clear()


async def has_permission(user_id: int, action: str) -> bool:
    """
    Проверяет, есть ли у пользователя право на определённое действие.
    action: строка вида "players.view", "players.edit", "complaints.resolve" и т.д.
    Права хранятся в JSON-поле permissions у роли.
    """
    info = await get_admin_info(user_id)
    if not info:
        return False

    # Руководство имеет все права
    if info["category"] == 4:
        return True

    # Проверяем явные права в permissions
    permissions = info.get("permissions", {})
    # Разбиваем действие на части
    parts = action.split(".")
    node = permissions
    for part in parts:
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return False
    return bool(node)


async def get_admin_category(user_id: int) -> int:
    """Возвращает категорию администратора или 0."""
    info = await get_admin_info(user_id)
    return info["category"] if info else 0


def get_chat_id(mode: int) -> Optional[int]:
    """Возвращает ID чата для заданного режима из config."""
    mapping = {
        2: CHAT_HELPERS,
        3: CHAT_ADMINS,
        4: CHAT_GA_STATS,
        5: CHAT_TEAM_GENERAL,
        6: CHAT_TESTERS,
        7: CHAT_FULL_LOG
    }
    return mapping.get(mode, 0)