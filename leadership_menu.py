# admin/project_leadership/keyboards/leadership_menu.py
# Клавиатуры для руководства проекта.

from vkbottle import Keyboard, KeyboardButtonColor, Text


def get_founder_main_keyboard() -> str:
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("👤 Игрок / Проект", payload={"cmd": "founder_players"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("👥 Команда проекта", payload={"cmd": "founder_team"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("💼 Бизнес основателя", payload={"cmd": "founder_business_accounts"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("🚪 Выход", payload={"cmd": "admin_logout"}), color=KeyboardButtonColor.NEGATIVE)
    return keyboard.get_json()


def get_players_menu_keyboard() -> str:
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.row()
    keyboard.add(Text("⬅️", payload={"cmd": "players_page", "page": 1}), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("📊 Статистика", payload={"cmd": "player_stats_request"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("➡️", payload={"cmd": "players_page", "page": 1}), color=KeyboardButtonColor.SECONDARY)
    keyboard.row()
    keyboard.add(Text("📋 Логи", payload={"cmd": "player_logs_request"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("🔍 Поиск", payload={"cmd": "player_search_request"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("⚙️ Управление", payload={"cmd": "player_manage_request"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("🔙 Назад", payload={"cmd": "founder_main"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_project_menu_keyboard() -> str:
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("📦 Бэкап", payload={"cmd": "system_backup"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("📋 Логи", payload={"cmd": "system_logs"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("🎁 Промокоды", payload={"cmd": "project_promocodes"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("⚙️ Настройка", payload={"cmd": "project_settings"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("💬 Чаты", payload={"cmd": "system_chats"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("📊 Статистика проекта", payload={"cmd": "project_statistics"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "founder_main"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_team_menu_keyboard() -> str:
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("⚙️ Управление", payload={"cmd": "team_management"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("🎁 Вознаграждения", payload={"cmd": "team_rewards"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("📊 Статистика", payload={"cmd": "team_statistics"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "founder_main"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_business_accounts_keyboard() -> str:
    keyboard = Keyboard(one_time=False, inline=True)
    # Кнопки для шести счетов (по 3 в ряд)
    accounts = [
        ("1", "emission_account"),
        ("2", "commission_account"),
        ("3", "lottery_account"),
        ("4", "investment_account"),
        ("5", "giveaways_account"),
        ("6", "salary_account"),
    ]
    for i, (num, cmd) in enumerate(accounts):
        if i % 3 == 0:
            keyboard.row()
        keyboard.add(Text(num, payload={"cmd": f"business_account_{cmd}"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "founder_main"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()