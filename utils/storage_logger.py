"""
Enhanced storage logger with comprehensive metadata tracking.

Stores all files and images to Telegram channel with detailed information.
"""

import hashlib
import logging
import os
import mimetypes
from io import BytesIO
from datetime import datetime
from telegram import InputFile
from models import StorageFile, ActionLog
from models_enums import FileCategory, UserAction
from config import STORAGE_CHANNEL_ID

logger = logging.getLogger(__name__)


# ================================================================
# INTERNAL HELPERS
# ================================================================
def _sha256_from_bytes(data: bytes) -> str:
    """Compute SHA-256 hash for content fingerprinting."""
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def _guess_mime(filename: str) -> str:
    """Guess MIME type from filename."""
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


def _format_file_caption(user, category: FileCategory, prompt: str = "",
                         model: str = "", extra_info: dict = None) -> str:
    """
    Format detailed caption for storage channel.

    Args:
        user: User object
        category: File category (image_gen, image_edit, pptx, etc.)
        prompt: User's prompt/request
        model: AI model used
        extra_info: Additional information dict

    Returns:
        Formatted caption string
    """
    lines = [
        "=" * 40,
        f"📁 FILE STORAGE LOG",
        "=" * 40,
        "",
        f"👤 User: {user.full_name}",
        f"🆔 Telegram ID: {user.tg_id}",
        f"🌐 Language: {user.lang.value if user.lang else 'N/A'}",
        "",
        f"🎯 Action: {category.value}",
    ]

    if model:
        lines.append(f"🤖 Model: {model}")

    if prompt:
        # Limit prompt length for caption
        prompt_display = prompt[:200] + "..." if len(prompt) > 200 else prompt
        lines.append(f"💬 Prompt: {prompt_display}")

    if extra_info:
        lines.append("")
        lines.append("📊 Additional Info:")
        for key, value in extra_info.items():
            lines.append(f"  • {key}: {value}")

    lines.append("")
    lines.append(f"⏰ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    lines.append("=" * 40)

    return "\n".join(lines)


# ================================================================
# MAIN STORAGE FUNCTIONS
# ================================================================

async def save_and_log_file(
        context,
        db,
        user,
        file_path: str,
        category: FileCategory,
        prompt: str = "",
        model: str = "",
        extra: dict = None
):
    """
    Upload a local file (PPTX, DOCX, etc.) to storage channel with metadata.

    Args:
        context: Telegram context
        db: Database session
        user: User object
        file_path: Path to local file
        category: File category
        prompt: User's original prompt
        model: AI model used
        extra: Additional metadata

    Returns:
        StorageFile object or None
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"❌ File not found: {file_path}")
            return None

        file_name = os.path.basename(file_path)
        mime = _guess_mime(file_name)
        size_bytes = os.path.getsize(file_path)

        # Read and hash file
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        sha256 = _sha256_from_bytes(file_bytes)

        # Prepare detailed caption
        caption = _format_file_caption(
            user=user,
            category=category,
            prompt=prompt,
            model=model,
            extra_info=extra or {}
        )

        # Upload to Telegram storage channel
        msg = await context.bot.send_document(
            chat_id=STORAGE_CHANNEL_ID,
            document=InputFile(BytesIO(file_bytes), filename=file_name),
            caption=caption[:1024],  # Telegram caption limit
        )

        tg_file_id = msg.document.file_id if msg.document else None
        if not tg_file_id:
            logger.warning("⚠️ Telegram returned no file_id")
            return None

        # Create database record
        storage_entry = StorageFile(
            owner_id=user.id,
            telegram_file_id=tg_file_id,
            storage_channel_id=STORAGE_CHANNEL_ID,
            storage_message_id=msg.message_id,
            category=category,
            mime=mime,
            original_name=file_name,
            size_bytes=size_bytes,
            sha256=sha256,
            extra={
                "prompt": prompt,
                "model": model,
                "user_lang": user.lang.value if user.lang else None,
                **(extra or {})
            },
        )
        db.add(storage_entry)
        db.flush()

        # Log action
        db.add(ActionLog(
            user_id=user.id,
            action=UserAction.file_upload,
            ref_id=storage_entry.id,
            meta={
                "category": category.value,
                "name": file_name,
                "model": model
            }
        ))
        db.commit()

        logger.info(f"✅ Stored file: {file_name} ({category.value})")
        return storage_entry

    except Exception as e:
        logger.error(f"❌ save_and_log_file error: {e}", exc_info=True)
        db.rollback()
        return None


async def save_and_log_image(
        context,
        db,
        user,
        image_data: bytes,
        prompt: str,
        category: FileCategory,
        model: str = "",
        extra: dict = None
):
    """
    Upload generated/edited image to storage channel with metadata.

    Args:
        context: Telegram context
        db: Database session
        user: User object
        image_data: Image bytes
        prompt: User's prompt
        category: File category (image_gen, image_edit)
        model: AI model used
        extra: Additional metadata

    Returns:
        StorageFile object or None
    """
    try:
        sha256 = _sha256_from_bytes(image_data)

        # Format caption
        caption = _format_file_caption(
            user=user,
            category=category,
            prompt=prompt,
            model=model,
            extra_info=extra or {}
        )

        # Upload to storage channel
        msg = await context.bot.send_photo(
            chat_id=STORAGE_CHANNEL_ID,
            photo=BytesIO(image_data),
            caption=caption[:1024]  # Telegram limit
        )

        tg_file_id = msg.photo[-1].file_id if msg.photo else None
        if not tg_file_id:
            logger.warning("⚠️ No file_id returned for image")
            return None

        # Create database record
        storage_entry = StorageFile(
            owner_id=user.id,
            telegram_file_id=tg_file_id,
            storage_channel_id=STORAGE_CHANNEL_ID,
            storage_message_id=msg.message_id,
            category=category,
            mime="image/png",
            size_bytes=len(image_data),
            sha256=sha256,
            extra={
                "prompt": prompt,
                "model": model,
                "user_lang": user.lang.value if user.lang else None,
                **(extra or {})
            },
        )
        db.add(storage_entry)
        db.flush()

        # Log action
        action_type = (
            UserAction.image_generation if category == FileCategory.image_gen
            else UserAction.image_edit
        )

        db.add(ActionLog(
            user_id=user.id,
            action=action_type,
            ref_id=storage_entry.id,
            meta={
                "prompt": prompt[:100],
                "category": category.value,
                "model": model
            }
        ))
        db.commit()

        logger.info(f"✅ Stored image ({category.value})")
        return storage_entry

    except Exception as e:
        logger.error(f"❌ save_and_log_image error: {e}", exc_info=True)
        db.rollback()
        return None


async def save_both_images(
        context,
        db,
        user,
        original_bytes: bytes,
        edited_bytes: bytes,
        prompt: str,
        model: str = "dall-e-3"
):
    """
    Save both images to storage channel as media group with combined caption.

    🔧 FIXED: Media group with ONE caption showing info for BOTH images
    """
    try:
        from telegram import InputMediaPhoto
        from io import BytesIO
        from datetime import datetime

        # Calculate hashes
        original_sha256 = _sha256_from_bytes(original_bytes)
        edited_sha256 = _sha256_from_bytes(edited_bytes)

        # 🔧 FIXED: ONE combined caption with info for BOTH images
        combined_caption = f"""🖼️ IMAGE EDITING LOG

👤 User: {user.full_name}
🆔 Telegram ID: {user.tg_id}
🌐 Language: {user.lang.value if user.lang else 'N/A'}

━━━━━━━━━━━━━━━━━━━━━━━━━━
📸 ORIGINAL (Left)
📏 Size: {round(len(original_bytes) / 1024, 2)} KB
🔑 Hash: {original_sha256[:12]}...

━━━━━━━━━━━━━━━━━━━━━━━━━━
🎨 EDITED (Right)
📏 Size: {round(len(edited_bytes) / 1024, 2)} KB
🔑 Hash: {edited_sha256[:12]}...

━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 Action: Image Edit
🤖 Model: {model}
💬 Prompt: {prompt[:120]}{'...' if len(prompt) > 120 else ''}

⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"""

        # 🔧 Send as media group with ONE combined caption
        media_group = [
            InputMediaPhoto(
                media=BytesIO(original_bytes)
            ),
            InputMediaPhoto(
                media=BytesIO(edited_bytes),
                caption=combined_caption[:1024]  # Caption on last image
            )
        ]

        # Send media group
        messages = await context.bot.send_media_group(
            chat_id=STORAGE_CHANNEL_ID,
            media=media_group
        )

        if not messages or len(messages) < 2:
            logger.warning("⚠️ Failed to send media group to storage")
            return None, None

        # Get file IDs from both messages
        original_msg = messages[0]
        edited_msg = messages[1]

        original_file_id = original_msg.photo[-1].file_id if original_msg.photo else None
        edited_file_id = edited_msg.photo[-1].file_id if edited_msg.photo else None

        if not original_file_id or not edited_file_id:
            logger.warning("⚠️ Missing file IDs from media group")
            return None, None

        # Create database record for ORIGINAL image
        original_storage = StorageFile(
            owner_id=user.id,
            telegram_file_id=original_file_id,
            storage_channel_id=STORAGE_CHANNEL_ID,
            storage_message_id=original_msg.message_id,
            category=FileCategory.image_edit,
            mime="image/png",
            size_bytes=len(original_bytes),
            sha256=original_sha256,
            extra={
                "type": "original",
                "edit_prompt": prompt,
                "model": model,
                "user_lang": user.lang.value if user.lang else None,
                "paired_with": "edited_image",
                "media_group_id": edited_msg.message_id
            },
        )
        db.add(original_storage)
        db.flush()

        # Create database record for EDITED image
        edited_storage = StorageFile(
            owner_id=user.id,
            telegram_file_id=edited_file_id,
            storage_channel_id=STORAGE_CHANNEL_ID,
            storage_message_id=edited_msg.message_id,
            category=FileCategory.image_edit,
            mime="image/png",
            size_bytes=len(edited_bytes),
            sha256=edited_sha256,
            extra={
                "type": "edited",
                "prompt": prompt,
                "model": model,
                "user_lang": user.lang.value if user.lang else None,
                "paired_with": "original_image",
                "original_file_id": original_file_id,
                "media_group_id": original_msg.message_id
            },
        )
        db.add(edited_storage)
        db.flush()

        # Log action
        db.add(ActionLog(
            user_id=user.id,
            action=UserAction.image_edit,
            ref_id=edited_storage.id,
            meta={
                "prompt": prompt[:100],
                "category": FileCategory.image_edit.value,
                "model": model,
                "both_images_stored": True,
                "storage_type": "media_group_with_combined_caption"
            }
        ))
        db.commit()

        logger.info("✅ Saved both images as media group with combined caption")
        return original_storage, edited_storage

    except Exception as e:
        logger.error(f"❌ save_both_images error: {e}", exc_info=True)
        db.rollback()
        return None, None
