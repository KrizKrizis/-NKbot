# admin/test_panel_management.py
# Тест-панель для тестировщика: виртуальная среда, не влияющая на реальных игроков.

import json
import logging
from datetime import datetime, timezone, timedelta
from vkbottle import Keyboard, KeyboardButtonColor, Text
from db.database import db
from utils.permissions import has_permission

logger = logging.getLogger(__name__)


async def get_test_menu_keyboard(admin_id: int) -> str:
    """Клавиатура тест-панели."""
    if not await has_permission(admin_id, "test_panel"):
        return None
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("⚒ Тестовый крафт", payload={"cmd": "test_craft"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("💰 Тестовый баланс", payload={"cmd": "test_balance"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("📈 Тестовый уровень", payload={"cmd": "test_level"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("🚀 Тест работы", payload={"cmd": "test_work"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("🏠 Тест недвижимости", payload={"cmd": "test_housing"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("🚗 Тест транспорта", payload={"cmd": "test_transport"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("📋 Логи ошибок", payload={"cmd": "test_logs"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("🔄 Сбросить тестовые данные", payload={"cmd": "test_reset"}), color=KeyboardButtonColor.NEGATIVE)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "admin_main_menu"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


async def give_test_balance(admin_id: int, amount: int) -> tuple:
    """Выдаёт виртуальный баланс тестировщику (не влияет на реальный)."""
    if not await has_permission(admin_id, "test_panel"):
        return False, "Недостаточно прав."
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'test_balance', ?)",
        admin_id, json.dumps({"balance": amount})
    )
    return True, f"Виртуальный баланс установлен: {amount}."


async def give_test_level(admin_id: int, level: int, exp: int = 0) -> tuple:
    """Устанавливает виртуальный уровень и опыт."""
    if not await has_permission(admin_id, "test_panel"):
        return False, "Недостаточно прав."
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'test_level', ?)",
        admin_id, json.dumps({"level": level, "exp": exp})
    )
    return True, f"Виртуальный уровень: {level}, опыт: {exp}."


async def give_test_item(admin_id: int, item_id: str, quantity: int = 1) -> tuple:
    """Выдаёт виртуальный предмет тестировщику."""
    if not await has_permission(admin_id, "test_panel"):
        return False, "Недостаточно прав."
    row = await db.fetchone("SELECT data FROM user_states WHERE user_id = ? AND state = 'test_inventory'", admin_id)
    inventory = json.loads(row["data"]) if row else {}
    inventory[item_id] = inventory.get(item_id, 0) + quantity
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'test_inventory', ?)",
        admin_id, json.dumps(inventory)
    )
    return True, f"Виртуально выдано {quantity} шт. {item_id}."


async def reset_test_data(admin_id: int) -> tuple:
    """Сбрасывает виртуальные данные тестировщика."""
    if not await has_permission(admin_id, "test_panel"):
        return False, "Недостаточно прав."
    await db.execute("DELETE FROM user_states WHERE user_id = ? AND state LIKE 'test_%'", admin_id)
    return True, "Виртуальные данные сброшены."


async def get_test_logs(admin_id: int) -> str:
    """Возвращает логи ошибок (из admin_log с action='error')."""
    if not await has_permission(admin_id, "test_panel"):
        return "Недостаточно прав."
    rows = await db.fetchall(
        "SELECT admin_id, action, details, timestamp FROM admin_log WHERE action='error' ORDER BY id DESC LIMIT 50"
    )
    if not rows:
        return "Ошибок нет."
    lines = ["📋 Логи ошибок:"]
    for r in rows:
        lines.append(f"  • {r['admin_id']}: {r['details']} ({r['timestamp']})")
    return "\n".join(lines)