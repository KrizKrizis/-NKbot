# shop/handlers/shop.py
# Обработчики магазина: электроника, инструменты, скупщик, биржа, бизнесы, аукцион.

import json
import logging
from vkbottle.bot import Blueprint, Message
from db.database import db
from services.shop_service import (
    get_items_by_type,
    buy_item,
    sell_harvest_to_shop,
    sell_to_private_buyer,
    exchange_crypto_to_nk,
    list_on_exchange,
)
from services.business_service import buy_personal_business
from shop.keyboards.shop import (
    get_shop_main_keyboard,
    get_electronics_keyboard,
    get_tools_keyboard,
    get_buyer_main_keyboard,
    get_exchange_keyboard,
    get_back_to_shop_keyboard,
    get_business_categories_keyboard,
    get_personal_business_list_keyboard,
)
from auction.handlers.auction import show_auction_menu

logger = logging.getLogger(__name__)

bp = Blueprint("shop")


async def show_shop_menu(message: Message):
    """Показывает главное меню магазина."""
    await message.answer("🛒 Магазин", keyboard=get_shop_main_keyboard())


@bp.on.message(payload={"cmd": "open_shop"})
async def open_shop(message: Message):
    await show_shop_menu(message)


@bp.on.message(payload={"cmd": "shop_main"})
async def shop_main(message: Message):
    await show_shop_menu(message)


# --- Электроника и инструменты ---

@bp.on.message(payload={"cmd": "shop_electronics"})
async def shop_electronics(message: Message):
    items = await get_items_by_type("videocard")
    if not items:
        await message.answer("В наличии нет видеокарт.", keyboard=get_back_to_shop_keyboard())
        return
    await message.answer("Электроника:", keyboard=get_electronics_keyboard(items))


@bp.on.message(payload={"cmd": "shop_tools"})
async def shop_tools(message: Message):
    items = await get_items_by_type("tool")
    if not items:
        await message.answer("В наличии нет инструментов.", keyboard=get_back_to_shop_keyboard())
        return
    await message.answer("Инструменты:", keyboard=get_tools_keyboard(items))


@bp.on.message(payload={"cmd": "shop_buy_item"})
async def shop_buy_item(message: Message):
    payload = message.get_payload_json()
    item_id = payload.get("item_id")
    success, msg = await buy_item(message.from_id, item_id, 1)
    await message.answer(msg)
    await show_shop_menu(message)


# --- Скупщик ---

@bp.on.message(payload={"cmd": "shop_buyer"})
async def shop_buyer(message: Message):
    await message.answer("Скупщик", keyboard=get_buyer_main_keyboard())


@bp.on.message(payload={"cmd": "shop_sell_weekly"})
async def shop_sell_weekly(message: Message):
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'shop_select_item_weekly', '{}')",
        message.from_id
    )
    items = await get_items_by_type("harvest")
    if not items:
        items = await get_items_by_type("resource")
    if not items:
        await message.answer("Нет предметов для продажи.")
        return
    from vkbottle import Keyboard, KeyboardButtonColor, Text
    kb = Keyboard(one_time=False, inline=True)
    for item in items:
        kb.add(Text(item["name"], payload={"cmd": "shop_weekly_select_item", "item_id": item["item_id"]}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("🔙 Назад", payload={"cmd": "shop_buyer"}), color=KeyboardButtonColor.SECONDARY)
    await message.answer("Выберите предмет для продажи магазину:", keyboard=kb)


@bp.on.message(payload={"cmd": "shop_weekly_select_item"})
async def shop_weekly_select_item(message: Message):
    payload = message.get_payload_json()
    item_id = payload.get("item_id")
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'shop_weekly_quantity', ?)",
        message.from_id, json.dumps({"item_id": item_id})
    )
    await message.answer("Введите количество:")


@bp.on.message(payload={"cmd": "shop_sell_private"})
async def shop_sell_private(message: Message):
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'shop_select_item_private', '{}')",
        message.from_id
    )
    items = await get_items_by_type("harvest")
    if not items:
        items = await get_items_by_type("resource")
    if not items:
        await message.answer("Нет предметов для продажи.")
        return
    from vkbottle import Keyboard, KeyboardButtonColor, Text
    kb = Keyboard(one_time=False, inline=True)
    for item in items:
        kb.add(Text(item["name"], payload={"cmd": "shop_private_select_item", "item_id": item["item_id"]}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("🔙 Назад", payload={"cmd": "shop_buyer"}), color=KeyboardButtonColor.SECONDARY)
    await message.answer("Выберите предмет для продажи частному лицу:", keyboard=kb)


@bp.on.message(payload={"cmd": "shop_private_select_item"})
async def shop_private_select_item(message: Message):
    payload = message.get_payload_json()
    item_id = payload.get("item_id")
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'shop_private_quantity', ?)",
        message.from_id, json.dumps({"item_id": item_id})
    )
    await message.answer("Введите количество:")


# --- Биржа ---

@bp.on.message(payload={"cmd": "shop_exchange"})
async def shop_exchange(message: Message):
    await message.answer("Биржа криптовалюты", keyboard=get_exchange_keyboard())


@bp.on.message(payload={"cmd": "exchange_instant"})
async def exchange_instant(message: Message):
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'exchange_instant_amount', '{}')",
        message.from_id
    )
    await message.answer("Введите количество криптовалюты для мгновенного обмена:")


@bp.on.message(payload={"cmd": "exchange_list"})
async def exchange_list(message: Message):
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'exchange_list_amount', '{}')",
        message.from_id
    )
    await message.answer("Введите количество криптовалюты для выставления на биржу (24 часа):")


# --- Бизнесы (личные) ---

@bp.on.message(payload={"cmd": "shop_businesses"})
async def shop_businesses(message: Message):
    await message.answer("Выберите категорию бизнеса или аукцион:", keyboard=get_business_categories_keyboard())


@bp.on.message(payload={"cmd": "shop_business_category"})
async def shop_business_category(message: Message):
    payload = message.get_payload_json()
    category = payload.get("category")
    businesses = await db.fetchall(
        "SELECT * FROM businesses WHERE type = 'personal' AND category = ? AND owner_id IS NULL",
        category
    )
    if not businesses:
        await message.answer("Нет доступных бизнесов в этой категории.")
        return
    await message.answer("Доступные бизнесы:", keyboard=get_personal_business_list_keyboard(businesses))


@bp.on.message(payload={"cmd": "shop_buy_business"})
async def shop_buy_business(message: Message):
    payload = message.get_payload_json()
    business_id = payload.get("business_id")
    success, msg = await buy_personal_business(message.from_id, business_id)
    await message.answer(msg)
    await show_shop_menu(message)


# --- Аукцион ---

@bp.on.message(payload={"cmd": "shop_open_auction"})
async def shop_open_auction(message: Message):
    await show_auction_menu(message)


# --- Обработка текстовых сообщений (FSM) ---

@bp.on.message()
async def handle_shop_text(message: Message):
    state_row = await db.fetchone("SELECT state, data FROM user_states WHERE user_id = ?", message.from_id)
    if not state_row:
        return

    state = state_row["state"]
    text = message.text.strip()

    if state == "shop_weekly_quantity":
        if not text.isdigit() or int(text) <= 0:
            await message.answer("Количество должно быть положительным числом.")
            return
        quantity = int(text)
        data = json.loads(state_row["data"])
        item_id = data.get("item_id")
        success, msg = await sell_harvest_to_shop(message.from_id, item_id, quantity)
        await message.answer(msg)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        await shop_buyer(message)

    elif state == "shop_private_quantity":
        if not text.isdigit() or int(text) <= 0:
            await message.answer("Количество должно быть положительным числом.")
            return
        quantity = int(text)
        data = json.loads(state_row["data"])
        item_id = data.get("item_id")
        success, msg = await sell_to_private_buyer(message.from_id, item_id, quantity)
        await message.answer(msg)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        await shop_buyer(message)

    elif state == "exchange_instant_amount":
        try:
            amount = float(text)
        except ValueError:
            await message.answer("Введите корректное число.")
            return
        success, msg = await exchange_crypto_to_nk(message.from_id, amount)
        await message.answer(msg)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        await shop_exchange(message)

    elif state == "exchange_list_amount":
        try:
            amount = float(text)
        except ValueError:
            await message.answer("Введите корректное число.")
            return
        success, msg = await list_on_exchange(message.from_id, amount)
        await message.answer(msg)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        await shop_exchange(message)

    else:
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)