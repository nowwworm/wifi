import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if TELEGRAM_BOT_TOKEN:
    TELEGRAM_BOT_TOKEN = TELEGRAM_BOT_TOKEN.strip()

ADMIN_TELEGRAM_ID_RAW = os.getenv("ADMIN_TELEGRAM_ID")
if ADMIN_TELEGRAM_ID_RAW:
    ADMIN_TELEGRAM_ID_RAW = ADMIN_TELEGRAM_ID_RAW.strip()

YANDEX_DISK_TOKEN = os.getenv("YANDEX_DISK_TOKEN")
if YANDEX_DISK_TOKEN:
    YANDEX_DISK_TOKEN = YANDEX_DISK_TOKEN.strip()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///edits.db")
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Simple validation
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment variables.")

if not ADMIN_TELEGRAM_ID_RAW:
    raise ValueError("ADMIN_TELEGRAM_ID is not set in environment variables.")

try:
    ADMIN_TELEGRAM_ID = int(ADMIN_TELEGRAM_ID_RAW)
except ValueError:
    raise ValueError(f"ADMIN_TELEGRAM_ID must be an integer, got: {ADMIN_TELEGRAM_ID_RAW}")

if not YANDEX_DISK_TOKEN:
    raise ValueError("YANDEX_DISK_TOKEN is not set in environment variables.")
