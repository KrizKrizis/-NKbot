# admin/administration/keyboards/administration_menu.py
# Клавиатура главного меню администрации.

from vkbottle import Keyboard, KeyboardButtonColor, Text


def get_administration_main_keyboard(admin_id: int, permissions: dict) -> str:
    """Главное меню администрации с учётом прав."""
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("👤 Игроки", payload={"cmd": "admin_players"}), color=KeyboardButtonColor.PRIMARY)

    if permissions.get("complaints.view", False):
        keyboard.add(Text("📋 Жалобы", payload={"cmd": "admin_complaints"}), color=KeyboardButtonColor.PRIMARY)

    if permissions.get("team.view", False):
        keyboard.add(Text("👥 Команда", payload={"cmd": "admin_team"}), color=KeyboardButtonColor.PRIMARY)

    if permissions.get("team.manage", False):
        keyboard.add(Text("📊 Статистика", payload={"cmd": "admin_statistics"}), color=KeyboardButtonColor.PRIMARY)

    keyboard.row()
    keyboard.add(Text("🔙 Выйти", payload={"cmd": "admin_logout"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()