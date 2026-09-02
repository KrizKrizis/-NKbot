# admin/spec_administration/keyboards/spec_admin_menu.py
# Клавиатура главного меню спец-администрации.

from vkbottle import Keyboard, KeyboardButtonColor, Text


def get_spec_admin_main_keyboard(user_id: int, permissions: dict) -> str:
    """Главное меню спец-администрации с учётом роли."""
    keyboard = Keyboard(one_time=False, inline=True)

    if permissions.get("players.view", False):
        keyboard.add(Text("👤 Игроки", payload={"cmd": "spec_players"}), color=KeyboardButtonColor.PRIMARY)

    if permissions.get("team.view", False):
        keyboard.add(Text("👥 Команда", payload={"cmd": "spec_team"}), color=KeyboardButtonColor.PRIMARY)

    if permissions.get("project.manage", False):
        keyboard.add(Text("⚙️ Проект", payload={"cmd": "spec_project"}), color=KeyboardButtonColor.PRIMARY)

    if permissions.get("test_panel", False):
        keyboard.add(Text("🛠 Тест-панель", payload={"cmd": "spec_test_panel"}), color=KeyboardButtonColor.PRIMARY)

    keyboard.row()
    keyboard.add(Text("🔙 Выйти", payload={"cmd": "admin_logout"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()