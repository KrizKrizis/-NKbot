# player/keyboards/inventory.py
# Клавиатура для инвентаря.

from vkbottle import Keyboard, KeyboardButtonColor, Text


def get_inventory_keyboard() -> str:
    """Клавиатура с кнопкой возврата в меню города."""
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("🔙 Назад", payload={"cmd": "back_to_city_menu"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()