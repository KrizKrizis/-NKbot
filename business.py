# business/handlers/business.py
# Обработчики управления бизнесами, менеджерами, репутацией, жалобами и выборами директора.

import json
import logging
from datetime import datetime, timezone, timedelta
from vkbottle.bot import Blueprint, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text
from db.database import db
from services.business_service import (
    get_user_businesses,
    sell_business_to_state,
    list_business_for_auction,
    remove_business_from_auction,
    withdraw_business_balance,
    pay_business_tax,
    pay_business_products,
    set_bank_commission,
    get_business_by_id,
    hire_manager,
    fire_manager,
    get_managers_for_business,
    pay_manager_salary,
    process_all_manager_salaries,
    update_manager_reputation,
    update_boss_reputation,
    elect_director,
    get_director_id,
    vote_for_director,
    complaint_on_manager,
)
from business.keyboards.business import (
    get_business_main_keyboard,
    get_my_businesses_keyboard,
    get_business_panel_keyboard,
    get_bank_commission_keyboard,
    get_managers_keyboard,
    get_managers_list_keyboard,
    get_managers_reputation_keyboard,
    get_complaint_reason_keyboard,
    get_candidates_keyboard,
    get_back_to_business_keyboard,
)

logger = logging.getLogger(__name__)

bp = Blueprint("business")


async def show_business_menu(message: Message):
    await message.answer("🏢 Бизнесы", keyboard=get_business_main_keyboard())


@bp.on.message(payload={"cmd": "open_businesses"})
async def open_businesses(message: Message):
    await show_business_menu(message)


@bp.on.message(payload={"cmd": "business_main"})
async def business_main(message: Message):
    await show_business_menu(message)


@bp.on.message(payload={"cmd": "business_my"})
async def business_my(message: Message):
    businesses = await get_user_businesses(message.from_id)
    if not businesses:
        await message.answer("У вас нет бизнесов.", keyboard=get_back_to_business_keyboard())
        return
    await message.answer("Ваши бизнесы:", keyboard=get_my_businesses_keyboard(businesses))


@bp.on.message(payload={"cmd": "business_panel"})
async def business_panel(message: Message):
    payload = message.get_payload_json()
    business_id = payload.get("business_id")
    biz = await db.fetchone("SELECT * FROM businesses WHERE business_id = ? AND owner_id = ?", business_id, message.from_id)
    if not biz:
        await message.answer("Бизнес не найден или не принадлежит вам.")
        return

    special_income_type = biz["special_income_type"]
    is_on_auction = bool(biz["is_on_auction"])
    commission_rate = biz["commission_rate"] if special_income_type == "bank_commission" else 0.0
    keyboard = get_business_panel_keyboard(business_id, is_on_auction, special_income_type, commission_rate)

    text = (
        f"Название: {biz['name']}\n"
        f"Баланс бизнеса: {biz['business_balance']} NK\n"
        f"Доход (мин-макс): {biz['income_min']}-{biz['income_max']} NK\n"
        f"Продукты: {biz['product_cost']} NK (каждые 6ч)\n"
        f"Налог: {biz['tax_amount']} NK (каждые 12ч)\n"
    )
    if special_income_type == "bank_commission":
        text += f"Текущая комиссия: {commission_rate:.0%}\n"
    await message.answer(text, keyboard=keyboard)


@bp.on.message(payload={"cmd": "business_withdraw"})
async def business_withdraw(message: Message):
    payload = message.get_payload_json()
    business_id = payload.get("business_id")
    success = await withdraw_business_balance(message.from_id, business_id)
    await message.answer("Доход снят на основной счёт." if success else "Не удалось снять доход.")
    await business_panel(message)


@bp.on.message(payload={"cmd": "business_pay_tax"})
async def business_pay_tax_handler(message: Message):
    payload = message.get_payload_json()
    business_id = payload.get("business_id")
    success = await pay_business_tax(business_id)
    await message.answer("Налог оплачен." if success else "Недостаточно средств на счёте бизнеса.")
    await business_panel(message)


@bp.on.message(payload={"cmd": "business_pay_products"})
async def business_pay_products_handler(message: Message):
    payload = message.get_payload_json()
    business_id = payload.get("business_id")
    success = await pay_business_products(business_id)
    await message.answer("Продукты оплачены." if success else "Недостаточно средств на счёте бизнеса.")
    await business_panel(message)


@bp.on.message(payload={"cmd": "business_list_auction"})
async def business_list_auction_handler(message: Message):
    payload = message.get_payload_json()
    business_id = payload.get("business_id")
    success, msg = await list_business_for_auction(message.from_id, business_id)
    await message.answer(msg)
    await business_panel(message)


@bp.on.message(payload={"cmd": "business_remove_auction"})
async def business_remove_auction_handler(message: Message):
    payload = message.get_payload_json()
    business_id = payload.get("business_id")
    success, msg = await remove_business_from_auction(message.from_id, business_id)
    await message.answer(msg)
    await business_panel(message)


@bp.on.message(payload={"cmd": "business_sell_state"})
async def business_sell_state_handler(message: Message):
    payload = message.get_payload_json()
    business_id = payload.get("business_id")
    success, msg = await sell_business_to_state(message.from_id, business_id)
    await message.answer(msg)
    await show_business_menu(message)


@bp.on.message(payload={"cmd": "business_set_commission"})
async def business_set_commission(message: Message):
    payload = message.get_payload_json()
    business_id = payload.get("business_id")
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'business_commission_select', ?)",
        message.from_id, json.dumps({"business_id": business_id})
    )
    await message.answer("Выберите новую комиссию:", keyboard=get_bank_commission_keyboard())


@bp.on.message(payload={"cmd": "business_bank_set_commission_value"})
async def business_bank_set_commission_value(message: Message):
    payload = message.get_payload_json()
    rate = int(payload.get("rate"))
    state_row = await db.fetchone("SELECT data FROM user_states WHERE user_id = ? AND state = 'business_commission_select'", message.from_id)
    if not state_row:
        await message.answer("Ошибка. Начните заново.")
        return
    data = json.loads(state_row["data"])
    business_id = data["business_id"]
    commission = rate / 100.0
    success = await set_bank_commission(business_id, commission)
    await message.answer("Комиссия обновлена." if success else "Ошибка обновления.")
    await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
    await business_panel(message)


@bp.on.message(payload={"cmd": "business_casino_stats"})
async def business_casino_stats(message: Message):
    payload = message.get_payload_json()
    business_id = payload.get("business_id")
    now = datetime.now(timezone.utc)
    hour_ago = now - timedelta(hours=1)
    stats = await db.fetchone(
        """
        SELECT COALESCE(SUM(bet_amount), 0) as total_bets,
               COALESCE(SUM(result_amount), 0) as total_wins
        FROM casino_bets
        WHERE created_at >= ?
        """,
        hour_ago.isoformat()
    )
    total_bets = stats["total_bets"] if stats else 0
    total_wins = stats["total_wins"] if stats else 0
    net_loss = max(0, total_bets - total_wins)
    owner_income = int(net_loss * 0.5)
    text = (
        f"📊 Статистика казино за последний час:\n"
        f"Всего ставок: {total_bets} NK\n"
        f"Выплачено выигрышей: {total_wins} NK\n"
        f"Чистый проигрыш игроков: {net_loss} NK\n"
        f"Ваш доход (50%): {owner_income} NK"
    )
    await message.answer(text, keyboard=get_back_to_business_keyboard())


@bp.on.message(payload={"cmd": "business_auto_stats"})
async def business_auto_stats(message: Message):
    total_vehicles = await db.fetchone("SELECT COUNT(*) as cnt FROM player_vehicles")
    total_vehicle_models = await db.fetchone("SELECT COUNT(*) as cnt FROM vehicles")
    text = (
        f"📊 Статистика авторынка:\n"
        f"Всего автомобилей у игроков: {total_vehicles['cnt']}\n"
        f"Всего моделей в продаже: {total_vehicle_models['cnt']}\n"
    )
    await message.answer(text, keyboard=get_back_to_business_keyboard())


@bp.on.message(payload={"cmd": "business_estate_stats"})
async def business_estate_stats(message: Message):
    total_housing = await db.fetchone("SELECT COUNT(*) as cnt FROM player_housing")
    total_housing_models = await db.fetchone("SELECT COUNT(*) as cnt FROM housing")
    text = (
        f"📊 Статистика рынка жилья:\n"
        f"Всего жилья у игроков: {total_housing['cnt']}\n"
        f"Всего объектов в продаже: {total_housing_models['cnt']}\n"
    )
    await message.answer(text, keyboard=get_back_to_business_keyboard())


@bp.on.message(payload={"cmd": "business_managers"})
async def business_managers(message: Message):
    payload = message.get_payload_json()
    business_id = payload.get("business_id")
    await message.answer("Раздел менеджеров", keyboard=get_managers_keyboard(business_id))


@bp.on.message(payload={"cmd": "business_managers_list"})
async def business_managers_list(message: Message):
    payload = message.get_payload_json()
    business_id = payload.get("business_id")
    managers = await get_managers_for_business(business_id)
    if not managers:
        await message.answer("Нет нанятых менеджеров.")
        return
    await message.answer("Менеджеры:", keyboard=get_managers_list_keyboard(managers))


@bp.on.message(payload={"cmd": "business_hire_manager"})
async def business_hire_manager(message: Message):
    payload = message.get_payload_json()
    business_id = payload.get("business_id")
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'business_hire_manager_id', ?)",
        message.from_id, json.dumps({"business_id": business_id})
    )
    await message.answer("Введите ID игрока, которого хотите нанять менеджером:")


@bp.on.message(payload={"cmd": "business_manager_fire"})
async def business_manager_fire(message: Message):
    payload = message.get_payload_json()
    manager_id = int(payload.get("manager_id"))
    success = await fire_manager(manager_id)
    await message.answer("Менеджер уволен." if success else "Ошибка увольнения.")
    await business_managers(message)


@bp.on.message(payload={"cmd": "business_pay_all_salaries"})
async def business_pay_all_salaries(message: Message):
    payload = message.get_payload_json()
    business_id = payload.get("business_id")
    managers = await get_managers_for_business(business_id)
    for m in managers:
        await pay_manager_salary(m["id"])
    await message.answer("Зарплаты выплачены.")
    await business_managers(message)


@bp.on.message(payload={"cmd": "business_managers_reputation"})
async def business_managers_reputation(message: Message):
    reps = await db.fetchall("SELECT * FROM manager_reputation")
    await message.answer("Репутации менеджеров:", keyboard=get_managers_reputation_keyboard(reps))


@bp.on.message(payload={"cmd": "business_complaint_manager"})
async def business_complaint_manager(message: Message):
    payload = message.get_payload_json()
    manager_id = int(payload.get("manager_id"))
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'business_complaint_reason', ?)",
        message.from_id, json.dumps({"manager_id": manager_id})
    )
    await message.answer("Выберите причину жалобы:", keyboard=get_complaint_reason_keyboard())


@bp.on.message(payload={"cmd": "business_complaint_reason"})
async def business_complaint_reason(message: Message):
    payload = message.get_payload_json()
    reason = payload.get("reason")
    state_row = await db.fetchone("SELECT data FROM user_states WHERE user_id = ? AND state = 'business_complaint_reason'", message.from_id)
    if not state_row:
        await message.answer("Ошибка.")
        return
    data = json.loads(state_row["data"])
    manager_id = data["manager_id"]
    await complaint_on_manager(manager_id, reason)
    await message.answer("Жалоба отправлена руководству.")
    await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
    await business_managers(message)


@bp.on.message(payload={"cmd": "business_elect_director"})
async def business_elect_director(message: Message):
    firm = await get_business_by_id("1.4.15")
    if not firm or firm["owner_id"] != message.from_id:
        await message.answer("Вы не владелец Фирмы менеджеров.")
        return
    await elect_director()
    await message.answer("Выборы запущены. Кандидаты определены.")


@bp.on.message(payload={"cmd": "business_vote_director"})
async def business_vote_director(message: Message):
    row = await db.fetchone("SELECT data FROM user_states WHERE state = 'firm_election_candidates'")
    if not row:
        await message.answer("Голосование не активно.")
        return
    candidates = json.loads(row["data"])
    if not candidates:
        await message.answer("Нет кандидатов.")
        return
    await message.answer("Выберите кандидата:", keyboard=get_candidates_keyboard(candidates))


@bp.on.message(payload={"cmd": "business_vote_candidate"})
async def business_vote_candidate(message: Message):
    payload = message.get_payload_json()
    candidate_id = int(payload.get("candidate_id"))
    success, msg = await vote_for_director(message.from_id, candidate_id)
    await message.answer(msg)
    if success:
        await business_managers(message)


@bp.on.message()
async def handle_business_text(message: Message):
    state_row = await db.fetchone("SELECT state, data FROM user_states WHERE user_id = ?", message.from_id)
    if not state_row:
        return
    state = state_row["state"]
    text = message.text.strip()
    if state == "business_hire_manager_id":
        if not text.isdigit():
            await message.answer("ID должен быть числом.")
            return
        manager_user_id = int(text)
        data = json.loads(state_row["data"])
        business_id = data["business_id"]
        success, msg = await hire_manager(business_id, manager_user_id)
        await message.answer(msg)
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)
        if success:
            await business_managers(message)
        else:
            await business_panel(message)
    else:
        await db.execute("DELETE FROM user_states WHERE user_id = ?", message.from_id)