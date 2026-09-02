# services/business_service.py
# Полная логика бизнесов: доходы, налоги, продукты, менеджеры, репутация, директор, голосование.

import random
import json
from datetime import datetime, timezone, timedelta
from db.database import db
from config import FOUNDER_ID, TECH_ADMIN_ID

# Константы
DEFAULT_MANAGER_SALARY = 1000
MANAGER_TAX_RATE = 0.10                  # 10% от зарплаты менеджера идёт директору фирмы
PLAYER_MANAGER_TAX_RATE_MIN = 0.25       # от 25% до 50% от зарплаты игрока-менеджера идёт директору
PLAYER_MANAGER_TAX_RATE_MAX = 0.50
DIRECTOR_ELECTION_INTERVAL_DAYS = 7
DIRECTOR_MIN_REPUTATION = 80
DIRECTOR_REMOVE_THRESHOLD = 50


async def get_business_by_id(business_id: str) -> dict:
    return await db.fetchone("SELECT * FROM businesses WHERE business_id = ?", business_id)


async def get_user_businesses(user_id: int) -> list:
    return await db.fetchall("SELECT * FROM businesses WHERE owner_id = ?", user_id)


async def get_business_count(user_id: int) -> int:
    row = await db.fetchone("SELECT COUNT(*) as cnt FROM businesses WHERE owner_id = ?", user_id)
    return row["cnt"] if row else 0


async def get_admin_category(user_id: int) -> int:
    from utils.permissions import get_admin_info
    info = await get_admin_info(user_id)
    return info["category"] if info else 0


async def can_own_more_businesses(user_id: int) -> bool:
    admin_cat = await get_admin_category(user_id)
    if admin_cat == 4:
        return await get_business_count(user_id) < 3

    businesses = await get_user_businesses(user_id)
    count = len(businesses)
    if count == 0:
        return True
    if count == 1:
        if businesses[0]["type"] == "personal" and businesses[0]["category"] == "novice":
            return True
        return False
    return False


async def buy_personal_business(user_id: int, business_id: str) -> tuple:
    biz = await get_business_by_id(business_id)
    if not biz or biz["type"] != "personal":
        return False, "Бизнес не найден или не является личным."

    if not await can_own_more_businesses(user_id):
        return False, "Вы не можете владеть ещё одним бизнесом."

    existing_personal = await db.fetchone(
        "SELECT * FROM businesses WHERE owner_id = ? AND type = 'personal'", user_id)
    if existing_personal and not (existing_personal["category"] == "novice" and biz["category"] != "novice"):
        return False, "У вас уже есть личный бизнес."

    price = biz["income_min"]
    user = await db.fetchone("SELECT bank_checking FROM users WHERE vk_id = ?", user_id)
    if user["bank_checking"] < price:
        return False, "Недостаточно средств на основном счёте."

    await db.execute("UPDATE users SET bank_checking = bank_checking - ? WHERE vk_id = ?", price, user_id)
    await db.execute("UPDATE businesses SET owner_id = ? WHERE business_id = ?", user_id, business_id)
    await db.execute("UPDATE system_accounts SET balance = balance + ? WHERE account_name = 'commission'", price)
    return True, f"Вы купили {biz['name']}."


async def sell_business_to_state(user_id: int, business_id: str) -> tuple:
    biz = await get_business_by_id(business_id)
    if not biz or biz["owner_id"] != user_id:
        return False, "Бизнес не найден или не принадлежит вам."

    if biz["type"] == "personal":
        base_price = biz["income_min"]
    else:
        base_price = 2_000_000 if biz["type"] == "auction_casino" else 500_000
    sell_price = int(base_price * 0.6)

    await db.execute("UPDATE system_accounts SET balance = balance - ? WHERE account_name = 'commission'", sell_price)
    await db.execute("UPDATE users SET bank_checking = bank_checking + ? WHERE vk_id = ?", sell_price, user_id)
    await db.execute("UPDATE businesses SET owner_id = NULL, business_balance = 0 WHERE business_id = ?", business_id)
    await db.execute("DELETE FROM business_managers WHERE business_id = ?", business_id)
    return True, f"Бизнес продан за {sell_price} NK."


async def list_business_for_auction(user_id: int, business_id: str) -> tuple:
    biz = await get_business_by_id(business_id)
    if not biz or biz["owner_id"] != user_id:
        return False, "Бизнес не найден или не принадлежит вам."
    if biz["is_on_auction"]:
        return False, "Бизнес уже выставлен на аукцион."

    user = await db.fetchone("SELECT bank_checking FROM users WHERE vk_id = ?", user_id)
    tax = 50000
    if user["bank_checking"] < tax:
        return False, f"Недостаточно средств для налога ({tax} NK)."

    await db.execute("UPDATE users SET bank_checking = bank_checking - ? WHERE vk_id = ?", tax, user_id)
    await db.execute("UPDATE system_accounts SET balance = balance + ? WHERE account_name = 'commission'", tax)

    start_price = 2_000_000 if biz["type"] == "auction_casino" else 500_000
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """UPDATE businesses SET owner_id = NULL, is_on_auction = 1, auction_start_time = ?,
           auction_end_time = NULL, auction_owner_id = ?, current_bid_user_id = NULL,
           current_bid_amount = ?, last_bid_time = NULL WHERE business_id = ?""",
        now, user_id, start_price, business_id)
    await db.execute("DELETE FROM auction_bids WHERE business_id = ?", business_id)
    return True, "Бизнес выставлен на аукцион."


async def remove_business_from_auction(user_id: int, business_id: str) -> tuple:
    biz = await get_business_by_id(business_id)
    if not biz or not biz["is_on_auction"] or biz["auction_owner_id"] != user_id:
        return False, "Бизнес не находится на аукционе."
    if biz["current_bid_user_id"] is not None:
        return False, "Нельзя снять бизнес, пока есть ставки."

    await db.execute(
        """UPDATE businesses SET owner_id = ?, is_on_auction = 0, auction_start_time = NULL,
           auction_end_time = NULL, auction_owner_id = NULL, current_bid_user_id = NULL,
           current_bid_amount = NULL, last_bid_time = NULL WHERE business_id = ?""",
        user_id, business_id)
    await db.execute("DELETE FROM auction_bids WHERE business_id = ?", business_id)
    return True, "Бизнес снят с аукциона."


async def collect_business_income(business_id: str) -> None:
    biz = await get_business_by_id(business_id)
    if not biz or biz["owner_id"] is None:
        return

    income = random.randint(biz["income_min"], biz["income_max"])
    manager = await db.fetchone(
        "SELECT * FROM business_managers WHERE business_id = ? AND manager_type = 'player' AND status = 'active'", business_id)
    if manager:
        income = int(income * 1.1)

    await db.execute("UPDATE businesses SET business_balance = business_balance + ? WHERE business_id = ?", income, business_id)


async def pay_business_products(business_id: str) -> bool:
    biz = await get_business_by_id(business_id)
    if not biz or biz["product_cost"] <= 0:
        return True
    if biz["business_balance"] < biz["product_cost"]:
        return False
    await db.execute("UPDATE businesses SET business_balance = business_balance - ? WHERE business_id = ?", biz["product_cost"], business_id)
    return True


async def pay_business_tax(business_id: str) -> bool:
    biz = await get_business_by_id(business_id)
    if not biz or biz["tax_amount"] <= 0:
        return True
    if biz["business_balance"] < biz["tax_amount"]:
        return False
    await db.execute("UPDATE businesses SET business_balance = business_balance - ? WHERE business_id = ?", biz["tax_amount"], business_id)
    await db.execute("UPDATE system_accounts SET balance = balance + ? WHERE account_name = 'commission'", biz["tax_amount"])
    return True


async def withdraw_business_balance(user_id: int, business_id: str) -> bool:
    biz = await get_business_by_id(business_id)
    if not biz or biz["owner_id"] != user_id:
        return False
    amount = biz["business_balance"]
    if amount <= 0:
        return False
    await db.execute("UPDATE businesses SET business_balance = 0 WHERE business_id = ?", business_id)
    await db.execute("UPDATE users SET bank_checking = bank_checking + ? WHERE vk_id = ?", amount, user_id)
    return True


async def set_bank_commission(business_id: str, commission: float) -> bool:
    if not 0 <= commission <= 0.05:
        return False
    biz = await get_business_by_id(business_id)
    if not biz or biz["special_income_type"] != "bank_commission":
        return False
    await db.execute("UPDATE businesses SET commission_rate = ? WHERE business_id = ?", commission, business_id)
    return True


# --- Специальные доходы ---

async def apply_work_percent_income(worker_id: int, job_id: str, salary: int) -> None:
    mapping = {
        "novice_1": "1.4.1",
        "novice_2": "1.4.2",
        "novice_3": "1.4.3",
        "novice_4": "1.4.4",
        "perm_3": "1.4.5",
        "perm_1": "1.4.7",
        "perm_2": "1.4.8",
        "perm_6": "1.4.11",
        "perm_5": "1.4.12",
    }
    business_id = mapping.get(job_id)
    if not business_id:
        return
    biz = await get_business_by_id(business_id)
    if not biz or biz["owner_id"] is None:
        return
    income = int(salary * 0.05)
    await db.execute("UPDATE businesses SET business_balance = business_balance + ? WHERE business_id = ?", income, business_id)


async def apply_auto_sale_income(vehicle_price: int) -> None:
    biz = await get_business_by_id("1.4.6")
    if not biz or biz["owner_id"] is None:
        return
    income = int(vehicle_price * 0.30)
    await db.execute("UPDATE businesses SET business_balance = business_balance + ? WHERE business_id = ?", income, "1.4.6")


async def apply_estate_sale_income(housing_price: int) -> None:
    biz = await get_business_by_id("1.4.14")
    if not biz or biz["owner_id"] is None:
        return
    income = int(housing_price * 0.30)
    await db.execute("UPDATE businesses SET business_balance = business_balance + ? WHERE business_id = ?", income, "1.4.14")


# --- Менеджеры ---

async def hire_manager(business_id: str, manager_user_id: int, salary: int = DEFAULT_MANAGER_SALARY) -> tuple:
    biz = await get_business_by_id(business_id)
    if not biz:
        return False, "Бизнес не найден."
    if biz["owner_id"] is None:
        return False, "У бизнеса нет владельца."
    if biz["type"] not in ("auction_standard", "auction_casino"):
        return False, "Менеджеры доступны только для аукционных бизнесов."

    existing = await db.fetchone(
        "SELECT id FROM business_managers WHERE business_id = ? AND manager_user_id = ? AND status = 'active'",
        business_id, manager_user_id)
    if existing:
        return False, "Игрок уже нанят менеджером в этом бизнесе."

    await db.execute(
        "INSERT INTO business_managers (business_id, manager_type, manager_user_id, salary, status, hired_at) VALUES (?, 'player', ?, ?, 'active', datetime('now'))",
        business_id, manager_user_id, salary)
    rep = await db.fetchone("SELECT id FROM manager_reputation WHERE user_id = ?", manager_user_id)
    if not rep:
        await db.execute("INSERT INTO manager_reputation (user_id, reputation, boss_reputation) VALUES (?, 50, 50)", manager_user_id)
    return True, "Менеджер нанят."


async def fire_manager(manager_id: int) -> bool:
    row = await db.fetchone("SELECT * FROM business_managers WHERE id = ?", manager_id)
    if not row:
        return False
    await db.execute("UPDATE business_managers SET status = 'fired' WHERE id = ?", manager_id)
    return True


async def get_managers_for_business(business_id: str) -> list:
    return await db.fetchall(
        "SELECT bm.*, u.first_name, u.last_name FROM business_managers bm JOIN users u ON bm.manager_user_id = u.vk_id WHERE bm.business_id = ? AND bm.status = 'active'",
        business_id)


async def update_manager_reputation(manager_user_id: int, delta: int) -> None:
    await db.execute(
        "UPDATE manager_reputation SET reputation = MIN(100, MAX(0, reputation + ?)) WHERE user_id = ?",
        delta, manager_user_id)


async def update_boss_reputation(boss_user_id: int, delta: int) -> None:
    await db.execute(
        "UPDATE manager_reputation SET boss_reputation = MIN(100, MAX(0, boss_reputation + ?)) WHERE user_id = ?",
        delta, boss_user_id)


async def pay_manager_salary(manager_id: int) -> tuple:
    manager = await db.fetchone("SELECT * FROM business_managers WHERE id = ?", manager_id)
    if not manager or manager["status"] != "active":
        return False, "Менеджер не найден."

    biz = await get_business_by_id(manager["business_id"])
    if not biz or biz["business_balance"] < manager["salary"]:
        return False, "Недостаточно средств на счету бизнеса."

    await db.execute(
        "UPDATE businesses SET business_balance = business_balance - ? WHERE business_id = ?",
        manager["salary"], manager["business_id"])
    await db.execute(
        "UPDATE users SET balance = balance + ? WHERE vk_id = ?",
        manager["salary"], manager["manager_user_id"])

    # Налог с зарплаты менеджера (10%) идёт директору Фирмы менеджеров
    firm = await db.fetchone("SELECT * FROM businesses WHERE special_income_type = 'manager_firm' AND owner_id IS NOT NULL")
    if firm:
        tax = int(manager["salary"] * MANAGER_TAX_RATE)
        await db.execute(
            "UPDATE businesses SET business_balance = business_balance + ? WHERE business_id = ?",
            tax, firm["business_id"])

    await db.execute("UPDATE business_managers SET last_payment_time = datetime('now') WHERE id = ?", manager_id)
    return True, f"Зарплата {manager['salary']} NK выплачена."


async def process_all_manager_salaries() -> None:
    managers = await db.fetchall("SELECT id FROM business_managers WHERE status = 'active'")
    for m in managers:
        await pay_manager_salary(m["id"])


# --- Фирма менеджеров: директор, репутация, выборы, голосование ---

async def get_manager_firm() -> dict:
    return await db.fetchone("SELECT * FROM businesses WHERE special_income_type = 'manager_firm'")


async def get_director_id() -> int:
    row = await db.fetchone("SELECT user_id FROM user_states WHERE state = 'firm_director'")
    return row["user_id"] if row else None


async def elect_director() -> None:
    """Запускает голосование: выдвигает кандидатов (репутация >= 80)."""
    firm = await get_manager_firm()
    if not firm:
        return

    # Кандидаты: менеджеры с репутацией >= 80
    candidates = await db.fetchall(
        "SELECT user_id, reputation FROM manager_reputation WHERE reputation >= ? ORDER BY reputation DESC LIMIT 3",
        DIRECTOR_MIN_REPUTATION)
    if not candidates:
        return

    # Сохраняем список кандидатов в user_states для голосования
    candidate_ids = [c["user_id"] for c in candidates]
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (0, 'firm_election_candidates', ?)",
        json.dumps(candidate_ids))
    # Очищаем старые голоса
    await db.execute("DELETE FROM director_elections")


async def vote_for_director(voter_id: int, candidate_id: int) -> tuple:
    """Голосование менеджера за кандидата."""
    # Проверяем, что голосующий - менеджер (любой нанятый)
    manager = await db.fetchone("SELECT id FROM business_managers WHERE manager_user_id = ? AND status = 'active'", voter_id)
    if not manager:
        return False, "Голосовать могут только менеджеры."

    candidates_row = await db.fetchone("SELECT data FROM user_states WHERE state = 'firm_election_candidates'")
    if not candidates_row:
        return False, "Голосование не активно."
    candidates = json.loads(candidates_row["data"])
    if candidate_id not in candidates:
        return False, "Кандидат не найден."

    # Запрещаем голосовать за себя
    if candidate_id == voter_id:
        return False, "Нельзя голосовать за себя."

    # Записываем голос
    await db.execute(
        "INSERT OR REPLACE INTO director_elections (candidate_id, voter_id, voted_at) VALUES (?, ?, datetime('now'))",
        candidate_id, voter_id)
    return True, "Голос принят."


async def finish_election() -> None:
    """Подсчитывает голоса и назначает директора."""
    candidates_row = await db.fetchone("SELECT data FROM user_states WHERE state = 'firm_election_candidates'")
    if not candidates_row:
        return
    candidates = json.loads(candidates_row["data"])

    # Подсчитываем голоса
    votes = await db.fetchall(
        "SELECT candidate_id, COUNT(*) as cnt FROM director_elections GROUP BY candidate_id ORDER BY cnt DESC")
    if not votes:
        return

    winner_id = votes[0]["candidate_id"]
    # Назначаем директора
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'firm_director', ?)",
        winner_id, json.dumps({"appointed_at": datetime.now(timezone.utc).isoformat()}))
    # Очищаем голоса и кандидатов
    await db.execute("DELETE FROM director_elections")
    await db.execute("DELETE FROM user_states WHERE state = 'firm_election_candidates'")


async def maybe_elect_director() -> None:
    """Планировщик: раз в неделю запускает выборы и завершает их."""
    await finish_election()  # завершаем предыдущие
    row = await db.fetchone("SELECT data FROM user_states WHERE state = 'firm_director'")
    if not row:
        await elect_director()
        return
    data = json.loads(row["data"])
    appointed_at = datetime.fromisoformat(data["appointed_at"])
    if datetime.now(timezone.utc) - appointed_at >= timedelta(days=DIRECTOR_ELECTION_INTERVAL_DAYS):
        await elect_director()


async def remove_director_if_bad() -> None:
    """Смещает директора, если его репутация упала ниже 50."""
    director_id = await get_director_id()
    if not director_id:
        return
    rep = await db.fetchone("SELECT reputation FROM manager_reputation WHERE user_id = ?", director_id)
    if rep and rep["reputation"] < DIRECTOR_REMOVE_THRESHOLD:
        await db.execute("DELETE FROM user_states WHERE state = 'firm_director'")
        await update_manager_reputation(director_id, -rep["reputation"])  # репутация в 0
        await elect_director()


async def complaint_on_manager(manager_id: int, reason: str) -> None:
    """Сохраняет жалобу на менеджера и уведомляет заместителя основателя и выше."""
    await db.execute(
        "INSERT INTO admin_log (admin_id, action, details) VALUES (?, 'complaint', ?)",
        manager_id, reason)
    leaders = await db.fetchall("SELECT user_id FROM admin_roles WHERE category >= 4")
    for leader in leaders:
        await db.execute(
            "INSERT INTO user_states (user_id, state, data) VALUES (?, 'notification', ?)",
            leader["user_id"], json.dumps({"text": f"Жалоба на менеджера {manager_id}: {reason}"}))


# --- Планировщик ---

async def collect_all_auction_incomes() -> None:
    businesses = await db.fetchall("SELECT business_id FROM businesses WHERE type IN ('auction_standard','auction_casino') AND owner_id IS NOT NULL")
    for b in businesses:
        await collect_business_income(b["business_id"])


async def collect_all_personal_incomes() -> None:
    businesses = await db.fetchall("SELECT business_id FROM businesses WHERE type = 'personal' AND owner_id IS NOT NULL")
    for b in businesses:
        await collect_business_income(b["business_id"])


async def pay_all_products() -> None:
    businesses = await db.fetchall("SELECT business_id FROM businesses WHERE product_cost > 0 AND owner_id IS NOT NULL")
    for b in businesses:
        await pay_business_products(b["business_id"])


async def pay_all_taxes() -> None:
    businesses = await db.fetchall("SELECT business_id FROM businesses WHERE tax_amount > 0 AND owner_id IS NOT NULL")
    for b in businesses:
        await pay_business_tax(b["business_id"])


async def manager_salaries_job() -> None:
    await process_all_manager_salaries()


async def director_election_job() -> None:
    await maybe_elect_director()
    await remove_director_if_bad()