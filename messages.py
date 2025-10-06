"""
Static user-facing messages translated into supported languages.

This module provides a dictionary of message templates keyed by a
string identifier and language code.  Handlers look up messages via
`get_message(key, lang)` to obtain the appropriate translation.
"""

from models_enums import Language


_MESSAGES = {
    "welcome": {
        Language.en: "👋 Welcome! I'm your AI assistant bot. Please choose your language.",
        Language.ru: "👋 Добро пожаловать! Я ваш AI‑ассистент. Пожалуйста, выберите язык.",
        Language.uz: "👋 Xush kelibsiz! Men sizning AI yordamchingizman. Iltimos, tilni tanlang.",
    },
    "prompt_main_menu": {
        Language.en: "Please choose an option from the menu below.",
        Language.ru: "Пожалуйста, выберите опцию из меню ниже.",
        Language.uz: "Iltimos, quyidagi menyudan birini tanlang.",
    },
    "prompt_ai_menu": {
        Language.en: "Select an AI function:",
        Language.ru: "Выберите AI функцию:",
        Language.uz: "AI funksiyani tanlang:",
    },
    "enter_chat": {
        Language.en: "You can now chat with the AI. Send /done or use the back button when you're finished.",
        Language.ru: "Теперь вы можете общаться с AI. Отправьте /done или нажмите кнопку назад, когда закончите.",
        Language.uz: "Endi AI bilan suhbatlashishingiz mumkin. Tugatganingizda /done yuboring yoki orqaga tugmasini bosing.",
    },
    "ask_image_prompt": {
        Language.en: "Send me a description of the image you'd like me to generate.",
        Language.ru: "Отправьте описание изображения, которое вы хотите создать.",
        Language.uz: "Qanday rasm yaratishimni xohlaysiz? Tavsifini yuboring.",
    },
    "ask_image_analysis": {
        Language.en: "Send me a photo and I'll describe it for you.",
        Language.ru: "Отправьте фотографию, и я опишу её для вас.",
        Language.uz: "Menga rasm yuboring va men uni siz uchun tavsiflab beraman.",
    },
    "ask_ppt_title": {
        Language.en: "Please send the presentation title.",
        Language.ru: "Пожалуйста, отправьте заголовок презентации.",
        Language.uz: "Iltimos, taqdimot sarlavhasini yuboring.",
    },
    "ask_ppt_slides": {
        Language.en: "Send the slide contents, one per line. Each new line will create a new slide.",
        Language.ru: "Отправьте содержимое слайдов, по одному на строку. Каждая новая строка создаст новый слайд.",
        Language.uz: "Slayd mazmunini yuboring, har bir qator bitta slayd bo'ladi.",
    },
    "ppt_created": {
        Language.en: "✅ Presentation generated successfully!", 
        Language.ru: "✅ Презентация успешно создана!", 
        Language.uz: "✅ Taqdimot muvaffaqiyatli yaratildi!", 
    },
    "quota_exceeded": {
        Language.en: "🚫 You have reached the daily limit for this feature. Please try again tomorrow or upgrade to premium.",
        Language.ru: "🚫 Вы исчерпали ежедневный лимит для этой функции. Попробуйте завтра или обновитесь до премиума.",
        Language.uz: "🚫 Siz ushbu funksiya uchun kundalik limitga yetdingiz. Iltimos, ertaga qayta urinib ko'ring yoki premiumga yangilang.",
    },
    "error_ai": {
        Language.en: "⚠️ Sorry, something went wrong while contacting the AI. Please try again later.",
        Language.ru: "⚠️ Извините, что‑то пошло не так при обращении к AI. Пожалуйста, попробуйте позже.",
        Language.uz: "⚠️ Kechirasiz, AI bilan bog'lanishda xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.",
    },
}


def get_message(key: str, lang: Language) -> str:
    """Retrieve a message by key and language.

    If the key or language is missing, falls back to English.
    """
    if key not in _MESSAGES:
        raise KeyError(f"Unknown message key: {key}")
    messages = _MESSAGES[key]
    return messages.get(lang, messages.get(Language.en))
