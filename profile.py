# player/handlers/profile.py
# Форматирование профиля игрока.

from db.database import db

async def format_profile(user) -> str:
    """Собирает текст профиля на основе данных пользователя."""
    lines = []
    
    # Имя и фамилия
    full_name = f"{user['first_name']} {user['last_name']}".strip()
    if full_name:
        lines.append(f"👤 {full_name}")
    else:
        lines.append("👤 Игрок")
    
    lines.append(f"🆔 ID: {user['game_id']}")
    lines.append(f"⭐ LVL: {user['level']} (Опыт: {user['exp']})")
    lines.append(f"💵 Наличные: {user['balance']} NK")
    
    # Банк (строка отображается только если выбран банк)
    if user['bank_name']:
        lines.append(f"🏦 Банк: {user['bank_name']}")
        lines.append(f"💰 Основной счёт: {user['bank_checking']} NK")
        lines.append(f"📈 Накопительный: {user['bank_savings']} NK")
        lines.append(f"🧾 Налоговый: {user['tax_account']} NK")
    
    # Жильё
    housing = await db.fetchone(
        "SELECT h.name FROM player_housing ph "
        "JOIN housing h ON ph.housing_id = h.housing_id "
        "WHERE ph.user_id = ?",
        user['vk_id']
    )
    if housing:
        lines.append(f"🏠 Жильё: {housing['name']}")
    
    # Активный транспорт
    vehicle = await db.fetchone(
        "SELECT v.name FROM player_vehicles pv "
        "JOIN vehicles v ON pv.vehicle_id = v.vehicle_id "
        "WHERE pv.user_id = ? AND pv.active = 1",
        user['vk_id']
    )
    if vehicle:
        lines.append(f"🚗 Транспорт: {vehicle['name']}")
    
    # Бизнесы
    businesses = await db.fetchall(
        "SELECT name FROM businesses WHERE owner_id = ?",
        user['vk_id']
    )
    if businesses:
        lines.append("🏪 Бизнес:")
        for b in businesses:
            lines.append(f"  • {b['name']}")
    
    lines.append(f"🏙 Город: {user['current_city']}")
    return "\n".join(lines)