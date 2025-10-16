"""
File operations handler.

Features:
- DOC/DOCX to PDF conversion
- TXT to PDF conversion
- File renaming
- Manual PPTX creation
- PDF merging
- OCR (text extraction from images)
"""

import logging
from typing import Optional

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from models import User
from models_enums import Language, UserAction
from keyboard import get_file_operations_keyboard, get_back_keyboard, get_main_keyboard
from messages import get_message
from db import get_db, log_action
from utils.quotas import increment_quota
from handlers.state import FILE_OPERATIONS, MAIN_MENU

logger = logging.getLogger(__name__)

_BACK_WORDS = {
    "/done", "⬅️ back", "⬅️ orqaga", "⬅️ назад",
    "back", "orqaga", "назад"
}


def _resolve_lang(raw) -> Language:
    """Resolve language from various input types."""
    if isinstance(raw, Language):
        return raw
    if isinstance(raw, str):
        low = raw.lower()
        if low.startswith("uz"):
            return Language.uz
        if low.startswith("ru"):
            return Language.ru
    return Language.en


async def file_operations_handler(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handle file operations menu routing and processing.
    """
    message = update.message
    if not message:
        return FILE_OPERATIONS

    user_lang = _resolve_lang(context.user_data.get("lang", Language.en))
    text = (message.text or "").strip()

    # Handle back button
    if text.lower() in _BACK_WORDS:
        with get_db() as db:
            user = db.query(User).filter(User.tg_id == update.effective_user.id).first()
            is_premium = bool(user.is_premium) if user else False

        await message.reply_text(
            get_message("prompt_main_menu", user_lang),
            reply_markup=get_main_keyboard(user_lang, is_premium)
        )
        return MAIN_MENU

    with get_db() as db:
        user: Optional[User] = db.query(User).filter(
            User.tg_id == update.effective_user.id
        ).first()

        if not user:
            await message.reply_text("⚠️ User not found. Please /start again.")
            return MAIN_MENU

        # Define operation labels
        operations = {
            "doc_to_pdf": {
                Language.en: "📄 DOC → PDF",
                Language.ru: "📄 DOC → PDF",
                Language.uz: "📄 DOC → PDF",
            },
            "txt_to_pdf": {
                Language.en: "📝 TXT → PDF",
                Language.ru: "📝 TXT → PDF",
                Language.uz: "📝 TXT → PDF",
            },
            "rename": {
                Language.en: "✏️ Rename File",
                Language.ru: "✏️ Переименовать файл",
                Language.uz: "✏️ Fayl nomini o'zgartirish",
            },
            "manual_pptx": {
                Language.en: "📊 Create PPTX Manually",
                Language.ru: "📊 Создать PPTX вручную",
                Language.uz: "📊 PPTX qo'lda yaratish",
            },
            "merge_pdf": {
                Language.en: "🔗 Merge PDFs",
                Language.ru: "🔗 Объединить PDF",
                Language.uz: "🔗 PDF birlashtirish",
            },
            "ocr": {
                Language.en: "🔍 OCR (Extract Text)",
                Language.ru: "🔍 OCR (текст из фото)",
                Language.uz: "🔍 OCR (rasmdan matn)",
            },
        }

        # Route to operation
        for op_key, op_labels in operations.items():
            if text == op_labels.get(user_lang):
                context.user_data["file_operation"] = op_key

                # Send instructions
                await message.reply_text(
                    get_message(f"enter_{op_key}", user_lang),
                    reply_markup=get_back_keyboard(user_lang)
                )
                return FILE_OPERATIONS

        # Handle file processing based on active operation
        current_op = context.user_data.get("file_operation")

        if current_op == "ocr":
            return await _handle_ocr(message, context, db, user, user_lang)
        elif current_op == "doc_to_pdf":
            return await _handle_doc_to_pdf(message, context, db, user, user_lang)
        elif current_op == "txt_to_pdf":
            return await _handle_txt_to_pdf(message, context, db, user, user_lang)
        elif current_op == "rename":
            return await _handle_rename(message, context, db, user, user_lang)
        elif current_op == "manual_pptx":
            return await _handle_manual_pptx(message, context, db, user, user_lang)
        elif current_op == "merge_pdf":
            return await _handle_merge_pdf(message, context, db, user, user_lang)

    # Default: show menu
    await message.reply_text(
        get_message("prompt_file_menu", user_lang),
        reply_markup=get_file_operations_keyboard(user_lang)
    )
    return FILE_OPERATIONS


# ============================================================================
# OPERATION HANDLERS
# ============================================================================

async def _handle_ocr(message, context, db, user, user_lang) -> int:
    """Extract text from image using OCR."""
    # Check if image sent
    has_photo = bool(message.photo)
    has_image_doc = (
            message.document
            and message.document.mime_type
            and message.document.mime_type.startswith("image/")
    )

    if not (has_photo or has_image_doc):
        await message.reply_text(get_message("enter_ocr", user_lang))
        return FILE_OPERATIONS

    try:
        # Download image
        if has_photo:
            file_id = message.photo[-1].file_id
        else:
            file_id = message.document.file_id

        tg_file = await context.bot.get_file(file_id)
        image_bytes = await tg_file.download_as_bytearray()

        await context.bot.send_chat_action(
            chat_id=message.chat_id,
            action=ChatAction.TYPING
        )

        # Use OpenAI Vision for OCR
        import base64
        from utils.openai_client import chat_with_ai

        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        ocr_prompt = {
            Language.en: "Extract ALL text from this image. Provide the text exactly as it appears, preserving formatting and structure.",
            Language.ru: "Извлеките ВЕСЬ текст с этого изображения. Предоставьте текст точно так, как он отображается, сохраняя форматирование и структуру.",
            Language.uz: "Ushbu rasmdan BARCHA matnni ajratib oling. Matnni formatlash va tuzilishni saqlab, aynan ko'ringanidek taqdim eting."
        }[user_lang]

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": ocr_prompt
                    }
                ]
            }
        ]

        extracted_text = await chat_with_ai(
            messages,
            model="gpt-4o",
            max_tokens=2000
        )

        if extracted_text and not extracted_text.startswith("❌"):
            success_msg = {
                Language.en: "✅ Text Extracted:\n\n",
                Language.ru: "✅ Текст извлечён:\n\n",
                Language.uz: "✅ Matn ajratildi:\n\n"
            }[user_lang]

            # Send in chunks if too long
            full_response = success_msg + extracted_text
            if len(full_response) > 4000:
                for i in range(0, len(full_response), 4000):
                    await message.reply_text(full_response[i:i + 4000])
            else:
                await message.reply_text(full_response)

            increment_quota(db, user, "convert", amount=1)
            log_action(db, user.id, UserAction.file_upload, meta={"operation": "ocr"})
        else:
            await message.reply_text(get_message("error_ai", user_lang))

    except Exception as e:
        logger.error(f"❌ OCR error: {e}", exc_info=True)
        await message.reply_text(f"❌ {get_message('error_general', user_lang)}")

    return FILE_OPERATIONS


async def _handle_doc_to_pdf(message, context, db, user, user_lang) -> int:
    """Convert DOC/DOCX to PDF."""
    await message.reply_text(
        "🚧 DOC to PDF conversion coming soon!\n\nThis feature is under development.",
        reply_markup=get_file_operations_keyboard(user_lang)
    )
    return FILE_OPERATIONS


async def _handle_txt_to_pdf(message, context, db, user, user_lang) -> int:
    """Convert TXT to PDF."""
    await message.reply_text(
        "🚧 TXT to PDF conversion coming soon!\n\nThis feature is under development.",
        reply_markup=get_file_operations_keyboard(user_lang)
    )
    return FILE_OPERATIONS


async def _handle_rename(message, context, db, user, user_lang) -> int:
    """Rename a file."""
    await message.reply_text(
        "🚧 File renaming coming soon!\n\nThis feature is under development.",
        reply_markup=get_file_operations_keyboard(user_lang)
    )
    return FILE_OPERATIONS


async def _handle_manual_pptx(message, context, db, user, user_lang) -> int:
    """Create PPTX manually from user content."""
    await message.reply_text(
        "🚧 Manual PPTX creation coming soon!\n\nThis feature is under development.",
        reply_markup=get_file_operations_keyboard(user_lang)
    )
    return FILE_OPERATIONS


async def _handle_merge_pdf(message, context, db, user, user_lang) -> int:
    """Merge multiple PDFs."""
    await message.reply_text(
        "🚧 PDF merging coming soon!\n\nThis feature is under development.",
        reply_markup=get_file_operations_keyboard(user_lang)
    )
    return FILE_OPERATIONS
