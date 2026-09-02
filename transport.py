# transport/handlers/transport.py
# Обработчики транспорта.

import logging
from vkbottle.bot import Blueprint, Message
from db.database import db
from services.transport_service import (
    get_available_vehicles, get_user_vehicles, get_active_vehicle,
    buy_vehicle, sell_vehicle, set_active_vehicle, refuel_vehicle,
)
from transport.keyboards.transport import (
    get_transport_main_keyboard, get_transport_list_keyboard,
    get_my_vehicles_keyboard, get_vehicle_actions_keyboard,
)

logger = logging.getLogger(__name__)

bp = Blueprint("transport")


async def show_transport_menu(message: Message):
    await message.answer("🚗 Транспорт", keyboard=get_transport_main_keyboard())


@bp.on.message(payload={"cmd": "open_transport"})
async def open_transport(message: Message):
    await show_transport_menu(message)


@bp.on.message(payload={"cmd": "transport_main"})
async def transport_main(message: Message):
    await show_transport_menu(message)


@bp.on.message(payload={"cmd": "transport_buy_list"})
async def transport_buy_list(message: Message):
    vehicles = await get_available_vehicles()
    await message.answer("Доступные автомобили:", keyboard=get_transport_list_keyboard(vehicles))


@bp.on.message(payload={"cmd": "transport_buy"})
async def transport_buy(message: Message):
    payload = message.get_payload_json()
    vehicle_id = payload.get("vehicle_id")
    success, msg = await buy_vehicle(message.from_id, vehicle_id)
    await message.answer(msg)
    await show_transport_menu(message)


@bp.on.message(payload={"cmd": "transport_my"})
async def transport_my(message: Message):
    vehicles = await get_user_vehicles(message.from_id)
    if not vehicles:
        await message.answer("У вас нет автомобилей.")
        return
    await message.answer("Ваши автомобили:", keyboard=get_my_vehicles_keyboard(vehicles))


@bp.on.message(payload={"cmd": "transport_vehicle"})
async def transport_vehicle(message: Message):
    payload = message.get_payload_json()
    vehicle_record_id = int(payload.get("vehicle_id"))
    vehicle = await db.fetchone("SELECT * FROM player_vehicles WHERE id = ? AND user_id = ?", vehicle_record_id, message.from_id)
    if not vehicle:
        await message.answer("Автомобиль не найден.")
        return
    is_active = vehicle["active"] == 1
    await message.answer(f"Действия с автомобилем ID {vehicle_record_id}:", keyboard=get_vehicle_actions_keyboard(vehicle_record_id, is_active))


@bp.on.message(payload={"cmd": "transport_set_active"})
async def transport_set_active(message: Message):
    payload = message.get_payload_json()
    vehicle_record_id = int(payload.get("vehicle_id"))
    success, msg = await set_active_vehicle(message.from_id, vehicle_record_id)
    await message.answer(msg)
    await transport_my(message)


@bp.on.message(payload={"cmd": "transport_sell"})
async def transport_sell(message: Message):
    payload = message.get_payload_json()
    vehicle_record_id = int(payload.get("vehicle_id"))
    success, msg = await sell_vehicle(message.from_id, vehicle_record_id)
    await message.answer(msg)
    await transport_my(message)


@bp.on.message(payload={"cmd": "transport_refuel"})
async def transport_refuel(message: Message):
    payload = message.get_payload_json()
    vehicle_record_id = int(payload.get("vehicle_id"))
    active = await get_active_vehicle(message.from_id)
    if not active or active["id"] != vehicle_record_id:
        await message.answer("Этот автомобиль не активен. Сначала сделайте его активным.")
        return
    success, msg = await refuel_vehicle(message.from_id, 10)
    await message.answer(msg)