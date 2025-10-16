"""
Configuration settings for the bot.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# TELEGRAM CONFIGURATION
# ============================================================================
TELEGRAM_TOKEN = os.getenv("BOT_TOKEN", "")
STORAGE_CHANNEL_ID = int(os.getenv("STORAGE_CHANNEL_ID", "0"))

# ============================================================================
# OPENAI CONFIGURATION
# ============================================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Chat models
PREMIUM_CHAT_MODEL = "gpt-4o"
FREE_CHAT_MODEL = "gpt-4o-mini"

# Image model
IMAGE_MODEL = "gpt-image-1"

# Token limits
PREMIUM_MAX_TOKENS = 2000
FREE_MAX_TOKENS = 800

# ============================================================================
# ADMIN CONFIGURATION
# ============================================================================
ADMIN_IDS = [
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip()
]

# ============================================================================
# QUOTA LIMITS (Daily)
# ============================================================================
# Free tier daily limits
FREE_QUICK_CHAT = 20
FREE_CODE_CHAT = 10
FREE_CONVERT = 5
FREE_PPTX = 2

# Premium tier (unlimited)
PREMIUM_QUICK_CHAT = 999999
PREMIUM_CODE_CHAT = 999999
PREMIUM_CONVERT = 999999
PREMIUM_PPTX = 999999

# ============================================================================
# TRIAL SYSTEM
# ============================================================================
TRIAL_PERIOD_DAYS = 7
TRIAL_USES_PER_PERIOD = 3

# ============================================================================
# DATABASE
# ============================================================================
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot.db")
