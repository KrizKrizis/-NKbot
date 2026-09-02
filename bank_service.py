# services/bank_service.py
# Логика банковских операций: переводы, комиссии, проценты.

from datetime import datetime, timezone
from db.database import db

INTEREST_RATE = 0.01
SAVINGS_LIMIT = 750_000


async def get_commission_rate(bank_name: str) -> float:
    """Возвращает комиссию для банка."""
    if bank_name == "NK Bank":
        return 0.0
    row = await db.fetchone(
        "SELECT commission_rate FROM businesses WHERE name = ?",
        bank_name
    )
    return row["commission_rate"] if row else 0.0


async def transfer_between_users(sender_id: int, receiver_id: int, amount: int) -> tuple:
    """Переводит сумму между основными счетами двух игроков."""
    if amount <= 0:
        return False, "Сумма должна быть положительной."

    sender = await db.fetchone("SELECT bank_checking, bank_name FROM users WHERE vk_id = ?", sender_id)
    receiver = await db.fetchone("SELECT vk_id FROM users WHERE vk_id = ?", receiver_id)

    if not sender or not receiver:
        return False, "Получатель не найден."

    commission_rate = await get_commission_rate(sender["bank_name"])
    commission = int(amount * commission_rate)
    total_debit = amount + commission

    if sender["bank_checking"] < total_debit:
        return False, "Недостаточно средств на основном счёте с учётом комиссии."

    await db.execute(
        "UPDATE users SET bank_checking = bank_checking - ? WHERE vk_id = ?",
        total_debit, sender_id
    )
    await db.execute(
        "UPDATE users SET bank_checking = bank_checking + ? WHERE vk_id = ?",
        amount, receiver_id
    )

    if commission > 0:
        bank_owner = await db.fetchone(
            "SELECT owner_id FROM businesses WHERE name = ? AND owner_id IS NOT NULL",
            sender["bank_name"]
        )
        if bank_owner:
            await db.execute(
                "UPDATE users SET balance = balance + ? WHERE vk_id = ?",
                commission, bank_owner["owner_id"]
            )
        else:
            await db.execute(
                "UPDATE system_accounts SET balance = balance + ? WHERE account_name = 'commission'",
                commission
            )
    return True, "Перевод выполнен."


async def transfer_between_own_accounts(user_id: int, from_account: str, to_account: str, amount: int) -> tuple:
    """Переводит средства между счетами пользователя."""
    if from_account == to_account:
        return False, "Счета совпадают."
    if amount <= 0:
        return False, "Сумма должна быть положительной."

    allowed_accounts = {'balance', 'bank_checking', 'bank_savings', 'tax_account'}
    if from_account not in allowed_accounts or to_account not in allowed_accounts:
        return False, "Неверный счёт."

    user = await db.fetchone(f"SELECT {from_account} FROM users WHERE vk_id = ?", user_id)
    if not user or user[from_account] < amount:
        return False, "Недостаточно средств."

    await db.execute(f"UPDATE users SET {from_account} = {from_account} - ? WHERE vk_id = ?", amount, user_id)
    await db.execute(f"UPDATE users SET {to_account} = {to_account} + ? WHERE vk_id = ?", amount, user_id)
    return True, "Перевод выполнен."


async def apply_savings_interest(user_id: int) -> None:
    """Начисляет проценты на накопительный счёт, если прошёл час."""
    user = await db.fetchone("SELECT bank_savings, last_interest_time FROM users WHERE vk_id = ?", user_id)
    if not user or user["bank_savings"] <= 0:
        return

    now = datetime.now(timezone.utc)
    last_str = user["last_interest_time"]
    if last_str:
        last = datetime.fromisoformat(last_str.replace("Z", "+00:00"))
        if (now - last).total_seconds() < 3600:
            return

    interest = int(user["bank_savings"] * INTEREST_RATE)
    new_savings = user["bank_savings"] + interest
    excess = 0
    if new_savings > SAVINGS_LIMIT:
        excess = new_savings - SAVINGS_LIMIT
        new_savings = SAVINGS_LIMIT
        await db.execute(
            "UPDATE system_accounts SET balance = balance + ? WHERE account_name = 'commission'",
            excess
        )
    await db.execute(
        "UPDATE users SET bank_savings = ?, last_interest_time = ? WHERE vk_id = ?",
        new_savings, now.isoformat(), user_id
    )


async def apply_savings_interest_to_all() -> None:
    """Начисляет проценты всем пользователям (вызывается планировщиком)."""
    users = await db.fetchall("SELECT vk_id FROM users")
    for user in users:
        await apply_savings_interest(user["vk_id"])