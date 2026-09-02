# gas_station/handlers/gas_station.py
# Обработчики заправки.

import logging
from vkbottle.bot import Blueprint, Message
from db.database import db
from services.transport_service import get_active_vehicle, refuel_vehicle
from gas_station.keyboards.gas_station import (
    get_gas_station_main_keyboard,
    get_gas_station_back_keyboard,
)

logger = logging.getLogger(__name__)

bp = Blueprint("gas_station")


async def show_gas_station_menu(message: Message):
    """Показывает меню заправки."""
    active = await get_active_vehicle(message.from_id)
    if not active:
        await message.answer("У вас нет активного транспорта. Сначала выберите транспорт.")
        return

    # Показываем текущий уровень топлива и цену за литр
    user = await db.fetchone("SELECT current_city, balance FROM users WHERE vk_id = ?", message.from_id)
    city = user["current_city"]
    fuel_price = 60 if city == "Величие" else 70
    text = (
        f"⛽ Заправка\n"
        f"Активный транспорт: {active['name']}\n"
        f"Топливо: {active['fuel_amount']:.1f} л / {active['tank_capacity']} л\n"
        f"Цена за литр: {fuel_price} NK\n\n"
        f"Выберите действие:"
    )
    await message.answer(text, keyboard=get_gas_station_main_keyboard())


@bp.on.message(payload={"cmd": "open_gas_station"})
async def open_gas_station(message: Message):
    await show_gas_station_menu(message)


@bp.on.message(payload={"cmd": "gas_main"})
async def gas_main(message: Message):
    await show_gas_station_menu(message)


@bp.on.message(payload={"cmd": "gas_refuel_10"})
async def gas_refuel_10(message: Message):
    success, msg = await refuel_vehicle(message.from_id, 10)
    await message.answer(msg)
    await show_gas_station_menu(message)


@bp.on.message(payload={"cmd": "gas_refuel_full"})
async def gas_refuel_full(message: Message):
    active = await get_active_vehicle(message.from_id)
    if not active:
        await message.answer("Нет активного транспорта.")
        return
    needed = active["tank_capacity"] - active["fuel_amount"]
    if needed <= 0:
        await message.answer("Бак уже полон.")
        return
    success, msg = await refuel_vehicle(message.from_id, needed)
    await message.answer(msg)
    await show_gas_station_menu(message)