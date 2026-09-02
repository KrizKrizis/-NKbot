# services/shop_service.py
# Логика магазина: покупка предметов, продажа урожая, биржа криптовалюты.

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


async def get_items_by_type(item_type: str) -> list:
    """Возвращает предметы определённого типа."""
    return await db.fetchall("SELECT * FROM items WHERE type = ?", item_type)


async def buy_item(user_id: int, item_id: str, quantity: int = 1) -> tuple:
    """Покупка предмета в магазине за наличные."""
    item = await db.fetchone("SELECT * FROM items WHERE item_id = ?", item_id)
    if not item:
        return False, "Предмет не найден."

    total_cost = item["base_price"] * quantity
    user = await db.fetchone("SELECT balance FROM users WHERE vk_id = ?", user_id)
    if user["balance"] < total_cost:
        return False, "Недостаточно наличных."

    await db.execute("UPDATE users SET balance = balance - ? WHERE vk_id = ?", total_cost, user_id)
    if item["stackable"]:
        existing = await db.fetchone("SELECT id, quantity FROM inventory WHERE user_id = ? AND item_id = ?", user_id, item_id)
        if existing:
            await db.execute("UPDATE inventory SET quantity = quantity + ? WHERE id = ?", quantity, existing["id"])
        else:
            await db.execute("INSERT INTO inventory (user_id, item_id, quantity, durability) VALUES (?, ?, ?, 100)", user_id, item_id, quantity)
    else:
        for _ in range(quantity):
            await db.execute("INSERT INTO inventory (user_id, item_id, quantity, durability) VALUES (?, ?, 1, 100)", user_id, item_id)
    return True, f"Куплено: {item['name']} x{quantity}."


async def sell_harvest_to_shop(user_id: int, item_id: str, quantity: int) -> tuple:
    """Продажа урожая магазину раз в неделю по x5 цене."""
    last_sale = await db.fetchone(
        "SELECT data FROM user_states WHERE user_id = ? AND state = 'weekly_shop_sale'",
        user_id
    )
    now = datetime.now(timezone.utc)
    if last_sale:
        last_time = datetime.fromisoformat(json.loads(last_sale["data"]).get("last_sale"))
        if (now - last_time).days < 7:
            return False, "Продажа магазину доступна раз в неделю."

    item = await db.fetchone("SELECT * FROM items WHERE item_id = ?", item_id)
    if not item or item["type"] not in ["harvest", "resource"]:
        return False, "Этот предмет нельзя продать."

    inv = await db.fetchone("SELECT id, quantity FROM inventory WHERE user_id = ? AND item_id = ?", user_id, item_id)
    if not inv or inv["quantity"] < quantity:
        return False, "Недостаточно предметов."

    multiplier = float(await get_config_value("weekly_shop_purchase_multiplier", 5))
    price_per_item = item["base_price"] * multiplier
    total = int(price_per_item * quantity)

    await db.execute("UPDATE users SET balance = balance + ? WHERE vk_id = ?", total, user_id)
    await db.execute("UPDATE inventory SET quantity = quantity - ? WHERE id = ?", quantity, inv["id"])
    await db.execute("DELETE FROM inventory WHERE id = ? AND quantity <= 0", inv["id"])

    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'weekly_shop_sale', ?)",
        user_id, json.dumps({"last_sale": now.isoformat()})
    )
    return True, f"Продано {quantity} шт. за {total} NK."


async def get_private_buyer_prices() -> dict:
    """Возвращает текущие цены частных лиц на продукты (случайные)."""
    products = await db.fetchall("SELECT item_id, name, base_price FROM items WHERE type IN ('harvest','resource')")
    prices = {}
    for p in products:
        multiplier = random.uniform(0.5, 1.5)
        prices[p["item_id"]] = int(p["base_price"] * multiplier)
    return prices


async def sell_to_private_buyer(user_id: int, item_id: str, quantity: int) -> tuple:
    """Продажа частному лицу по рандомной цене."""
    item = await db.fetchone("SELECT * FROM items WHERE item_id = ?", item_id)
    if not item or item["type"] not in ["harvest", "resource"]:
        return False, "Этот предмет нельзя продать."

    inv = await db.fetchone("SELECT id, quantity FROM inventory WHERE user_id = ? AND item_id = ?", user_id, item_id)
    if not inv or inv["quantity"] < quantity:
        return False, "Недостаточно предметов."

    if item["type"] == "harvest":
        min_qty = 20 if "tree" not in item["name"] else 100
        if quantity < min_qty:
            return False, f"Минимальная партия для продажи: {min_qty} шт."

    prices = await get_private_buyer_prices()
    price = prices.get(item_id, item["base_price"])
    total = price * quantity

    await db.execute("UPDATE users SET balance = balance + ? WHERE vk_id = ?", total, user_id)
    await db.execute("UPDATE inventory SET quantity = quantity - ? WHERE id = ?", quantity, inv["id"])
    await db.execute("DELETE FROM inventory WHERE id = ? AND quantity <= 0", inv["id"])
    return True, f"Продано {quantity} шт. за {total} NK (цена за шт: {price})."


async def exchange_crypto_to_nk(user_id: int, crypto_amount: float) -> tuple:
    """Мгновенная продажа криптовалюты по фиксированному курсу."""
    rate = float(await get_config_value("crypto_to_nk_rate", 10))
    nk_amount = int(crypto_amount * rate)
    user = await db.fetchone("SELECT crypto_balance, balance FROM users WHERE vk_id = ?", user_id)
    if user["crypto_balance"] < crypto_amount:
        return False, "Недостаточно криптовалюты."

    await db.execute("UPDATE users SET crypto_balance = crypto_balance - ?, balance = balance + ? WHERE vk_id = ?", crypto_amount, nk_amount, user_id)
    return True, f"Обменяно {crypto_amount} крипто на {nk_amount} NK."


async def list_on_exchange(user_id: int, crypto_amount: float) -> tuple:
    """Выставить криптовалюту на биржу на сутки."""
    user = await db.fetchone("SELECT crypto_balance FROM users WHERE vk_id = ?", user_id)
    if user["crypto_balance"] < crypto_amount:
        return False, "Недостаточно криптовалюты."

    await db.execute("UPDATE users SET crypto_balance = crypto_balance - ? WHERE vk_id = ?", crypto_amount, user_id)
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'exchange_pending', ?)",
        user_id, json.dumps({"crypto_amount": crypto_amount, "created_at": datetime.now(timezone.utc).isoformat()})
    )
    return True, "Криптовалюта выставлена на биржу. Результат будет через 24 часа."


async def process_exchange_pending() -> None:
    """Обрабатывает завершённые заявки на бирже (вызывается планировщиком)."""
    now = datetime.now(timezone.utc)
    rows = await db.fetchall("SELECT user_id, data FROM user_states WHERE state = 'exchange_pending'")
    for row in rows:
        data = json.loads(row["data"])
        created_at = datetime.fromisoformat(data["created_at"])
        if (now - created_at).total_seconds() >= 86400:
            variation_percent = float(await get_config_value("exchange_rate_variation_percent", 2))
            variations = [-2, -1.5, -1, -0.5, 0.5, 1, 1.5, 2]
            coef = random.choice(variations)
            base_rate = float(await get_config_value("crypto_to_nk_rate", 10))
            final_rate = base_rate * (1 + coef / 100)
            nk_amount = int(data["crypto_amount"] * final_rate)
            await db.execute("UPDATE users SET balance = balance + ? WHERE vk_id = ?", nk_amount, row["user_id"])
            await db.execute("DELETE FROM user_states WHERE user_id = ? AND state = 'exchange_pending'", row["user_id"])