"""
Main Telegram Bot Application

SHOWS ALL ERRORS IN TERMINAL - Perfect for debugging!
All logs displayed in console + saved to file
"""

import logging
import sys
import asyncio

from handlers.file_operations import file_operations_handler

# ============================================================================
# WINDOWS EVENT LOOP FIX - Must be at the top before other imports!
# ============================================================================
if sys.platform == 'win32':
    # Fix for Windows semaphore timeout issues
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    logging.info("Applied Windows event loop policy fix")

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    PicklePersistence,
)

from config import TELEGRAM_TOKEN
from db import init_db, check_db_health
from models_enums import Language
from keyboard import get_main_keyboard

# Import handlers
from handlers.start import (
    start_command,
    handle_language_selection,
    main_menu_router,
    ai_menu_router,
    profile_menu_router,
    change_language_handler,
    add_phone_handler,
)
from handlers.ai import chat_handler
from handlers.image_edit import image_edit_handler
from handlers.state import (
    SELECT_LANGUAGE,
    MAIN_MENU,
    AI_MENU,
    CHAT,
    IMAGE_EDIT,
    PROFILE_MENU,
    CHANGE_LANGUAGE,
    ADD_PHONE, FILE_OPERATIONS,
)

# ============================================================================
# LOGGING CONFIGURATION - SHOWS EVERYTHING IN TERMINAL!
# ============================================================================

# Create formatters
detailed_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
simple_formatter = logging.Formatter(
    '%(levelname)s - %(message)s'
)

# Console handler (prints to terminal)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(simple_formatter)

# File handler (saves to bot.log)
file_handler = logging.FileHandler("bot.log", encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(detailed_formatter)

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(console_handler)
root_logger.addHandler(file_handler)

# Enable detailed logging for network issues
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Our logger
logger = logging.getLogger(__name__)


# ============================================================================
# CANCEL COMMAND
# ============================================================================

async def cancel_command(update, context):
    """Handle /cancel command - exit conversation."""
    from telegram.ext import ConversationHandler as CH

    lang = context.user_data.get("lang", Language.en)

    cancel_msg = {
        Language.en: "Operation cancelled.",
        Language.ru: "Операция отменена.",
        Language.uz: "Amal bekor qilindi."
    }[lang]

    await update.message.reply_text(
        cancel_msg,
        reply_markup=get_main_keyboard(lang, False)
    )

    context.user_data.clear()
    return CH.END


# ============================================================================
# ERROR HANDLER - SHOWS FULL ERROR IN TERMINAL
# ============================================================================

async def error_handler(update, context):
    """
    Log errors with full traceback - displays in terminal!
    """
    # Log to console and file with full details
    logger.error(
        "=" * 60 + "\n" +
        "ERROR OCCURRED!\n" +
        "=" * 60 + "\n" +
        f"Update: {update}\n" +
        f"Error: {context.error}\n" +
        "=" * 60,
        exc_info=context.error
    )

    # Try to notify user (with retry logic)
    try:
        if update and update.effective_message:
            from utils.network_retry import safe_send_message

            error_msg = {
                Language.en: "An error occurred. Please try again or contact support.",
                Language.ru: "Произошла ошибка. Попробуйте снова или обратитесь в поддержку.",
                Language.uz: "Xatolik yuz berdi. Qaytadan urinib ko'ring yoki qo'llab-quvvatlashga murojaat qiling."
            }

            lang = context.user_data.get("lang", Language.en)
            await safe_send_message(
                update.effective_message,
                error_msg.get(lang, error_msg[Language.en]),
                max_retries=2  # Fewer retries in error handler
            )
    except Exception as e:
        logger.error(f"Failed to send error message to user: {e}")


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main() -> None:
    """Initialize and run the bot."""

    print("\n" + "=" * 60)
    print("AI ASSISTANT TELEGRAM BOT")
    print("=" * 60 + "\n")

    # ========================================================================
    # INITIALIZE DATABASE
    # ========================================================================
    logger.info("Initializing database...")
    try:
        init_db()
        logger.info("Database initialized successfully")

        if not check_db_health():
            logger.error("Database health check failed!")
            sys.exit(1)
        logger.info("Database health check passed")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        sys.exit(1)

    # ========================================================================
    # CREATE PERSISTENCE
    # ========================================================================
    logger.info("Creating persistence...")
    persistence = PicklePersistence(filepath="bot_state.pkl")

    # ========================================================================
    # BUILD APPLICATION WITH OPTIMIZED SETTINGS
    # ========================================================================
    logger.info("Building application...")
    try:
        application = (
            ApplicationBuilder()
            .token(TELEGRAM_TOKEN)
            .persistence(persistence)
            .concurrent_updates(True)
            .connection_pool_size(8)
            .pool_timeout(30.0)
            .connect_timeout(30.0)
            .read_timeout(30.0)
            .write_timeout(30.0)
            .build()
        )
        logger.info("Application built successfully")
    except Exception as e:
        logger.error(f"Failed to build application: {e}", exc_info=True)
        sys.exit(1)

    # ========================================================================
    # LOAD ADMIN HANDLERS
    # ========================================================================
    try:
        from admin import get_admin_handlers

        for handler in get_admin_handlers():
            application.add_handler(handler)

        logger.info("Admin handlers loaded successfully")
    except ImportError:
        logger.warning("Admin module not found - admin features disabled")
    except Exception as e:
        logger.warning(f"Admin handlers not loaded: {e}")

    # ========================================================================
    # REGISTER USER CONVERSATION HANDLER
    # ========================================================================
    logger.info("Registering conversation handlers...")

    user_conversation = ConversationHandler(
        entry_points=[
            CommandHandler("start", start_command)
        ],
        states={
            SELECT_LANGUAGE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_language_selection
                )
            ],
            MAIN_MENU: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    main_menu_router
                )
            ],
            AI_MENU: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    ai_menu_router
                )
            ],
            CHAT: [
                MessageHandler(
                    (filters.TEXT | filters.PHOTO | filters.Document.IMAGE) & ~filters.COMMAND,
                    chat_handler
                )
            ],
            IMAGE_EDIT: [
                MessageHandler(
                    (filters.TEXT | filters.PHOTO | filters.Document.IMAGE) & ~filters.COMMAND,
                    image_edit_handler
                )
            ],
            PROFILE_MENU: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    profile_menu_router
                )
            ],
            CHANGE_LANGUAGE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    change_language_handler
                )
            ],
            ADD_PHONE: [
                MessageHandler(
                    (filters.CONTACT | filters.TEXT) & ~filters.COMMAND,
                    add_phone_handler
                )
            ],
            FILE_OPERATIONS: [
                MessageHandler(
                    (filters.TEXT | filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND,
                    file_operations_handler
                )
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_command)
        ],
        name="user_conversation",
        persistent=True,
        allow_reentry=True,
    )

    application.add_handler(user_conversation)
    logger.info("User conversation handler registered")

    # ========================================================================
    # REGISTER ERROR HANDLER
    # ========================================================================
    application.add_error_handler(error_handler)
    logger.info("Error handler registered")

    # ========================================================================
    # START BOT
    # ========================================================================
    print("\n" + "=" * 60)
    print("BOT IS RUNNING!")
    print("=" * 60)
    print("\nConfiguration:")
    print("  - Concurrent updates: ENABLED")
    print("  - Connection pool: 8")
    print("  - Timeouts: 30 seconds")
    print("  - Logging: INFO level")
    print("  - Error display: TERMINAL + FILE")
    if sys.platform == 'win32':
        print("  - Windows event loop: FIXED")
    print("\n" + "=" * 60)
    print("All errors will be shown here in the terminal!")
    print("Also saving detailed logs to: bot.log")
    print("=" * 60)
    print("\nPress Ctrl+C to stop\n")

    # Run the bot
    try:
        logger.info("Starting polling...")
        application.run_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True
        )
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
        print("\n\nBot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error during polling: {e}", exc_info=True)
        print(f"\n\nFATAL ERROR: {e}")
        print("Check the error above for details!")
        raise


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nBot stopped by user")
        sys.exit(0)
    except Exception as e:
        print("\n" + "=" * 60)
        print("FATAL ERROR!")
        print("=" * 60)
        print(f"\n{e}\n")
        print("Check bot.log for full details")
        print("=" * 60 + "\n")
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        sys.exit(1)
