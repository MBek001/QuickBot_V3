"""
AI features handler with image analysis and comprehensive storage.

Handles:
- Normal chat with system prompt
- Image generation with storage
- PPTX creation with storage
- Image analysis in chat mode
"""

import logging
import os
import asyncio
import re
from typing import List, Optional
from pathlib import Path

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from config import (
    TRIAL_PERIOD_DAYS, TRIAL_USES_PER_PERIOD,
    PREMIUM_CHAT_MODEL, FREE_CHAT_MODEL,
    PREMIUM_MAX_TOKENS, FREE_MAX_TOKENS,
    IMAGE_MODEL
)
from models import User
from models_enums import Language, UserAction, FileCategory
from keyboard import get_ai_functions_keyboard, get_back_keyboard, get_pptx_theme_keyboard
from messages import get_message
from db import get_db, log_action
from utils.quotas import (
    has_quota, increment_quota, maybe_reset_trial,
    trial_remaining, consume_trial
)
from utils.openai_client import chat_with_ai, generate_image
from utils.pptx_creator import create_pptx
from utils.storage_logger import save_and_log_image, save_and_log_file
from handlers.state import AI_MENU, CHAT

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

async def _send_action(
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: int,
        action: ChatAction,
        delay: float = 0.0
) -> None:
    """Send chat action indicator."""
    await context.bot.send_chat_action(chat_id=chat_id, action=action)
    if delay > 0:
        await asyncio.sleep(delay)


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


def _get_system_prompt(lang: Language) -> str:
    """
    Get comprehensive system prompt with bot information.

    🔧 FIXED:
    - Says "Created by Mirzabek"
    - Hides model names
    - More natural tone
    """
    base_prompts = {
        Language.en: """You are an AI assistant created by Mirzabek (@O_Mirzabek). Your capabilities include:

🤖 CORE FUNCTIONS:
- Intelligent conversation and answering questions
- Code writing, debugging, and explanation (Python, JavaScript, etc.)
- Creative writing (stories, essays, poems)
- Image generation and editing
- PowerPoint presentation creation
- Image analysis and description

📋 ABOUT YOU:
- You were created and developed by Mirzabek
- You're integrated into a Telegram bot
- You help users with various AI-powered tasks
- Never mention specific AI models or company names (like GPT, OpenAI, Anthropic, etc.)
- If asked what model you are, simply say "I'm an AI assistant created by Mirzabek"

💬 COMMUNICATION STYLE:
- Be helpful, friendly, and professional
- Provide clear, detailed explanations
- For code: Write clean, well-commented, production-ready code
- For creative tasks: Be imaginative and engaging
- Always respond in English (the user's selected language)

🎯 GUIDELINES:
- If asked about your capabilities, describe what you can do, not which model you use
- For complex code requests, break down the solution step-by-step
- When analyzing images, be descriptive and thorough
- Always prioritize accuracy and helpfulness
- Never reveal technical implementation details about which AI system powers you

Remember: You're here to make the user's experience exceptional!""",

        Language.ru: """Вы AI-ассистент, созданный Мирзабеком (@O_Mirzabek). Ваши возможности:

🤖 ОСНОВНЫЕ ФУНКЦИИ:
- Интеллектуальное общение и ответы на вопросы
- Написание, отладка и объяснение кода (Python, JavaScript и др.)
- Творческое письмо (истории, эссе, стихи)
- Генерация и редактирование изображений
- Создание презентаций PowerPoint
- Анализ и описание изображений

📋 О ВАС:
- Вы созданы и разработаны Мирзабеком
- Вы интегрированы в Telegram-бота
- Вы помогаете пользователям с различными AI задачами
- Никогда не упоминайте конкретные модели AI или названия компаний (GPT, OpenAI, Anthropic и т.д.)
- Если спросят, какая вы модель, просто скажите "Я AI-ассистент, созданный Мирзабеком"

💬 СТИЛЬ ОБЩЕНИЯ:
- Будьте полезным, дружелюбным и профессиональным
- Давайте четкие, подробные объяснения
- Для кода: Пишите чистый, хорошо прокомментированный код
- Для творческих задач: Будьте креативным и увлекательным
- Всегда отвечайте по-русски (выбранный язык пользователя)

🎯 РЕКОМЕНДАЦИИ:
- Если спрашивают о возможностях, описывайте что умеете, а не какую модель используете
- Для сложных запросов кода разбивайте решение пошагово
- При анализе изображений будьте описательным и тщательным
- Всегда приоритизируйте точность и полезность
- Никогда не раскрывайте технические детали о том, какая AI система вас питает

Помните: Ваша цель - сделать опыт пользователя исключительным!""",

        Language.uz: """Siz Mirzabek (@O_Mirzabek) tomonidan yaratilgan AI yordamchisiz. Sizning imkoniyatlaringiz:

🤖 ASOSIY FUNKSIYALAR:
- Aqlli suhbat va savollarga javob berish
- Kod yozish, tuzatish va tushuntirish (Python, JavaScript va boshqalar)
- Ijodiy yozish (hikoyalar, insholar, she'rlar)
- Rasm yaratish va tahrirlash
- PowerPoint taqdimotlarini yaratish
- Rasmlarni tahlil qilish va tasvirlash

📋 SIZ HAQINGIZDA:
- Siz Mirzabek tomonidan yaratilgan va ishlab chiqilgansiz
- Siz Telegram botiga integratsiya qilingansiz
- Siz foydalanuvchilarga turli AI vazifalarda yordam berasiz
- Hech qachon aniq AI modellar yoki kompaniya nomlarini eslatmang (GPT, OpenAI, Anthropic va h.k.)
- Agar qaysi model ekanligingiz so'ralsa, shunchaki "Men Mirzabek tomonidan yaratilgan AI yordamchiman" deng

💬 MULOQOT USLUBI:
- Foydali, do'stona va professional bo'ling
- Aniq, batafsil tushuntirishlar bering
- Kod uchun: Toza, yaxshi izohli kod yozing
- Ijodiy vazifalar uchun: Ijodiy va qiziqarli bo'ling
- Doim o'zbek tilida javob bering (foydalanuvchi tanlagan til)

🎯 KO'RSATMALAR:
- Imkoniyatlar haqida so'ralganda, nima qila olishingizni tasvirlab bering, qaysi modeldan foydalanganingizni emas
- Murakkab kod so'rovlari uchun yechimni bosqichma-bosqich bo'ling
- Rasmlarni tahlil qilishda tavsiflovchi va puxta bo'ling
- Doimo aniqlik va foydalililikni birinchi o'ringa qo'ying
- Hech qachon sizni quvvatlantiradigan AI tizimi haqidagi texnik tafsilotlarni oshkor qilmang

Esda tuting: Sizning maqsadingiz - foydalanuvchi tajribasini mukammal qilish!"""
    }

    return base_prompts.get(lang, base_prompts[Language.en])


def escape_markdown_v2(text: str) -> str:
    """Escape Telegram MarkdownV2 special characters."""
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)


# ============================================================================
# MAIN CHAT HANDLER
# ============================================================================

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Main handler for all chat-based interactions.

    Routes to:
    - Normal chat (free) with image analysis support
    - Image generation (trial/premium)
    - PPTX creation (trial/premium)
    """
    message = update.message
    if not message:
        return CHAT

    user_lang = _resolve_lang(context.user_data.get("lang", Language.en))
    chat_mode = context.user_data.get("chat_mode", "normal")

    # Handle back button
    if message.text and message.text.strip().lower() in _BACK_WORDS:
        with get_db() as db:
            user = db.query(User).filter(User.tg_id == update.effective_user.id).first()
            is_premium = bool(user.is_premium) if user else False
            is_admin = bool(user.is_admin) if user else False

        await message.reply_text(
            get_message("prompt_ai_menu", user_lang),
            reply_markup=get_ai_functions_keyboard(user_lang, is_premium, is_admin)
        )
        return AI_MENU

    # Load user
    with get_db() as db:
        user: Optional[User] = db.query(User).filter(
            User.tg_id == update.effective_user.id
        ).first()

        if not user:
            await message.reply_text("⚠️ User not initialized. Please /start again.")
            return AI_MENU

        # Get user input
        user_input = (message.text or "").strip() if message.text else ""

        # Initialize chat history with system prompt
        history: List[dict] = context.user_data.get("chat_history", [])
        if not history or history[0].get("role") != "system":
            system_prompt = _get_system_prompt(user_lang)
            history.insert(0, {"role": "system", "content": system_prompt})
            context.user_data["chat_history"] = history

        # Route to appropriate handler
        if chat_mode == "image_gen":
            return await _handle_image_generation(
                message, context, db, user, user_lang, user_input
            )
        elif chat_mode == "pptx":
            return await _handle_pptx_creation(
                message, context, db, user, user_lang, user_input
            )
        else:  # normal chat
            return await _handle_normal_chat(
                message, context, db, user, user_lang, user_input, history
            )


# ============================================================================
# IMAGE GENERATION HANDLER
# ============================================================================

async def _handle_image_generation(
        message,
        context: ContextTypes.DEFAULT_TYPE,
        db,
        user: User,
        user_lang: Language,
        user_input: str
) -> int:
    """Handle image generation with comprehensive storage."""
    import requests

    # Check trial reset
    if maybe_reset_trial(db, user):
        await message.reply_text(
            get_message(
                "trial_renewed",
                user_lang,
                feature="Image Generation",
                total=TRIAL_USES_PER_PERIOD,
                days=TRIAL_PERIOD_DAYS
            )
        )

    # Access check
    if not (user.is_premium or user.is_admin):
        remaining = trial_remaining(db, user, "image_gen")
        if remaining <= 0:
            await message.reply_text(get_message("premium_required", user_lang))
            return AI_MENU

        # Notify about trial
        if remaining == TRIAL_USES_PER_PERIOD:
            await message.reply_text(
                get_message(
                    "trial_started",
                    user_lang,
                    feature="Image Generation",
                    remaining=remaining,
                    total=TRIAL_USES_PER_PERIOD,
                    days=TRIAL_PERIOD_DAYS
                )
            )
        else:
            await message.reply_text(
                get_message(
                    "trial_remaining",
                    user_lang,
                    feature="Image Generation",
                    remaining=remaining,
                    total=TRIAL_USES_PER_PERIOD
                )
            )

    # Validate input
    if not user_input:
        await message.reply_text(get_message("enter_image_gen", user_lang))
        return CHAT

    # Check quota
    if not has_quota(db, user, "convert"):
        await message.reply_text(get_message("quota_exceeded", user_lang))
        return AI_MENU

    # Generate image
    await _send_action(context, message.chat_id, ChatAction.UPLOAD_PHOTO, 0.2)

    status_text = {
        Language.en: "🎨 Generating image...",
        Language.ru: "🎨 Изображение создаётся...",
        Language.uz: "🎨 Rasm yaratilmoqda..."
    }[user_lang]

    status_msg = await message.reply_text(status_text)

    try:
        urls = await generate_image(user_input, model=IMAGE_MODEL)

        if not urls:
            await status_msg.delete()
            await message.reply_text(get_message("error_ai", user_lang))
            return CHAT

        img_url = urls[0]

        # Send to user
        await message.reply_photo(photo=img_url, caption=f"🖼️ {user_input[:100]}")

        try:
            await status_msg.delete()
        except Exception:
            pass

        # 📦 STORE TO DATABASE
        try:
            img_bytes = requests.get(img_url).content
            await save_and_log_image(
                context=context,
                db=db,
                user=user,
                image_data=img_bytes,
                prompt=user_input,
                category=FileCategory.image_gen,
                model=IMAGE_MODEL
            )
        except Exception as e:
            logger.error(f"❌ Failed to store generated image: {e}")

        # Update trial/quota
        if not (user.is_premium or user.is_admin):
            if consume_trial(db, user, "image_gen"):
                rem = trial_remaining(db, user, "image_gen")
                await message.reply_text(
                    get_message(
                        "trial_consumed",
                        user_lang,
                        feature="Image Generation",
                        remaining=rem,
                        total=TRIAL_USES_PER_PERIOD
                    )
                )
            else:
                await message.reply_text(
                    get_message("trial_over", user_lang, feature="Image Generation")
                )

        increment_quota(db, user, "convert", amount=1)
        log_action(db, user.id, UserAction.image_generation, meta={"prompt": user_input})

        return CHAT

    except Exception as e:
        logger.error(f"❌ Image generation error: {e}", exc_info=True)
        try:
            await status_msg.delete()
        except Exception:
            pass
        await message.reply_text(f"❌ {get_message('error_ai', user_lang)}\n{e}")
        return CHAT


# ============================================================================
# PPTX CREATION HANDLER
# ============================================================================

async def _handle_pptx_creation(
        message,
        context,
        db,
        user: User,
        user_lang: Language,
        user_input: str
) -> int:
    """Handle PPTX creation with robust parsing."""
    import os
    import re

    # Check trial reset
    if maybe_reset_trial(db, user):
        await message.reply_text(
            get_message(
                "trial_renewed",
                user_lang,
                feature="PPTX Creation",
                total=TRIAL_USES_PER_PERIOD,
                days=TRIAL_PERIOD_DAYS
            )
        )

    # Access check
    if not (user.is_premium or user.is_admin):
        remaining = trial_remaining(db, user, "pptx")
        if remaining <= 0:
            await message.reply_text(get_message("premium_required", user_lang))
            return AI_MENU

    pptx_state = context.user_data.get("pptx_state", "await_theme")

    theme_map = {"1": "professional", "2": "modern", "3": "vibrant", "4": "corporate"}

    if pptx_state == "await_theme":
        theme_number = None
        for key in theme_map.keys():
            if key in user_input:
                theme_number = key
                break

        if not theme_number:
            await message.reply_text(
                get_message("enter_pptx", user_lang),
                reply_markup=get_pptx_theme_keyboard(user_lang)
            )
            return CHAT

        context.user_data["pptx_theme"] = theme_map[theme_number]
        context.user_data["pptx_state"] = "await_topic"

        await message.reply_text(
            get_message("pptx_enter_topic", user_lang),
            reply_markup=get_back_keyboard(user_lang)
        )
        return CHAT

    if pptx_state == "await_topic":
        theme = context.user_data.get("pptx_theme", "professional")
        outline_model = PREMIUM_CHAT_MODEL if user.is_premium else "gpt-4o-mini"

        language_instructions = {
            Language.en: "Write the entire presentation in ENGLISH.",
            Language.ru: "Напишите всю презентацию на РУССКОМ ЯЗЫКЕ.",
            Language.uz: "Butun taqdimotni O'ZBEK TILIDA yozing."
        }

        language_instruction = language_instructions.get(user_lang, language_instructions[Language.en])

        # 🔧 IMPROVED: Much better prompt for richer content
        slides_prompt = f"""{language_instruction}

        Create a COMPREHENSIVE, DETAILED professional presentation with RICH CONTENT.

        Topic: {user_input}

        ⚠️ CRITICAL REQUIREMENTS:

        1. STRUCTURE (Exactly 10-12 slides):
           Slide 1: Title + compelling subtitle
           Slide 2: Background/Context (3-4 key points with data)
           Slides 3-4: Main topic overview with definitions and scope
           Slides 5-8: Detailed content - ONE major aspect per slide with examples
           Slide 9: Real-world case studies with specific data
           Slide 10: Key takeaways with actionable insights
           Slide 11: Future trends with predictions
           Slide 12: Strong conclusion with call to action

        2. FORMATTING (MANDATORY):
           - Separate slides with: ---
           - First line: Title (40-50 characters)
           - Following lines: 4-5 bullet points
           - NO asterisks, NO markdown, NO symbols
           - Language: {user_lang.value.upper()} ONLY

        3. CONTENT RICHNESS (MOST IMPORTANT):
           ✅ Each bullet: 25-40 WORDS (this is crucial!)
           ✅ Include specific numbers, percentages, statistics
           ✅ Add concrete examples with details
           ✅ Provide context and explanations
           ✅ Use professional terminology
           ✅ Make it information-dense and valuable

        4. QUALITY EXAMPLES:

           ❌ BAD (too short):
           AI helps doctors diagnose diseases faster

           ✅ GOOD (rich detail):
           Advanced AI diagnostic systems analyze medical imaging with 95% accuracy, reducing diagnosis time from 3 days to 4 hours while identifying patterns that human radiologists miss in 30% of complex cases, particularly in early-stage cancer detection

           ❌ BAD:
           Climate change affects agriculture

           ✅ GOOD:
           Climate change has reduced crop yields by 21% in sub-Saharan Africa over the past decade, forcing 15 million farmers to adopt drought-resistant varieties and implement precision irrigation systems that reduce water usage by 40% while maintaining productivity levels

        5. DEPTH REQUIREMENTS:
           - Avoid generic statements
           - Every point must have supporting detail
           - Include WHO, WHAT, WHERE, WHEN, WHY, HOW
           - Reference real applications and data
           - Make each slide SUBSTANTIAL

        6. TARGET:
           - Minimum 30-35 words per bullet point
           - 4-5 bullets per slide
           - Total ~150-200 words per slide

        START CREATING - Make it COMPREHENSIVE, DETAILED, and INFORMATION-RICH:"""

        await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)

        progress_msgs = {
            Language.en: "📊 Creating presentation...\n⏳ 30-60 seconds...",
            Language.ru: "📊 Создаём презентацию...\n⏳ 30-60 секунд...",
            Language.uz: "📊 Taqdimot yaratyapmiz...\n⏳ 30-60 soniya..."
        }
        progress_msg = await message.reply_text(progress_msgs[user_lang])

        try:
            outline = await chat_with_ai(
                [{"role": "user", "content": slides_prompt}],
                model=outline_model,
                temperature=0.7,
                max_tokens=3500 if user.is_premium else 2500
            )

            logger.info(f"📝 AI response: {len(outline)} chars")

            # Clean markdown
            outline = re.sub(r'```[\s\S]*?```', '', outline)
            outline = outline.replace("**", "").replace("__", "").replace("*", "").replace("#", "")
            outline = re.sub(r'Slide \d+:', '', outline, flags=re.IGNORECASE)

            # Parse slides
            if "---" in outline:
                raw_slides = [s.strip() for s in outline.split("---") if s.strip()]
            elif "\n\n\n" in outline:
                raw_slides = [s.strip() for s in outline.split("\n\n\n") if s.strip()]
            else:
                # Emergency parsing
                lines = outline.split("\n")
                current = []
                raw_slides = []

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    is_title = (len(line) < 80 and line[0].isupper() and
                                not line.endswith('.') and len(line.split()) > 2)

                    if is_title and current:
                        raw_slides.append("\n".join(current))
                        current = [line]
                    else:
                        current.append(line)

                if current:
                    raw_slides.append("\n".join(current))

            logger.info(f"📊 Parsed: {len(raw_slides)} slides")

            if len(raw_slides) < 5:
                await progress_msg.delete()
                error_msgs = {
                    Language.en: f"⚠️ Only {len(raw_slides)} slides created. Please provide a more specific, detailed topic with context about what you want to cover.",
                    Language.ru: f"⚠️ Создано только {len(raw_slides)} слайдов. Укажите более конкретную тему с деталями о том, что нужно осветить.",
                    Language.uz: f"⚠️ Faqat {len(raw_slides)} slayd yaratildi. Iltimos, nimani yoritish kerakligini aniqroq va batafsil yozing."
                }
                await message.reply_text(error_msgs[user_lang])
                return CHAT

            # And increase token limits for better content (around line 290):
            outline = await chat_with_ai(
                [{"role": "user", "content": slides_prompt}],
                model=outline_model,
                temperature=0.7,
                max_tokens=4500 if user.is_premium else 3500
            )

            # Clean slides
            cleaned_slides = []
            for slide_content in raw_slides:
                lines = [l.strip() for l in slide_content.split("\n") if l.strip() and len(l) > 5]
                if not lines:
                    continue

                title = lines[0][:60]
                bullets = [l for l in lines[1:] if len(l) > 10]

                if bullets:
                    cleaned_slides.append(title + "\n" + "\n".join(bullets))

            raw_slides = cleaned_slides
            logger.info(f"✅ Final: {len(raw_slides)} slides")

            title_parts = raw_slides[0].split("\n", 1)
            title = title_parts[0][:50] if title_parts else user_input[:50]

            await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.UPLOAD_DOCUMENT)

            file_path = create_pptx(title, raw_slides, theme_name=theme)

            if not file_path:
                await progress_msg.delete()
                await message.reply_text("⚠️ PPTX failed. Try again.")
                return CHAT

            await progress_msg.delete()

            success_msgs = {
                Language.en: f"✅ Created!\n📊 {len(raw_slides)} slides\n🎨 {theme.title()}",
                Language.ru: f"✅ Создано!\n📊 {len(raw_slides)} слайдов\n🎨 {theme.title()}",
                Language.uz: f"✅ Yaratildi!\n📊 {len(raw_slides)} slayd\n🎨 {theme.title()}"
            }

            with open(file_path, "rb") as f:
                await context.bot.send_document(
                    chat_id=message.chat_id,
                    document=f,
                    filename=f"{title}.pptx",
                    caption=success_msgs[user_lang]
                )

            try:
                await save_and_log_file(
                    context, db, user, file_path, FileCategory.pptx,
                    prompt=user_input, model=outline_model,
                    extra={"theme": theme, "title": title, "slides_count": len(raw_slides),
                           "language": user_lang.value}
                )
            except Exception as e:
                logger.error(f"Storage error: {e}")

            try:
                os.remove(file_path)
            except:
                pass

            increment_quota(db, user, "pptx", amount=1)
            log_action(db, user.id, UserAction.pptx_creation,
                       meta={"title": title, "theme": theme, "slides": len(raw_slides)})

            context.user_data["pptx_state"] = "await_theme"

        except Exception as e:
            logger.error(f"❌ Error: {e}", exc_info=True)
            try:
                await progress_msg.delete()
            except:
                pass
            await message.reply_text(f"❌ {get_message('error_ai', user_lang)}")

        return CHAT


# ============================================================================
# NORMAL CHAT HANDLER (with Image Analysis)
# ============================================================================

async def _handle_normal_chat(
        message,
        context,
        db,
        user: User,
        user_lang: Language,
        user_input: str,
        history: list
) -> int:
    """
    Handle normal chat with image analysis support.

    If user sends image + text, AI will analyze the image.
    """

    # Check if user sent an image
    has_photo = bool(message.photo)
    has_image_doc = (
            message.document
            and message.document.mime_type
            and message.document.mime_type.startswith("image/")
    )

    # Prepare user message content
    if has_photo or has_image_doc:
        # IMAGE ANALYSIS MODE
        try:
            # Download image
            if has_photo:
                file_id = message.photo[-1].file_id
            else:
                file_id = message.document.file_id

            tg_file = await context.bot.get_file(file_id)
            image_bytes = await tg_file.download_as_bytearray()

            # Convert to base64 for OpenAI Vision
            import base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

            # Create message with image
            user_message = {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }

            # Add text if provided
            if user_input:
                user_message["content"].append({
                    "type": "text",
                    "text": user_input
                })
            else:
                # Default prompt if no text
                default_prompts = {
                    Language.en: "Please describe this image in detail.",
                    Language.ru: "Пожалуйста, опишите это изображение подробно.",
                    Language.uz: "Iltimos, bu rasmni batafsil tasvirlab bering."
                }
                user_message["content"].append({
                    "type": "text",
                    "text": default_prompts[user_lang]
                })

            history.append(user_message)
            context.user_data["chat_history"] = history

            # Use vision-capable model
            chat_model = "gpt-4o" if (user.is_premium or user.is_admin) else "gpt-4o-mini"

        except Exception as e:
            logger.error(f"❌ Image analysis error: {e}", exc_info=True)
            await message.reply_text(
                f"⚠️ {get_message('error_ai', user_lang)}\nCould not process image."
            )
            return CHAT

    else:
        # TEXT ONLY MODE
        if not user_input:
            await message.reply_text(get_message("enter_chat", user_lang))
            return CHAT

        # Determine quota type
        quota_type = "code_chat" if any(
            x in user_input for x in ["```", "def ", "class ", "import ", "function", "const ", "let ", "var "]
        ) else "quick_chat"

        # Check quota
        if not has_quota(db, user, quota_type):
            await message.reply_text(get_message("quota_exceeded", user_lang))
            return AI_MENU

        # Add text message to history
        history.append({"role": "user", "content": user_input})
        context.user_data["chat_history"] = history

        # Choose model
        chat_model = PREMIUM_CHAT_MODEL if (user.is_premium or user.is_admin) else FREE_CHAT_MODEL

    # Show typing indicator
    await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)

    # Get max tokens
    max_tokens = PREMIUM_MAX_TOKENS if (user.is_premium or user.is_admin) else FREE_MAX_TOKENS

    try:
        # Get AI response
        reply = await chat_with_ai(
            history,
            model=chat_model,
            temperature=0.7,
            max_tokens=max_tokens
        )
    except Exception as e:
        logger.error(f"❌ Chat error: {e}", exc_info=True)
        reply = f"⚠️ {get_message('error_ai', user_lang)}"

    # Add assistant response to history
    history.append({"role": "assistant", "content": reply})
    context.user_data["chat_history"] = history

    # Update quota and log (only for text mode)
    if not (has_photo or has_image_doc):
        increment_quota(db, user, quota_type, amount=1)
        log_action(
            db,
            user.id,
            UserAction.chat,
            meta={"mode": quota_type, "prompt": user_input[:100]}
        )

    # 🔧 FIXED: Smart code formatting
    try:
        await _send_formatted_reply(message, reply)
    except Exception as e:
        logger.warning(f"⚠️ Formatting failed: {e}")
        await message.reply_text(reply)

    return CHAT


async def _send_formatted_reply(message, reply: str):
    """
    Send reply with proper code formatting.
    Uses Markdown for code blocks when detected.
    """
    # Check if reply already has markdown code blocks
    if "```" in reply:
        try:
            await message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
            return
        except Exception as e:
            logger.warning(f"⚠️ Markdown failed: {e}")

    # Check if reply looks like code (detect by keywords and structure)
    code_keywords = [
        'def ', 'class ', 'import ', 'from ', 'function',
        'const ', 'let ', 'var ', 'public ', 'private',
        'for ', 'while ', 'if (', 'return ', '#include',
        'package ', 'use ', 'fn ', 'impl '
    ]

    lines = reply.split('\n')
    code_lines = sum(
        1 for line in lines
        if any(keyword in line.lower() for keyword in code_keywords) or
        line.strip().endswith((';', ':', '{', '}', '=>'))
    )

    # If >30% of lines are code-like and we have 3+ lines, format as code
    if len(lines) > 3 and code_lines / len(lines) > 0.3:
        formatted = f"```\n{reply}\n```"
        try:
            await message.reply_text(formatted, parse_mode=ParseMode.MARKDOWN)
            return
        except Exception as e:
            logger.warning(f"⚠️ Code formatting failed: {e}")

    # Plain text (default)
    await message.reply_text(reply)
