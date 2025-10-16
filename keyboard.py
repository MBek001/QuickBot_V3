"""
Telegram reply keyboard layouts for the bot.

FIXED VERSION:
- Added file operations keyboard
- Updated main menu with new button
"""

from telegram import ReplyKeyboardMarkup, KeyboardButton

from models_enums import Language


# ============================================================================
# LANGUAGE SELECTION
# ============================================================================

def get_language_keyboard() -> ReplyKeyboardMarkup:
    """Get keyboard for language selection."""
    keys = [
        ["🇬🇧 English", "🇷🇺 Русский", "🇺🇿 O'zbek"]
    ]
    return ReplyKeyboardMarkup(keys, resize_keyboard=True, one_time_keyboard=True)


# ============================================================================
# MAIN MENU
# ============================================================================

def get_main_keyboard(lang: Language, is_premium: bool = False) -> ReplyKeyboardMarkup:
    """
    Get main menu keyboard.

    Args:
        lang: User's language
        is_premium: Whether user has premium access
    """
    if lang == Language.ru:
        keys = [
            ["🤖 AI функции", "📁 Работа с файлами"],  # 🆕 UPDATED
            ["👤 Профиль"]
        ]
        if not is_premium:
            keys.append(["💎 Премиум"])
    elif lang == Language.uz:
        keys = [
            ["🤖 AI funksiyalari", "📁 Fayllar bilan ishlash"],  # 🆕 UPDATED
            ["👤 Profil"]
        ]
        if not is_premium:
            keys.append(["💎 Premium"])
    else:  # English
        keys = [
            ["🤖 AI functions", "📁 File Operations"],  # 🆕 UPDATED
            ["👤 Profile"]
        ]
        if not is_premium:
            keys.append(["💎 Premium"])

    return ReplyKeyboardMarkup(keys, resize_keyboard=True)


# ============================================================================
# AI FUNCTIONS MENU
# ============================================================================

def get_ai_functions_keyboard(
        lang: Language,
        is_premium: bool = False,
        is_admin: bool = False
) -> ReplyKeyboardMarkup:
    """
    Get AI functions menu keyboard.

    Args:
        lang: User's language
        is_premium: Whether user has premium access
        is_admin: Whether user is admin (same as premium)
    """
    full_access = is_premium or is_admin

    if lang == Language.ru:
        keys = [
            ["💬 Чат с AI"],
            ["🛠 Редактирование изображения" if full_access else "🛠 Редактирование (Trial)"],  # 🔧 FIXED
        ]
        # Image Gen and PPTX (premium features with trial)
        keys.append([
            "🎨 Генерация изображений" if full_access else "🎨 Генерация (Trial)",
            "📊 Презентация" if full_access else "📊 Презентация (Trial)"
        ])
        keys.append(["⬅️ Назад"])

    elif lang == Language.uz:
        keys = [
            ["💬 AI bilan suhbat"],
            ["🛠 Rasmni tahrirlash" if full_access else "🛠 Tahrirlash (Sinov)"],  # 🔧 FIXED
        ]
        keys.append([
            "🎨 Rasm yaratish" if full_access else "🎨 Rasm (Sinov)",
            "📊 Taqdimot" if full_access else "📊 Taqdimot (Sinov)"
        ])
        keys.append(["⬅️ Orqaga"])

    else:  # English
        keys = [
            ["💬 Chat with AI"],
            ["🛠 Image Editing" if full_access else "🛠 Edit Image (Trial)"],  # 🔧 FIXED
        ]
        keys.append([
            "🎨 Generate Image" if full_access else "🎨 Image (Trial)",
            "📊 Presentation" if full_access else "📊 PPTX (Trial)"
        ])
        keys.append(["⬅️ Back"])

    return ReplyKeyboardMarkup(keys, resize_keyboard=True)


# ============================================================================
# FILE OPERATIONS MENU (🆕 NEW)
# ============================================================================

def get_file_operations_keyboard(lang: Language) -> ReplyKeyboardMarkup:
    """
    Get file operations menu keyboard.

    Features:
    - DOC/DOCX to PDF
    - TXT to PDF
    - Rename files
    - Manual PPTX creation
    - Merge PDFs
    - Extract text from images (OCR)
    """
    if lang == Language.ru:
        keys = [
            ["📄 DOC → PDF", "📝 TXT → PDF"],
            ["✏️ Переименовать файл", "📊 Создать PPTX вручную"],
            ["🔗 Объединить PDF", "🔍 OCR (текст из фото)"],
            ["⬅️ Назад"]
        ]
    elif lang == Language.uz:
        keys = [
            ["📄 DOC → PDF", "📝 TXT → PDF"],
            ["✏️ Fayl nomini o'zgartirish", "📊 PPTX qo'lda yaratish"],
            ["🔗 PDF birlashtirish", "🔍 OCR (rasmdan matn)"],
            ["⬅️ Orqaga"]
        ]
    else:  # English
        keys = [
            ["📄 DOC → PDF", "📝 TXT → PDF"],
            ["✏️ Rename File", "📊 Create PPTX Manually"],
            ["🔗 Merge PDFs", "🔍 OCR (Extract Text)"],
            ["⬅️ Back"]
        ]

    return ReplyKeyboardMarkup(keys, resize_keyboard=True)


# ============================================================================
# NAVIGATION
# ============================================================================

def get_back_keyboard(lang: Language) -> ReplyKeyboardMarkup:
    """Get simple back button keyboard."""
    if lang == Language.ru:
        key = "⬅️ Назад"
    elif lang == Language.uz:
        key = "⬅️ Orqaga"
    else:
        key = "⬅️ Back"

    return ReplyKeyboardMarkup([[key]], resize_keyboard=True)


# ============================================================================
# PPTX THEME SELECTION
# ============================================================================

def get_pptx_theme_keyboard(lang: Language) -> ReplyKeyboardMarkup:
    """Get keyboard for PPTX theme selection."""
    if lang == Language.ru:
        keys = [
            ["1️⃣ Профессиональная", "2️⃣ Современная"],
            ["3️⃣ Яркая", "4️⃣ Корпоративная"],
            ["⬅️ Назад"]
        ]
    elif lang == Language.uz:
        keys = [
            ["1️⃣ Professional", "2️⃣ Zamonaviy"],
            ["3️⃣ Yorqin", "4️⃣ Korporativ"],
            ["⬅️ Orqaga"]
        ]
    else:  # English
        keys = [
            ["1️⃣ Professional", "2️⃣ Modern"],
            ["3️⃣ Vibrant", "4️⃣ Corporate"],
            ["⬅️ Back"]
        ]

    return ReplyKeyboardMarkup(keys, resize_keyboard=True)


# ============================================================================
# PROFILE MENU
# ============================================================================

def get_profile_keyboard(lang: Language, is_admin: bool = False) -> ReplyKeyboardMarkup:
    """
    Get profile menu keyboard.

    Args:
        lang: User's language
        is_admin: Whether user is admin (shows additional options)
    """
    if lang == Language.ru:
        keys = [
            ["📊 Моя статистика", "🌐 Изменить язык"],
            ["📱 Добавить телефон"],
            ["⬅️ Назад"]
        ]
    elif lang == Language.uz:
        keys = [
            ["📊 Mening statistikam", "🌐 Tilni o'zgartirish"],
            ["📱 Telefon qo'shish"],
            ["⬅️ Orqaga"]
        ]
    else:  # English
        keys = [
            ["📊 My Statistics", "🌐 Change Language"],
            ["📱 Add Phone"],
            ["⬅️ Back"]
        ]

    return ReplyKeyboardMarkup(keys, resize_keyboard=True)


# ============================================================================
# PHONE SHARING
# ============================================================================

def get_phone_share_keyboard(lang: Language) -> ReplyKeyboardMarkup:
    """Get keyboard with contact sharing button."""
    if lang == Language.ru:
        share_btn = KeyboardButton(text="📱 Отправить контакт", request_contact=True)
        back_btn = KeyboardButton(text="⬅️ Назад")
    elif lang == Language.uz:
        share_btn = KeyboardButton(text="📱 Kontaktni yuborish", request_contact=True)
        back_btn = KeyboardButton(text="⬅️ Orqaga")
    else:  # English
        share_btn = KeyboardButton(text="📱 Share Contact", request_contact=True)
        back_btn = KeyboardButton(text="⬅️ Back")

    keys = [[share_btn], [back_btn]]
    return ReplyKeyboardMarkup(keys, resize_keyboard=True)
