# services/casino_service.py
# Логика казино: покупка/продажа фишек, три игры, доход владельца.

import random
import json
from datetime import datetime, timezone
from db.database import db


async def buy_chips(user_id: int, amount_nk: int) -> tuple:
    """Покупает фишки за наличные (1 фишка = 100 NK)."""
    user = await db.fetchone("SELECT balance FROM users WHERE vk_id = ?", user_id)
    if user["balance"] < amount_nk:
        return False, "Недостаточно наличных."

    chips = amount_nk // 100
    if chips < 1:
        return False, "Минимальная покупка 100 NK."

    await db.execute(
        "UPDATE users SET balance = balance - ?, casino_chips = casino_chips + ? WHERE vk_id = ?",
        amount_nk, chips, user_id
    )
    return True, f"Вы купили {chips} фишек."


async def sell_chips(user_id: int, chips: int) -> tuple:
    """Продаёт фишки за наличные (1 фишка = 90 NK)."""
    user = await db.fetchone("SELECT casino_chips FROM users WHERE vk_id = ?", user_id)
    if user["casino_chips"] < chips:
        return False, "Недостаточно фишек."

    money = chips * 90
    await db.execute(
        "UPDATE users SET casino_chips = casino_chips - ?, balance = balance + ? WHERE vk_id = ?",
        chips, money, user_id
    )
    return True, f"Вы продали {chips} фишек за {money} NK."


async def play_dice(user_id: int, bet: int, guess: str) -> tuple:
    """Игра в кости. guess: 'чёт', 'нечет' или число от 2 до 12."""
    user = await db.fetchone("SELECT casino_chips FROM users WHERE vk_id = ?", user_id)
    if user["casino_chips"] < bet:
        return False, "Недостаточно фишек.", 0

    dice1 = random.randint(1, 6)
    dice2 = random.randint(1, 6)
    total = dice1 + dice2

    win = 0
    if guess.isdigit() and int(guess) == total:
        win = bet * 4
    elif guess in ("чёт", "чет") and total % 2 == 0:
        win = int(bet * 1.5)
    elif guess in ("нечет", "нечёт") and total % 2 != 0:
        win = int(bet * 1.5)

    await db.execute(
        "UPDATE users SET casino_chips = casino_chips - ? WHERE vk_id = ?",
        bet, user_id
    )
    if win > 0:
        await db.execute(
            "UPDATE users SET casino_chips = casino_chips + ? WHERE vk_id = ?",
            win, user_id
        )
        await db.execute(
            "INSERT INTO casino_bets (user_id, game_type, bet_amount, result_amount) VALUES (?, 'dice', ?, ?)",
            user_id, bet, win
        )
        return True, f"Выпало {total}. Выигрыш {win} фишек!", win
    else:
        await db.execute(
            "INSERT INTO casino_bets (user_id, game_type, bet_amount, result_amount) VALUES (?, 'dice', ?, 0)",
            user_id, bet
        )
        return True, f"Выпало {total}. Проигрыш.", 0


async def play_slots(user_id: int, bet: int) -> tuple:
    """Игра в слоты."""
    user = await db.fetchone("SELECT casino_chips FROM users WHERE vk_id = ?", user_id)
    if user["casino_chips"] < bet:
        return False, "Недостаточно фишек.", 0

    symbols = ["🍒", "🍋", "🍊", "🍇", "💎", "J"]
    reel1 = random.choice(symbols)
    reel2 = random.choice(symbols)
    reel3 = random.choice(symbols)

    win = 0
    if reel1 == reel2 == reel3:
        win = bet * 100 if reel1 == "💎" else bet * 10
    elif "J" in [reel1, reel2, reel3] and (reel1 == reel2 or reel2 == reel3 or reel1 == reel3):
        win = bet * 5

    await db.execute(
        "UPDATE users SET casino_chips = casino_chips - ? WHERE vk_id = ?",
        bet, user_id
    )
    if win > 0:
        await db.execute(
            "UPDATE users SET casino_chips = casino_chips + ? WHERE vk_id = ?",
            win, user_id
        )
        await db.execute(
            "INSERT INTO casino_bets (user_id, game_type, bet_amount, result_amount) VALUES (?, 'slots', ?, ?)",
            user_id, bet, win
        )
        return True, f"Результат: {reel1} {reel2} {reel3}. Выигрыш {win} фишек!", win
    else:
        await db.execute(
            "INSERT INTO casino_bets (user_id, game_type, bet_amount, result_amount) VALUES (?, 'slots', ?, 0)",
            user_id, bet
        )
        return True, f"Результат: {reel1} {reel2} {reel3}. Проигрыш.", 0


async def play_russian_roulette(user_id: int, bet: int) -> tuple:
    """Русская рулетка: один выстрел, шанс выжить 5/6, при выживании выигрыш удваивается."""
    user = await db.fetchone("SELECT casino_chips FROM users WHERE vk_id = ?", user_id)
    if user["casino_chips"] < bet:
        return False, "Недостаточно фишек.", 0

    state_row = await db.fetchone("SELECT data FROM user_states WHERE user_id = ? AND state = 'roulette'", user_id)
    current_pot = 0
    if state_row:
        data = json.loads(state_row["data"])
        current_pot = data.get("current_pot", 0)

    await db.execute(
        "UPDATE users SET casino_chips = casino_chips - ? WHERE vk_id = ?",
        bet, user_id
    )

    if random.randint(1, 6) == 1:
        await db.execute("DELETE FROM user_states WHERE user_id = ? AND state = 'roulette'", user_id)
        await db.execute(
            "INSERT INTO casino_bets (user_id, game_type, bet_amount, result_amount) VALUES (?, 'roulette', ?, 0)",
            user_id, bet
        )
        return True, "🔫 Выстрел! Вы проиграли серию.", 0

    current_pot = (current_pot + bet) * 2
    await db.execute(
        "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, 'roulette', ?)",
        user_id, json.dumps({"current_pot": current_pot})
    )
    return True, f"😅 Вы выжили. Текущий банк: {current_pot} фишек. Можете забрать или продолжить.", current_pot


async def collect_russian_roulette_winnings(user_id: int) -> tuple:
    """Забирает выигрыш из русской рулетки."""
    state_row = await db.fetchone("SELECT data FROM user_states WHERE user_id = ? AND state = 'roulette'", user_id)
    if not state_row:
        return False, "Нет активной серии.", 0

    data = json.loads(state_row["data"])
    amount = data.get("current_pot", 0)
    if amount <= 0:
        return False, "Нет выигрыша для снятия.", 0

    await db.execute(
        "UPDATE users SET casino_chips = casino_chips + ? WHERE vk_id = ?",
        amount, user_id
    )
    await db.execute("DELETE FROM user_states WHERE user_id = ? AND state = 'roulette'", user_id)
    await db.execute(
        "INSERT INTO casino_bets (user_id, game_type, bet_amount, result_amount) VALUES (?, 'roulette', 0, ?)",
        user_id, amount
    )
    return True, f"Вы забрали {amount} фишек.", amount


async def get_casino_owner_income(business_id: str) -> int:
    """Вычисляет доход владельца казино за последний час (50% от чистого проигрыша)."""
    now = datetime.now(timezone.utc)
    hour_start = now.replace(minute=0, second=0, microsecond=0)
    row = await db.fetchone(
        "SELECT COALESCE(SUM(bet_amount - result_amount), 0) as net_loss FROM casino_bets WHERE created_at >= ?",
        hour_start.isoformat()
    )
    net_loss = row["net_loss"] if row else 0
    if net_loss < 0:
        net_loss = 0
    return int(net_loss * 0.5)


async def distribute_casino_income() -> None:
    """Распределяет доход казино между владельцем и основателем (если владельца нет)."""
    casino = await db.fetchone("SELECT * FROM businesses WHERE type = 'auction_casino' AND hidden = 0")
    if not casino:
        return

    income = await get_casino_owner_income(casino["business_id"])
    if income <= 0:
        return

    if casino["owner_id"] is not None:
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE vk_id = ?",
            income, casino["owner_id"]
        )
    else:
        await db.execute(
            "UPDATE system_accounts SET balance = balance + ? WHERE account_name = 'commission'",
            income
        )