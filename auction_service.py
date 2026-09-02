# services/auction_service.py
# Логика аукционов бизнесов: создание, ставки, завершение, выставление/снятие.

from datetime import datetime, timezone, timedelta
from db.database import db

MIN_BID_STEP = 15000
AUCTION_DURATION_MINUTES = 10
START_PRICE = 500000
CASINO_START_PRICE = 2000000
AUCTION_LISTING_TAX = 50000


async def create_auction(business_id: str) -> bool:
    """Создаёт аукцион для свободного бизнеса."""
    biz = await db.fetchone("SELECT * FROM businesses WHERE business_id = ?", business_id)
    if not biz or biz["owner_id"] is not None:
        return False

    start_price = CASINO_START_PRICE if biz["type"] == "auction_casino" else START_PRICE
    await db.execute("DELETE FROM auction_bids WHERE business_id = ?", business_id)
    await db.execute(
        """
        UPDATE businesses
        SET current_bid_user_id = NULL,
            current_bid_amount = ?,
            last_bid_time = NULL
        WHERE business_id = ?
        """,
        start_price, business_id
    )
    return True


async def list_business_for_auction(user_id: int, business_id: str) -> tuple:
    """Выставляет бизнес игрока на аукцион. Списывает налог 50 000 NK."""
    biz = await db.fetchone("SELECT * FROM businesses WHERE business_id = ?", business_id)
    if not biz or biz["owner_id"] != user_id:
        return False, "Бизнес не найден или не принадлежит вам."

    if biz["is_on_auction"]:
        return False, "Бизнес уже выставлен на аукцион."

    user = await db.fetchone("SELECT bank_checking FROM users WHERE vk_id = ?", user_id)
    if user["bank_checking"] < AUCTION_LISTING_TAX:
        return False, f"Недостаточно средств для налога ({AUCTION_LISTING_TAX} NK)."

    await db.execute(
        "UPDATE users SET bank_checking = bank_checking - ? WHERE vk_id = ?",
        AUCTION_LISTING_TAX, user_id
    )
    await db.execute(
        "UPDATE system_accounts SET balance = balance + ? WHERE account_name = 'commission'",
        AUCTION_LISTING_TAX
    )

    start_price = CASINO_START_PRICE if biz["type"] == "auction_casino" else START_PRICE
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """
        UPDATE businesses
        SET owner_id = NULL,
            is_on_auction = 1,
            auction_start_time = ?,
            auction_end_time = NULL,
            auction_owner_id = ?,
            current_bid_user_id = NULL,
            current_bid_amount = ?,
            last_bid_time = NULL
        WHERE business_id = ?
        """,
        now, user_id, start_price, business_id
    )
    await db.execute("DELETE FROM auction_bids WHERE business_id = ?", business_id)
    return True, "Бизнес выставлен на аукцион."


async def remove_business_from_auction(user_id: int, business_id: str) -> tuple:
    """Снимает бизнес с аукциона (возвращает владельцу). Налог не возвращается."""
    biz = await db.fetchone("SELECT * FROM businesses WHERE business_id = ?", business_id)
    if not biz or not biz["is_on_auction"] or biz["auction_owner_id"] != user_id:
        return False, "Бизнес не находится на аукционе."

    if biz["current_bid_user_id"] is not None:
        return False, "Нельзя снять бизнес, пока есть ставки."

    await db.execute(
        """
        UPDATE businesses
        SET owner_id = ?,
            is_on_auction = 0,
            auction_start_time = NULL,
            auction_end_time = NULL,
            auction_owner_id = NULL,
            current_bid_user_id = NULL,
            current_bid_amount = NULL,
            last_bid_time = NULL
        WHERE business_id = ?
        """,
        user_id, business_id
    )
    await db.execute("DELETE FROM auction_bids WHERE business_id = ?", business_id)
    return True, "Бизнес снят с аукциона."


async def place_bid(user_id: int, business_id: str, amount: int) -> tuple:
    """Делает ставку на аукционе. Ставка должна быть не менее текущей + MIN_BID_STEP."""
    biz = await db.fetchone("SELECT * FROM businesses WHERE business_id = ?", business_id)
    if not biz or biz["owner_id"] is not None:
        return False, "Бизнес недоступен для ставок."

    current_bid = biz["current_bid_amount"] or (
        CASINO_START_PRICE if biz["type"] == "auction_casino" else START_PRICE
    )
    min_required = current_bid + MIN_BID_STEP
    if amount < min_required:
        return False, f"Минимальная ставка: {min_required} NK."

    user = await db.fetchone("SELECT bank_checking FROM users WHERE vk_id = ?", user_id)
    if user["bank_checking"] < amount:
        return False, "Недостаточно средств на основном счёте."

    if biz["current_bid_user_id"] is not None:
        await db.execute(
            "UPDATE users SET bank_checking = bank_checking + ? WHERE vk_id = ?",
            biz["current_bid_amount"], biz["current_bid_user_id"]
        )

    await db.execute(
        "UPDATE users SET bank_checking = bank_checking - ? WHERE vk_id = ?",
        amount, user_id
    )

    await db.execute(
        """
        UPDATE businesses
        SET current_bid_user_id = ?,
            current_bid_amount = ?,
            last_bid_time = ?
        WHERE business_id = ?
        """,
        user_id, amount, datetime.now(timezone.utc).isoformat(), business_id
    )

    await db.execute(
        "INSERT INTO auction_bids (business_id, user_id, amount) VALUES (?, ?, ?)",
        business_id, user_id, amount
    )
    return True, "Ставка принята."


async def finish_auction(business_id: str) -> tuple:
    """
    Завершает аукцион, если прошло достаточно времени с последней ставки и есть лидер.
    Если ставок не было, аукцион остаётся активным.
    """
    biz = await db.fetchone("SELECT * FROM businesses WHERE business_id = ?", business_id)
    if not biz or biz["owner_id"] is not None:
        return False, "Бизнес уже имеет владельца."

    if biz["current_bid_user_id"] is None:
        return False, "На этот бизнес ещё нет ставок."

    last_bid_time = datetime.fromisoformat(biz["last_bid_time"])
    if datetime.now(timezone.utc) - last_bid_time < timedelta(minutes=AUCTION_DURATION_MINUTES):
        return False, "Аукцион ещё идёт."

    winner_id = biz["current_bid_user_id"]
    winning_bid = biz["current_bid_amount"]

    if biz["auction_owner_id"] is not None:
        await db.execute(
            "UPDATE users SET bank_checking = bank_checking + ? WHERE vk_id = ?",
            winning_bid, biz["auction_owner_id"]
        )
    else:
        await db.execute(
            "UPDATE system_accounts SET balance = balance + ? WHERE account_name = 'commission'",
            winning_bid
        )

    await db.execute(
        """
        UPDATE businesses
        SET owner_id = ?,
            is_on_auction = 0,
            auction_start_time = NULL,
            auction_end_time = NULL,
            auction_owner_id = NULL,
            current_bid_user_id = NULL,
            current_bid_amount = NULL,
            last_bid_time = NULL
        WHERE business_id = ?
        """,
        winner_id, business_id
    )
    await db.execute("DELETE FROM auction_bids WHERE business_id = ?", business_id)
    return True, f"Бизнес передан игроку {winner_id}."


async def check_and_finish_auctions() -> None:
    """Проверяет все активные аукционы и завершает просроченные."""
    active = await db.fetchall(
        """
        SELECT business_id
        FROM businesses
        WHERE owner_id IS NULL
          AND current_bid_user_id IS NOT NULL
          AND last_bid_time IS NOT NULL
        """
    )
    for row in active:
        biz = await db.fetchone("SELECT * FROM businesses WHERE business_id = ?", row["business_id"])
        if biz:
            last_bid_time = datetime.fromisoformat(biz["last_bid_time"])
            if datetime.now(timezone.utc) - last_bid_time >= timedelta(minutes=AUCTION_DURATION_MINUTES):
                await finish_auction(row["business_id"])


async def get_auction_businesses() -> list:
    """
    Возвращает список всех аукционных бизнесов (type IN ('auction_standard','auction_casino'))
    с информацией о владельце, статусе аукциона и текущей ставке.
    """
    rows = await db.fetchall(
        """
        SELECT b.*, u.first_name AS owner_first_name, u.last_name AS owner_last_name
        FROM businesses b
        LEFT JOIN users u ON b.owner_id = u.vk_id
        WHERE b.type IN ('auction_standard','auction_casino')
        ORDER BY b.business_id
        """
    )
    result = []
    for row in rows:
        biz = dict(row)
        # Определяем статус
        if biz["owner_id"] is not None:
            status = f"Владелец: {biz.get('owner_first_name','')} {biz.get('owner_last_name','')}".strip()
        else:
            if biz["is_on_auction"]:
                if biz["auction_owner_id"] is not None:
                    # Игрок выставил
                    seller = await db.fetchone("SELECT first_name, last_name FROM users WHERE vk_id = ?", biz["auction_owner_id"])
                    seller_name = f"{seller['first_name']} {seller['last_name']}".strip() if seller else "игрок"
                    status = f"Выставлен игроком: {seller_name}"
                else:
                    status = "Выставлено государством"
            else:
                status = "Выставлено государством"
        biz["status_text"] = status
        result.append(biz)
    return result