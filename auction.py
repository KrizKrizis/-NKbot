# auction/handlers/auction.py
# Обработчики аукциона бизнесов.

import json
import logging
from vkbottle.bot import Blueprint, Message
from db.database import db
from services.auction_service import place_bid, get_auction_businesses
from auction.keyboards.auction import get_auction_list_keyboard, get_auction_info_keyboard

logger = logging.getLogger(__name__)

bp = Blueprint("auction")


async def show_auction_menu(message: Message):
    businesses = await get_auction_businesses()
    if not businesses:
        await message.answer("На аукционе нет бизнесов.")
        return
    await message.answer("Аукционные бизнесы:", keyboard=get_auction_list_keyboard(businesses))


@bp.on.message(payload={"cmd": "open_auction"})
async def open_auction(message: Message):
    await show_auction_menu(message)


@bp.on.message(payload={"cmd": "auction_list"})
async def auction_list(message: Message):
    await show_auction_menu(message)


@bp.on.message(payload={"cmd": "auction_info"})
async def auction_info(message: Message):
    payload = message.get_payload_json()
    business_id = payload.get("business_id")
    biz = await db.fetchone("SELECT * FROM businesses WHERE business_id = ?", business_id)
    if not biz:
        await message.answer("Бизнес не найден.")
        return
    current_bid = biz["current_bid_amount"] or (2000000 if biz["type"] == "auction_casino" else 500000)
    text = f"Бизнес: {biz['name']}\nТекущая ставка: {current_bid} NK\n"
    await message.answer(text, keyboard=get_auction_info_keyboard(business_id))


@bp.on.message(payload={"cmd": "auction_bid"})
async def auction_bid(message: Message):
    payload = message.get_payload_json()
    business_id = payload.get("business_id")
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'auction_bid_amount', ?)",
        message.from_id, json.dumps({"business_id": business_id})
    )
    await message.answer("Введите сумму ставки:")


@bp.on.message()
async def handle_auction_text(message: Message):
    state_row = await db.fetchone("SELECT state, data FROM user_states WHERE user_id = ?", message.from_id)
    if not state_row or state_row["state"] != "auction_bid_amount":
        return
    text = message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await message.answer("Сумма ставки должна быть числом.")
        return
    amount = int(text)
    data = json.loads(state_row["data"])
    business_id = data.get("business_id")
    success, msg = await place_bid(message.from_id, business_id, amount)
    await message.answer(msg)
    await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
    if success:
        await auction_info(message)
    else:
        await auction_list(message)