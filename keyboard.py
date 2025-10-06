"""
Keyboards for user and admin interactions.

This module centralises all Telegram keyboard construction so that
different parts of the bot can request the appropriate keyboard given
the current language or context.  All keyboards are returned as
`ReplyKeyboardMarkup` objects ready to be passed to Telegram API
methods.
"""

from telegram import ReplyKeyboardMarkup
from models_enums import Language


def get_language_keyboard() -> ReplyKeyboardMarkup:
    """Return a keyboard prompting the user to select a language.

    The keyboard is one-time to encourage the user to make a selection
    immediately.  Labels are displayed in the respective languages.
    """
    keys = [
        ["🇬🇧 English", "🇷🇺 Русский", "🇺🇿 O‘zbek"]
    ]
    return ReplyKeyboardMarkup(keys, resize_keyboard=True, one_time_keyboard=True)


def get_main_keyboard(lang: Language) -> ReplyKeyboardMarkup:
    """Return the main menu keyboard for the given language.

    At present the main menu exposes only the AI functions.  Additional
    items can be added here as new features are implemented.
    """
    if lang == Language.ru:
        keys = [["🤖 AI функции"]]
    elif lang == Language.uz:
        keys = [["🤖 AI funksiyalari"]]
    else:
        keys = [["🤖 AI functions"]]
    return ReplyKeyboardMarkup(keys, resize_keyboard=True)


def get_ai_functions_keyboard(lang: Language) -> ReplyKeyboardMarkup:
    """Return the AI submenu keyboard for the given language.

    The menu includes options to chat with AI, generate images,
    analyse images and create presentations.  A back button allows
    returning to the previous menu.  Labels are translated.
    """
    if lang == Language.ru:
        keys = [
            ["💬 Чат с AI", "🎨 Создать изображение"],
            ["🖼️ Анализ изображения", "📊 Создать презентацию"],
            ["⬅️ Назад"],
        ]
    elif lang == Language.uz:
        keys = [
            ["💬 AI bilan suhbat", "🎨 Rasm yaratish"],
            ["🖼️ Rasm tahlili", "📊 Slayd tayyorlash"],
            ["⬅️ Orqaga"],
        ]
    else:
        keys = [
            ["💬 Chat with AI", "🎨 Generate image"],
            ["🖼️ Image analysis", "📊 Create presentation"],
            ["⬅️ Back"],
        ]
    return ReplyKeyboardMarkup(keys, resize_keyboard=True)


def get_back_keyboard(lang: Language) -> ReplyKeyboardMarkup:
    """Return a simple back button keyboard for the given language."""
    if lang == Language.ru:
        key = "⬅️ Назад"
    elif lang == Language.uz:
        key = "⬅️ Orqaga"
    else:
        key = "⬅️ Back"
    return ReplyKeyboardMarkup([[key]], resize_keyboard=True)
