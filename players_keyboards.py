# admin/project_leadership/keyboards/players_keyboards.py
# Клавиатуры для управления игроками (руководство).

from vkbottle import Keyboard, KeyboardButtonColor, Text


def get_players_page_keyboard(page: int, total_pages: int) -> str:
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.row()
    left_color = KeyboardButtonColor.SECONDARY if page == 1 else KeyboardButtonColor.PRIMARY
    right_color = KeyboardButtonColor.SECONDARY if page >= total_pages else KeyboardButtonColor.POSITIVE
    keyboard.add(Text("⬅️", payload={"cmd": "players_page", "page": page - 1 if page > 1 else 1}), color=left_color)
    keyboard.add(Text("📊 Статистика", payload={"cmd": "player_stats_request"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("➡️", payload={"cmd": "players_page", "page": page + 1 if page < total_pages else page}), color=right_color)
    keyboard.row()
    keyboard.add(Text("📋 Логи", payload={"cmd": "player_logs_request"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("🔍 Поиск", payload={"cmd": "player_search_request"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("⚙️ Управление", payload={"cmd": "player_manage_request"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("🔙 Назад", payload={"cmd": "founder_main"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_player_manage_keyboard(target_id: int) -> str:
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("Заморозить", payload={"cmd": "manage_freeze", "target_id": target_id}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Точечная блокировка", payload={"cmd": "manage_target_block", "target_id": target_id}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Полный бан", payload={"cmd": "manage_full_ban", "target_id": target_id}), color=KeyboardButtonColor.NEGATIVE)
    keyboard.add(Text("Разблокировать", payload={"cmd": "manage_unblock", "target_id": target_id}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Выдать деньги", payload={"cmd": "manage_give_money", "target_id": target_id}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Изъять деньги", payload={"cmd": "manage_take_money", "target_id": target_id}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Выдать предмет", payload={"cmd": "manage_give_item", "target_id": target_id}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Изъять предмет", payload={"cmd": "manage_take_item", "target_id": target_id}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "founder_players"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()