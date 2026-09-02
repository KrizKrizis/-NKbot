# admin/spec_administration/keyboards/deputy_keyboards.py
# Клавиатуры заместителя основателя.

from vkbottle import Keyboard, KeyboardButtonColor, Text


def get_deputy_menu_keyboard() -> str:
    """Главное меню заместителя основателя."""
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("👤 Игроки", payload={"cmd": "spec_players"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("👥 Команда", payload={"cmd": "spec_team"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("⚙️ Проект", payload={"cmd": "spec_project"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("📊 Статистика проекта", payload={"cmd": "spec_project_stats"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "admin_main_menu"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()