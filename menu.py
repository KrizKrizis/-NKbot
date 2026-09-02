# jobs/menu.py
# Меню категорий работ.

from vkbottle.bot import Blueprint, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text
from db.database import db

bp = Blueprint("jobs_menu")


async def get_user_level(user_id: int) -> int:
    row = await db.fetchone("SELECT level FROM users WHERE vk_id = ?", user_id)
    return row["level"] if row else 1


async def has_all_mars_items(user_id: int) -> bool:
    """Проверяет наличие всех предметов, необходимых для работы на Марсе."""
    required_items = {'4.8.1', '4.5.3', '4.3.10', '4.5.4'}
    rows = await db.fetchall(
        "SELECT item_id FROM inventory WHERE user_id = ? AND item_id IN (?, ?, ?, ?)",
        user_id, '4.8.1', '4.5.3', '4.3.10', '4.5.4'
    )
    owned = {row["item_id"] for row in rows}
    return required_items.issubset(owned)


async def show_categories(message: Message):
    """Показывает доступные категории работ в зависимости от уровня и предметов."""
    user_id = message.from_id
    level = await get_user_level(user_id)

    keyboard = Keyboard(one_time=False, inline=True)

    # Начальные доступны всегда
    keyboard.add(Text("🆕 Начальные", payload={"cmd": "jobs_category", "category": "novice"}), color=KeyboardButtonColor.PRIMARY)

    # Постоянные доступны с 3 уровня
    if level >= 3:
        keyboard.add(Text("🚖 Постоянные", payload={"cmd": "jobs_category", "category": "permanent"}), color=KeyboardButtonColor.PRIMARY)

    # Миллионер доступны с 10 уровня
    if level >= 10:
        keyboard.add(Text("💼 Миллионер", payload={"cmd": "jobs_category", "category": "millionaire"}), color=KeyboardButtonColor.PRIMARY)

    # Элитная доступна только при уровне 49+ и наличии всех предметов
    if level >= 49 and await has_all_mars_items(user_id):
        keyboard.add(Text("🚀 Элитные", payload={"cmd": "jobs_category", "category": "elite"}), color=KeyboardButtonColor.PRIMARY)

    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "back_to_main"}), color=KeyboardButtonColor.SECONDARY)

    await message.answer("Выберите категорию работ:", keyboard=keyboard)


@bp.on.message(payload={"cmd": "open_jobs"})
async def open_jobs(message: Message):
    await show_categories(message)


@bp.on.message(payload={"cmd": "jobs_category"})
async def jobs_category(message: Message):
    payload = message.get_payload_json()
    category = payload.get("category")

    if category == "novice":
        from jobs.novice.handlers.jobs import show_novice_jobs
        await show_novice_jobs(message)
    elif category == "permanent":
        from jobs.permanent.handlers.jobs import show_permanent_jobs
        await show_permanent_jobs(message)
    elif category == "millionaire":
        from jobs.millionaire.handlers.jobs import show_millionaire_jobs
        await show_millionaire_jobs(message)
    elif category == "elite":
        from jobs.elite.handlers.jobs import show_elite_jobs
        await show_elite_jobs(message)