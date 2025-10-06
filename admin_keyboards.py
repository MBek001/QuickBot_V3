"""
Reply keyboards used in the admin panel.

The admin panel is navigated via a series of custom keyboards.  This
module centralises keyboard construction so that the layout can be
adjusted easily without touching the handlers themselves.
"""

from telegram import ReplyKeyboardMarkup


def get_admin_main_menu() -> ReplyKeyboardMarkup:
    keys = [
        ["👥 Users", "💳 Premium"],
        ["📊 Stats", "📢 Broadcast"],
        ["⬅️ Exit Admin"],
    ]
    return ReplyKeyboardMarkup(keys, resize_keyboard=True)


def get_admin_users_menu() -> ReplyKeyboardMarkup:
    keys = [
        ["🔍 Find User", "🛠 Make Admin"],
        ["⚠️ Remove Admin", "🚫 Block User"],
        ["✅ Unblock User", "📋 List Admins"],
        ["⬅️ Back"],
    ]
    return ReplyKeyboardMarkup(keys, resize_keyboard=True)


def get_admin_premium_menu() -> ReplyKeyboardMarkup:
    keys = [
        ["➕ Grant Premium", "❌ Revoke Premium"],
        ["📋 Active Premiums"],
        ["⬅️ Back"],
    ]
    return ReplyKeyboardMarkup(keys, resize_keyboard=True)


def get_admin_stats_menu() -> ReplyKeyboardMarkup:
    keys = [
        ["📊 Overview", "👥 User Stats"],
        ["💰 Revenue Stats"],
        ["⬅️ Back"],
    ]
    return ReplyKeyboardMarkup(keys, resize_keyboard=True)


def get_back_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["⬅️ Back"]], resize_keyboard=True)
