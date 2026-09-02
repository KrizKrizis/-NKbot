# housing/keyboards/housing.py
# Клавиатуры для жилья.

from vkbottle import Keyboard, KeyboardButtonColor, Text


def get_housing_main_keyboard(user_housing: dict) -> str:
    """Главное меню жилья."""
    keyboard = Keyboard(one_time=False, inline=True)
    if user_housing:
        keyboard.add(Text("🏠 Мой дом", payload={"cmd": "housing_my"}), color=KeyboardButtonColor.PRIMARY)
        keyboard.add(Text("🔧 Криптоферма", payload={"cmd": "housing_crypto_farm"}), color=KeyboardButtonColor.PRIMARY)
        if user_housing["type"] == "house":
            keyboard.add(Text("🌱 Садоводство", payload={"cmd": "housing_garden"}), color=KeyboardButtonColor.PRIMARY)
        keyboard.add(Text("💰 Продать", payload={"cmd": "housing_sell"}), color=KeyboardButtonColor.NEGATIVE)
    else:
        keyboard.add(Text("🛒 Купить жильё", payload={"cmd": "housing_buy_list"}), color=KeyboardButtonColor.POSITIVE)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "back_to_city_menu"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_housing_list_keyboard(housing_list: list) -> str:
    """Клавиатура списка доступного жилья."""
    keyboard = Keyboard(one_time=False, inline=True)
    for h in housing_list:
        label = f"{h['name']} - {h['price']} NK ({h['parking_spots']} мест)"
        keyboard.add(Text(label, payload={"cmd": "housing_buy", "housing_id": h["housing_id"]}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "housing_main"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_housing_my_keyboard() -> str:
    """Клавиатура просмотра своего жилья."""
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("🔙 Назад", payload={"cmd": "housing_main"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_crypto_farm_keyboard(has_farm: bool) -> str:
    """Клавиатура криптофермы."""
    keyboard = Keyboard(one_time=False, inline=True)
    if not has_farm:
        keyboard.add(Text("Установить криптоферму (150 000 NK)", payload={"cmd": "housing_buy_farm"}), color=KeyboardButtonColor.POSITIVE)
    else:
        keyboard.add(Text("Продать криптоферму (50 000 NK)", payload={"cmd": "housing_sell_farm"}), color=KeyboardButtonColor.NEGATIVE)
        keyboard.add(Text("Установить видеокарту", payload={"cmd": "housing_install_videocard"}), color=KeyboardButtonColor.PRIMARY)
        keyboard.add(Text("Снять видеокарту", payload={"cmd": "housing_remove_videocard"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "housing_main"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_garden_main_keyboard() -> str:
    """Клавиатура садоводства."""
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("Купить участок 1 (500 000 NK)", payload={"cmd": "garden_buy_plot", "plot": 1}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Купить участок 2 (800 000 NK)", payload={"cmd": "garden_buy_plot", "plot": 2}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "housing_main"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_garden_plots_keyboard(plots: list) -> str:
    """Клавиатура участков."""
    keyboard = Keyboard(one_time=False, inline=True)
    for plot in plots:
        keyboard.add(Text(f"Участок {plot['plot_number']}", payload={"cmd": "garden_plot", "plot_number": plot["plot_number"]}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "housing_garden"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_garden_plot_actions_keyboard(plot_number: int) -> str:
    """Клавиатура действий на участке."""
    keyboard = Keyboard(one_time=False, inline=True)
    keyboard.add(Text("Посадить", payload={"cmd": "garden_plant", "plot": plot_number}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Полить", payload={"cmd": "garden_water", "plot": plot_number}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Собрать", payload={"cmd": "garden_harvest", "plot": plot_number}), color=KeyboardButtonColor.PRIMARY)
    keyboard.row()
    keyboard.add(Text("🔙 Назад", payload={"cmd": "housing_garden"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()