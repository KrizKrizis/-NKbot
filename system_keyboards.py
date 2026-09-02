# admin/project_leadership/keyboards/system_keyboards.py
# Клавиатуры для системных функций (руководство).

from vkbottle import Keyboard, KeyboardButtonColor, Text


def get_system_menu_keyboard() -> str:
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("🔄 Сбросить кеш ролей", payload={"cmd": "system_reload_cache"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("📦 Создать бэкап", payload={"cmd": "system_backup"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("📋 Логи", payload={"cmd": "system_logs"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("💬 Управление чатами", payload={"cmd": "system_chats"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("⏰ Планировщик", payload={"cmd": "system_scheduler"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("🚀 Перезагрузить конфигурацию", payload={"cmd": "system_reload_config"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "founder_main"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_chats_menu_keyboard() -> str:
    keyboard = Keyboard(one_time=False, inline=True)
    modes = {2: "Хелперы", 3: "Администрация", 4: "Статистика", 5: "Общая команда", 6: "Тестеры", 7: "Полный лог"}
    for mode, desc in modes.items():
        keyboard.add(Text(f"Режим {mode}: {desc}", payload={"cmd": "system_chat_set", "mode": mode}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "system_menu"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()