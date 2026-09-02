# admin/helpers/handlers/helpers.py
# Обработчики для хелперов (категория 1).

import logging
from vkbottle.bot import Blueprint, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text
from db.database import db
from admin.player_management import format_player_list_page, get_total_pages, get_player_profile
from admin.helpers.keyboards.helpers_menu import (
    get_helpers_main_keyboard,
    get_helpers_players_keyboard,
)

logger = logging.getLogger(__name__)

bp = Blueprint("helpers")


async def show_helpers_menu(message: Message):
    """Показывает главное меню хелпера."""
    await message.answer("🛠 Меню хелпера", keyboard=get_helpers_main_keyboard())


@bp.on.message(payload={"cmd": "helpers_main"})
async def helpers_main(message: Message):
    await show_helpers_menu(message)


@bp.on.message(payload={"cmd": "helpers_players"})
async def helpers_players(message: Message):
    # Хелпер видит только базовый список игроков (первая страница)
    text, _ = await format_player_list_page(1)
    total_pages = await get_total_pages()
    keyboard_obj = Keyboard(one_time=False, inline=True)
    keyboard_obj.row()
    left_color = KeyboardButtonColor.SECONDARY
    right_color = KeyboardButtonColor.SECONDARY if total_pages <= 1 else KeyboardButtonColor.POSITIVE
    keyboard_obj.add(Text("⬅️", payload={"cmd": "helpers_players_page", "page": 1}), color=left_color)
    keyboard_obj.add(Text("📊 Статистика", payload={"cmd": "helpers_player_stats"}), color=KeyboardButtonColor.PRIMARY)
    keyboard_obj.add(Text("➡️", payload={"cmd": "helpers_players_page", "page": 2 if total_pages > 1 else 1}), color=right_color)
    keyboard_obj.row()
    keyboard_obj.add(Text("🔙 Назад", payload={"cmd": "helpers_main"}), color=KeyboardButtonColor.SECONDARY)
    await message.answer(text, keyboard=keyboard_obj.get_json())


@bp.on.message(payload={"cmd": "helpers_players_page"})
async def helpers_players_page(message: Message):
    payload = message.get_payload_json()
    page = int(payload.get("page", 1))
    text, _ = await format_player_list_page(page)
    total_pages = await get_total_pages()
    keyboard_obj = Keyboard(one_time=False, inline=True)
    keyboard_obj.row()
    left_color = KeyboardButtonColor.SECONDARY if page <= 1 else KeyboardButtonColor.PRIMARY
    right_color = KeyboardButtonColor.SECONDARY if page >= total_pages else KeyboardButtonColor.POSITIVE
    keyboard_obj.add(Text("⬅️", payload={"cmd": "helpers_players_page", "page": page - 1 if page > 1 else 1}), color=left_color)
    keyboard_obj.add(Text("📊 Статистика", payload={"cmd": "helpers_player_stats"}), color=KeyboardButtonColor.PRIMARY)
    keyboard_obj.add(Text("➡️", payload={"cmd": "helpers_players_page", "page": page + 1 if page < total_pages else page}), color=right_color)
    keyboard_obj.row()
    keyboard_obj.add(Text("🔙 Назад", payload={"cmd": "helpers_main"}), color=KeyboardButtonColor.SECONDARY)
    await message.answer(text, keyboard=keyboard_obj.get_json())


@bp.on.message(payload={"cmd": "helpers_player_stats"})
async def helpers_player_stats(message: Message):
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'helpers_stats_id_input', '{}')",
        message.from_id
    )
    await message.answer("Введите игровой ID игрока для просмотра статистики:")


@bp.on.message(payload={"cmd": "helpers_requests"})
async def helpers_requests(message: Message):
    # В будущем здесь будет список обращений, пока просто заглушка
    await message.answer("📬 Обращений пока нет.")


@bp.on.message(payload={"cmd": "helpers_stats"})
async def helpers_stats(message: Message):
    # Показываем количество обработанных обращений (заглушка)
    await message.answer("📊 Ваша статистика за сегодня: 0 обращений.")


# Обработчик текстового ввода ID для статистики
@bp.on.message()
async def handle_helpers_text(message: Message):
    state_row = await db.fetchone("SELECT state, data FROM user_states WHERE user_id = ?", message.from_id)
    if not state_row:
        return
    state = state_row["state"]
    if state == "helpers_stats_id_input":
        text = message.text.strip()
        if not text.isdigit():
            await message.answer("ID должен быть числом.")
            return
        game_id = int(text)
        user = await db.fetchone("SELECT vk_id FROM users WHERE game_id = ?", game_id)
        if not user:
            await message.answer("Игрок не найден.")
            await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
            return
        profile = await get_player_profile(user["vk_id"], message.from_id)
        await message.answer(profile)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
    else:
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)