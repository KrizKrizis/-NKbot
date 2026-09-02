# mars/handlers/mars.py
# Обработчики инвестиций в Марс.

import json
from vkbottle.bot import Blueprint, Message
from db.database import db
from mars.keyboards.mars import (
    get_investments_keyboard,
    get_invest_back_keyboard,
)

bp = Blueprint("mars")

GLOBAL_GOAL = 1_000_000_000
PLAYER_LIMIT = 10_000_000


async def get_total_invested() -> int:
    """Возвращает общую сумму инвестиций."""
    row = await db.fetchone("SELECT COALESCE(SUM(amount), 0) as total FROM mars_investments")
    return row["total"] if row else 0


async def get_user_invested(user_id: int) -> int:
    """Возвращает сумму инвестиций конкретного игрока."""
    row = await db.fetchone(
        "SELECT COALESCE(SUM(amount), 0) as total FROM mars_investments WHERE user_id = ?",
        user_id
    )
    return row["total"] if row else 0


async def show_investments_menu(message: Message):
    """Показывает меню инвестиций."""
    total = await get_total_invested()
    user_total = await get_user_invested(message.from_id)
    progress = (total / GLOBAL_GOAL) * 100 if GLOBAL_GOAL else 0
    text = (
        f"🚀 Инвестиции в терраформирование Марса\n\n"
        f"Общий прогресс: {total:,} / {GLOBAL_GOAL:,} NK ({progress:.2f}%)\n"
        f"Ваш вклад: {user_total:,} NK\n"
        f"Лимит на игрока: {PLAYER_LIMIT:,} NK"
    )
    await message.answer(text, keyboard=get_investments_keyboard())


@bp.on.message(payload={"cmd": "open_investments"})
async def open_investments(message: Message):
    await show_investments_menu(message)


@bp.on.message(payload={"cmd": "invest_main"})
async def invest_main(message: Message):
    await show_investments_menu(message)


@bp.on.message(payload={"cmd": "invest_progress"})
async def invest_progress(message: Message):
    await show_investments_menu(message)


@bp.on.message(payload={"cmd": "invest_start"})
async def invest_start(message: Message):
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'awaiting_invest_amount', '{}')",
        message.from_id
    )
    await message.answer("Введите сумму для инвестирования (от 1 до 10 000 000 NK):")


@bp.on.message()
async def handle_invest_text(message: Message):
    state_row = await db.fetchone("SELECT state, data FROM user_states WHERE user_id = ?", message.from_id)
    if not state_row or state_row["state"] != "awaiting_invest_amount":
        return

    text = message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await message.answer("Сумма должна быть положительным целым числом.")
        return

    amount = int(text)
    user_id = message.from_id

    already = await get_user_invested(user_id)
    if already + amount > PLAYER_LIMIT:
        await message.answer(f"Вы превышаете лимит. Осталось доступно: {PLAYER_LIMIT - already} NK.")
        return

    user = await db.fetchone("SELECT bank_checking FROM users WHERE vk_id = ?", user_id)
    if user["bank_checking"] < amount:
        await message.answer("Недостаточно средств на основном счёте.")
        return

    await db.execute(
        "UPDATE users SET bank_checking = bank_checking - ? WHERE vk_id = ?",
        amount, user_id
    )
    await db.execute(
        "INSERT INTO mars_investments (user_id, amount) VALUES (?, ?)",
        user_id, amount
    )

    await db.execute("DELETE FROM user_states WHERE user_id = ?", user_id)

    total = await get_total_invested()
    await message.answer(
        f"✅ Вы инвестировали {amount:,} NK. Общий сбор: {total:,} NK.",
        keyboard=get_invest_back_keyboard()
    )

    if total >= GLOBAL_GOAL:
        await _handle_goal_reached()


async def _handle_goal_reached():
    """Выдаёт Базу на Марсе всем, кто выполнил условия."""
    investors = await db.fetchall(
        """
        SELECT user_id, SUM(amount) as total_amount
        FROM mars_investments
        GROUP BY user_id
        HAVING SUM(amount) >= 10000000
        """
    )
    for inv in investors:
        user_id = inv["user_id"]
        items = await db.fetchall(
            """
            SELECT item_id FROM inventory
            WHERE user_id = ? AND item_id IN ('4.3.10', '4.5.4', '4.5.3')
            """,
            user_id
        )
        if {row["item_id"] for row in items} == {'4.3.10', '4.5.4', '4.5.3'}:
            existing = await db.fetchone(
                "SELECT id FROM inventory WHERE user_id = ? AND item_id = '4.8.1'",
                user_id
            )
            if not existing:
                await db.execute(
                    "INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, '4.8.1', 1)",
                    user_id
                )
                await bp.api.messages.send(
                    user_id=user_id,
                    message="🎉 Поздравляем! Вы получили Базу на Марсе!",
                    random_id=0
                )