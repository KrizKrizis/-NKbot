# craft/handlers/craft.py
# Обработчики крафта.

import logging
from datetime import datetime, timezone
from vkbottle.bot import Blueprint, Message
from db.database import db
from services.craft_service import (
    get_all_recipes,
    get_recipe_by_id,
    get_recipe_ingredients,
    start_craft,
    finish_craft,
    cancel_craft,
    get_active_craft,
)
from craft.keyboards.craft import (
    get_craft_recipes_keyboard,
    get_recipe_info_keyboard,
    get_active_craft_keyboard,
)

logger = logging.getLogger(__name__)

bp = Blueprint("craft")


async def show_craft_menu(message: Message):
    """Показывает список рецептов или активный крафт."""
    user_id = message.from_id

    # Если есть активный крафт, показываем его
    active = await get_active_craft(user_id)
    if active:
        await show_active_craft(message)
        return

    recipes = await get_all_recipes()
    if not recipes:
        await message.answer("Нет доступных рецептов.")
        return

    await message.answer("Рецепты крафта:", keyboard=get_craft_recipes_keyboard(recipes))


@bp.on.message(payload={"cmd": "open_craft"})
async def open_craft(message: Message):
    await show_craft_menu(message)


@bp.on.message(payload={"cmd": "craft_recipes"})
async def craft_recipes(message: Message):
    await show_craft_menu(message)


@bp.on.message(payload={"cmd": "craft_recipe_info"})
async def craft_recipe_info(message: Message):
    payload = message.get_payload_json()
    recipe_id = payload.get("recipe_id")
    recipe = await get_recipe_by_id(recipe_id)
    if not recipe:
        return

    ingredients = await get_recipe_ingredients(recipe_id)
    ing_lines = []
    for ing in ingredients:
        item = await db.fetchone("SELECT name FROM items WHERE item_id = ?", ing["item_id"])
        name = item["name"] if item else ing["item_id"]
        if ing["is_tool"]:
            ing_lines.append(f"• {name} (инструмент, не расходуется)")
        else:
            ing_lines.append(f"• {name} x{ing['quantity']}")

    text = f"{recipe['name']}\nДлительность: {recipe['duration_minutes']} мин\nШанс успеха: {int(recipe['success_chance']*100)}%\n\nИнгредиенты:\n" + "\n".join(ing_lines)
    await message.answer(text, keyboard=get_recipe_info_keyboard(recipe_id))


@bp.on.message(payload={"cmd": "start_craft"})
async def start_craft_handler(message: Message):
    payload = message.get_payload_json()
    recipe_id = payload.get("recipe_id")

    success, msg = await start_craft(message.from_id, recipe_id)
    if not success:
        await message.answer(msg)
        await show_craft_menu(message)
        return

    await show_active_craft(message)


async def show_active_craft(message: Message):
    """Показывает экран с активным крафтом и таймером."""
    active = await get_active_craft(message.from_id)
    if not active:
        await show_craft_menu(message)
        return

    now = datetime.now(timezone.utc)
    end_time = datetime.fromisoformat(active["end_time"])
    remaining = end_time - now
    if remaining.total_seconds() < 0:
        success, msg = await finish_craft(message.from_id)
        await message.answer(msg)
        await show_craft_menu(message)
        return

    recipe = await get_recipe_by_id(active["recipe_id"])
    total_seconds = int(remaining.total_seconds())
    minutes, seconds = divmod(total_seconds, 60)
    time_left = f"{minutes:02d}:{seconds:02d}"

    text = f"Крафт: {recipe['name']}\nОсталось: {time_left}"
    await message.answer(text, keyboard=get_active_craft_keyboard())


@bp.on.message(payload={"cmd": "refresh_craft"})
async def refresh_craft(message: Message):
    await show_active_craft(message)


@bp.on.message(payload={"cmd": "cancel_craft"})
async def cancel_craft_handler(message: Message):
    await cancel_craft(message.from_id)
    await message.answer("Крафт отменён.")
    await show_craft_menu(message)


@bp.on.message(payload={"cmd": "back_to_more_menu"})
async def back_to_more_menu(message: Message):
    from city.handlers.cities import show_more_menu
    await show_more_menu(message)