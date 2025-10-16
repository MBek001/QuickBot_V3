"""
Start command and menu navigation handlers.

FIXED VERSION:
- Removed duplicate message sends
- Proper trial limit imports from config
- Added file operations menu
"""

import logging
from datetime import date
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_IDS, TRIAL_PERIOD_DAYS, TRIAL_USES_PER_PERIOD
from db import get_db, log_action
from models import User, Plan, QuotaUsage
from models_enums import Language, PlanCode, UserAction
from keyboard import (
    get_language_keyboard, get_main_keyboard, get_ai_functions_keyboard,
    get_back_keyboard, get_profile_keyboard, get_phone_share_keyboard,
    get_file_operations_keyboard  # 🆕 NEW
)
from messages import get_message
from handlers.state import (
    SELECT_LANGUAGE, MAIN_MENU, AI_MENU, CHAT, IMAGE_EDIT,
    PROFILE_MENU, CHANGE_LANGUAGE, ADD_PHONE, FILE_OPERATIONS  # 🆕 NEW
)
from utils.quotas import maybe_reset_trial, get_quota_status

logger = logging.getLogger(__name__)


# ============================================================================
# START COMMAND
# ============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle /start command - initialize or resume user session.

    Creates new users and directs to language selection or main menu.
    """
    tg_user = update.effective_user

    logger.info(f"👤 /start from user {tg_user.id} (@{tg_user.username})")

    with get_db() as db:
        # Get or create user
        user: Optional[User] = db.query(User).filter(User.tg_id == tg_user.id).first()

        # Ensure free plan exists
        free_plan = db.query(Plan).filter(Plan.code == PlanCode.free).first()
        if not free_plan:
            free_plan = Plan(
                code=PlanCode.free,
                title="Free Plan",
                description="Basic features with daily limits"
            )
            db.add(free_plan)
            db.flush()

        # Create new user if doesn't exist
        if not user:
            user = User(
                tg_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                plan_code=PlanCode.free,
                is_admin=tg_user.id in ADMIN_IDS,
            )
            db.add(user)
            db.flush()

            log_action(db, user.id, UserAction.profile_view, meta={"action": "registration"})
            logger.info(f"✅ New user created: {user.full_name} (TG: {tg_user.id})")

        # Update user info if changed
        else:
            changed = False
            if user.username != tg_user.username:
                user.username = tg_user.username
                changed = True
            if user.first_name != tg_user.first_name:
                user.first_name = tg_user.first_name
                changed = True
            if user.last_name != tg_user.last_name:
                user.last_name = tg_user.last_name
                changed = True

            if changed:
                db.add(user)
                logger.info(f"🔄 Updated user info: {user.full_name}")

        # Check trial reset (don't notify here, will notify in AI menu)
        maybe_reset_trial(db, user)

        user_lang = user.lang
        is_premium = user.is_premium

    # Store language in context
    if user_lang:
        context.user_data["lang"] = user_lang

    # If no language set, show language selection
    if not user_lang:
        await update.message.reply_text(
            get_message("welcome", Language.en),
            reply_markup=get_language_keyboard(),
        )
        return SELECT_LANGUAGE

    # Otherwise, show main menu
    await update.message.reply_text(
        get_message("prompt_main_menu", user_lang),
        reply_markup=get_main_keyboard(user_lang, is_premium),
    )
    return MAIN_MENU


# ============================================================================
# LANGUAGE SELECTION
# ============================================================================

async def handle_language_selection(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle language selection from welcome screen."""
    selection = (update.message.text or "").lower()

    # Parse language from button text
    if "english" in selection or "🇬🇧" in selection:
        lang = Language.en
    elif "рус" in selection or "🇷🇺" in selection:
        lang = Language.ru
    elif any(x in selection for x in ["o'bek", "ozbek", "🇺🇿", "o'zbek"]):
        lang = Language.uz
    else:
        lang = Language.en

    logger.info(f"🌐 User selected language: {lang}")

    # Save language to database and context
    context.user_data["lang"] = lang

    with get_db() as db:
        user = db.query(User).filter(User.tg_id == update.effective_user.id).first()
        if user:
            user.lang = lang
            db.add(user)
            log_action(db, user.id, UserAction.language_change, meta={"language": lang.value})
            is_premium = user.is_premium
        else:
            is_premium = False

    await update.message.reply_text(
        get_message("prompt_main_menu", lang),
        reply_markup=get_main_keyboard(lang, is_premium),
    )
    return MAIN_MENU


# ============================================================================
# MAIN MENU ROUTER
# ============================================================================

async def main_menu_router(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Route user selection from main menu."""
    text = (update.message.text or "").strip()
    user_lang: Language = context.user_data.get("lang", Language.en)

    logger.info(f"📱 Main menu selection: {text}")

    with get_db() as db:
        user = db.query(User).filter(User.tg_id == update.effective_user.id).first()
        if not user:
            await update.message.reply_text("⚠️ Error: User not found. Please /start again.")
            return MAIN_MENU

        # Define button labels
        ai_labels = {
            Language.en: "🤖 AI functions",
            Language.ru: "🤖 AI функции",
            Language.uz: "🤖 AI funksiyalari",
        }

        # 🆕 NEW: File operations labels
        file_labels = {
            Language.en: "📁 File Operations",
            Language.ru: "📁 Работа с файлами",
            Language.uz: "📁 Fayllar bilan ishlash",
        }

        profile_labels = {
            Language.en: "👤 Profile",
            Language.ru: "👤 Профиль",
            Language.uz: "👤 Profil",
        }
        premium_labels = {
            Language.en: "💎 Premium",
            Language.ru: "💎 Премиум",
            Language.uz: "💎 Premium",
        }

        # AI Functions
        if text == ai_labels.get(user_lang):
            # Check and notify about trial resets
            if maybe_reset_trial(db, user):
                await update.message.reply_text(
                    get_message(
                        "trial_renewed",
                        user_lang,
                        feature="All Features",
                        total=TRIAL_USES_PER_PERIOD,
                        days=TRIAL_PERIOD_DAYS
                    )
                )

            await update.message.reply_text(
                get_message("prompt_ai_menu", user_lang),
                reply_markup=get_ai_functions_keyboard(user_lang, user.is_premium, user.is_admin),
            )
            return AI_MENU

        # 🆕 NEW: File Operations
        if text == file_labels.get(user_lang):
            await update.message.reply_text(
                get_message("prompt_file_menu", user_lang),
                reply_markup=get_file_operations_keyboard(user_lang),
            )
            return FILE_OPERATIONS

        # Profile
        if text == profile_labels.get(user_lang):
            await update.message.reply_text(
                "👤 Profile",
                reply_markup=get_profile_keyboard(user_lang, user.is_admin),
            )
            return PROFILE_MENU

        # Premium
        if text == premium_labels.get(user_lang):
            if user.is_premium or user.is_admin:
                if user_lang == Language.ru:
                    msg = "✨ У вас уже есть Премиум!"
                elif user_lang == Language.uz:
                    msg = "✨ Sizda allaqachon Premium bor!"
                else:
                    msg = "✨ You already have Premium!"
            else:
                msg = get_message("premium_required", user_lang)

            await update.message.reply_text(
                msg,
                reply_markup=get_main_keyboard(user_lang, user.is_premium)
            )
            return MAIN_MENU

    # Unknown selection - show menu again
    await update.message.reply_text(
        get_message("prompt_main_menu", user_lang),
        reply_markup=get_main_keyboard(user_lang, user.is_premium if user else False),
    )
    return MAIN_MENU


# ============================================================================
# AI MENU ROUTER
# ============================================================================

async def ai_menu_router(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Route user selection from AI functions menu."""
    text = (update.message.text or "").strip()
    user_lang: Language = context.user_data.get("lang", Language.en)

    logger.info(f"🤖 AI menu selection: {text}")

    with get_db() as db:
        user = db.query(User).filter(User.tg_id == update.effective_user.id).first()
        if not user:
            await update.message.reply_text("⚠️ Error: User not found. Please /start again.")
            return AI_MENU

        # Define labels
        labels = {
            "chat": {
                Language.en: "💬 Chat with AI",
                Language.ru: "💬 Чат с AI",
                Language.uz: "💬 AI bilan suhbat",
            },
            "image_edit": {
                Language.en: "🛠 Image Editing",
                Language.ru: "🛠 Редактирование изображения",
                Language.uz: "🛠 Rasmni tahrirlash",
            },
            "back": {
                Language.en: "⬅️ Back",
                Language.ru: "⬅️ Назад",
                Language.uz: "⬅️ Orqaga",
            },
        }

        # Chat (free feature)
        if text == labels["chat"][user_lang]:
            context.user_data["chat_history"] = []
            context.user_data["chat_mode"] = "normal"

            await update.message.reply_text(
                get_message("enter_chat", user_lang),
                reply_markup=get_back_keyboard(user_lang)
            )
            return CHAT

        # 🔧 FIXED: Image Editing - Check ALL possible button texts
        if (text == labels["image_edit"][user_lang] or
                "🛠" in text or
                "tahrirlash" in text.lower() or
                "редактирование" in text.lower() or
                "editing" in text.lower() or
                "trial" in text.lower() or
                "sinov" in text.lower()):
            context.user_data["chat_mode"] = "image_edit"
            context.user_data.pop("regen_image_file_id", None)

            await update.message.reply_text(
                get_message("enter_image_edit", user_lang),
                reply_markup=get_back_keyboard(user_lang)
            )
            return IMAGE_EDIT

        # Image Generation
        if any(x in text for x in ["🎨", "Generate", "Генерация", "yaratish", "Rasm"]):
            context.user_data["chat_history"] = []
            context.user_data["chat_mode"] = "image_gen"

            await update.message.reply_text(
                get_message("enter_image_gen", user_lang),
                reply_markup=get_back_keyboard(user_lang)
            )
            return CHAT

        # PPTX Creation
        if any(x in text for x in ["📊", "Presentation", "презентацию", "Taqdimot", "PPTX"]):
            context.user_data["chat_history"] = []
            context.user_data["chat_mode"] = "pptx"
            context.user_data["pptx_state"] = "await_theme"

            from keyboard import get_pptx_theme_keyboard
            await update.message.reply_text(
                get_message("enter_pptx", user_lang),
                reply_markup=get_pptx_theme_keyboard(user_lang)
            )
            return CHAT

        # Back button
        if text == labels["back"][user_lang]:
            await update.message.reply_text(
                get_message("prompt_main_menu", user_lang),
                reply_markup=get_main_keyboard(user_lang, user.is_premium),
            )
            return MAIN_MENU

    # Unknown selection
    await update.message.reply_text(
        get_message("prompt_ai_menu", user_lang),
        reply_markup=get_ai_functions_keyboard(
            user_lang,
            user.is_premium if user else False,
            user.is_admin if user else False
        ),
    )
    return AI_MENU


# ============================================================================
# PROFILE MENU ROUTER
# ============================================================================

async def profile_menu_router(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Route user selection from profile menu."""
    text = (update.message.text or "").strip()
    user_lang: Language = context.user_data.get("lang", Language.en)

    logger.info(f"👤 Profile menu selection: {text}")

    with get_db() as db:
        user = db.query(User).filter(User.tg_id == update.effective_user.id).first()
        if not user:
            await update.message.reply_text("⚠️ Error: User not found. Please /start again.")
            return MAIN_MENU

        # Define labels
        stats_labels = {
            Language.en: "📊 My Statistics",
            Language.ru: "📊 Моя статистика",
            Language.uz: "📊 Mening statistikam",
        }
        lang_labels = {
            Language.en: "🌐 Change Language",
            Language.ru: "🌐 Изменить язык",
            Language.uz: "🌐 Tilni o'zgartirish",
        }
        phone_labels = {
            Language.en: "📱 Add Phone",
            Language.ru: "📱 Добавить телефон",
            Language.uz: "📱 Telefon qo'shish",
        }
        back_labels = {
            Language.en: "⬅️ Back",
            Language.ru: "⬅️ Назад",
            Language.uz: "⬅️ Orqaga",
        }

        # Statistics
        if text == stats_labels.get(user_lang):
            quota_status = get_quota_status(db, user)

            chats_used = quota_status["quick_chat"][0] + quota_status["code_chat"][0]
            chats_limit = quota_status["quick_chat"][1] + quota_status["code_chat"][1]

            premium_text = {
                Language.en: "✅ Active" if user.is_premium else "❌ Not Active",
                Language.ru: "✅ Активен" if user.is_premium else "❌ Не активен",
                Language.uz: "✅ Faol" if user.is_premium else "❌ Faol emas",
            }[user_lang]

            plan_text = "Premium" if user.is_premium else "Free"

            phone_display = user.phone or {
                Language.en: "Not added",
                Language.ru: "Не добавлен",
                Language.uz: "Qo'shilmagan"
            }[user_lang]

            # Build message without markdown to avoid parse errors
            if user_lang == Language.ru:
                msg = (
                    "👤 Ваш профиль\n\n"
                    f"📋 План: {plan_text}\n"
                    f"💎 Премиум: {premium_text}\n\n"
                    "📊 Использовано сегодня:\n"
                    f"  • Чаты: {chats_used}/{chats_limit}\n"
                    f"  • Конверсии: {quota_status['convert'][0]}/{quota_status['convert'][1]}\n"
                    f"  • PPTX: {quota_status['pptx'][0]}/{quota_status['pptx'][1]}\n"
                    f"📱 Телефон: {phone_display}"
                )
            elif user_lang == Language.uz:
                msg = (
                    "👤 Sizning profilingiz\n\n"
                    f"📋 Reja: {plan_text}\n"
                    f"💎 Premium: {premium_text}\n\n"
                    "📊 Bugungi foydalanish:\n"
                    f"  • Suhbatlar: {chats_used}/{chats_limit}\n"
                    f"  • Konversiyalar: {quota_status['convert'][0]}/{quota_status['convert'][1]}\n"
                    f"  • PPTX: {quota_status['pptx'][0]}/{quota_status['pptx'][1]}\n"
                    f"📱 Telefon: {phone_display}"
                )
            else:  # English
                msg = (
                    "👤 Your Profile\n\n"
                    f"📋 Plan: {plan_text}\n"
                    f"💎 Premium: {premium_text}\n\n"
                    "📊 Today's Usage:\n"
                    f"  • Chats: {chats_used}/{chats_limit}\n"
                    f"  • Conversions: {quota_status['convert'][0]}/{quota_status['convert'][1]}\n"
                    f"  • PPTX: {quota_status['pptx'][0]}/{quota_status['pptx'][1]}\n"
                    f"📱 Phone: {phone_display}"
                )

            await update.message.reply_text(
                msg,
                reply_markup=get_profile_keyboard(user_lang, user.is_admin)
            )
            return PROFILE_MENU

        # Change Language
        if text == lang_labels.get(user_lang):
            msg = {
                Language.en: "🌐 Select your language:",
                Language.ru: "🌐 Выберите язык:",
                Language.uz: "🌐 Tilni tanlang:"
            }[user_lang]

            await update.message.reply_text(msg, reply_markup=get_language_keyboard())
            return CHANGE_LANGUAGE

        # Add Phone
        if text == phone_labels.get(user_lang):
            await update.message.reply_text(
                get_message("phone_request", user_lang),
                reply_markup=get_phone_share_keyboard(user_lang)
            )
            return ADD_PHONE

        # Back
        if text == back_labels.get(user_lang):
            await update.message.reply_text(
                get_message("prompt_main_menu", user_lang),
                reply_markup=get_main_keyboard(user_lang, user.is_premium),
            )
            return MAIN_MENU

    # Unknown selection
    await update.message.reply_text(
        "👤 Profile",
        reply_markup=get_profile_keyboard(user_lang, user.is_admin if user else False)
    )
    return PROFILE_MENU


# ============================================================================
# CHANGE LANGUAGE HANDLER
# ============================================================================

async def change_language_handler(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle language change from profile menu."""
    selection = (update.message.text or "").lower()

    # Parse language
    if "english" in selection or "🇬🇧" in selection:
        lang = Language.en
    elif "рус" in selection or "🇷🇺" in selection:
        lang = Language.ru
    elif any(x in selection for x in ["o'bek", "ozbek", "🇺🇿", "o'zbek"]):
        lang = Language.uz
    else:
        lang = Language.en

    logger.info(f"🌐 User changed language to: {lang}")

    context.user_data["lang"] = lang

    with get_db() as db:
        user = db.query(User).filter(User.tg_id == update.effective_user.id).first()
        if user:
            user.lang = lang
            db.add(user)
            log_action(db, user.id, UserAction.language_change, meta={"language": lang.value})
            is_admin = user.is_admin
        else:
            is_admin = False

    await update.message.reply_text(
        get_message("language_changed", lang),
        reply_markup=get_profile_keyboard(lang, is_admin)
    )
    return PROFILE_MENU


# ============================================================================
# ADD PHONE HANDLER
# ============================================================================

async def add_phone_handler(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle phone number sharing."""
    message = update.message
    user_lang: Language = context.user_data.get("lang", Language.en)
    contact = message.contact
    text = (message.text or "").strip().lower() if message.text else ""

    # Back button
    if text in {"⬅️ back", "⬅️ orqaga", "⬅️ назад", "back", "orqaga", "назад"}:
        with get_db() as db:
            user = db.query(User).filter(User.tg_id == update.effective_user.id).first()
            is_admin = user.is_admin if user else False

        await message.reply_text(
            "👤 Profile",
            reply_markup=get_profile_keyboard(user_lang, is_admin)
        )
        return PROFILE_MENU

    # Handle contact
    if not contact or not contact.phone_number:
        await message.reply_text(
            get_message("phone_request", user_lang),
            reply_markup=get_phone_share_keyboard(user_lang)
        )
        return ADD_PHONE

    phone_number = contact.phone_number
    logger.info(f"📱 User shared phone: {phone_number}")

    with get_db() as db:
        user = db.query(User).filter(User.tg_id == update.effective_user.id).first()
        if user:
            user.phone = phone_number
            db.add(user)
            log_action(db, user.id, UserAction.phone_added, meta={"phone": phone_number})
            is_admin = user.is_admin
        else:
            is_admin = False

    await message.reply_text(
        get_message("phone_added", user_lang),
        reply_markup=get_profile_keyboard(user_lang, is_admin)
    )
    return PROFILE_MENU
