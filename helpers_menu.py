# admin/helpers/keyboards/helpers_menu.py
# Клавиатуры для хелперов (категория 1).

from vkbottle import Keyboard, KeyboardButtonColor, Text


def get_helpers_main_keyboard() -> str:
    """Главное меню хелпера."""
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("👥 Игроки", payload={"cmd": "helpers_players"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("📬 Обращения", payload={"cmd": "helpers_requests"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("📊 Моя статистика", payload={"cmd": "helpers_stats"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🔙 Выйти", payload={"cmd": "admin_logout"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_helpers_players_keyboard() -> str:
    """Клавиатура возврата к списку игроков."""
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("🔙 Назад", payload={"cmd": "helpers_main"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()