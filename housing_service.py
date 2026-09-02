# services/housing_service.py
# Логика жилья: покупка, продажа, криптоферма, садоводство, топор.

import random
import json
from datetime import datetime, timezone, timedelta
from db.database import db


async def get_config_value(key: str, default=None):
    """Возвращает значение из конфигурации по ключу."""
    row = await db.fetchone("SELECT value FROM config WHERE key = ?", key)
    if row:
        return row["value"]
    return default


async def get_available_housing() -> list:
    """Возвращает список всех объектов жилья."""
    return await db.fetchall("SELECT * FROM housing")


async def get_user_housing(user_id: int) -> dict:
    """Возвращает информацию о жилье пользователя."""
    row = await db.fetchone(
        """
        SELECT ph.*, h.name, h.type, h.price, h.parking_spots
        FROM player_housing ph
        JOIN housing h ON ph.housing_id = h.housing_id
        WHERE ph.user_id = ?
        """,
        user_id
    )
    return row


async def buy_housing(user_id: int, housing_id: str) -> tuple:
    """Покупка жилья."""
    existing = await get_user_housing(user_id)
    if existing:
        return False, "У вас уже есть жильё."

    housing = await db.fetchone("SELECT * FROM housing WHERE housing_id = ?", housing_id)
    if not housing:
        return False, "Жильё не найдено."

    user = await db.fetchone("SELECT balance FROM users WHERE vk_id = ?", user_id)
    if user["balance"] < housing["price"]:
        return False, "Недостаточно наличных."

    await db.execute(
        "UPDATE users SET balance = balance - ? WHERE vk_id = ?",
        housing["price"], user_id
    )
    await db.execute(
        "INSERT INTO player_housing (user_id, housing_id, has_crypto_farm) VALUES (?, ?, 0)",
        user_id, housing_id
    )
    return True, f"Вы купили {housing['name']}."


async def sell_housing(user_id: int) -> tuple:
    """Продажа жилья государству за 60%."""
    housing = await get_user_housing(user_id)
    if not housing:
        return False, "У вас нет жилья."

    sell_price = int(housing["price"] * 0.6)
    await db.execute(
        "UPDATE users SET balance = balance + ? WHERE vk_id = ?",
        sell_price, user_id
    )
    await db.execute("DELETE FROM player_housing WHERE user_id = ?", user_id)
    await db.execute("DELETE FROM garden_plots WHERE user_id = ?", user_id)
    await db.execute("DELETE FROM garden_plants WHERE user_id = ?", user_id)
    await db.execute("DELETE FROM crypto_farm WHERE user_id = ?", user_id)
    return True, f"Жильё продано за {sell_price} NK."


async def buy_crypto_farm(user_id: int) -> tuple:
    """Покупка стойки криптофермы."""
    housing = await get_user_housing(user_id)
    if not housing:
        return False, "Сначала купите жильё."
    if housing["has_crypto_farm"]:
        return False, "Криптоферма уже установлена."

    cost = int(await get_config_value("crypto_farm_base_cost", 150000))
    user = await db.fetchone("SELECT balance FROM users WHERE vk_id = ?", user_id)
    if user["balance"] < cost:
        return False, "Недостаточно наличных."

    await db.execute(
        "UPDATE users SET balance = balance - ? WHERE vk_id = ?",
        cost, user_id
    )
    await db.execute(
        "UPDATE player_housing SET has_crypto_farm = 1, crypto_farm_installed_at = ? WHERE user_id = ?",
        datetime.now(timezone.utc).isoformat(), user_id
    )
    return True, "Криптоферма установлена."


async def sell_crypto_farm(user_id: int) -> tuple:
    """Продажа криптофермы за фиксированную цену."""
    housing = await get_user_housing(user_id)
    if not housing or not housing["has_crypto_farm"]:
        return False, "Криптоферма не установлена."

    sell_price = int(await get_config_value("crypto_farm_sell_price", 50000))
    await db.execute(
        "UPDATE users SET balance = balance + ? WHERE vk_id = ?",
        sell_price, user_id
    )
    await db.execute("UPDATE player_housing SET has_crypto_farm = 0, crypto_farm_installed_at = NULL WHERE user_id = ?", user_id)
    await db.execute("DELETE FROM crypto_farm WHERE user_id = ?", user_id)
    return True, f"Криптоферма продана за {sell_price} NK."


async def get_videocard_slots(user_id: int) -> int:
    """Возвращает максимальное количество видеокарт для жилья игрока."""
    housing = await get_user_housing(user_id)
    if not housing:
        return 0
    slots_map = {
        "2.1.1": 5,
        "2.1.2": 10,
        "2.1.3": 20,
        "2.1.4": 10,
        "2.2.1": 50,
        "2.2.2": 100,
    }
    return slots_map.get(housing["housing_id"], 0)


async def install_videocard(user_id: int, item_id: str) -> tuple:
    """Установка видеокарты в криптоферму."""
    housing = await get_user_housing(user_id)
    if not housing or not housing["has_crypto_farm"]:
        return False, "Криптоферма не установлена."

    inv = await db.fetchone("SELECT id FROM inventory WHERE user_id = ? AND item_id = ? AND quantity > 0", user_id, item_id)
    if not inv:
        return False, "Видеокарта отсутствует в инвентаре."

    slots = await get_videocard_slots(user_id)
    current_count = await db.fetchone("SELECT COUNT(*) as cnt FROM crypto_farm WHERE user_id = ?", user_id)
    if current_count["cnt"] >= slots:
        return False, "Нет свободных слотов для видеокарты."

    await db.execute("UPDATE inventory SET quantity = quantity - 1 WHERE id = ?", inv["id"])
    await db.execute("DELETE FROM inventory WHERE id = ? AND quantity <= 0", inv["id"])

    await db.execute(
        "INSERT INTO crypto_farm (user_id, videocard_id, installed_at, income_accumulated) VALUES (?, ?, ?, 0)",
        user_id, item_id, datetime.now(timezone.utc).isoformat()
    )
    return True, "Видеокарта установлена."


async def remove_videocard(user_id: int, videocard_id: str) -> tuple:
    """Снятие видеокарты (возвращается в инвентарь)."""
    farm_row = await db.fetchone("SELECT id FROM crypto_farm WHERE user_id = ? AND videocard_id = ?", user_id, videocard_id)
    if not farm_row:
        return False, "Видеокарта не найдена в ферме."

    await db.execute("DELETE FROM crypto_farm WHERE id = ?", farm_row["id"])
    await add_item_to_inventory(user_id, videocard_id, 1)
    return True, "Видеокарта снята и возвращена в инвентарь."


async def add_item_to_inventory(user_id: int, item_id: str, quantity: int = 1) -> None:
    """Добавляет предмет в инвентарь."""
    existing = await db.fetchone("SELECT id, quantity FROM inventory WHERE user_id = ? AND item_id = ?", user_id, item_id)
    if existing:
        await db.execute("UPDATE inventory SET quantity = quantity + ? WHERE id = ?", quantity, existing["id"])
    else:
        await db.execute("INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, ?, ?)", user_id, item_id, quantity)


async def get_garden_plots(user_id: int) -> list:
    """Возвращает участки садоводства игрока."""
    return await db.fetchall("SELECT * FROM garden_plots WHERE user_id = ?", user_id)


async def buy_garden_plot(user_id: int, plot_number: int) -> tuple:
    """Покупка участка для садоводства (только для домов)."""
    housing = await get_user_housing(user_id)
    if not housing or housing["type"] != "house":
        return False, "Участки доступны только для домов."

    if plot_number == 1:
        cost = int(await get_config_value("garden_plot_1_cost", 500000))
    elif plot_number == 2:
        cost = int(await get_config_value("garden_plot_2_cost", 800000))
    else:
        return False, "Неверный номер участка."

    plot = await db.fetchone("SELECT id FROM garden_plots WHERE user_id = ? AND plot_number = ?", user_id, plot_number)
    if plot:
        return False, "Этот участок уже куплен."

    user = await db.fetchone("SELECT balance FROM users WHERE vk_id = ?", user_id)
    if user["balance"] < cost:
        return False, "Недостаточно наличных."

    await db.execute("UPDATE users SET balance = balance - ? WHERE vk_id = ?", cost, user_id)
    await db.execute("INSERT INTO garden_plots (user_id, plot_number, capacity, purchased) VALUES (?, ?, 25, 1)", user_id, plot_number)
    return True, "Участок куплен."


async def plant_seed(user_id: int, plot_number: int, slot_number: int, seed_item_id: str) -> tuple:
    """Посадка семени в лунку."""
    seed = await db.fetchone("SELECT id, quantity FROM inventory WHERE user_id = ? AND item_id = ?", user_id, seed_item_id)
    if not seed or seed["quantity"] < 1:
        return False, "Нет семян."

    existing_plant = await db.fetchone("SELECT id FROM garden_plants WHERE user_id = ? AND plot_number = ? AND slot_number = ?", user_id, plot_number, slot_number)
    if existing_plant:
        return False, "Лунка занята."

    item = await db.fetchone("SELECT name FROM items WHERE item_id = ?", seed_item_id)
    if not item:
        return False, "Предмет не найден."

    plant_type = item["name"].lower()
    plant_info = await get_plant_info(plant_type)
    if not plant_info:
        return False, "Неизвестное растение."

    now = datetime.now(timezone.utc)
    water_by = now + timedelta(hours=plant_info["water_interval_hours"])
    if plant_info["type"] == "annual":
        harvest_at = now + timedelta(hours=plant_info["grow_hours"])
        is_tree = 0
    else:
        harvest_at = now + timedelta(hours=plant_info["fruit_interval_hours"])
        is_tree = 1

    await db.execute("UPDATE inventory SET quantity = quantity - 1 WHERE id = ?", seed["id"])
    await db.execute("DELETE FROM inventory WHERE id = ? AND quantity <= 0", seed["id"])

    await db.execute(
        """
        INSERT INTO garden_plants (user_id, plot_number, slot_number, plant_type, seed_item_id,
                                   planted_at, water_required_by, harvest_ready_at, can_harvest, is_tree,
                                   tree_fruit_count, tree_last_harvest)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, 0, NULL)
        """,
        user_id, plot_number, slot_number, plant_type, seed_item_id,
        now.isoformat(), water_by.isoformat(), harvest_at.isoformat(), is_tree
    )
    return True, f"Посажено: {plant_type}."


async def get_plant_info(plant_type: str) -> dict:
    """Возвращает информацию о растении."""
    plants = {
        "огурцы": {"type": "annual", "water_interval_hours": 1, "grow_hours": 3, "fruit_interval_hours": 6},
        "помидоры": {"type": "annual", "water_interval_hours": 1, "grow_hours": 3, "fruit_interval_hours": 6},
        "морковь": {"type": "annual", "water_interval_hours": 1, "grow_hours": 3, "fruit_interval_hours": 6},
        "земляника": {"type": "annual", "water_interval_hours": 1, "grow_hours": 3, "fruit_interval_hours": 6},
        "ежевика": {"type": "annual", "water_interval_hours": 1, "grow_hours": 3, "fruit_interval_hours": 6},
        "дыня": {"type": "annual", "water_interval_hours": 1, "grow_hours": 3, "fruit_interval_hours": 6},
        "арбуз": {"type": "annual", "water_interval_hours": 1, "grow_hours": 3, "fruit_interval_hours": 6},
        "картошка": {"type": "annual", "water_interval_hours": 1, "grow_hours": 3, "fruit_interval_hours": 6},
        "яблоко": {"type": "tree", "water_interval_hours": 2, "grow_hours": 0, "fruit_interval_hours": 6},
        "вишня": {"type": "tree", "water_interval_hours": 2, "grow_hours": 0, "fruit_interval_hours": 6},
        "груша": {"type": "tree", "water_interval_hours": 2, "grow_hours": 0, "fruit_interval_hours": 6},
        "мандарин": {"type": "tree", "water_interval_hours": 2, "grow_hours": 0, "fruit_interval_hours": 6},
    }
    return plants.get(plant_type)


async def water_plant(user_id: int, plant_id: int) -> tuple:
    """Полив растения."""
    plant = await db.fetchone("SELECT * FROM garden_plants WHERE id = ? AND user_id = ?", plant_id, user_id)
    if not plant:
        return False, "Растение не найдено."

    now = datetime.now(timezone.utc)
    if datetime.fromisoformat(plant["water_required_by"]) > now:
        return False, "Поливать ещё рано."

    plant_info = await get_plant_info(plant["plant_type"])
    new_water_by = now + timedelta(hours=plant_info["water_interval_hours"])
    await db.execute("UPDATE garden_plants SET water_required_by = ? WHERE id = ?", new_water_by.isoformat(), plant_id)
    return True, "Растение полито."


async def harvest_plant(user_id: int, plant_id: int) -> tuple:
    """Сбор урожая."""
    plant = await db.fetchone("SELECT * FROM garden_plants WHERE id = ? AND user_id = ?", plant_id, user_id)
    if not plant:
        return False, "Растение не найдено."

    now = datetime.now(timezone.utc)
    if plant["can_harvest"] == 0:
        return False, "Урожай ещё не созрел."

    plant_info = await get_plant_info(plant["plant_type"])
    if plant_info["type"] == "annual":
        amount = random.randint(int(await get_config_value("annual_yield_min", 10)), int(await get_config_value("annual_yield_max", 50)))
        await add_harvest_item(user_id, plant["plant_type"], amount)
        await db.execute("DELETE FROM garden_plants WHERE id = ?", plant_id)
        return True, f"Собрано {amount} единиц урожая."
    else:
        amount = random.randint(int(await get_config_value("tree_yield_min", 25)), int(await get_config_value("tree_yield_max", 75)))
        await add_harvest_item(user_id, plant["plant_type"], amount)
        next_harvest = now + timedelta(hours=plant_info["fruit_interval_hours"])
        await db.execute(
            "UPDATE garden_plants SET tree_fruit_count = tree_fruit_count + ?, tree_last_harvest = ?, harvest_ready_at = ? WHERE id = ?",
            amount, now.isoformat(), next_harvest.isoformat(), plant_id
        )
        return True, f"Собрано {amount} единиц урожая."


async def add_harvest_item(user_id: int, plant_type: str, quantity: int) -> None:
    """Добавляет урожай в инвентарь."""
    item_id = f"harvest_{plant_type}"
    existing_item = await db.fetchone("SELECT id FROM items WHERE item_id = ?", item_id)
    if not existing_item:
        await db.execute(
            "INSERT INTO items (item_id, name, description, type, base_price, stackable) VALUES (?, ?, ?, 'harvest', 10, 1)",
            item_id, f"Урожай {plant_type}", f"Урожай {plant_type}"
        )
    await add_item_to_inventory(user_id, item_id, quantity)


async def chop_tree(user_id: int, plant_id: int) -> tuple:
    """Вырубка дерева топором."""
    plant = await db.fetchone("SELECT * FROM garden_plants WHERE id = ? AND user_id = ?", plant_id, user_id)
    if not plant or not plant["is_tree"]:
        return False, "Это не дерево."

    axe = await db.fetchone("SELECT id, durability FROM inventory WHERE user_id = ? AND item_id = '4.9.1'", user_id)
    if not axe:
        return False, "Нужен топор для вырубки дерева."

    wood_amount = random.randint(
        int(await get_config_value("tree_wood_drop_min", 2)),
        int(await get_config_value("tree_wood_drop_max", 4))
    )
    await add_item_to_inventory(user_id, "4.1.12", wood_amount)

    new_durability = axe["durability"] - 1
    if new_durability <= 0:
        await db.execute("DELETE FROM inventory WHERE id = ?", axe["id"])
    else:
        await db.execute("UPDATE inventory SET durability = ? WHERE id = ?", new_durability, axe["id"])

    await db.execute("DELETE FROM garden_plants WHERE id = ?", plant_id)
    return True, f"Дерево вырублено, получено {wood_amount} дерева."