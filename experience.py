# player/handlers/experience.py
# Кнопка "Опыт" в главном меню: просмотр и получение бонусного опыта раз в час.

import logging
import random
from datetime import datetime, timezone
from vkbottle.bot import Blueprint, Message
from db.database import db
from player.keyboards.main_menu import get_experience_keyboard

logger = logging.getLogger(__name__)

bp = Blueprint("player_experience")


def _parse_datetime(dt_str: str):
    """Преобразует строку из SQLite в datetime."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return None


@bp.on.message(payload={"cmd": "open_experience"})
async def open_experience(message: Message):
    user = await db.fetchone("SELECT level, exp, last_exp_bonus_time FROM users WHERE vk_id = ?", message.from_id)
    if not user:
        return

    level = user["level"]
    exp = user["exp"]
    last_bonus_str = user["last_exp_bonus_time"]
    exp_to_next = 5 * level
    progress = int((exp / exp_to_next) * 100) if exp_to_next > 0 else 100

    now = datetime.now(timezone.utc)
    can_claim = False
    if last_bonus_str:
        last_bonus = _parse_datetime(last_bonus_str)
        if last_bonus and (now - last_bonus).total_seconds() >= 3600:
            can_claim = True
    else:
        can_claim = True

    text = (
        f"📈 Уровень: {level}\n"
        f"Опыт: {exp} / {exp_to_next}\n"
        f"Прогресс до следующего уровня: {progress}%\n\n"
        "Бонусный опыт доступен раз в час."
    )
    await message.answer(text, keyboard=get_experience_keyboard(can_claim))


@bp.on.message(payload={"cmd": "claim_exp"})
async def claim_exp(message: Message):
    user = await db.fetchone("SELECT level, exp, last_exp_bonus_time FROM users WHERE vk_id = ?", message.from_id)
    if not user:
        return

    level = user["level"]
    exp = user["exp"]
    last_bonus_str = user["last_exp_bonus_time"]

    now = datetime.now(timezone.utc)
    can_claim = False
    if last_bonus_str:
        last_bonus = _parse_datetime(last_bonus_str)
        if last_bonus and (now - last_bonus).total_seconds() >= 3600:
            can_claim = True
    else:
        can_claim = True

    if not can_claim:
        await message.answer("⏳ Бонусный опыт ещё не готов. Попробуйте позже.")
        return

    gained_exp = random.randint(100, 500)
    new_exp = exp + gained_exp
    new_level = level
    leveled_up = False
    while new_exp >= 5 * new_level:
        new_exp -= 5 * new_level
        new_level += 1
        leveled_up = True

    await db.execute(
        "UPDATE users SET exp = ?, level = ?, last_exp_bonus_time = ? WHERE vk_id = ?",
        new_exp, new_level, now.isoformat(), message.from_id
    )

    text = f"🎁 Вы получили {gained_exp} опыта."
    if leveled_up:
        text += f"\n🎉 Поздравляем! Ваш уровень повышен до {new_level}!"

    await message.answer(text)


@bp.on.message(payload={"cmd": "noop"})
async def noop(message: Message):
    pass