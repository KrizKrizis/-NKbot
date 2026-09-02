# admin/project_leadership/keyboards/team_keyboards.py
# Клавиатуры для управления командой (руководство).

from vkbottle import Keyboard, KeyboardButtonColor, Text


def get_team_management_keyboard() -> str:
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("Назначить роль", payload={"cmd": "team_assign_role"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Снять роль", payload={"cmd": "team_remove_role"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Повысить/Понизить", payload={"cmd": "team_promote"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Выдать выговор", payload={"cmd": "team_warning"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "founder_team"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_team_rewards_keyboard() -> str:
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("Начислить админ-койны", payload={"cmd": "team_rewards"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "founder_team"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()