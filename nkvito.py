# nkvito/handlers/nkvito.py
# Обработчики NKVito.

import json
from vkbottle.bot import Blueprint, Message
from db.database import db
from services.nkvito_service import (
    get_active_listings,
    get_user_listings,
    get_user_inventory_items,
    create_listing,
    buy_listing,
    cancel_listing,
    check_expired_listings,
)
from nkvito.keyboards.nkvito import (
    get_nkvito_main_keyboard,
    get_listings_keyboard,
    get_inventory_items_keyboard,
    get_duration_keyboard,
    get_my_listings_keyboard,
)

bp = Blueprint("nkvito")


async def show_nkvito_menu(message: Message):
    """Показывает главное меню NKVito."""
    await check_expired_listings()
    await message.answer("🤝 NKVito — торговая площадка", keyboard=get_nkvito_main_keyboard())


@bp.on.message(payload={"cmd": "open_nkvito"})
async def open_nkvito(message: Message):
    await show_nkvito_menu(message)


@bp.on.message(payload={"cmd": "nkvito_menu"})
async def nkvito_menu(message: Message):
    await show_nkvito_menu(message)


@bp.on.message(payload={"cmd": "nkvito_listings"})
async def nkvito_listings(message: Message):
    await show_listings_page(message, page=1)


@bp.on.message(payload={"cmd": "nkvito_page"})
async def nkvito_page(message: Message):
    payload = message.get_payload_json()
    page = int(payload.get("page", 1))
    await show_listings_page(message, page)


async def show_listings_page(message: Message, page: int):
    """Показывает страницу списка лотов."""
    listings = await get_active_listings(page)
    next_page = await get_active_listings(page + 1)
    has_next = len(next_page) > 0
    if not listings:
        await message.answer("Нет активных лотов.", keyboard=get_nkvito_main_keyboard())
        return
    keyboard = get_listings_keyboard(listings, page, has_next)
    await message.answer("Активные лоты:", keyboard=keyboard)


@bp.on.message(payload={"cmd": "nkvito_create"})
async def nkvito_create(message: Message):
    """Начинает создание лота: показывает инвентарь для выбора предмета."""
    items = await get_user_inventory_items(message.from_id)
    if not items:
        await message.answer("Ваш инвентарь пуст.", keyboard=get_nkvito_main_keyboard())
        return
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'nkvito_select_item', '{}')",
        message.from_id
    )
    await message.answer("Выберите предмет для продажи:", keyboard=get_inventory_items_keyboard(items))


@bp.on.message(payload={"cmd": "nkvito_select_item"})
async def nkvito_select_item(message: Message):
    payload = message.get_payload_json()
    item_id = payload.get("item_id")
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'nkvito_enter_price', ?)",
        message.from_id, json.dumps({"item_id": item_id})
    )
    await message.answer("Введите цену (в NK):")


@bp.on.message(payload={"cmd": "nkvito_duration"})
async def nkvito_duration(message: Message):
    payload = message.get_payload_json()
    days = int(payload.get("days"))
    state_row = await db.fetchone("SELECT data FROM user_states WHERE user_id = ? AND state = 'nkvito_enter_duration'", message.from_id)
    if not state_row:
        await message.answer("Ошибка. Начните заново.", keyboard=get_nkvito_main_keyboard())
        return
    data = json.loads(state_row["data"])
    item_id = data.get("item_id")
    price = int(data.get("price"))

    success, msg = await create_listing(message.from_id, item_id, price, days)
    await message.answer(msg)
    await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
    await show_nkvito_menu(message)


@bp.on.message()
async def handle_nkvito_text(message: Message):
    """Обрабатывает текстовый ввод цены."""
    state_row = await db.fetchone("SELECT state, data FROM user_states WHERE user_id = ?", message.from_id)
    if not state_row:
        return

    state = state_row["state"]
    if state == "nkvito_enter_price":
        text = message.text.strip()
        if not text.isdigit() or int(text) <= 0:
            await message.answer("Цена должна быть положительным числом.")
            return
        price = int(text)
        data = json.loads(state_row["data"])
        data["price"] = price
        await db.execute(
            "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'nkvito_enter_duration', ?)",
            message.from_id, json.dumps(data)
        )
        await message.answer("Выберите срок размещения:", keyboard=get_duration_keyboard())
    else:
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)


@bp.on.message(payload={"cmd": "nkvito_my"})
async def nkvito_my(message: Message):
    """Показывает лоты текущего пользователя."""
    listings = await get_user_listings(message.from_id)
    if not listings:
        await message.answer("У вас нет активных лотов.", keyboard=get_nkvito_main_keyboard())
        return
    await message.answer("Ваши лоты (нажмите, чтобы снять):", keyboard=get_my_listings_keyboard(listings))


@bp.on.message(payload={"cmd": "nkvito_cancel"})
async def nkvito_cancel(message: Message):
    payload = message.get_payload_json()
    listing_id = int(payload.get("listing_id"))
    success, msg = await cancel_listing(listing_id, message.from_id)
    await message.answer(msg)
    await nkvito_my(message)


@bp.on.message(payload={"cmd": "nkvito_buy"})
async def nkvito_buy(message: Message):
    payload = message.get_payload_json()
    listing_id = int(payload.get("listing_id"))
    success, msg = await buy_listing(listing_id, message.from_id)
    await message.answer(msg)
    if success:
        await show_nkvito_menu(message)