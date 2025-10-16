
import logging
from typing import Optional

from telegram import Update, InputMediaPhoto
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from config import (
    TRIAL_PERIOD_DAYS,
    TRIAL_USES_PER_PERIOD,
    IMAGE_MODEL
)
from models import User
from models_enums import Language, UserAction
from keyboard import get_ai_functions_keyboard, get_back_keyboard
from messages import get_message
from db import get_db, log_action
from utils.quotas import (
    has_quota, increment_quota, maybe_reset_trial,
    trial_remaining, consume_trial
)
from utils.openai_client import create_image_variation
from utils.network_retry import (
    safe_send_message,
    safe_send_photo,
    safe_delete_message
)
from utils.storage_logger import save_both_images
from handlers.state import AI_MENU, IMAGE_EDIT

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================

_BACK_WORDS = {
    "/done", "⬅️ back", "⬅️ orqaga", "⬅️ назад",
    "back", "orqaga", "назад"
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

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


def _get_edit_instructions(lang: Language) -> str:
    """Get detailed editing instructions for user."""
    instructions = {
        Language.en: """🛠 **Smart Image Editing Mode**

📸 **Step 1:** Send ONE image
✏️ **Step 2:** Describe what to change

**Examples of edit requests:**
• "Make the sky blue and add neon lights"
• "Change background to a beach sunset"
• "Add sunglasses and make it nighttime"
• "Turn into a painting style"

**How it works:**
✨ AI analyzes your photo with advanced vision
🎨 Maintains your pose and composition
🖼️ Applies your edits naturally and realistically

**Premium Feature with Free Trial:**
• 3 free edits every 7 days for free users
• Unlimited edits for premium members

Press BACK when finished.""",

        Language.ru: """🛠 **Умное редактирование изображений**

📸 **Шаг 1:** Отправьте ОДНО изображение
✏️ **Шаг 2:** Опишите, что изменить

**Примеры запросов:**
• "Сделай небо синим и добавь неоновые огни"
• "Смени фон на закат на пляже"
• "Добавь солнцезащитные очки и сделай ночь"
• "Преврати в живописный стиль"

**Как это работает:**
✨ AI анализирует ваше фото продвинутым зрением
🎨 Сохраняет вашу позу и композицию
🖼️ Применяет изменения естественно и реалистично

**Премиум-функция с бесплатной пробной версией:**
• 3 бесплатных редактирования каждые 7 дней
• Неограниченно для премиум-пользователей

Нажмите НАЗАД, когда закончите.""",

        Language.uz: """🛠 **Aqlli rasm tahrirlash**

📸 **1-qadam:** BITTA rasm yuboring
✏️ **2-qadam:** Nima o'zgartirishni yozing

**So'rov misollari:**
• "Osmonni ko'k qiling va neon chiroqlar qo'shing"
• "Fonni plyaj quyosh botishiga o'zgartiring"
• "Ko'zoynak qo'shing va kechaga aylantiring"
• "Rassom uslubiga aylantiring"

**Qanday ishlaydi:**
✨ AI fotoingizni ilg'or ko'rish bilan tahlil qiladi
🎨 Pozangiz va kompozitsiyangizni saqlab qoladi
🖼️ O'zgarishlarni tabiiy va real qo'llaydi

**Premium funksiya bepul sinov bilan:**
• Har 7 kunda 3 ta bepul tahrirlash
• Premium foydalanuvchilar uchun cheklovsiz

Tugagach ORQAGA bosing."""
    }

    return instructions.get(lang, instructions[Language.en])


async def _send_typing_action(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Send typing indicator to user."""
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    except Exception as e:
        logger.warning(f"⚠️ Could not send typing action: {e}")


# ============================================================================
# MAIN HANDLER
# ============================================================================

async def image_edit_handler(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Smart image editing handler with Vision-powered analysis.

    Flow:
    1. User sends image → Store file_id
    2. User sends edit description → Process with Vision + DALL-E 3
    3. Send both original and edited images
    4. Store both images to channel
    """
    message = update.message
    if not message:
        return IMAGE_EDIT

    user_lang = _resolve_lang(context.user_data.get("lang", Language.en))

    # ========================================================================
    # HANDLE BACK BUTTON
    # ========================================================================
    if message.text and message.text.strip().lower() in _BACK_WORDS:
        context.user_data.pop("regen_image_file_id", None)

        with get_db() as db:
            user = db.query(User).filter(User.tg_id == update.effective_user.id).first()
            is_premium = bool(user.is_premium) if user else False
            is_admin = bool(user.is_admin) if user else False

        await safe_send_message(
            message,
            get_message("prompt_ai_menu", user_lang),
            reply_markup=get_ai_functions_keyboard(user_lang, is_premium, is_admin)
        )
        return AI_MENU

    # ========================================================================
    # LOAD USER
    # ========================================================================
    with get_db() as db:
        user: Optional[User] = db.query(User).filter(
            User.tg_id == update.effective_user.id
        ).first()

        if not user:
            await safe_send_message(
                message,
                "⚠️ User not found. Please /start the bot again."
            )
            return AI_MENU

        # Check for trial reset
        if maybe_reset_trial(db, user):
            await safe_send_message(
                message,
                get_message(
                    "trial_renewed",
                    user_lang,
                    feature="Image Editing",
                    total=TRIAL_USES_PER_PERIOD,
                    days=TRIAL_PERIOD_DAYS
                ),
                parse_mode=ParseMode.MARKDOWN
            )

        # ====================================================================
        # STEP 1: USER SENDS IMAGE
        # ====================================================================
        has_photo = bool(message.photo)
        has_image_doc = (
                message.document
                and message.document.mime_type
                and message.document.mime_type.startswith("image/")
        )

        if (has_photo or has_image_doc) and "regen_image_file_id" not in context.user_data:
            # Store the image file ID
            file_id = message.photo[-1].file_id if has_photo else message.document.file_id
            context.user_data["regen_image_file_id"] = file_id

            logger.info(f"📸 Image received from user {user.tg_id}")

            # Send instructions for next step
            prompt_msg = {
                Language.en: """✅ **Image Received!**

Now describe what you want to edit or change.

**Be specific for best results:**
✅ "Make the sky purple with stars"
✅ "Change background to Tokyo at night"
✅ "Add neon eyebrows and make hair blue"
✅ "Transform into Van Gogh painting style"

❌ Avoid vague requests like "make it better"

What would you like to change?""",

                Language.ru: """✅ **Изображение получено!**

Теперь опишите, что вы хотите изменить или отредактировать.

**Будьте конкретны для лучших результатов:**
✅ "Сделай небо фиолетовым со звёздами"
✅ "Смени фон на ночной Токио"
✅ "Добавь неоновые брови и сделай волосы синими"
✅ "Преврати в стиль картины Ван Гога"

❌ Избегайте размытых запросов типа "сделай лучше"

Что вы хотите изменить?""",

                Language.uz: """✅ **Rasm qabul qilindi!**

Endi nima tahrirlash yoki o'zgartirishni xohlayotganingizni tasvirlab bering.

**Eng yaxshi natija uchun aniq bo'ling:**
✅ "Osmonni binafsha rangda yulduzlar bilan qiling"
✅ "Fonni Tokiodagi tunga o'zgartiring"
✅ "Neon qoshlar qo'shing va sochni ko'k qiling"
✅ "Van Gog rasm uslubiga aylantiring"

❌ "Yaxshiroq qiling" kabi noaniq so'rovlardan saqlaning

Nimani o'zgartirmoqchisiz?"""
            }.get(user_lang)

            await safe_send_message(
                message,
                prompt_msg,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_back_keyboard(user_lang)
            )
            return IMAGE_EDIT

        # ====================================================================
        # STEP 2: USER SENDS EDIT DESCRIPTION
        # ====================================================================
        if "regen_image_file_id" in context.user_data and message.text:
            edit_prompt = message.text.strip()

            # Validate prompt length
            if len(edit_prompt) < 5:
                await safe_send_message(
                    message,
                    "⚠️ Please provide a more detailed description of what to edit."
                )
                return IMAGE_EDIT

            # ================================================================
            # ACCESS CHECK: Trial or Premium
            # ================================================================
            if not (user.is_premium or user.is_admin):
                remaining = trial_remaining(db, user, "image_edit")

                if remaining <= 0:
                    await safe_send_message(
                        message,
                        get_message("premium_required", user_lang),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    context.user_data.pop("regen_image_file_id", None)
                    return AI_MENU

                # Notify about trial usage
                if remaining == TRIAL_USES_PER_PERIOD:
                    await safe_send_message(
                        message,
                        get_message(
                            "trial_started",
                            user_lang,
                            feature="Image Editing",
                            remaining=remaining,
                            total=TRIAL_USES_PER_PERIOD,
                            days=TRIAL_PERIOD_DAYS
                        )
                    )
                else:
                    await safe_send_message(
                        message,
                        get_message(
                            "trial_remaining",
                            user_lang,
                            feature="Image Editing",
                            remaining=remaining,
                            total=TRIAL_USES_PER_PERIOD
                        )
                    )

            # ================================================================
            # QUOTA CHECK
            # ================================================================
            if not has_quota(db, user, "convert"):
                await safe_send_message(
                    message,
                    get_message("quota_exceeded", user_lang),
                    parse_mode=ParseMode.MARKDOWN
                )
                context.user_data.pop("regen_image_file_id", None)
                return AI_MENU

            file_id = context.user_data.pop("regen_image_file_id")

            try:
                # ============================================================
                # DOWNLOAD ORIGINAL IMAGE
                # ============================================================
                logger.info(f"📥 Downloading original image for user {user.tg_id}")
                tg_file = await context.bot.get_file(file_id)
                original_bytes = await tg_file.download_as_bytearray()
                logger.info(f"✅ Downloaded {len(original_bytes)} bytes")

                # Show typing indicator
                await _send_typing_action(context, message.chat_id)

                # Status message
                status_text = {
                    Language.en: """🛠 **Processing Your Image...**

🔍 Analyzing with AI Vision...
🎨 Applying your edits...
⏳ This may take 20-30 seconds

Please wait...""",
                    Language.ru: """🛠 **Обработка вашего изображения...**

🔍 Анализ с AI Vision...
🎨 Применение ваших правок...
⏳ Это может занять 20-30 секунд

Пожалуйста, подождите...""",
                    Language.uz: """🛠 **Rasmingiz qayta ishlanmoqda...**

🔍 AI Vision bilan tahlil qilinmoqda...
🎨 Tahrirlashlaringiz qo'llanmoqda...
⏳ Bu 20-30 soniya davom etishi mumkin

Iltimos, kuting..."""
                }[user_lang]

                status_msg = await safe_send_message(
                    message,
                    status_text,
                    parse_mode=ParseMode.MARKDOWN
                )

                # ============================================================
                # SMART IMAGE EDITING with Vision + DALL-E 3
                # ============================================================
                logger.info(f"🎨 Starting smart image editing...")
                logger.info(f"📝 Edit prompt: {edit_prompt}")

                edited_url = await create_image_variation(
                    image_bytes=bytes(original_bytes),
                    prompt=edit_prompt
                )

                if not edited_url:
                    await safe_delete_message(status_msg)

                    error_msg = {
                        Language.en: "❌ Failed to edit image. Please try:\n• A more specific description\n• Different editing request\n• Try again in a moment",
                        Language.ru: "❌ Не удалось отредактировать. Попробуйте:\n• Более конкретное описание\n• Другой запрос\n• Попробуйте снова через момент",
                        Language.uz: "❌ Tahrirlash amalga oshmadi. Sinab ko'ring:\n• Aniqroq tavsif\n• Boshqa so'rov\n• Bir ozdan keyin qayta urinib ko'ring"
                    }[user_lang]

                    await safe_send_message(message, error_msg)
                    return IMAGE_EDIT

                # ============================================================
                # DOWNLOAD EDITED IMAGE
                # ============================================================
                import requests
                edited_bytes = requests.get(edited_url, timeout=30).content
                logger.info(f"✅ Edited image downloaded: {len(edited_bytes)} bytes")

                await safe_delete_message(status_msg)

                # ============================================================
                # SEND BOTH IMAGES AS MEDIA GROUP
                # ============================================================
                try:
                    caption_original = {
                        Language.en: "📸 Original",
                        Language.ru: "📸 Оригинал",
                        Language.uz: "📸 Asl rasm"
                    }[user_lang]

                    caption_edited = {
                        Language.en: f"✨ Edited\n\n💬 Changes: {edit_prompt[:100]}",
                        Language.ru: f"✨ Отредактировано\n\n💬 Изменения: {edit_prompt[:100]}",
                        Language.uz: f"✨ Tahrirlangan\n\n💬 O'zgarishlar: {edit_prompt[:100]}"
                    }[user_lang]

                    media_group = [
                        InputMediaPhoto(
                            media=bytes(original_bytes),
                            caption=caption_original
                        ),
                        InputMediaPhoto(
                            media=edited_bytes,
                            caption=caption_edited
                        )
                    ]

                    await context.bot.send_media_group(
                        chat_id=message.chat_id,
                        media=media_group
                    )

                    logger.info("✅ Sent both images as media group")

                except Exception as e:
                    logger.error(f"❌ Failed to send media group: {e}")
                    # Fallback: Send separately
                    await safe_send_photo(
                        message,
                        photo=bytes(original_bytes),
                        caption=caption_original
                    )
                    await safe_send_photo(
                        message,
                        photo=edited_bytes,
                        caption=caption_edited
                    )

                # ============================================================
                # SAVE BOTH IMAGES TO STORAGE CHANNEL
                # ============================================================
                try:
                    await save_both_images(
                        context=context,
                        db=db,
                        user=user,
                        original_bytes=bytes(original_bytes),
                        edited_bytes=edited_bytes,
                        prompt=edit_prompt,
                        model=IMAGE_MODEL
                    )
                    logger.info("✅ Stored both images to channel")
                except Exception as e:
                    logger.error(f"❌ Storage error: {e}")

                # ============================================================
                # UPDATE TRIAL/QUOTA COUNTERS
                # ============================================================
                if not (user.is_premium or user.is_admin):
                    if consume_trial(db, user, "image_edit"):
                        rem = trial_remaining(db, user, "image_edit")
                        await safe_send_message(
                            message,
                            get_message(
                                "trial_consumed",
                                user_lang,
                                feature="Image Editing",
                                remaining=rem,
                                total=TRIAL_USES_PER_PERIOD
                            ),
                            parse_mode=ParseMode.MARKDOWN
                        )
                    else:
                        await safe_send_message(
                            message,
                            get_message(
                                "trial_over",
                                user_lang,
                                feature="Image Editing"
                            ),
                            parse_mode=ParseMode.MARKDOWN
                        )

                increment_quota(db, user, "convert", amount=1)
                log_action(
                    db,
                    user.id,
                    UserAction.image_edit,
                    meta={"prompt": edit_prompt}
                )

                # Success message
                success_msg = {
                    Language.en: "✅ Image edited successfully!\n\nSend another image to edit more, or press BACK.",
                    Language.ru: "✅ Изображение успешно отредактировано!\n\nОтправьте ещё изображение или нажмите НАЗАД.",
                    Language.uz: "✅ Rasm muvaffaqiyatli tahrirlandi!\n\nYana rasm yuboring yoki ORQAGA bosing."
                }[user_lang]

                await safe_send_message(message, success_msg)

            except Exception as e:
                logger.error(f"❌ Image editing error: {e}", exc_info=True)

                # Clean up status message
                try:
                    if 'status_msg' in locals() and status_msg:
                        await safe_delete_message(status_msg)
                except Exception:
                    pass

                # Send error message
                error_text = {
                    Language.en: f"❌ Error while editing image.\n\nPlease try:\n• Different image\n• Simpler edit request\n• Try again in a moment\n\nError: {str(e)[:100]}",
                    Language.ru: f"❌ Ошибка при редактировании.\n\nПопробуйте:\n• Другое изображение\n• Более простой запрос\n• Попробуйте позже\n\nОшибка: {str(e)[:100]}",
                    Language.uz: f"❌ Tahrirlashda xatolik.\n\nSinab ko'ring:\n• Boshqa rasm\n• Soddaroq so'rov\n• Keyinroq qayta urinib ko'ring\n\nXatolik: {str(e)[:100]}"
                }[user_lang]

                await safe_send_message(message, error_text)

            return IMAGE_EDIT

    # ========================================================================
    # FALLBACK: SHOW INSTRUCTIONS
    # ========================================================================
    await safe_send_message(
        message,
        _get_edit_instructions(user_lang),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_back_keyboard(user_lang)
    )
    return IMAGE_EDIT
