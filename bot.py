"""
Main entry point for the Telegram AI assistant bot.

This module constructs the bot application, registers all conversation
handlers and starts polling.  It ties together the user flow defined
in `handlers/start.py` and `handlers/ai.py` with the admin panel in
`admin.py`.

To run the bot, execute this file as a module or script.  You must
provide a valid bot token via the TELEGRAM_TOKEN environment variable.
"""

import asyncio
import logging

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import TELEGRAM_TOKEN
from handlers.start import (
    start_command,
    handle_language_selection,
    main_menu_router,
    ai_menu_router,
)
from handlers.ai import (
    chat_handler,
    image_prompt_handler,
    image_analysis_handler,
    ppt_title_handler,
    ppt_slides_handler,
)
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


# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


async def cancel_command(update, context):
    """Allow the user to cancel any conversation."""
    from telegram.ext import ConversationHandler  # imported here to avoid circular import
    # Clear user state and return to main menu if possible
    user_lang = context.user_data.get("lang")
    from .keyboard import get_main_keyboard
    from .models_enums import Language
    lang = user_lang or Language.en
    await update.message.reply_text(
        "❌ Conversation cancelled.",
        reply_markup=get_main_keyboard(lang),
    )
    context.user_data.clear()
    return ConversationHandler.END


def main() -> None:
    """Create and run the bot application."""
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    # User conversation handler
    user_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            SELECT_LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_language_selection)],
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_router)],
            AI_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, ai_menu_router)],
            CHAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler)],
            IMAGE_GEN_PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, image_prompt_handler)],
            IMAGE_ANALYSIS_WAIT_IMAGE: [
                MessageHandler((filters.PHOTO | filters.Document.IMAGE) & ~filters.COMMAND, image_analysis_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, image_analysis_handler),
            ],
            PPTX_WAIT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ppt_title_handler)],
            PPTX_WAIT_SLIDES: [MessageHandler(filters.TEXT & ~filters.COMMAND, ppt_slides_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
        name="user_conversation",
        persistent=False,
    )
    # Register handlers
    application.add_handler(user_conv)
    # Admin handlers
    from admin import get_admin_handlers
    for handler in get_admin_handlers():
        application.add_handler(handler)
    # Run the bot
    application.run_polling()


if __name__ == "__main__":
    main()
