import os
from typing import List
from dotenv import load_dotenv

# === Load environment variables from .env file ===
# It will look for a file named ".env" in the current working directory
load_dotenv()

# === Telegram and API keys ===
TELEGRAM_TOKEN: str = os.getenv("BOT_TOKEN")  # Your bot token from BotFather
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")

# === Database ===
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./bot.db")

# === Storage (Telegram channel ID for storing files) ===
STORAGE_CHANNEL_ID = os.getenv("STORAGE_CHANNEL_ID")

# === Admin IDs ===
_admin_ids_env: str = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: List[int] = [
    int(x) for x in _admin_ids_env.split(",") if x.strip().isdigit()
]

# === Optional debug print ===
if not TELEGRAM_TOKEN:
    print("⚠️  BOT_TOKEN not found in environment variables or .env file!")
