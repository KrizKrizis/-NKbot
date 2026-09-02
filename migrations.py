# db/migrations.py
# Создание всех таблиц базы данных.

from db.database import db

async def init_db():
    """Создаёт все таблицы, если их нет."""

    # ==================== ОСНОВНЫЕ ТАБЛИЦЫ ====================

    # Пользователи (с расширенными банковскими полями)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            vk_id INTEGER UNIQUE NOT NULL,
            first_name TEXT,
            last_name TEXT,
            game_id INTEGER UNIQUE,
            balance INTEGER DEFAULT 0,
            exp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            current_city TEXT DEFAULT 'Величие',
            reputation INTEGER DEFAULT 0,
            bank_name TEXT,
            bank_checking INTEGER DEFAULT 0,
            bank_savings INTEGER DEFAULT 0,
            tax_account INTEGER DEFAULT 0,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Настройки пользователя
    await db.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            receive_notifications BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(vk_id) ON DELETE CASCADE
        )
    """)

    # Игроки (доп. статистика)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY,
            vk_id INTEGER UNIQUE NOT NULL,
            nickname TEXT,
            level INTEGER DEFAULT 1,
            experience INTEGER DEFAULT 0,
            balance INTEGER DEFAULT 0,
            energy INTEGER DEFAULT 100,
            health INTEGER DEFAULT 100,
            location TEXT DEFAULT 'city',
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vk_id) REFERENCES users(vk_id) ON DELETE CASCADE
        )
    """)

    # Города
    await db.execute("""
        CREATE TABLE IF NOT EXISTS cities (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            owner_vk_id INTEGER,
            population INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_vk_id) REFERENCES users(vk_id) ON DELETE SET NULL
        )
    """)

    # Работы
    await db.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            salary INTEGER DEFAULT 0,
            required_level INTEGER DEFAULT 1,
            city_id INTEGER,
            FOREIGN KEY (city_id) REFERENCES cities(id) ON DELETE CASCADE
        )
    """)

    # Трудоустройство
    await db.execute("""
        CREATE TABLE IF NOT EXISTS player_jobs (
            id INTEGER PRIMARY KEY,
            player_vk_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            hired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(player_vk_id, job_id),
            FOREIGN KEY (player_vk_id) REFERENCES players(vk_id) ON DELETE CASCADE,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
        )
    """)

    # Банковские счета (основные, если нужны отдельно)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS bank_accounts (
            id INTEGER PRIMARY KEY,
            player_vk_id INTEGER UNIQUE NOT NULL,
            balance INTEGER DEFAULT 0,
            interest_rate REAL DEFAULT 0.01,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player_vk_id) REFERENCES players(vk_id) ON DELETE CASCADE
        )
    """)

    # Жильё (каталог)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS housing (
            housing_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER DEFAULT 0,
            city_id INTEGER,
            FOREIGN KEY (city_id) REFERENCES cities(id) ON DELETE SET NULL
        )
    """)

    # Владение жильём игроками
    await db.execute("""
        CREATE TABLE IF NOT EXISTS player_housing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            housing_id INTEGER NOT NULL,
            purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(vk_id) ON DELETE CASCADE,
            FOREIGN KEY (housing_id) REFERENCES housing(housing_id) ON DELETE CASCADE,
            UNIQUE(user_id, housing_id)
        )
    """)

    # Транспорт (каталог)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER DEFAULT 0,
            speed INTEGER DEFAULT 10,
            fuel INTEGER DEFAULT 100
        )
    """)

    # Владение транспортом игроками
    await db.execute("""
        CREATE TABLE IF NOT EXISTS player_vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            vehicle_id INTEGER NOT NULL,
            active BOOLEAN DEFAULT 0,
            purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(vk_id) ON DELETE CASCADE,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
            UNIQUE(user_id, vehicle_id)
        )
    """)

    # Бизнесы (уже были, но оставлю для совместимости)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS businesses (
            business_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT DEFAULT 'standard',
            owner_id INTEGER,
            city_id INTEGER,
            profit_per_hour INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_on_auction BOOLEAN DEFAULT 0,
            auction_start_time TIMESTAMP,
            auction_end_time TIMESTAMP,
            auction_owner_id INTEGER,
            current_bid_user_id INTEGER,
            current_bid_amount INTEGER,
            last_bid_time TIMESTAMP,
            FOREIGN KEY (owner_id) REFERENCES users(vk_id) ON DELETE SET NULL,
            FOREIGN KEY (city_id) REFERENCES cities(id) ON DELETE SET NULL
        )
    """)

    # Ставки на аукционы бизнесов
    await db.execute("""
        CREATE TABLE IF NOT EXISTS auction_bids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            bid_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (business_id) REFERENCES businesses(business_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(vk_id) ON DELETE CASCADE
        )
    """)

    # Системные счета
    await db.execute("""
        CREATE TABLE IF NOT EXISTS system_accounts (
            account_name TEXT PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await db.execute(
        "INSERT OR IGNORE INTO system_accounts (account_name, balance) VALUES ('commission', 0)"
    )

    # Казино, NKVito, крафт, инвентарь, лотереи, магазины, АЗС, аукционы товаров, админ-логи
    await db.execute("""
        CREATE TABLE IF NOT EXISTS casino_bets (
            id INTEGER PRIMARY KEY,
            player_vk_id INTEGER NOT NULL,
            bet_amount INTEGER NOT NULL,
            win_amount INTEGER,
            game_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player_vk_id) REFERENCES players(vk_id) ON DELETE CASCADE
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS nkvito_wallets (
            id INTEGER PRIMARY KEY,
            player_vk_id INTEGER UNIQUE NOT NULL,
            balance INTEGER DEFAULT 0,
            last_transaction TIMESTAMP,
            FOREIGN KEY (player_vk_id) REFERENCES players(vk_id) ON DELETE CASCADE
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS craft_recipes (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            ingredients TEXT,
            result_item TEXT NOT NULL,
            required_level INTEGER DEFAULT 1
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS player_inventory (
            id INTEGER PRIMARY KEY,
            player_vk_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER DEFAULT 1,
            FOREIGN KEY (player_vk_id) REFERENCES players(vk_id) ON DELETE CASCADE
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS lotteries (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            ticket_price INTEGER DEFAULT 10,
            prize_pool INTEGER DEFAULT 0,
            end_date TIMESTAMP,
            winner_vk_id INTEGER,
            FOREIGN KEY (winner_vk_id) REFERENCES players(vk_id) ON DELETE SET NULL
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS shops (
            id INTEGER PRIMARY KEY,
            city_id INTEGER,
            name TEXT NOT NULL,
            owner_vk_id INTEGER,
            FOREIGN KEY (city_id) REFERENCES cities(id) ON DELETE CASCADE,
            FOREIGN KEY (owner_vk_id) REFERENCES players(vk_id) ON DELETE SET NULL
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS shop_items (
            id INTEGER PRIMARY KEY,
            shop_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            price INTEGER NOT NULL,
            stock INTEGER DEFAULT 0,
            FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS gas_stations (
            id INTEGER PRIMARY KEY,
            city_id INTEGER,
            fuel_price INTEGER DEFAULT 1,
            owner_vk_id INTEGER,
            FOREIGN KEY (city_id) REFERENCES cities(id) ON DELETE CASCADE,
            FOREIGN KEY (owner_vk_id) REFERENCES players(vk_id) ON DELETE SET NULL
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS auctions (
            id INTEGER PRIMARY KEY,
            item_name TEXT NOT NULL,
            starting_price INTEGER NOT NULL,
            current_price INTEGER,
            seller_vk_id INTEGER NOT NULL,
            buyer_vk_id INTEGER,
            end_time TIMESTAMP,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (seller_vk_id) REFERENCES players(vk_id) ON DELETE CASCADE,
            FOREIGN KEY (buyer_vk_id) REFERENCES players(vk_id) ON DELETE SET NULL
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY,
            admin_vk_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            target_vk_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_vk_id) REFERENCES users(vk_id) ON DELETE CASCADE
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS user_states (
            user_id INTEGER PRIMARY KEY,
            state TEXT,
            data TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    await db.conn.commit()