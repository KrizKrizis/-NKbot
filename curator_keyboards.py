# admin/spec_administration/keyboards/curator_keyboards.py
# Клавиатуры куратора.

from vkbottle import Keyboard, KeyboardButtonColor, Text


def get_curator_menu_keyboard() -> str:
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("👤 Игроки", payload={"cmd": "spec_players"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("👥 Команда", payload={"cmd": "spec_team"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("📊 Статистика", payload={"cmd": "spec_statistics"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("📋 Аудит", payload={"cmd": "spec_audit"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "admin_main_menu"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()