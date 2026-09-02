# lottery/handlers/lottery.py
# Обработчики лотереи: покупка билетов, просмотр своих билетов.
# Функция process_finished_draws вызывается планировщиком для розыгрыша.

import logging
import random
from datetime import datetime, timezone, timedelta
from vkbottle.bot import Blueprint, Message
from db.database import db
from lottery.keyboards.lottery import (
    get_lottery_main_keyboard,
    get_lottery_result_keyboard,
)

logger = logging.getLogger(__name__)

bp = Blueprint("lottery")

TICKET_PRICE = 1500
DRAW_HOURS = list(range(10, 23))  # 10:00, 11:00, ..., 22:00 (13 тиражей)


def get_moscow_now() -> datetime:
    """Возвращает текущее время в Москве (UTC+3)."""
    return datetime.now(timezone.utc) + timedelta(hours=3)


def get_lottery_status() -> tuple:
    """
    Определяет текущий статус лотереи.
    Возвращает: текст статуса, можно ли купить билет сейчас, доп. информацию.
    """
    now = get_moscow_now()
    current_hour = now.hour
    current_minute = now.minute

    # Продажа на розыгрыш H:00 открыта с H-1:00 до H-1:58
    for draw_hour in DRAW_HOURS:
        sale_start_hour = draw_hour - 1
        if current_hour == sale_start_hour and current_minute < 59:
            remaining_minutes = 59 - current_minute
            if remaining_minutes == 0:
                remaining_minutes = 1
            time_to_draw = f"1 ч {remaining_minutes:02d} мин"
            status_text = f"Идёт продажа билетов на розыгрыш в {draw_hour:02d}:00.\nИтоги будут через {time_to_draw}.\nСтоимость билета: {TICKET_PRICE} NK."
            return status_text, True, {}

    # Минута 59 — подведение итогов
    if current_minute == 59:
        if current_hour == 22:
            status_text = "Подводятся итоги последнего розыгрыша дня. Следующая продажа откроется завтра в 09:00."
        elif 9 <= current_hour < 22:
            next_draw = current_hour + 1
            status_text = f"Подводятся итоги розыгрыша. Продажа на розыгрыш {next_draw:02d}:00 начнётся в {next_draw-1:02d}:00."
        else:
            status_text = "В данный момент покупка билетов невозможна."
        return status_text, False, {}

    # Вне периода продаж
    if current_hour < 9:
        status_text = "В данный момент купить билет невозможно. Продажа начнётся в 09:00 (на розыгрыш в 10:00)."
    elif current_hour >= 23:
        status_text = "В данный момент купить билет невозможно. Следующая продажа завтра в 09:00."
    elif current_hour == 9 and current_minute >= 59:
        status_text = "В данный момент купить билет невозможно. Продажа начнётся в 09:00 (на розыгрыш в 10:00)."
    elif current_hour == 22:
        status_text = "В данный момент купить билет невозможно. Следующая продажа завтра в 09:00."
    else:
        status_text = "В данный момент купить билет невозможно."
    return status_text, False, {}


async def show_lottery_menu(message: Message):
    """Показывает меню лотереи с актуальным статусом."""
    status_text, can_buy, _ = get_lottery_status()
    keyboard = get_lottery_main_keyboard(can_buy)
    await message.answer(status_text, keyboard=keyboard)


async def _ensure_draw_for_current_hour():
    """Определяет тираж, на который можно купить билет в текущий момент."""
    now = get_moscow_now()
    if now.minute < 59:
        draw_hour = now.hour + 1
    else:
        return None

    if draw_hour not in DRAW_HOURS:
        return None

    draw_time = now.replace(hour=draw_hour, minute=0, second=0, microsecond=0)
    draw_time_str = draw_time.isoformat()

    row = await db.fetchone(
        "SELECT id FROM lottery_draws WHERE draw_time = ?",
        draw_time_str
    )
    if row:
        return row["id"]

    await db.execute(
        "INSERT INTO lottery_draws (draw_time, total_pool, status) VALUES (?, 0, 'pending')",
        draw_time_str
    )
    new_row = await db.fetchone(
        "SELECT id FROM lottery_draws WHERE draw_time = ?",
        draw_time_str
    )
    return new_row["id"] if new_row else None


async def process_finished_draws():
    """Разыгрывает все завершённые тиражи (вызывается планировщиком каждый час)."""
    now = get_moscow_now()
    current_hour_start = now.replace(minute=0, second=0, microsecond=0)

    rows = await db.fetchall(
        "SELECT id FROM lottery_draws WHERE status = 'pending'"
    )
    for row in rows:
        draw = await db.fetchone(
            "SELECT draw_time FROM lottery_draws WHERE id = ?",
            row["id"]
        )
        if not draw:
            continue
        draw_time = datetime.fromisoformat(draw["draw_time"])
        if draw_time < current_hour_start:
            await _perform_draw(row["id"])


async def _perform_draw(draw_id: int):
    """Проводит розыгрыш конкретного тиража."""
    draw = await db.fetchone(
        "SELECT total_pool, status FROM lottery_draws WHERE id = ?",
        draw_id
    )
    if not draw or draw["status"] != "pending":
        return

    tickets = await db.fetchall(
        "SELECT user_id, COUNT(*) as cnt FROM lottery_tickets WHERE draw_id = ? GROUP BY user_id",
        draw_id
    )

    if len(tickets) < 3:
        for t in tickets:
            refund = t["cnt"] * TICKET_PRICE
            await db.execute(
                "UPDATE users SET bank_checking = bank_checking + ? WHERE vk_id = ?",
                refund, t["user_id"]
            )
        await db.execute(
            "UPDATE lottery_draws SET status = 'cancelled' WHERE id = ?",
            draw_id
        )
        return

    total_pool = sum(t["cnt"] for t in tickets) * TICKET_PRICE
    winners = random.sample([t["user_id"] for t in tickets], k=min(3, len(tickets)))
    prize1 = int(total_pool * 0.5)
    prize2 = int(total_pool * 0.3)
    prize3 = int(total_pool * 0.2)

    if len(winners) >= 1:
        await db.execute(
            "UPDATE users SET bank_checking = bank_checking + ? WHERE vk_id = ?",
            prize1, winners[0]
        )
    if len(winners) >= 2:
        await db.execute(
            "UPDATE users SET bank_checking = bank_checking + ? WHERE vk_id = ?",
            prize2, winners[1]
        )
    if len(winners) >= 3:
        await db.execute(
            "UPDATE users SET bank_checking = bank_checking + ? WHERE vk_id = ?",
            prize3, winners[2]
        )

    await db.execute(
        "UPDATE lottery_draws SET status = 'finished', total_pool = ?, winners = ? WHERE id = ?",
        total_pool, str(winners), draw_id
    )


@bp.on.message(payload={"cmd": "open_lottery"})
async def open_lottery(message: Message):
    await show_lottery_menu(message)


@bp.on.message(payload={"cmd": "lottery_main"})
async def lottery_main(message: Message):
    await show_lottery_menu(message)


@bp.on.message(payload={"cmd": "lottery_buy_ticket"})
async def lottery_buy_ticket(message: Message):
    _, can_buy, _ = get_lottery_status()
    if not can_buy:
        await message.answer("В данный момент покупка билетов невозможна.")
        await show_lottery_menu(message)
        return

    user_id = message.from_id
    draw_id = await _ensure_draw_for_current_hour()
    if draw_id is None:
        await message.answer("Не удалось определить текущий тираж. Попробуйте позже.")
        return

    user = await db.fetchone("SELECT bank_checking FROM users WHERE vk_id = ?", user_id)
    if user["bank_checking"] < TICKET_PRICE:
        await message.answer("Недостаточно средств на основном счёте.")
        return

    await db.execute(
        "UPDATE users SET bank_checking = bank_checking - ? WHERE vk_id = ?",
        TICKET_PRICE, user_id
    )
    await db.execute(
        "INSERT INTO lottery_tickets (user_id, draw_id, ticket_count) VALUES (?, ?, 1)",
        user_id, draw_id
    )
    await db.execute(
        "UPDATE lottery_draws SET total_pool = total_pool + ? WHERE id = ?",
        TICKET_PRICE, draw_id
    )

    await message.answer(
        f"Вы купили билет за {TICKET_PRICE} NK. Удачи!",
        keyboard=get_lottery_result_keyboard()
    )


@bp.on.message(payload={"cmd": "lottery_my_tickets"})
async def lottery_my_tickets(message: Message):
    tickets = await db.fetchall(
        """
        SELECT d.draw_time, COUNT(t.id) as cnt
        FROM lottery_tickets t
        JOIN lottery_draws d ON t.draw_id = d.id
        WHERE t.user_id = ? AND d.status = 'pending'
        GROUP BY d.draw_time
        """,
        message.from_id
    )
    if not tickets:
        await message.answer("У вас нет активных билетов.")
        return

    lines = ["Ваши билеты:"]
    for t in tickets:
        lines.append(f"• {t['draw_time']} — {t['cnt']} шт.")
    await message.answer("\n".join(lines), keyboard=get_lottery_result_keyboard())


@bp.on.message(payload={"cmd": "noop"})
async def noop(message: Message):
    """Обработчик неактивной кнопки — ничего не делает."""
    pass