# admin/project_leadership/keyboards/project_keyboards.py
# Клавиатуры для управления проектом (руководство).

from vkbottle import Keyboard, KeyboardButtonColor, Text


def get_project_settings_keyboard() -> str:
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("Цены бизнесов", payload={"cmd": "project_setting_category", "category": "business_prices"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Цены жилья", payload={"cmd": "project_setting_category", "category": "housing_prices"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Цены транспорта", payload={"cmd": "project_setting_category", "category": "vehicle_prices"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Комиссии банков", payload={"cmd": "project_setting_category", "category": "bank_commission"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Зарплаты работ", payload={"cmd": "project_setting_category", "category": "work_salaries"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Налоговые ставки", payload={"cmd": "project_setting_category", "category": "tax_rates"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Лимиты", payload={"cmd": "project_setting_category", "category": "limits"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Проценты специальных доходов", payload={"cmd": "project_setting_category", "category": "special_income_percents"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "founder_project"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()