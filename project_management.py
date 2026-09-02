# admin/project_management.py
# Управление проектом: цены, проценты, комиссии, налоги, лимиты, работы, аукционы, промокоды.

import json
import logging
from datetime import datetime, timezone, timedelta
from vkbottle import Keyboard, KeyboardButtonColor, Text
from db.database import db
from utils.permissions import has_permission, get_admin_info

logger = logging.getLogger(__name__)

# Типы параметров и их описания
PROJECT_SETTINGS = {
    "business_prices": "Цены бизнесов",
    "housing_prices": "Цены жилья",
    "vehicle_prices": "Цены транспорта",
    "bank_commission": "Комиссии банков",
    "work_salaries": "Зарплаты работ",
    "tax_rates": "Налоговые ставки",
    "limits": "Лимиты",
    "special_income_percents": "Проценты специальных доходов",
}


async def get_config_value(key: str, default=None):
    """Возвращает значение из таблицы config по ключу."""
    row = await db.fetchone("SELECT value FROM config WHERE key = ?", key)
    if row:
        return row["value"]
    return default


async def set_config_value(key: str, value: str) -> None:
    """Устанавливает значение в таблице config."""
    await db.execute(
        "INSERT OR REPLACE INTO config (key, value, description) VALUES (?, ?, ?)",
        key, str(value), key
    )


async def list_project_settings() -> str:
    """Возвращает список всех настроек проекта для отображения."""
    rows = await db.fetchall("SELECT key, value, description FROM config ORDER BY key")
    if not rows:
        return "Настройки не найдены."
    lines = ["⚙️ Настройки проекта:"]
    for r in rows:
        lines.append(f"  • {r['key']}: {r['value']} ({r['description']})")
    return "\n".join(lines)


async def get_project_settings_keyboard() -> str:
    """Возвращает клавиатуру со списком категорий настроек."""
    keyboard = Keyboard(one_time=False, inline=True)
    for key, desc in PROJECT_SETTINGS.items():
        keyboard.add(Text(desc, payload={"cmd": "project_setting_category", "category": key}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "admin_main_menu"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


async def get_setting_category_keyboard(category: str) -> str:
    """Возвращает клавиатуру с параметрами выбранной категории."""
    keyboard = Keyboard(one_time=False, inline=True)
    # Получаем список ключей, относящихся к категории
    rows = await db.fetchall("SELECT key, value, description FROM config WHERE key LIKE ?", f"{category}_%")
    if not rows:
        return keyboard.get_json()
    for r in rows:
        keyboard.add(Text(f"{r['key']}: {r['value']}", payload={"cmd": "project_setting_edit", "key": r["key"]}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "project_settings"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


async def edit_setting_value(admin_id: int, key: str, new_value: str) -> tuple:
    """Изменяет значение настройки. Проверяет права."""
    if not await has_permission(admin_id, "project.manage"):
        return False, "Недостаточно прав."

    # Валидация: попытка конвертировать в число
    try:
        float(new_value)
    except ValueError:
        return False, "Значение должно быть числом."

    await set_config_value(key, new_value)
    await db.execute(
        "INSERT INTO admin_log (admin_id, action, details) VALUES (?, 'edit_setting', ?)",
        admin_id, f"key={key}, value={new_value}"
    )
    return True, f"Параметр {key} изменён на {new_value}."


async def list_works() -> str:
    """Возвращает список работ с их зарплатами."""
    rows = await db.fetchall("SELECT job_id, name, base_reward_min, base_reward_max FROM jobs ORDER BY job_id")
    if not rows:
        return "Работы не найдены."
    lines = ["💼 Работы:"]
    for r in rows:
        lines.append(f"  • {r['name']}: {r['base_reward_min']}-{r['base_reward_max']} NK")
    return "\n".join(lines)


async def edit_work_salary(admin_id: int, job_id: str, new_min: int, new_max: int) -> tuple:
    """Изменяет зарплату работы."""
    if not await has_permission(admin_id, "project.manage"):
        return False, "Недостаточно прав."

    await db.execute(
        "UPDATE jobs SET base_reward_min = ?, base_reward_max = ? WHERE job_id = ?",
        new_min, new_max, job_id
    )
    await db.execute(
        "UPDATE work_settings SET reward_min = ?, reward_max = ? WHERE job_id = ?",
        new_min, new_max, job_id
    )
    await db.execute(
        "INSERT INTO admin_log (admin_id, action, details) VALUES (?, 'edit_work_salary', ?)",
        admin_id, f"job_id={job_id}, min={new_min}, max={new_max}"
    )
    return True, f"Зарплата работы {job_id} обновлена."


async def list_promocodes() -> list:
    """Возвращает список промокодов."""
    return await db.fetchall("SELECT * FROM promocodes ORDER BY code")


async def create_promocode(admin_id: int, code: str, reward_type: str, reward_id: str, reward_amount: int, uses_left: int, expires_at: str = None) -> tuple:
    """Создаёт промокод."""
    if not await has_permission(admin_id, "project.manage"):
        return False, "Недостаточно прав."

    exists = await db.fetchone("SELECT id FROM promocodes WHERE code = ?", code)
    if exists:
        return False, "Такой промокод уже существует."

    await db.execute(
        "INSERT INTO promocodes (code, reward_type, reward_id, reward_amount, uses_left, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
        code, reward_type, reward_id, reward_amount, uses_left, expires_at
    )
    await db.execute(
        "INSERT INTO admin_log (admin_id, action, details) VALUES (?, 'create_promocode', ?)",
        admin_id, f"code={code}"
    )
    return True, f"Промокод {code} создан."


async def delete_promocode(admin_id: int, code: str) -> tuple:
    """Удаляет промокод."""
    if not await has_permission(admin_id, "project.manage"):
        return False, "Недостаточно прав."
    await db.execute("DELETE FROM promocodes WHERE code = ?", code)
    await db.execute(
        "INSERT INTO admin_log (admin_id, action, details) VALUES (?, 'delete_promocode', ?)",
        admin_id, f"code={code}"
    )
    return True, f"Промокод {code} удалён."


async def list_auction_businesses() -> list:
    """Возвращает список аукционных бизнесов с текущим статусом."""
    return await db.fetchall("SELECT * FROM businesses WHERE type IN ('auction_standard','auction_casino') ORDER BY business_id")


async def format_auction_businesses(admin_id: int) -> str:
    """Форматирует список аукционных бизнесов для админ-просмотра."""
    rows = await list_auction_businesses()
    if not rows:
        return "Аукционные бизнесы не найдены."
    lines = ["🏛 Аукционные бизнесы:"]
    for b in rows:
        owner = ""
        if b["owner_id"]:
            user = await db.fetchone("SELECT first_name, last_name FROM users WHERE vk_id = ?", b["owner_id"])
            if user:
                owner = f"{user['first_name']} {user['last_name']}"
        status = f"Владелец: {owner}" if owner else "Свободен"
        lines.append(f"  • {b['name']} ({b['business_id']}): {status}")
    return "\n".join(lines)


async def force_assign_business(admin_id: int, business_id: str, target_user_id: int) -> tuple:
    """Принудительно выдаёт бизнес игроку."""
    if not await has_permission(admin_id, "project.manage"):
        return False, "Недостаточно прав."
    # Проверяем, что бизнес свободен
    biz = await db.fetchone("SELECT owner_id FROM businesses WHERE business_id = ?", business_id)
    if not biz:
        return False, "Бизнес не найден."
    if biz["owner_id"]:
        return False, "Бизнес уже имеет владельца."

    await db.execute("UPDATE businesses SET owner_id = ? WHERE business_id = ?", target_user_id, business_id)
    await db.execute(
        "INSERT INTO admin_log (admin_id, action, details) VALUES (?, 'force_assign_business', ?)",
        admin_id, f"business={business_id}, target={target_user_id}"
    )
    return True, f"Бизнес {business_id} выдан игроку {target_user_id}."


async def force_remove_business(admin_id: int, business_id: str) -> tuple:
    """Принудительно изъимает бизнес у владельца."""
    if not await has_permission(admin_id, "project.manage"):
        return False, "Недостаточно прав."
    biz = await db.fetchone("SELECT owner_id FROM businesses WHERE business_id = ?", business_id)
    if not biz or not biz["owner_id"]:
        return False, "У бизнеса нет владельца."
    await db.execute("UPDATE businesses SET owner_id = NULL, business_balance = 0 WHERE business_id = ?", business_id)
    await db.execute(
        "INSERT INTO admin_log (admin_id, action, details) VALUES (?, 'force_remove_business', ?)",
        admin_id, f"business={business_id}"
    )
    return True, f"Бизнес {business_id} изъят."