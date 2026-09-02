# admin/project_leadership/keyboards/roles_keyboards.py
# Клавиатуры для управления ролями (только назначение/снятие).

from vkbottle import Keyboard, KeyboardButtonColor, Text


def get_roles_menu_keyboard() -> str:
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("Назначить роль", payload={"cmd": "team_assign_role"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Снять роль", payload={"cmd": "team_remove_role"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "founder_main"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()