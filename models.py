# db/models.py
# DDL-запросы для создания всех таблиц проекта.

TABLES = {}

TABLES["users"] = """
CREATE TABLE IF NOT EXISTS users (
    vk_id INTEGER PRIMARY KEY,
    game_id INTEGER UNIQUE NOT NULL,
    first_name TEXT NOT NULL DEFAULT '',
    last_name TEXT NOT NULL DEFAULT '',
    balance INTEGER NOT NULL DEFAULT 0,
    crypto_balance REAL NOT NULL DEFAULT 0,
    bank_checking INTEGER NOT NULL DEFAULT 0,
    bank_savings INTEGER NOT NULL DEFAULT 0,
    tax_account INTEGER NOT NULL DEFAULT 0,
    bank_name TEXT,
    level INTEGER NOT NULL DEFAULT 1,
    exp INTEGER NOT NULL DEFAULT 0,
    current_city TEXT NOT NULL DEFAULT 'Величие',
    reputation INTEGER NOT NULL DEFAULT 0,
    current_work TEXT,
    work_start_time TEXT,
    work_end_time TEXT,
    work_reward INTEGER,
    work_drop_data TEXT,
    casino_chips INTEGER NOT NULL DEFAULT 0,
    achievements_enabled INTEGER NOT NULL DEFAULT 0,
    last_exp_bonus_time TEXT,
    last_interest_time TEXT,
    is_blocked INTEGER NOT NULL DEFAULT 0,
    temporary_blocked_until TEXT,
    registration_date TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

TABLES["user_states"] = """
CREATE TABLE IF NOT EXISTS user_states (
    user_id INTEGER PRIMARY KEY,
    state TEXT NOT NULL,
    data TEXT DEFAULT '{}',
    FOREIGN KEY (user_id) REFERENCES users(vk_id)
);
"""

TABLES["admin_roles"] = """
CREATE TABLE IF NOT EXISTS admin_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    category INTEGER NOT NULL CHECK(category BETWEEN 1 AND 4),
    position TEXT NOT NULL,
    permissions TEXT DEFAULT '{}',
    assigned_by INTEGER NOT NULL,
    assigned_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(vk_id),
    FOREIGN KEY (assigned_by) REFERENCES users(vk_id)
);
"""

TABLES["admin_log"] = """
CREATE TABLE IF NOT EXISTS admin_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    details TEXT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (admin_id) REFERENCES users(vk_id)
);
"""

TABLES["jobs"] = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('novice','permanent','millionaire','elite')),
    base_reward_min INTEGER NOT NULL,
    base_reward_max INTEGER NOT NULL,
    duration_minutes INTEGER NOT NULL,
    level_required INTEGER NOT NULL DEFAULT 1,
    city_restriction TEXT,
    required_item_id TEXT
);
"""

TABLES["work_settings"] = """
CREATE TABLE IF NOT EXISTS work_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    reward_min INTEGER NOT NULL,
    reward_max INTEGER NOT NULL,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);
"""

TABLES["work_bonuses"] = """
CREATE TABLE IF NOT EXISTS work_bonuses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    chance REAL NOT NULL,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id),
    FOREIGN KEY (item_id) REFERENCES items(item_id)
);
"""

TABLES["items"] = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL DEFAULT 'resource',
    base_price INTEGER NOT NULL DEFAULT 0,
    stackable INTEGER NOT NULL DEFAULT 1
);
"""

TABLES["inventory"] = """
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    durability INTEGER DEFAULT 100,
    FOREIGN KEY (user_id) REFERENCES users(vk_id),
    FOREIGN KEY (item_id) REFERENCES items(item_id)
);
"""

TABLES["businesses"] = """
CREATE TABLE IF NOT EXISTS businesses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('personal','auction_standard','auction_casino')),
    category TEXT,
    city TEXT,
    owner_id INTEGER,
    income_min INTEGER NOT NULL,
    income_max INTEGER NOT NULL,
    product_cost INTEGER NOT NULL DEFAULT 0,
    tax_amount INTEGER NOT NULL DEFAULT 0,
    special_income_type TEXT DEFAULT 'none',
    business_balance INTEGER NOT NULL DEFAULT 0,
    hidden INTEGER NOT NULL DEFAULT 0,
    casino_revenue_share REAL DEFAULT 0.5,
    license_end TEXT,
    commission_rate REAL DEFAULT 0.0,
    last_bid_time TEXT,
    current_bid_user_id INTEGER,
    current_bid_amount INTEGER,
    is_on_auction INTEGER NOT NULL DEFAULT 0,
    auction_start_time TEXT,
    auction_end_time TEXT,
    auction_owner_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (owner_id) REFERENCES users(vk_id),
    FOREIGN KEY (current_bid_user_id) REFERENCES users(vk_id)
);
"""

TABLES["auction_bids"] = """
CREATE TABLE IF NOT EXISTS auction_bids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    bid_time TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (business_id) REFERENCES businesses(business_id),
    FOREIGN KEY (user_id) REFERENCES users(vk_id)
);
"""

TABLES["business_managers"] = """
CREATE TABLE IF NOT EXISTS business_managers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id TEXT NOT NULL,
    manager_type TEXT NOT NULL CHECK(manager_type IN ('government','player')),
    manager_level INTEGER DEFAULT 1,
    manager_user_id INTEGER,
    status TEXT NOT NULL DEFAULT 'active',
    salary INTEGER NOT NULL DEFAULT 0,
    hired_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_payment_time TEXT,
    FOREIGN KEY (business_id) REFERENCES businesses(business_id),
    FOREIGN KEY (manager_user_id) REFERENCES users(vk_id)
);
"""

TABLES["manager_reputation"] = """
CREATE TABLE IF NOT EXISTS manager_reputation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    reputation INTEGER NOT NULL DEFAULT 50,
    boss_reputation INTEGER NOT NULL DEFAULT 50,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(vk_id)
);
"""

TABLES["director_elections"] = """
CREATE TABLE IF NOT EXISTS director_elections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL,
    voter_id INTEGER NOT NULL,
    voted_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(candidate_id, voter_id),
    FOREIGN KEY (candidate_id) REFERENCES users(vk_id),
    FOREIGN KEY (voter_id) REFERENCES users(vk_id)
);
"""

TABLES["craft_recipes"] = """
CREATE TABLE IF NOT EXISTS craft_recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    result_item_id TEXT NOT NULL,
    result_quantity INTEGER NOT NULL DEFAULT 1,
    duration_minutes INTEGER NOT NULL DEFAULT 1,
    success_chance REAL NOT NULL,
    level_required INTEGER NOT NULL DEFAULT 0,
    mars_only INTEGER NOT NULL DEFAULT 0,
    color TEXT NOT NULL DEFAULT 'base',
    FOREIGN KEY (result_item_id) REFERENCES items(item_id)
);
"""

TABLES["craft_ingredients"] = """
CREATE TABLE IF NOT EXISTS craft_ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    is_tool INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (recipe_id) REFERENCES craft_recipes(recipe_id),
    FOREIGN KEY (item_id) REFERENCES items(item_id)
);
"""

TABLES["active_crafts"] = """
CREATE TABLE IF NOT EXISTS active_crafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    recipe_id TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    FOREIGN KEY (user_id) REFERENCES users(vk_id),
    FOREIGN KEY (recipe_id) REFERENCES craft_recipes(recipe_id)
);
"""

TABLES["vehicles"] = """
CREATE TABLE IF NOT EXISTS vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    price INTEGER NOT NULL,
    tank_capacity INTEGER NOT NULL,
    fuel_consumption REAL NOT NULL,
    country TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'car'
);
"""

TABLES["player_vehicles"] = """
CREATE TABLE IF NOT EXISTS player_vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    vehicle_id TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 0,
    fuel_amount REAL NOT NULL,
    mileage INTEGER NOT NULL DEFAULT 0,
    purchase_date TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(vk_id),
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id)
);
"""

TABLES["housing"] = """
CREATE TABLE IF NOT EXISTS housing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    housing_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('apartment','house')),
    price INTEGER NOT NULL,
    parking_spots INTEGER NOT NULL
);
"""

TABLES["player_housing"] = """
CREATE TABLE IF NOT EXISTS player_housing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    housing_id TEXT NOT NULL,
    has_crypto_farm INTEGER NOT NULL DEFAULT 0,
    crypto_farm_installed_at TEXT,
    tax_paid_until TEXT,
    FOREIGN KEY (user_id) REFERENCES users(vk_id),
    FOREIGN KEY (housing_id) REFERENCES housing(housing_id)
);
"""

TABLES["garden_plots"] = """
CREATE TABLE IF NOT EXISTS garden_plots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    plot_number INTEGER NOT NULL,
    capacity INTEGER NOT NULL DEFAULT 25,
    purchased INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(vk_id)
);
"""

TABLES["garden_plants"] = """
CREATE TABLE IF NOT EXISTS garden_plants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    plot_number INTEGER NOT NULL,
    slot_number INTEGER NOT NULL,
    plant_type TEXT NOT NULL,
    seed_item_id TEXT NOT NULL,
    planted_at TEXT NOT NULL,
    water_required_by TEXT,
    harvest_ready_at TEXT,
    can_harvest INTEGER NOT NULL DEFAULT 0,
    is_tree INTEGER NOT NULL DEFAULT 0,
    tree_fruit_count INTEGER DEFAULT 0,
    tree_last_harvest TEXT,
    FOREIGN KEY (user_id) REFERENCES users(vk_id),
    FOREIGN KEY (seed_item_id) REFERENCES items(item_id)
);
"""

TABLES["lottery_draws"] = """
CREATE TABLE IF NOT EXISTS lottery_draws (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draw_time TEXT NOT NULL,
    total_pool INTEGER NOT NULL DEFAULT 0,
    winners TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
);
"""

TABLES["lottery_tickets"] = """
CREATE TABLE IF NOT EXISTS lottery_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    draw_id INTEGER NOT NULL,
    ticket_count INTEGER NOT NULL DEFAULT 1,
    purchased_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(vk_id),
    FOREIGN KEY (draw_id) REFERENCES lottery_draws(id)
);
"""

TABLES["events"] = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    prize_pool INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    winner_id INTEGER,
    FOREIGN KEY (winner_id) REFERENCES users(vk_id)
);
"""

TABLES["event_participants"] = """
CREATE TABLE IF NOT EXISTS event_participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    FOREIGN KEY (event_id) REFERENCES events(id),
    FOREIGN KEY (user_id) REFERENCES users(vk_id)
);
"""

TABLES["nkvito_listings"] = """
CREATE TABLE IF NOT EXISTS nkvito_listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id INTEGER NOT NULL,
    item_id TEXT,
    business_id TEXT,
    price INTEGER NOT NULL,
    listing_duration_days INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    FOREIGN KEY (seller_id) REFERENCES users(vk_id),
    FOREIGN KEY (item_id) REFERENCES items(item_id),
    FOREIGN KEY (business_id) REFERENCES businesses(business_id)
);
"""

TABLES["casino_bets"] = """
CREATE TABLE IF NOT EXISTS casino_bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    game_type TEXT NOT NULL,
    bet_amount INTEGER NOT NULL,
    result_amount INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(vk_id)
);
"""

TABLES["casino_stats"] = """
CREATE TABLE IF NOT EXISTS casino_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id TEXT NOT NULL,
    hour_start TEXT NOT NULL,
    total_bets INTEGER NOT NULL DEFAULT 0,
    total_wins INTEGER NOT NULL DEFAULT 0,
    net_loss INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (business_id) REFERENCES businesses(business_id)
);
"""

TABLES["achievements"] = """
CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    achievement_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    condition_type TEXT NOT NULL
);
"""

TABLES["user_achievements"] = """
CREATE TABLE IF NOT EXISTS user_achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    achievement_id TEXT NOT NULL,
    received_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(vk_id),
    FOREIGN KEY (achievement_id) REFERENCES achievements(achievement_id),
    UNIQUE(user_id, achievement_id)
);
"""

TABLES["system_accounts"] = """
CREATE TABLE IF NOT EXISTS system_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_name TEXT UNIQUE NOT NULL,
    balance INTEGER NOT NULL DEFAULT 0,
    description TEXT
);
"""

TABLES["chat_config"] = """
CREATE TABLE IF NOT EXISTS chat_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_mode INTEGER NOT NULL UNIQUE,
    chat_id INTEGER NOT NULL,
    description TEXT
);
"""

TABLES["user_settings"] = """
CREATE TABLE IF NOT EXISTS user_settings (
    user_id INTEGER PRIMARY KEY,
    receive_notifications INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(vk_id)
);
"""

TABLES["fired_staff"] = """
CREATE TABLE IF NOT EXISTS fired_staff (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    old_position TEXT,
    old_category INTEGER,
    fired_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(vk_id)
);
"""

TABLES["promocodes"] = """
CREATE TABLE IF NOT EXISTS promocodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    reward_type TEXT NOT NULL,
    reward_id TEXT,
    reward_amount INTEGER,
    uses_left INTEGER NOT NULL,
    expires_at TEXT
);
"""

TABLES["mars_investments"] = """
CREATE TABLE IF NOT EXISTS mars_investments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    invested_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(vk_id)
);
"""

TABLES["work_experience"] = """
CREATE TABLE IF NOT EXISTS work_experience (
    user_id INTEGER NOT NULL,
    job_id TEXT NOT NULL,
    experience INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, job_id),
    FOREIGN KEY (user_id) REFERENCES users(vk_id),
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);
"""

TABLES["crypto_farm"] = """
CREATE TABLE IF NOT EXISTS crypto_farm (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    videocard_id TEXT NOT NULL,
    installed_at TEXT NOT NULL DEFAULT (datetime('now')),
    income_accumulated REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(vk_id),
    FOREIGN KEY (videocard_id) REFERENCES items(item_id)
);
"""

TABLES["config"] = """
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT
);
"""


def get_all_create_queries() -> list:
    return list(TABLES.values())