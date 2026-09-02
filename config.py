# config.py
# Загружает переменные окружения из .env и предоставляет настройки проекта.

import os
from dotenv import load_dotenv

load_dotenv()

# Настройки ВКонтакте
VK_TOKEN = os.getenv("VK_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID", "0"))

# Настройки базы данных
DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()
SQLITE_PATH = os.getenv("SQLITE_PATH", "nikskriz.db")
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Руководство проекта (категория 4)
FOUNDER_ID = int(os.getenv("FOUNDER_ID", "0"))
TECH_ADMIN_ID = int(os.getenv("TECH_ADMIN_ID", "0"))

# Уровень логирования
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ID чатов для режимов (0 = не задано)
CHAT_HELPERS = int(os.getenv("CHAT_HELPERS", "0"))
CHAT_ADMINS = int(os.getenv("CHAT_ADMINS", "0"))
CHAT_GA_STATS = int(os.getenv("CHAT_GA_STATS", "0"))
CHAT_TEAM_GENERAL = int(os.getenv("CHAT_TEAM_GENERAL", "0"))
CHAT_TESTERS = int(os.getenv("CHAT_TESTERS", "0"))
CHAT_FULL_LOG = int(os.getenv("CHAT_FULL_LOG", "0"))