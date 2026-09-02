# city/handlers/cities.py
# Меню города, автобусные поездки, маршруты, обработчики для всех разделов.

import asyncio
import logging
from vkbottle.bot import Blueprint, Message
from db.database import db
from city.keyboards.cities import (
    get_city_menu_keyboard,
    get_more_menu_keyboard,
    get_bus_routes_keyboard,
    get_travel_result_keyboard,
)

from housing.handlers.housing import show_housing_menu
from transport.handlers.transport import show_transport_menu
from shop.handlers.shop import show_shop_menu
from gas_station.handlers.gas_station import show_gas_station_menu
from casino.handlers.casino import show_casino_menu
from mars.handlers.mars import show_investments_menu
from lottery.handlers.lottery import show_lottery_menu
from player.handlers.inventory import show_inventory_menu
from craft.handlers.craft import show_craft_menu
from nkvito.handlers.nkvito import show_nkvito_menu

logger = logging.getLogger(__name__)

bp = Blueprint("city")

AVAILABLE_CITIES = ["Звездограцк", "Мемград", "Величие"]
BUS_TICKET_PRICE = 250
TRAVEL_DELAY_SECONDS = 30


async def _get_user_city(user_id: int) -> str:
    row = await db.fetchone("SELECT current_city FROM users WHERE vk_id = ?", user_id)
    return row["current_city"] if row else None


async def _has_active_vehicle(user_id: int) -> bool:
    row = await db.fetchone(
        "SELECT id FROM player_vehicles WHERE user_id = ? AND active = 1",
        user_id
    )
    return row is not None


async def show_city_menu(message: Message):
    user_id = message.from_id
    current_city = await _get_user_city(user_id)
    has_vehicle = await _has_active_vehicle(user_id)
    keyboard = get_city_menu_keyboard(current_city, has_vehicle)
    text = f"📍 Текущий город: {current_city}\n\nЧто вы хотите сделать?"
    await message.answer(text, keyboard=keyboard)


async def show_more_menu(message: Message):
    await message.answer("Дополнительно:", keyboard=get_more_menu_keyboard())


@bp.on.message(payload={"cmd": "open_city"})
async def open_city(message: Message):
    await show_city_menu(message)


@bp.on.message(payload={"cmd": "open_housing"})
async def open_housing(message: Message):
    await show_housing_menu(message)


@bp.on.message(payload={"cmd": "open_transport"})
async def open_transport(message: Message):
    await show_transport_menu(message)


@bp.on.message(payload={"cmd": "open_shop"})
async def open_shop(message: Message):
    await show_shop_menu(message)


@bp.on.message(payload={"cmd": "open_gas_station"})
async def open_gas_station(message: Message):
    await show_gas_station_menu(message)


@bp.on.message(payload={"cmd": "open_casino"})
async def open_casino(message: Message):
    await show_casino_menu(message)


@bp.on.message(payload={"cmd": "open_investments"})
async def open_investments(message: Message):
    await show_investments_menu(message)


@bp.on.message(payload={"cmd": "open_lottery"})
async def open_lottery(message: Message):
    await show_lottery_menu(message)


@bp.on.message(payload={"cmd": "open_inventory"})
async def open_inventory(message: Message):
    await show_inventory_menu(message)


@bp.on.message(payload={"cmd": "open_craft"})
async def open_craft(message: Message):
    await show_craft_menu(message)


@bp.on.message(payload={"cmd": "open_nkvito"})
async def open_nkvito(message: Message):
    await show_nkvito_menu(message)


@bp.on.message(payload={"cmd": "open_more"})
async def open_more(message: Message):
    await show_more_menu(message)


@bp.on.message(payload={"cmd": "back_to_city_menu"})
async def back_to_city_menu(message: Message):
    await show_city_menu(message)


@bp.on.message(payload={"cmd": "open_bus_routes"})
async def open_bus_routes(message: Message):
    current_city = await _get_user_city(message.from_id)
    keyboard = get_bus_routes_keyboard(current_city)
    text = "🚌 Выберите город, в который хотите отправиться на автобусе:"
    await message.answer(text, keyboard=keyboard)


@bp.on.message(payload={"cmd": "travel_bus"})
async def travel_bus(message: Message):
    payload = message.get_payload_json()
    target_city = payload.get("city")

    user_id = message.from_id
    user = await db.fetchone("SELECT balance FROM users WHERE vk_id = ?", user_id)
    balance = user["balance"]

    if balance < BUS_TICKET_PRICE:
        await message.answer(f"Недостаточно средств на автобусный билет. Нужно {BUS_TICKET_PRICE} NK.")
        return

    await db.execute(
        "UPDATE users SET balance = balance - ? WHERE vk_id = ?",
        BUS_TICKET_PRICE, user_id
    )

    await message.answer(
        f"🚌 Вы сели на автобус до города {target_city}. "
        f"С вас списано {BUS_TICKET_PRICE} NK. "
        f"Время в пути: {TRAVEL_DELAY_SECONDS} секунд."
    )

    await asyncio.sleep(TRAVEL_DELAY_SECONDS)

    await db.execute(
        "UPDATE users SET current_city = ? WHERE vk_id = ?",
        target_city, user_id
    )

    await message.answer(
        f"✅ Вы прибыли в город {target_city}.",
        keyboard=get_travel_result_keyboard()
    )


@bp.on.message(payload={"cmd": "back_to_main_from_city"})
async def back_to_main_from_city(message: Message):
    from player.handlers.main_menu import show_main_menu
    await show_main_menu(message, edit=True)