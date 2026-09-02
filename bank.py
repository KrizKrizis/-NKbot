# bank/handlers/bank.py
# Обработчики банковских операций.

import json
from vkbottle.bot import Blueprint, Message
from db.database import db
from services.bank_service import (
    get_commission_rate,
    transfer_between_users,
    transfer_between_own_accounts,
    apply_savings_interest,
)
from bank.keyboards.bank import (
    get_bank_main_keyboard,
    get_bank_selection_keyboard,
    get_balance_keyboard,
    get_transfer_menu_keyboard,
    get_account_selection_keyboard,
    get_savings_keyboard,
    get_tax_keyboard,
)

bp = Blueprint("bank")


async def show_bank_menu(message: Message):
    """Показывает главное меню банка."""
    user = await db.fetchone("SELECT bank_name FROM users WHERE vk_id = ?", message.from_id)
    has_bank = user["bank_name"] is not None if user else False
    await apply_savings_interest(message.from_id)
    await message.answer("🏦 Банк", keyboard=get_bank_main_keyboard(has_bank))


@bp.on.message(payload={"cmd": "open_bank"})
async def open_bank(message: Message):
    await show_bank_menu(message)


@bp.on.message(payload={"cmd": "bank_main"})
async def bank_main(message: Message):
    await show_bank_menu(message)


@bp.on.message(payload={"cmd": "bank_select"})
async def bank_select(message: Message):
    await message.answer("Выберите банк из списка:", keyboard=get_bank_selection_keyboard())


@bp.on.message(payload={"cmd": "bank_choose"})
async def bank_choose(message: Message):
    payload = message.get_payload_json()
    bank_name = payload.get("bank")
    if bank_name not in ["NK Bank", "Zero Bank", "Fallen Bank"]:
        await message.answer("Ошибка выбора банка.")
        return

    await db.execute(
        "UPDATE users SET bank_name = ? WHERE vk_id = ?",
        bank_name, message.from_id
    )
    await message.answer(f"Вы выбрали банк: {bank_name}")
    await show_bank_menu(message)


@bp.on.message(payload={"cmd": "bank_balance"})
async def bank_balance(message: Message):
    await apply_savings_interest(message.from_id)
    user = await db.fetchone(
        "SELECT balance, bank_checking, bank_savings, tax_account, bank_name FROM users WHERE vk_id = ?",
        message.from_id
    )
    text = (
        f"💰 Баланс\n"
        f"💵 Наличные: {user['balance']} NK\n"
        f"🏦 Банк: {user['bank_name']}\n"
        f"💳 Основной счёт: {user['bank_checking']} NK\n"
        f"📈 Накопительный: {user['bank_savings']} NK (лимит 750 000)\n"
        f"🧾 Налоговый: {user['tax_account']} NK"
    )
    await message.answer(text, keyboard=get_balance_keyboard())


@bp.on.message(payload={"cmd": "bank_transfer_menu"})
async def bank_transfer_menu(message: Message):
    await message.answer("Переводы:", keyboard=get_transfer_menu_keyboard())


@bp.on.message(payload={"cmd": "bank_transfer_user"})
async def bank_transfer_user(message: Message):
    # Устанавливаем состояние ожидания ID получателя
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'awaiting_receiver_id', '{}')",
        message.from_id
    )
    await message.answer("Введите ID игрока, которому хотите перевести средства:")


@bp.on.message(payload={"cmd": "bank_transfer_own"})
async def bank_transfer_own(message: Message):
    await message.answer("Выберите счёт, с которого хотите перевести:", keyboard=get_account_selection_keyboard())


@bp.on.message(payload={"cmd": "bank_select_account"})
async def bank_select_account(message: Message):
    payload = message.get_payload_json()
    account = payload.get("account")

    state_row = await db.fetchone("SELECT state, data FROM user_states WHERE user_id = ?", message.from_id)

    if state_row is None:
        # Первый выбор: счёт-источник
        await db.execute(
            "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'awaiting_to_account', ?)",
            message.from_id, json.dumps({"from_account": account})
        )
        await message.answer("Теперь выберите счёт назначения:", keyboard=get_account_selection_keyboard())
    else:
        state = state_row["state"]
        if state == "awaiting_to_account":
            data = json.loads(state_row["data"])
            from_account = data.get("from_account")
            to_account = account
            await db.execute(
                "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'awaiting_amount_own', ?)",
                message.from_id, json.dumps({"from_account": from_account, "to_account": to_account})
            )
            await message.answer("Введите сумму для перевода:")
        else:
            await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
            await message.answer("Ошибка. Начните заново.")


@bp.on.message()
async def handle_bank_text(message: Message):
    """Обрабатывает текстовые сообщения для FSM переводов."""
    state_row = await db.fetchone("SELECT state, data FROM user_states WHERE user_id = ?", message.from_id)
    if not state_row:
        return

    state = state_row["state"]
    data = json.loads(state_row["data"])
    text = message.text.strip()

    if state == "awaiting_receiver_id":
        if not text.isdigit():
            await message.answer("ID должен быть числом.")
            return
        receiver_id = int(text)
        await db.execute(
            "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'awaiting_amount_user', ?)",
            message.from_id, json.dumps({"receiver_id": receiver_id})
        )
        await message.answer("Введите сумму для перевода:")

    elif state == "awaiting_amount_user":
        if not text.isdigit() or int(text) <= 0:
            await message.answer("Сумма должна быть положительным числом.")
            return
        amount = int(text)
        receiver_id = data.get("receiver_id")
        success, msg = await transfer_between_users(message.from_id, receiver_id, amount)
        await message.answer(msg)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        if success:
            await show_bank_menu(message)

    elif state == "awaiting_amount_own":
        if not text.isdigit() or int(text) <= 0:
            await message.answer("Сумма должна быть положительным числом.")
            return
        amount = int(text)
        from_account = data.get("from_account")
        to_account = data.get("to_account")
        success, msg = await transfer_between_own_accounts(message.from_id, from_account, to_account, amount)
        await message.answer(msg)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        if success:
            await show_bank_menu(message)

    else:
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)


@bp.on.message(payload={"cmd": "bank_savings"})
async def bank_savings(message: Message):
    await apply_savings_interest(message.from_id)
    user = await db.fetchone("SELECT bank_savings FROM users WHERE vk_id = ?", message.from_id)
    await message.answer(
        f"📈 Накопительный счёт: {user['bank_savings']} NK\n"
        f"Проценты начисляются раз в час (1%).",
        keyboard=get_savings_keyboard()
    )


@bp.on.message(payload={"cmd": "bank_tax"})
async def bank_tax(message: Message):
    user = await db.fetchone("SELECT tax_account FROM users WHERE vk_id = ?", message.from_id)
    await message.answer(
        f"🧾 Налоговый счёт: {user['tax_account']} NK",
        keyboard=get_tax_keyboard()
    )