# admin/spec_administration/keyboards/tester_keyboards.py
# Клавиатуры тестировщика.

from vkbottle import Keyboard, KeyboardButtonColor, Text


def get_tester_menu_keyboard() -> str:
    """Клавиатура тест-панели тестировщика."""
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("⚒ Тестовый крафт", payload={"cmd": "test_craft"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("💰 Тестовый баланс", payload={"cmd": "test_balance"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("📈 Тестовый уровень", payload={"cmd": "test_level"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("🚀 Тест работы", payload={"cmd": "test_work"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("🏠 Тест недвижимости", payload={"cmd": "test_housing"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("🚗 Тест транспорта", payload={"cmd": "test_transport"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("📋 Логи ошибок", payload={"cmd": "test_logs"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("🔄 Сбросить тестовые данные", payload={"cmd": "test_reset"}), color=KeyboardButtonColor.NEGATIVE)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "admin_main_menu"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()