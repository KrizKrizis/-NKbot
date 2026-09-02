# player/keyboards/main_menu.py
# Клавиатуры для главного меню, регистрации и опыта.

from typing import Optional
from vkbottle import Keyboard, KeyboardButtonColor, Text


def get_registration_keyboard(step: str) -> str:
    """Клавиатура для вводной цепочки регистрации."""
    keyboard = Keyboard(one_time=False, inline=True)
    if step == "first":
        keyboard.add(Text("Продолжить", payload={"cmd": "intro_next_1"}), color=KeyboardButtonColor.PRIMARY)
    elif step == "second":
        keyboard.add(Text("Дальше", payload={"cmd": "intro_next_2"}), color=KeyboardButtonColor.PRIMARY)
    elif step == "third":
        keyboard.add(Text("Дальше", payload={"cmd": "intro_finish"}), color=KeyboardButtonColor.PRIMARY)
    return keyboard.get_json()


def get_main_menu_keyboard(admin_category: Optional[int] = None) -> str:
    """Главное меню игрока: Обновить, Работа, Город, Банк, Опыт + админ-кнопка при наличии роли."""
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.row()
    keyboard.add(Text("🔄 Обновить", payload={"cmd": "refresh_profile"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("💼 Работа", payload={"cmd": "open_jobs"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("🏙 Город", payload={"cmd": "open_city"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🏦 Банк", payload={"cmd": "open_bank"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("📈 Опыт", payload={"cmd": "open_experience"}), color=KeyboardButtonColor.PRIMARY)

    if admin_category:
        admin_button_text = {
            1: "Мод-Пан",
            2: "Адм-Пан",
            3: "Спец-Пан",
            4: "Тех-Пан"
        }.get(admin_category, "Адм-Пан")
        keyboard.row()
        keyboard.add(Text(admin_button_text, payload={"cmd": "open_admin_panel"}), color=KeyboardButtonColor.NEGATIVE)

    return keyboard.get_json()


def get_experience_keyboard(can_claim: bool) -> str:
    """Клавиатура для раздела опыта."""
    keyboard = Keyboard(one_time=False, inline=True)
    if can_claim:
        keyboard.add(Text("Получить опыт", payload={"cmd": "claim_exp"}), color=KeyboardButtonColor.POSITIVE)
    else:
        keyboard.add(Text("Получить опыт (недоступно)", payload={"cmd": "noop"}), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("🔙 Назад", payload={"cmd": "back_to_main"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()