# admin/administration/keyboards/complaints_keyboards.py
# Клавиатуры для раздела «Жалобы» администрации.

from vkbottle import Keyboard, KeyboardButtonColor, Text


def get_complaints_list_keyboard(complaints: list) -> str:
    """Клавиатура списка жалоб."""
    keyboard = Keyboard(one_time=False, inline=True)
    for c in complaints[:10]:
        keyboard.add(Text(f"#{c['id']}: {c['details'][:30]}", payload={"cmd": "admin_complaint_detail", "id": c["id"]}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "admin_main_menu"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_complaint_detail_keyboard(complaint_id: int) -> str:
    """Клавиатура для конкретной жалобы."""
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("✅ Принять", payload={"cmd": "admin_complaint_accept", "id": complaint_id}), color=KeyboardButtonColor.POSITIVE)
    keyboard.add(Text("❌ Отклонить", payload={"cmd": "admin_complaint_reject", "id": complaint_id}), color=KeyboardButtonColor.NEGATIVE)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "admin_complaints"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()