# services/craft_service.py
# Логика крафта: рецепты, ингредиенты, запуск и завершение.

import random
from datetime import datetime, timezone, timedelta
from db.database import db


async def get_all_recipes() -> list:
    """Возвращает все рецепты крафта."""
    return await db.fetchall("SELECT * FROM craft_recipes")


async def get_recipe_by_id(recipe_id: str) -> dict:
    """Возвращает информацию о рецепте по его идентификатору."""
    return await db.fetchone("SELECT * FROM craft_recipes WHERE recipe_id = ?", recipe_id)


async def get_recipe_ingredients(recipe_id: str) -> list:
    """Возвращает список ингредиентов для рецепта."""
    return await db.fetchall(
        "SELECT item_id, quantity, is_tool FROM craft_ingredients WHERE recipe_id = ?",
        recipe_id
    )


async def has_enough_items(user_id: int, ingredients: list) -> bool:
    """Проверяет, достаточно ли у игрока предметов для крафта."""
    for ing in ingredients:
        item_id = ing["item_id"]
        required_qty = ing["quantity"]
        is_tool = ing["is_tool"]

        row = await db.fetchone(
            "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
            user_id, item_id
        )
        if not row:
            return False
        if not is_tool and row["quantity"] < required_qty:
            return False
        if is_tool and row["quantity"] < 1:
            return False
    return True


async def consume_ingredients(user_id: int, ingredients: list) -> None:
    """Списывает расходуемые ингредиенты из инвентаря игрока."""
    for ing in ingredients:
        if ing["is_tool"]:
            continue
        item_id = ing["item_id"]
        required_qty = ing["quantity"]
        await db.execute(
            "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?",
            required_qty, user_id, item_id
        )
        await db.execute(
            "DELETE FROM inventory WHERE user_id = ? AND item_id = ? AND quantity <= 0",
            user_id, item_id
        )


async def add_item_to_inventory(user_id: int, item_id: str, quantity: int = 1) -> None:
    """Добавляет предмет в инвентарь игрока."""
    existing = await db.fetchone(
        "SELECT id, quantity FROM inventory WHERE user_id = ? AND item_id = ?",
        user_id, item_id
    )
    if existing:
        await db.execute(
            "UPDATE inventory SET quantity = quantity + ? WHERE id = ?",
            quantity, existing["id"]
        )
    else:
        await db.execute(
            "INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, ?, ?)",
            user_id, item_id, quantity
        )


async def start_craft(user_id: int, recipe_id: str) -> tuple:
    """
    Запускает крафт для игрока.
    Проверяет отсутствие активного крафта, наличие ингредиентов, списывает их
    и создаёт запись в active_crafts.
    Возвращает (успех, сообщение).
    """
    active = await db.fetchone(
        "SELECT id FROM active_crafts WHERE user_id = ? AND status = 'active'",
        user_id
    )
    if active:
        return False, "У вас уже есть активный крафт."

    recipe = await get_recipe_by_id(recipe_id)
    if not recipe:
        return False, "Рецепт не найден."

    ingredients = await get_recipe_ingredients(recipe_id)
    if not await has_enough_items(user_id, ingredients):
        return False, "Недостаточно ингредиентов."

    await consume_ingredients(user_id, ingredients)

    now = datetime.now(timezone.utc)
    end_time = now + timedelta(minutes=recipe["duration_minutes"])
    await db.execute(
        "INSERT INTO active_crafts (user_id, recipe_id, start_time, end_time, status) VALUES (?, ?, ?, ?, 'active')",
        user_id, recipe_id, now.isoformat(), end_time.isoformat()
    )
    return True, "Крафт начат."


async def finish_craft(user_id: int) -> tuple:
    """
    Завершает активный крафт игрока.
    Проверяет шанс успеха и выдаёт предмет при успехе.
    Возвращает (успех, сообщение).
    """
    active = await db.fetchone(
        "SELECT id, recipe_id, end_time FROM active_crafts WHERE user_id = ? AND status = 'active'",
        user_id
    )
    if not active:
        return False, "Нет активного крафта."

    now = datetime.now(timezone.utc)
    end_time = datetime.fromisoformat(active["end_time"])
    if now < end_time:
        return False, "Крафт ещё не завершён."

    recipe = await get_recipe_by_id(active["recipe_id"])
    if not recipe:
        return False, "Рецепт не найден."

    success = random.random() < recipe["success_chance"]
    if success:
        await add_item_to_inventory(user_id, recipe["result_item_id"], recipe["result_quantity"])
        message = f"Крафт успешен! Получен предмет: {recipe['result_item_id']}."
    else:
        message = "Крафт провалился. Ингредиенты потеряны."

    await db.execute(
        "UPDATE active_crafts SET status = 'finished' WHERE id = ?",
        active["id"]
    )
    return True, message


async def cancel_craft(user_id: int) -> bool:
    """Отменяет активный крафт без выдачи результата (ингредиенты не возвращаются)."""
    active = await db.fetchone(
        "SELECT id FROM active_crafts WHERE user_id = ? AND status = 'active'",
        user_id
    )
    if not active:
        return False
    await db.execute(
        "UPDATE active_crafts SET status = 'cancelled' WHERE id = ?",
        active["id"]
    )
    return True


async def get_active_craft(user_id: int) -> dict:
    """Возвращает информацию об активном крафте игрока или None."""
    row = await db.fetchone(
        "SELECT * FROM active_crafts WHERE user_id = ? AND status = 'active'",
        user_id
    )
    return row