"""
Handlers for AI‑related user interactions.

This module defines the logic for chatting with the AI, generating
images, analysing images, and creating PowerPoint presentations.  It
relies on the state machine defined in `handlers/state.py` and is
invoked by the main menu router when the user selects an AI function.
"""

from typing import List, Optional

from telegram import Update, InputMediaPhoto, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from models import User, StorageFile
from models_enums import Language, FileCategory, UserAction
from keyboard import get_ai_functions_keyboard, get_back_keyboard
from messages import get_message
from db import get_db, log_action
from utils.quotas import has_quota, increment_quota
from utils.openai_client import chat_with_ai, generate_image, analyze_image
from utils.pptx_creator import create_pptx
from handlers.state import (
    AI_MENU,
    CHAT,
    IMAGE_GEN_PROMPT,
    IMAGE_ANALYSIS_WAIT_IMAGE,
    PPTX_WAIT_TITLE,
    PPTX_WAIT_SLIDES,
)
from config import STORAGE_CHANNEL_ID


async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle messages during the chat session with the AI."""
    user_input = update.message.text
    # Check for exit command
    if user_input and user_input.strip().lower() in {"/done", "⬅️ back", "⬅️ orqaga", "⬅️ назад", "back", "orqaga", "назад"}:
        # Return to AI menu
        user_lang = context.user_data.get("lang", Language.en)
        await update.message.reply_text(
            get_message("prompt_ai_menu", user_lang),
            reply_markup=get_ai_functions_keyboard(user_lang),
        )
        return AI_MENU
    # Determine quota type
    quota_type = "quick_chat"
    if user_input and ("```" in user_input or "def " in user_input or "class " in user_input or "import " in user_input):
        quota_type = "code_chat"
    with get_db() as db:
        user: Optional[User] = db.query(User).filter(User.tg_id == update.effective_user.id).first()
        if not user:
            return AI_MENU  # Should not happen
        user_lang = user.lang or Language.en
        # Check quota
        if not has_quota(db, user, quota_type):
            await update.message.reply_text(
                get_message("quota_exceeded", user_lang),
                reply_markup=get_ai_functions_keyboard(user_lang),
            )
            return AI_MENU
        # Build conversation history from context
        history: List[dict] = context.user_data.get("chat_history", [])
        # Append user message
        history.append({"role": "user", "content": user_input})
        # Call OpenAI
        reply = await chat_with_ai(history)
        # Append assistant message to history for context
        history.append({"role": "assistant", "content": reply})
        context.user_data["chat_history"] = history
        # Increment quota
        increment_quota(db, user, quota_type, amount=1)
        log_action(db, user.id, UserAction.chat, meta={"mode": quota_type, "prompt": user_input, "reply": reply})
    # Respond to user
    await update.message.reply_text(reply)
    return CHAT


async def image_prompt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the prompt for image generation."""
    prompt = update.message.text
    user_lang = context.user_data.get("lang", Language.en)
    with get_db() as db:
        user: Optional[User] = db.query(User).filter(User.tg_id == update.effective_user.id).first()
        if not user:
            return AI_MENU
        # Use convert quota for image generation
        if not has_quota(db, user, "convert"):
            await update.message.reply_text(
                get_message("quota_exceeded", user_lang),
                reply_markup=get_ai_functions_keyboard(user_lang),
            )
            return AI_MENU
        # Generate image
        urls = await generate_image(prompt, n=1)
        if not urls:
            await update.message.reply_text(
                get_message("error_ai", user_lang),
                reply_markup=get_ai_functions_keyboard(user_lang),
            )
            return AI_MENU
        image_url = urls[0]
        # Send image to user
        await update.message.reply_photo(photo=image_url)
        # Increment quota and log
        increment_quota(db, user, "convert", amount=1)
        log_action(db, user.id, UserAction.image_generation, meta={"prompt": prompt, "image_url": image_url})
    # Return to AI menu
    await update.message.reply_text(
        get_message("prompt_ai_menu", user_lang),
        reply_markup=get_ai_functions_keyboard(user_lang),
    )
    return AI_MENU


async def image_analysis_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle image analysis once the user sends a photo."""
    # Expecting a photo document or photo
    photo = None
    if update.message.photo:
        # Take the largest resolution
        photo = update.message.photo[-1]
    elif update.message.document and update.message.document.mime_type.startswith("image/"):
        photo = update.message.document
    if not photo:
        user_lang = context.user_data.get("lang", Language.en)
        await update.message.reply_text(
            get_message("ask_image_analysis", user_lang),
            reply_markup=get_back_keyboard(user_lang),
        )
        return IMAGE_ANALYSIS_WAIT_IMAGE
    # Get file path
    file = await context.bot.get_file(photo.file_id)
    file_url = file.file_path
    user_lang = context.user_data.get("lang", Language.en)
    with get_db() as db:
        user: Optional[User] = db.query(User).filter(User.tg_id == update.effective_user.id).first()
        if not user:
            return AI_MENU
        # Use convert quota for analysis
        if not has_quota(db, user, "convert"):
            await update.message.reply_text(
                get_message("quota_exceeded", user_lang),
                reply_markup=get_ai_functions_keyboard(user_lang),
            )
            return AI_MENU
        description = await analyze_image(file_url)
        increment_quota(db, user, "convert", amount=1)
        log_action(db, user.id, UserAction.image_analysis, meta={"file_url": file_url, "description": description})
    await update.message.reply_text(description)
    # Return to AI menu
    await update.message.reply_text(
        get_message("prompt_ai_menu", user_lang),
        reply_markup=get_ai_functions_keyboard(user_lang),
    )
    return AI_MENU


async def ppt_title_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the title input for PPT creation."""
    title = update.message.text.strip()
    user_lang = context.user_data.get("lang", Language.en)
    # Save the title in user_data
    context.user_data["ppt_title"] = title
    await update.message.reply_text(
        get_message("ask_ppt_slides", user_lang),
        reply_markup=get_back_keyboard(user_lang),
    )
    return PPTX_WAIT_SLIDES


async def ppt_slides_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the slides content for PPT creation."""
    user_lang = context.user_data.get("lang", Language.en)
    # Extract slides.  Each line becomes a slide; if blank lines are
    # present they are ignored.  The first line of each slide will be
    # used as the slide title.
    slides_text = update.message.text.strip()
    lines = [line.strip() for line in slides_text.split("\n") if line.strip()]
    if not lines:
        await update.message.reply_text(
            get_message("ask_ppt_slides", user_lang),
            reply_markup=get_back_keyboard(user_lang),
        )
        return PPTX_WAIT_SLIDES
    title = context.user_data.get("ppt_title", "Presentation")
    # Create PPT
    file_path = create_pptx(title, lines)
    with get_db() as db:
        user: Optional[User] = db.query(User).filter(User.tg_id == update.effective_user.id).first()
        if not user:
            return AI_MENU
        # Check quota for pptx
        if not has_quota(db, user, "pptx"):
            await update.message.reply_text(
                get_message("quota_exceeded", user_lang),
                reply_markup=get_ai_functions_keyboard(user_lang),
            )
            return AI_MENU
        if file_path is None:
            await update.message.reply_text(
                "⚠️ PPTX creation failed because the python-pptx library is not installed.",
                reply_markup=get_ai_functions_keyboard(user_lang),
            )
            return AI_MENU
        # Send to storage channel and user
        # Upload to channel first
        try:
            with open(file_path, "rb") as f:
                channel_msg = await context.bot.send_document(
                    chat_id=STORAGE_CHANNEL_ID,
                    document=f,
                    filename=f"{title}.pptx",
                    caption=f"Presentation generated for {update.effective_user.first_name}",
                )
            # Save StorageFile entry
            storage_doc = channel_msg.document
            storage_file_id = storage_doc.file_id
            sf = StorageFile(
                owner_id=user.id,
                telegram_file_id=storage_file_id,
                storage_channel_id=STORAGE_CHANNEL_ID,
                storage_message_id=channel_msg.message_id,
                category=FileCategory.pptx,
                original_name=f"{title}.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                size_bytes=storage_doc.file_size or 0,
                extra={},
            )
            db.add(sf)
            # Send to user
            with open(file_path, "rb") as f:
                await context.bot.send_document(
                    chat_id=update.effective_user.id,
                    document=f,
                    filename=f"{title}.pptx",
                    caption=get_message("ppt_created", user_lang),
                )
            # Increment quota and log
            increment_quota(db, user, "pptx", amount=1)
            log_action(db, user.id, UserAction.pptx_creation, meta={"title": title, "slides": lines})
        except Exception as e:
            await update.message.reply_text(
                f"⚠️ Failed to send PPTX: {str(e)}",
                reply_markup=get_ai_functions_keyboard(user_lang),
            )
            return AI_MENU
    # Remove the temporary file
    try:
        import os
        os.remove(file_path)
    except Exception:
        pass
    # Clear temporary data
    context.user_data.pop("ppt_title", None)
    # Return to AI menu
    await update.message.reply_text(
        get_message("prompt_ai_menu", user_lang),
        reply_markup=get_ai_functions_keyboard(user_lang),
    )
    return AI_MENU
