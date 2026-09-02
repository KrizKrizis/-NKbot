# casino/handlers/casino.py
# Обработчики казино.

import logging
import json
from vkbottle.bot import Blueprint, Message
from db.database import db
from services.casino_service import (
    buy_chips,
    sell_chips,
    play_dice,
    play_slots,
    play_russian_roulette,
    collect_russian_roulette_winnings,
    distribute_casino_income,
)
from services.business_service import withdraw_business_balance, pay_business_tax
from casino.keyboards.casino import (
    get_casino_main_keyboard,
    get_games_keyboard,
    get_dice_guess_keyboard,
    get_roulette_keyboard,
    get_back_to_casino_keyboard,
)

logger = logging.getLogger(__name__)

bp = Blueprint("casino")


async def is_casino_available() -> bool:
    """Проверяет, есть ли активное казино."""
    casino = await db.fetchone(
        "SELECT * FROM businesses WHERE business_id = '1.4.13' AND hidden = 0 AND owner_id IS NOT NULL"
    )
    return casino is not None


async def is_casino_owner(user_id: int) -> bool:
    """Проверяет, является ли игрок владельцем казино."""
    row = await db.fetchone(
        "SELECT id FROM businesses WHERE business_id = '1.4.13' AND owner_id = ?",
        user_id
    )
    return row is not None


async def show_casino_menu(message: Message):
    """Показывает меню казино."""
    # Проверяем город
    user = await db.fetchone("SELECT current_city FROM users WHERE vk_id = ?", message.from_id)
    if user["current_city"] != "Мемград":
        await message.answer("Казино доступно только в Мемграде.")
        return

    # Проверяем наличие казино
    if not await is_casino_available():
        await message.answer("Казино закрыто.")
        return

    is_owner = await is_casino_owner(message.from_id)
    keyboard = get_casino_main_keyboard(is_owner)
    await message.answer("🎰 Казино", keyboard=keyboard)


@bp.on.message(payload={"cmd": "open_casino"})
async def open_casino(message: Message):
    await show_casino_menu(message)


@bp.on.message(payload={"cmd": "casino_main"})
async def casino_main(message: Message):
    await show_casino_menu(message)


@bp.on.message(payload={"cmd": "casino_buy_chips"})
async def casino_buy_chips(message: Message):
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'casino_buy_chips_amount', '{}')",
        message.from_id
    )
    await message.answer("Введите сумму в NK для покупки фишек (1 фишка = 100 NK):")


@bp.on.message(payload={"cmd": "casino_sell_chips"})
async def casino_sell_chips(message: Message):
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'casino_sell_chips_amount', '{}')",
        message.from_id
    )
    await message.answer("Введите количество фишек для продажи (1 фишка = 90 NK):")


@bp.on.message(payload={"cmd": "casino_games"})
async def casino_games(message: Message):
    await message.answer("Выберите игру:", keyboard=get_games_keyboard())


# --- Игра в кости ---

@bp.on.message(payload={"cmd": "casino_dice_start"})
async def casino_dice_start(message: Message):
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'casino_dice_bet', '{}')",
        message.from_id
    )
    await message.answer("Введите ставку в фишках:")


@bp.on.message(payload={"cmd": "casino_dice_guess"})
async def casino_dice_guess(message: Message):
    payload = message.get_payload_json()
    guess = payload.get("guess")
    # Получаем ставку из состояния
    state_row = await db.fetchone("SELECT data FROM user_states WHERE user_id = ? AND state = 'casino_dice_bet'", message.from_id)
    if not state_row:
        await message.answer("Ошибка. Начните игру заново.")
        await casino_games(message)
        return
    data = json.loads(state_row["data"])
    bet = int(data.get("bet", 0))
    success, msg, _ = await play_dice(message.from_id, bet, guess)
    await message.answer(msg)
    await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
    await casino_main(message)


@bp.on.message(payload={"cmd": "casino_dice_exact"})
async def casino_dice_exact(message: Message):
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'casino_dice_exact_number', '{}')",
        message.from_id
    )
    await message.answer("Введите число от 2 до 12:")


# --- Слоты ---

@bp.on.message(payload={"cmd": "casino_slots_start"})
async def casino_slots_start(message: Message):
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'casino_slots_bet', '{}')",
        message.from_id
    )
    await message.answer("Введите ставку в фишках:")


# --- Русская рулетка ---

@bp.on.message(payload={"cmd": "casino_roulette_start"})
async def casino_roulette_start(message: Message):
    # Проверяем, есть ли активная серия
    state_row = await db.fetchone("SELECT data FROM user_states WHERE user_id = ? AND state = 'roulette'", message.from_id)
    if state_row:
        data = json.loads(state_row["data"])
        current_pot = data.get("current_pot", 0)
        await message.answer(f"У вас уже есть активная серия. Текущий банк: {current_pot}", keyboard=get_roulette_keyboard(current_pot))
        return
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'casino_roulette_bet', '{}')",
        message.from_id
    )
    await message.answer("Введите ставку в фишках:")


@bp.on.message(payload={"cmd": "casino_roulette_shot"})
async def casino_roulette_shot(message: Message):
    # Берём ставку из состояния, если серия уже идёт, то ставку не спрашиваем
    state_row = await db.fetchone("SELECT state, data FROM user_states WHERE user_id = ?", message.from_id)
    if not state_row:
        await message.answer("Нет активной игры.")
        return
    state = state_row["state"]
    if state == "roulette":
        # Серия уже идёт, ставка не требуется, выстрел
        data = json.loads(state_row["data"])
        # Ставка может быть 0, если серия уже была
        bet = 0
        success, msg, current_pot = await play_russian_roulette(message.from_id, bet)
        await message.answer(msg)
        if current_pot > 0:
            await message.answer("Хотите продолжить?", keyboard=get_roulette_keyboard(current_pot))
        else:
            await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
            await casino_main(message)
    elif state == "casino_roulette_bet":
        # Серия начинается, ставка сохранена в data
        data = json.loads(state_row["data"])
        bet = int(data.get("bet", 0))
        success, msg, current_pot = await play_russian_roulette(message.from_id, bet)
        await message.answer(msg)
        if current_pot > 0:
            await message.answer("Хотите продолжить?", keyboard=get_roulette_keyboard(current_pot))
        else:
            await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
            await casino_main(message)
    else:
        await message.answer("Ошибка состояния.")


@bp.on.message(payload={"cmd": "casino_roulette_collect"})
async def casino_roulette_collect(message: Message):
    success, msg, _ = await collect_russian_roulette_winnings(message.from_id)
    await message.answer(msg)
    await casino_main(message)


# --- Панель владельца ---

@bp.on.message(payload={"cmd": "casino_owner_panel"})
async def casino_owner_panel(message: Message):
    if not await is_casino_owner(message.from_id):
        await message.answer("Вы не владелец казино.")
        return
    casino = await db.fetchone("SELECT * FROM businesses WHERE business_id = '1.4.13'")
    text = (
        f"👑 Панель владельца казино\n"
        f"Баланс казино: {casino['business_balance']} NK\n"
        f"Доход от проигрыша игроков (за час): будет рассчитан при следующем распределении.\n"
        f"Налог: {casino['tax_amount']} NK (каждые 12 часов)\n"
        f"Продукты: {casino['product_cost']} NK (каждые 6 часов)\n"
    )
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("💰 Снять доход", payload={"cmd": "casino_owner_withdraw"}), color=KeyboardButtonColor.POSITIVE)
    keyboard.add(Text("🧾 Оплатить налог", payload={"cmd": "casino_owner_pay_tax"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("📉 Продать лицензию", payload={"cmd": "casino_owner_sell"}), color=KeyboardButtonColor.NEGATIVE)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "casino_main"}), color=KeyboardButtonColor.SECONDARY)
    await message.answer(text, keyboard=keyboard)


@bp.on.message(payload={"cmd": "casino_owner_withdraw"})
async def casino_owner_withdraw(message: Message):
    success = await withdraw_business_balance(message.from_id, "1.4.13")
    if success:
        await message.answer("Доход снят на основной счёт.")
    else:
        await message.answer("Не удалось снять доход (возможно, баланс 0).")
    await casino_owner_panel(message)


@bp.on.message(payload={"cmd": "casino_owner_pay_tax"})
async def casino_owner_pay_tax(message: Message):
    success = await pay_business_tax("1.4.13")
    if success:
        await message.answer("Налог оплачен со счёта казино.")
    else:
        await message.answer("Недостаточно средств на счёте казино для оплаты налога.")
    await casino_owner_panel(message)


@bp.on.message(payload={"cmd": "casino_owner_sell"})
async def casino_owner_sell(message: Message):
    # Продажа лицензии государству за 60% от стартовой цены (2 000 000)
    sell_price = int(2_000_000 * 0.6)
    # Начисляем деньги владельцу
    await db.execute(
        "UPDATE users SET balance = balance + ? WHERE vk_id = ?",
        sell_price, message.from_id
    )
    # Снимаем владельца
    await db.execute(
        "UPDATE businesses SET owner_id = NULL, business_balance = 0 WHERE business_id = '1.4.13'"
    )
    await message.answer(f"Вы продали лицензию казино за {sell_price} NK. Казино закрыто.")
    await show_casino_menu(message)


# --- Обработка текстовых сообщений ---

@bp.on.message()
async def handle_casino_text(message: Message):
    state_row = await db.fetchone("SELECT state, data FROM user_states WHERE user_id = ?", message.from_id)
    if not state_row:
        return

    state = state_row["state"]
    text = message.text.strip()
    data = json.loads(state_row["data"])

    if state == "casino_buy_chips_amount":
        if not text.isdigit() or int(text) <= 0:
            await message.answer("Введите корректную сумму в NK.")
            return
        amount = int(text)
        success, msg = await buy_chips(message.from_id, amount)
        await message.answer(msg)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        await casino_main(message)

    elif state == "casino_sell_chips_amount":
        if not text.isdigit() or int(text) <= 0:
            await message.answer("Введите корректное количество фишек.")
            return
        chips = int(text)
        success, msg = await sell_chips(message.from_id, chips)
        await message.answer(msg)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        await casino_main(message)

    elif state == "casino_dice_bet":
        if not text.isdigit() or int(text) <= 0:
            await message.answer("Ставка должна быть положительным числом.")
            return
        bet = int(text)
        await db.execute(
            "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'casino_dice_bet', ?)",
            message.from_id, json.dumps({"bet": bet})
        )
        await message.answer("Выберите тип ставки:", keyboard=get_dice_guess_keyboard())

    elif state == "casino_dice_exact_number":
        if not text.isdigit() or int(text) < 2 or int(text) > 12:
            await message.answer("Введите число от 2 до 12.")
            return
        guess = text
        # Получаем ставку
        bet_state = await db.fetchone("SELECT data FROM user_states WHERE user_id = ? AND state = 'casino_dice_bet'", message.from_id)
        if not bet_state:
            await message.answer("Ошибка. Ставка не найдена.")
            return
        bet = int(json.loads(bet_state["data"]).get("bet", 0))
        success, msg, _ = await play_dice(message.from_id, bet, guess)
        await message.answer(msg)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        await casino_main(message)

    elif state == "casino_slots_bet":
        if not text.isdigit() or int(text) <= 0:
            await message.answer("Ставка должна быть положительным числом.")
            return
        bet = int(text)
        success, msg, _ = await play_slots(message.from_id, bet)
        await message.answer(msg)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        await casino_main(message)

    elif state == "casino_roulette_bet":
        if not text.isdigit() or int(text) <= 0:
            await message.answer("Ставка должна быть положительным числом.")
            return
        bet = int(text)
        await db.execute(
            "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'casino_roulette_bet', ?)",
            message.from_id, json.dumps({"bet": bet})
        )
        success, msg, current_pot = await play_russian_roulette(message.from_id, bet)
        await message.answer(msg)
        if current_pot > 0:
            await message.answer("Продолжайте или заберите выигрыш:", keyboard=get_roulette_keyboard(current_pot))
        else:
            await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
            await casino_main(message)

    else:
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)