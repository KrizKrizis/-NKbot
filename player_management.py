# admin/player_management.py
# Управление игроками: список, статистика, поиск, блокировки, выдача/изъятие.

import json
import logging
from datetime import datetime, timezone
from vkbottle import Keyboard, KeyboardButtonColor, Text
from db.database import db
from utils.permissions import has_permission, get_admin_info

logger = logging.getLogger(__name__)

PAGE_SIZE = 50


async def get_player_page(page: int) -> list:
    """Возвращает список игроков на указанной странице (по 50)."""
    offset = (page - 1) * PAGE_SIZE
    players = await db.fetchall(
        """
        SELECT vk_id, game_id, first_name, last_name, level, balance, bank_checking, is_blocked
        FROM users
        ORDER BY game_id
        LIMIT ? OFFSET ?
        """,
        PAGE_SIZE, offset
    )
    return players


async def get_total_pages() -> int:
    """Возвращает общее количество страниц списка игроков."""
    total = await db.fetchone("SELECT COUNT(*) as cnt FROM users")
    count = total["cnt"] if total else 0
    return (count + PAGE_SIZE - 1) // PAGE_SIZE


async def format_player_list_page(page: int) -> tuple:
    """Формирует текст и клавиатуру для страницы списка игроков."""
    players = await get_player_page(page)
    if not players:
        return "Игроки не найдены.", None

    lines = [f"Страница {page}"]
    for p in players:
        status = "🔴" if p["is_blocked"] else "🟢"
        lines.append(f"{status} {p['game_id']} | {p['first_name']} {p['last_name']} | LVL {p['level']} | NK {p['balance']}")

    total_pages = await get_total_pages()
    keyboard = Keyboard(one_time=False, inline=True)

    # Первый ряд: стрелки и статистика
    keyboard.row()
    left_color = KeyboardButtonColor.SECONDARY if page == 1 else KeyboardButtonColor.PRIMARY
    right_color = KeyboardButtonColor.SECONDARY if page >= total_pages else KeyboardButtonColor.POSITIVE
    keyboard.add(Text("⬅️", payload={"cmd": "players_page", "page": page - 1 if page > 1 else 1}), color=left_color)
    keyboard.add(Text("📊 Статистика", payload={"cmd": "player_stats_request"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("➡️", payload={"cmd": "players_page", "page": page + 1 if page < total_pages else page}), color=right_color)

    # Второй ряд: Логи, Поиск, Управление, Назад
    keyboard.row()
    keyboard.add(Text("📋 Логи", payload={"cmd": "player_logs_request"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("🔍 Поиск", payload={"cmd": "player_search_request"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("⚙️ Управление", payload={"cmd": "player_manage_request"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("🔙 Назад", payload={"cmd": "admin_main_menu"}), color=KeyboardButtonColor.SECONDARY)

    return "\n".join(lines), keyboard.get_json()


async def get_player_profile(target_id: int, viewer_id: int) -> str:
    """
    Возвращает профиль игрока в зависимости от прав смотрящего.
    Хелпер видит только базовую статистику, руководство — полную.
    """
    user = await db.fetchone("SELECT * FROM users WHERE vk_id = ?", target_id)
    if not user:
        return "Игрок не найден."

    # Базовая информация (доступна хелперу и выше)
    lines = [
        f"👤 {user['first_name']} {user['last_name']}",
        f"🆔 ID: {user['game_id']}",
        f"⭐ LVL: {user['level']} (Опыт: {user['exp']})",
        f"💵 Наличные: {user['balance']} NK",
        f"🏦 Банк: {user['bank_name'] or 'не выбран'}",
        f"🏙 Город: {user['current_city']}",
    ]

    # Проверяем, может ли видеть больше (админ и выше)
    if await has_permission(viewer_id, "players.view_extended"):
        # Расширенная статистика
        lines.append(f"💳 Основной счёт: {user['bank_checking']} NK")
        lines.append(f"📈 Накопительный: {user['bank_savings']} NK")
        lines.append(f"🧾 Налоговый: {user['tax_account']} NK")
        lines.append(f"⭐ Репутация: {user['reputation']}")
        if user["is_blocked"]:
            lines.append("🔴 Заблокирован")
        if user["temporary_blocked_until"]:
            lines.append(f"⏳ Заморожен до: {user['temporary_blocked_until']}")

        # Промокоды, если они есть
        promos = await db.fetchall(
            "SELECT code FROM promocodes WHERE id IN (SELECT promocode_id FROM user_promocodes WHERE user_id = ?)",
            target_id
        )
        if promos:
            lines.append("🎁 Промокоды:")
            for p in promos:
                lines.append(f"  • {p['code']}")

        # Последние транзакции (упрощённо)
        transactions = await db.fetchall(
            "SELECT * FROM admin_log WHERE admin_id = ? ORDER BY timestamp DESC LIMIT 5",
            target_id
        )
        if transactions:
            lines.append("📋 Последние действия:")
            for t in transactions:
                lines.append(f"  • {t['action']} ({t['timestamp']})")

    return "\n".join(lines)


async def search_player(query: str) -> list:
    """Ищет игроков по ID, имени, фамилии или username."""
    # Проверяем, если query - число, ищем по game_id или vk_id
    if query.isdigit():
        players = await db.fetchall(
            "SELECT * FROM users WHERE game_id = ? OR vk_id = ?",
            int(query), int(query)
        )
    else:
        players = await db.fetchall(
            """
            SELECT * FROM users
            WHERE first_name LIKE ? OR last_name LIKE ?
            """,
            f"%{query}%", f"%{query}%"
        )
    return players


async def format_search_results(players: list) -> str:
    """Форматирует результаты поиска."""
    if not players:
        return "Никого не найдено."
    lines = ["Результаты поиска:"]
    for p in players:
        lines.append(f"🆔 {p['game_id']} | {p['first_name']} {p['last_name']} | LVL {p['level']}")
    return "\n".join(lines)


async def block_player(admin_id: int, target_id: int, block_type: str, duration_days: int = 0) -> tuple:
    """
    Блокирует игрока.
    block_type: 'freeze' (заморозка), 'target' (точечная), 'full' (полный бан).
    duration_days: 0 = навсегда, иначе количество дней.
    """
    # Проверка прав
    if block_type == "freeze" and not await has_permission(admin_id, "players.freeze"):
        return False, "Недостаточно прав для заморозки."
    if block_type == "target" and not await has_permission(admin_id, "players.target_block"):
        return False, "Недостаточно прав для точечной блокировки."
    if block_type == "full" and not await has_permission(admin_id, "players.full_ban"):
        return False, "Недостаточно прав для полного бана."

    if target_id == admin_id:
        return False, "Нельзя заблокировать себя."

    if duration_days > 0:
        # Временная блокировка
        until = datetime.now(timezone.utc) + timedelta(days=duration_days)
        if block_type == "freeze":
            await db.execute(
                "UPDATE users SET temporary_blocked_until = ? WHERE vk_id = ?",
                until.isoformat(), target_id
            )
        elif block_type == "target":
            # Точечная блокировка накладывается отдельным полем, в нашем случае is_blocked с пометкой
            await db.execute(
                "UPDATE users SET is_blocked = 1, temporary_blocked_until = ? WHERE vk_id = ?",
                until.isoformat(), target_id
            )
        elif block_type == "full":
            await db.execute(
                "UPDATE users SET is_blocked = 1, temporary_blocked_until = ? WHERE vk_id = ?",
                until.isoformat(), target_id
            )
    else:
        # Перманентная блокировка
        await db.execute("UPDATE users SET is_blocked = 1 WHERE vk_id = ?", target_id)

    # Логируем
    await db.execute(
        "INSERT INTO admin_log (admin_id, action, details) VALUES (?, 'block', ?)",
        admin_id, f"block_type={block_type}, target={target_id}, duration={duration_days}"
    )
    return True, f"Игрок {target_id} заблокирован ({block_type}, {duration_days or 'навсегда'})."


async def unblock_player(admin_id: int, target_id: int) -> tuple:
    """Разблокирует игрока."""
    if not await has_permission(admin_id, "players.unblock"):
        return False, "Недостаточно прав для разблокировки."
    await db.execute(
        "UPDATE users SET is_blocked = 0, temporary_blocked_until = NULL WHERE vk_id = ?",
        target_id
    )
    await db.execute(
        "INSERT INTO admin_log (admin_id, action, details) VALUES (?, 'unblock', ?)",
        admin_id, f"target={target_id}"
    )
    return True, f"Игрок {target_id} разблокирован."


async def give_item(admin_id: int, target_id: int, item_id: str, quantity: int = 1) -> tuple:
    """Выдаёт предмет игроку."""
    if not await has_permission(admin_id, "players.give_item"):
        return False, "Недостаточно прав для выдачи предмета."

    item = await db.fetchone("SELECT * FROM items WHERE item_id = ?", item_id)
    if not item:
        return False, "Предмет не найден."

    existing = await db.fetchone("SELECT id, quantity FROM inventory WHERE user_id = ? AND item_id = ?", target_id, item_id)
    if existing:
        await db.execute("UPDATE inventory SET quantity = quantity + ? WHERE id = ?", quantity, existing["id"])
    else:
        await db.execute("INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, ?, ?)", target_id, item_id, quantity)

    await db.execute(
        "INSERT INTO admin_log (admin_id, action, details) VALUES (?, 'give_item', ?)",
        admin_id, f"target={target_id}, item={item_id}, qty={quantity}"
    )
    return True, f"Выдано {quantity} шт. {item['name']}."


async def take_item(admin_id: int, target_id: int, item_id: str, quantity: int = 1) -> tuple:
    """Изъимает предмет у игрока."""
    if not await has_permission(admin_id, "players.take_item"):
        return False, "Недостаточно прав для изъятия предмета."

    inv = await db.fetchone("SELECT id, quantity FROM inventory WHERE user_id = ? AND item_id = ?", target_id, item_id)
    if not inv or inv["quantity"] < quantity:
        return False, "Недостаточно предметов у игрока."

    await db.execute("UPDATE inventory SET quantity = quantity - ? WHERE id = ?", quantity, inv["id"])
    await db.execute("DELETE FROM inventory WHERE id = ? AND quantity <= 0", inv["id"])

    await db.execute(
        "INSERT INTO admin_log (admin_id, action, details) VALUES (?, 'take_item', ?)",
        admin_id, f"target={target_id}, item={item_id}, qty={quantity}"
    )
    return True, f"Изъято {quantity} шт. предмета {item_id}."


async def give_money(admin_id: int, target_id: int, amount: int) -> tuple:
    """Выдаёт деньги игроку (на наличные)."""
    if not await has_permission(admin_id, "players.give_money"):
        return False, "Недостаточно прав для выдачи денег."
    await db.execute("UPDATE users SET balance = balance + ? WHERE vk_id = ?", amount, target_id)
    await db.execute(
        "INSERT INTO admin_log (admin_id, action, details) VALUES (?, 'give_money', ?)",
        admin_id, f"target={target_id}, amount={amount}"
    )
    return True, f"Выдано {amount} NK."


async def take_money(admin_id: int, target_id: int, amount: int) -> tuple:
    """Изъимает деньги у игрока."""
    if not await has_permission(admin_id, "players.take_money"):
        return False, "Недостаточно прав для изъятия денег."
    user = await db.fetchone("SELECT balance FROM users WHERE vk_id = ?", target_id)
    if user["balance"] < amount:
        return False, "У игрока недостаточно денег."
    await db.execute("UPDATE users SET balance = balance - ? WHERE vk_id = ?", amount, target_id)
    await db.execute(
        "INSERT INTO admin_log (admin_id, action, details) VALUES (?, 'take_money', ?)",
        admin_id, f"target={target_id}, amount={amount}"
    )
    return True, f"Изъято {amount} NK."