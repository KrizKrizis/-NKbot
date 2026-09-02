# services/transport_service.py
# Логика транспорта: покупка, продажа, заправка, перемещение.

from datetime import datetime, timezone
from db.database import db

FUEL_PRICE_STANDARD = 70
FUEL_PRICE_VELICHIE = 60
TRAVEL_DISTANCE_KM = 50


async def get_available_vehicles() -> list:
    """Возвращает список всех моделей транспорта."""
    return await db.fetchall("SELECT * FROM vehicles")


async def get_user_vehicles(user_id: int) -> list:
    """Возвращает список транспортных средств игрока."""
    return await db.fetchall(
        """
        SELECT pv.*, v.name, v.tank_capacity, v.fuel_consumption, v.country, v.type
        FROM player_vehicles pv
        JOIN vehicles v ON pv.vehicle_id = v.vehicle_id
        WHERE pv.user_id = ?
        """,
        user_id
    )


async def get_active_vehicle(user_id: int) -> dict:
    """Возвращает активное транспортное средство."""
    row = await db.fetchone(
        """
        SELECT pv.*, v.name, v.tank_capacity, v.fuel_consumption
        FROM player_vehicles pv
        JOIN vehicles v ON pv.vehicle_id = v.vehicle_id
        WHERE pv.user_id = ? AND pv.active = 1
        """,
        user_id
    )
    return row


async def get_parking_limit(user_id: int) -> int:
    """Возвращает максимальное количество парковочных мест."""
    housing = await db.fetchone(
        "SELECT h.parking_spots FROM player_housing ph JOIN housing h ON ph.housing_id = h.housing_id WHERE ph.user_id = ?",
        user_id
    )
    return housing["parking_spots"] if housing else 1


async def buy_vehicle(user_id: int, vehicle_id: str) -> tuple:
    """Покупка транспортного средства."""
    vehicle = await db.fetchone("SELECT * FROM vehicles WHERE vehicle_id = ?", vehicle_id)
    if not vehicle:
        return False, "Транспорт не найден."

    current_count = await db.fetchone("SELECT COUNT(*) as cnt FROM player_vehicles WHERE user_id = ?", user_id)
    limit = await get_parking_limit(user_id)
    if current_count["cnt"] >= limit:
        return False, "Нет свободных парковочных мест."

    user = await db.fetchone("SELECT balance FROM users WHERE vk_id = ?", user_id)
    if user["balance"] < vehicle["price"]:
        return False, "Недостаточно наличных."

    await db.execute("UPDATE users SET balance = balance - ? WHERE vk_id = ?", vehicle["price"], user_id)
    fuel_amount = vehicle["tank_capacity"] * 0.75
    await db.execute(
        "INSERT INTO player_vehicles (user_id, vehicle_id, active, fuel_amount, mileage) VALUES (?, ?, 0, ?, 0)",
        user_id, vehicle_id, fuel_amount
    )
    return True, f"Вы купили {vehicle['name']}."


async def sell_vehicle(user_id: int, vehicle_record_id: int) -> tuple:
    """Продажа транспортного средства государству за 60%."""
    vehicle = await db.fetchone(
        "SELECT pv.*, v.price, v.name FROM player_vehicles pv JOIN vehicles v ON pv.vehicle_id = v.vehicle_id WHERE pv.id = ? AND pv.user_id = ?",
        vehicle_record_id, user_id
    )
    if not vehicle:
        return False, "Транспорт не найден."

    sell_price = int(vehicle["price"] * 0.6)
    await db.execute("UPDATE users SET balance = balance + ? WHERE vk_id = ?", sell_price, user_id)
    await db.execute("DELETE FROM player_vehicles WHERE id = ?", vehicle_record_id)
    return True, f"Транспорт {vehicle['name']} продан за {sell_price} NK."


async def set_active_vehicle(user_id: int, vehicle_record_id: int) -> tuple:
    """Устанавливает активное транспортное средство (только в Величии)."""
    user = await db.fetchone("SELECT current_city FROM users WHERE vk_id = ?", user_id)
    if user["current_city"] != "Величие":
        return False, "Сменить активный транспорт можно только в Величии."

    vehicle = await db.fetchone("SELECT id FROM player_vehicles WHERE id = ? AND user_id = ?", vehicle_record_id, user_id)
    if not vehicle:
        return False, "Транспорт не найден."

    await db.execute("UPDATE player_vehicles SET active = 0 WHERE user_id = ?", user_id)
    await db.execute("UPDATE player_vehicles SET active = 1 WHERE id = ?", vehicle_record_id)
    return True, "Активный транспорт обновлён."


async def refuel_vehicle(user_id: int, amount_liters: float) -> tuple:
    """Заправка активного транспортного средства."""
    active = await get_active_vehicle(user_id)
    if not active:
        return False, "Нет активного транспорта."

    user = await db.fetchone("SELECT balance, current_city FROM users WHERE vk_id = ?", user_id)
    fuel_price = FUEL_PRICE_VELICHIE if user["current_city"] == "Величие" else FUEL_PRICE_STANDARD
    total_cost = int(amount_liters * fuel_price)

    if user["balance"] < total_cost:
        return False, "Недостаточно наличных."

    new_fuel = min(active["tank_capacity"], active["fuel_amount"] + amount_liters)
    await db.execute("UPDATE users SET balance = balance - ? WHERE vk_id = ?", total_cost, user_id)
    await db.execute("UPDATE player_vehicles SET fuel_amount = ? WHERE id = ?", new_fuel, active["id"])
    return True, f"Заправлено {amount_liters} л за {total_cost} NK."


async def travel_with_vehicle(user_id: int, target_city: str) -> tuple:
    """Перемещение на активном транспорте."""
    active = await get_active_vehicle(user_id)
    if not active:
        return False, "Нет активного транспорта."

    consumption = active["fuel_consumption"] * TRAVEL_DISTANCE_KM / 100
    if active["fuel_amount"] < consumption:
        return False, "Недостаточно топлива. Заправьтесь или используйте автобус."

    new_fuel = active["fuel_amount"] - consumption
    await db.execute(
        "UPDATE player_vehicles SET fuel_amount = ?, mileage = mileage + ? WHERE id = ?",
        new_fuel, TRAVEL_DISTANCE_KM, active["id"]
    )
    await db.execute("UPDATE users SET current_city = ? WHERE vk_id = ?", target_city, user_id)
    return True, f"Вы приехали в {target_city} на {active['name']}."