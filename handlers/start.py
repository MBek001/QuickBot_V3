"""
Entry and navigation handlers for regular users.

This module defines the `/start` command handler, language selection
handling and routing between the main menu and AI submenus.  It is
responsible for initialising new users in the database and storing
their chosen language in both the database and per‑chat context.
"""

from typing import Optional

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from db import get_db
from models import User, Plan
from models_enums import Language, PlanCode
from keyboard import get_language_keyboard, get_main_keyboard, get_ai_functions_keyboard, get_back_keyboard
from messages import get_message
from handlers.state import (
    SELECT_LANGUAGE,
    MAIN_MENU,
    AI_MENU,
    CHAT,
    IMAGE_GEN_PROMPT,
    IMAGE_ANALYSIS_WAIT_IMAGE,
    PPTX_WAIT_TITLE,
    PPTX_WAIT_SLIDES,
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the /start command.

    Creates a new user if necessary and prompts for language selection if
    not yet set.  Otherwise shows the main menu directly.
    """
    tg_user = update.effective_user
    with get_db() as db:
        user: Optional[User] = db.query(User).filter(User.tg_id == tg_user.id).first()
        # Ensure at least one plan exists (free plan)
        plan = db.query(Plan).filter(Plan.code == PlanCode.free).first()
        if not plan:
            plan = Plan(code=PlanCode.free, title="Free", description="Free plan", daily_quick_chat=30, daily_code_chat=10, daily_convert=5, daily_pptx=3)
            db.add(plan)
        if not user:
            # Create new user
            user = User(
                tg_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                plan_code=PlanCode.free,
                is_admin=tg_user.id in ADMIN_IDS,
            )
            db.add(user)
        # Persist any changes
        # user is persisted via get_db context
        user_lang = user.lang
    # Store language in context for quick access
    if user_lang:
        context.user_data["lang"] = user_lang
    # Prompt language selection if not set
    if not user_lang:
        await update.message.reply_text(
            get_message("welcome", Language.en),
            reply_markup=get_language_keyboard(),
        )
        return SELECT_LANGUAGE
    # Show main menu
    await update.message.reply_text(
        get_message("prompt_main_menu", user_lang),
        reply_markup=get_main_keyboard(user_lang),
    )
    return MAIN_MENU


async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Persist the user's selected language and show the main menu."""
    selection = (update.message.text or "").lower()
    # Map textual representation to Language enum
    if "english" in selection or "🇬🇧" in selection:
        lang = Language.en
    elif "рус" in selection or "🇷🇺" in selection:
        lang = Language.ru
    elif "o‘bek" in selection or "ozbek" in selection or "🇺🇿" in selection or "o‘zbek" in selection:
        lang = Language.uz
    else:
        # Default to English if unrecognised
        lang = Language.en
    context.user_data["lang"] = lang
    with get_db() as db:
        user: Optional[User] = db.query(User).filter(User.tg_id == update.effective_user.id).first()
        if user:
            user.lang = lang
            db.add(user)
    await update.message.reply_text(
        get_message("prompt_main_menu", lang),
        reply_markup=get_main_keyboard(lang),
    )
    return MAIN_MENU


async def main_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Route user selection in the main menu."""
    text = (update.message.text or "").strip()
    user_lang: Language = context.user_data.get("lang", Language.en)
    # Determine which label corresponds to AI functions
    ai_labels = {
        Language.en: "🤖 AI functions",
        Language.ru: "🤖 AI функции",
        Language.uz: "🤖 AI funksiyalari",
    }
    if text == ai_labels.get(user_lang):
        await update.message.reply_text(
            get_message("prompt_ai_menu", user_lang),
            reply_markup=get_ai_functions_keyboard(user_lang),
        )
        return AI_MENU
    # Unknown selection – repeat menu
    await update.message.reply_text(
        get_message("prompt_main_menu", user_lang),
        reply_markup=get_main_keyboard(user_lang),
    )
    return MAIN_MENU


async def ai_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Route user selection in the AI submenu."""
    text = (update.message.text or "").strip()
    user_lang: Language = context.user_data.get("lang", Language.en)
    # Localised labels
    labels = {
        "chat": {
            Language.en: "💬 Chat with AI",
            Language.ru: "💬 Чат с AI",
            Language.uz: "💬 AI bilan suhbat",
        },
        "generate": {
            Language.en: "🎨 Generate image",
            Language.ru: "🎨 Создать изображение",
            Language.uz: "🎨 Rasm yaratish",
        },
        "analyse": {
            Language.en: "🖼️ Image analysis",
            Language.ru: "🖼️ Анализ изображения",
            Language.uz: "🖼️ Rasm tahlili",
        },
        "pptx": {
            Language.en: "📊 Create presentation",
            Language.ru: "📊 Создать презентацию",
            Language.uz: "📊 Slayd tayyorlash",
        },
        "back": {
            Language.en: "⬅️ Back",
            Language.ru: "⬅️ Назад",
            Language.uz: "⬅️ Orqaga",
        },
    }
    if text == labels["chat"][user_lang]:
        # Reset chat history
        context.user_data["chat_history"] = []
        await update.message.reply_text(
            get_message("enter_chat", user_lang),
            reply_markup=get_back_keyboard(user_lang),
        )
        return CHAT
    if text == labels["generate"][user_lang]:
        await update.message.reply_text(
            get_message("ask_image_prompt", user_lang),
            reply_markup=get_back_keyboard(user_lang),
        )
        return IMAGE_GEN_PROMPT
    if text == labels["analyse"][user_lang]:
        await update.message.reply_text(
            get_message("ask_image_analysis", user_lang),
            reply_markup=get_back_keyboard(user_lang),
        )
        return IMAGE_ANALYSIS_WAIT_IMAGE
    if text == labels["pptx"][user_lang]:
        await update.message.reply_text(
            get_message("ask_ppt_title", user_lang),
            reply_markup=get_back_keyboard(user_lang),
        )
        return PPTX_WAIT_TITLE
    if text == labels["back"][user_lang]:
        await update.message.reply_text(
            get_message("prompt_main_menu", user_lang),
            reply_markup=get_main_keyboard(user_lang),
        )
        return MAIN_MENU
    # Unknown selection – repeat AI menu
    await update.message.reply_text(
        get_message("prompt_ai_menu", user_lang),
        reply_markup=get_ai_functions_keyboard(user_lang),
    )
    return AI_MENU
