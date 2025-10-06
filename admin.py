"""
Administrative command handlers for the AI assistant bot.

This module implements an extensive admin panel that allows privileged
users to manage other users, grant and revoke premium access, view
statistics and broadcast announcements.  It is adapted from the
example provided by the user and refactored to use relative imports.

To enable admin functionality in your bot, add the handlers returned
by `get_admin_handlers()` to your application.  Only users flagged
as admins in the database or listed in the `ADMIN_IDS` config will
gain access.
"""

import logging
from datetime import datetime, timedelta, timezone, date
from typing import Optional

from telegram import Update, ReplyKeyboardRemove
from telegram.constants import ParseMode
from telegram.ext import (
    CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters
)

from admin_keyboards import (
    get_admin_main_menu,
    get_admin_users_menu,
    get_admin_premium_menu,
    get_admin_stats_menu,
    get_back_menu,
)
from db import get_db, log_action
from models import User, PremiumGrant, Plan, QuotaUsage, ActionLog
from models_enums import PlanCode, UserAction
from sqlalchemy import func

logger = logging.getLogger(__name__)

(
    ADMIN_MAIN,
    ADMIN_USERS,
    ADMIN_PREMIUM,
    ADMIN_STATS,
    A_FIND_USER_WAIT,
    A_MAKE_ADMIN_WAIT,
    A_REMOVE_ADMIN_WAIT,
    A_BLOCK_USER_WAIT,
    A_UNBLOCK_USER_WAIT,
    A_GRANT_PREM_WAIT_ID,
    A_GRANT_PREM_WAIT_DAYS,
    A_REVOKE_PREM_WAIT,
    A_BROADCAST_MESSAGE,
    A_BROADCAST_CONFIRM,
) = range(14)


def _require_admin(func):
    """Decorator to restrict handlers to admin users."""

    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if context.user_data.get("is_admin_verified"):
            return await func(update, context, *args, **kwargs)

        # Verify against DB
        with get_db() as db:
            tg_user = update.effective_user
            user: Optional[User] = db.query(User).filter(User.tg_id == tg_user.id).first()

            if not user or not user.is_admin:
                await update.effective_message.reply_text(
                    "🚫 You are not authorized to use admin commands."
                )
                return ConversationHandler.END

            context.user_data["is_admin_verified"] = True
            logger.info("Admin access granted to %s (TG: %s)", user.full_name, tg_user.id)

        return await func(update, context, *args, **kwargs)

    return wrapper


def _parse_int(s: str) -> Optional[int]:
    try:
        return int(s.strip())
    except Exception:
        return None


def _get_user_by_tg(db, tg_id: int) -> Optional[User]:
    return db.query(User).filter(User.tg_id == tg_id).first()


def _fmt_user(u: User) -> str:
    """Format user info for display with proper markdown escaping."""
    premium = "Yes" if (u.premium_until and u.premium_until > datetime.utcnow()) else "No"

    # Escape markdown special characters
    def escape_md(text: Optional[str]) -> str:
        if not text:
            return "N/A"
        text = str(text)
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text

    username_display = f"@{escape_md(u.username)}" if u.username else "N/A"
    name_parts = []
    if u.first_name:
        name_parts.append(escape_md(u.first_name))
    if u.last_name:
        name_parts.append(escape_md(u.last_name))
    full_name = " ".join(name_parts) if name_parts else "Unknown"

    return (
        f"📋 **User Info**\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"**ID:** `{u.id}`\n"
        f"**Telegram ID:** `{u.tg_id}`\n"
        f"**Name:** {full_name}\n"
        f"**Username:** {username_display}\n"
        f"**Phone:** {escape_md(u.phone) if u.phone else 'N/A'}\n"
        f"**Language:** {u.lang.value if u.lang else 'N/A'}\n"
        f"**Plan:** {u.plan_code.value.upper()}\n"
        f"**Premium:** {premium}"
        + (f" \(until {u.premium_until:%Y-%m-%d %H:%M}\)" if u.premium_until else "")
        + f"\n**Blocked:** {'✅ Yes' if u.is_blocked else '❌ No'}"
        + f"\n**Admin:** {'✅ Yes' if u.is_admin else '❌ No'}"
        + f"\n**Registered:** {u.created_at:%Y\-%m\-%d %H:%M}"
    )


def _log_admin_action(db, admin_id: int, action: str, target_id: Optional[int] = None, details: str = ""):
    try:
        log_action(db, admin_id, UserAction.profile_view,
                   meta={"admin_action": action, "target": target_id, "details": details})
        logger.info("Admin action logged: %s by admin %s on user %s", action, admin_id, target_id)
    except Exception as e:
        logger.error("Failed to log admin action: %s", e)


@_require_admin
async def admin_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "⚙️ **Admin Panel**\n\nWelcome to the admin control panel.",
        reply_markup=get_admin_main_menu(),
        parse_mode=ParseMode.MARKDOWN
    )
    return ADMIN_MAIN


@_require_admin
async def admin_main_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    logger.info("Admin main menu selection: %s", text)

    if text == "👥 Users":
        await update.message.reply_text(
            "👥 **User Management**\n\nManage users, admins, and permissions.",
            reply_markup=get_admin_users_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_USERS

    if text == "💳 Premium":
        await update.message.reply_text(
            "💳 **Premium Management**\n\nGrant or revoke premium access.",
            reply_markup=get_admin_premium_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_PREMIUM

    if text == "📊 Stats":
        await update.message.reply_text(
            "📊 **Statistics**\n\nView bot statistics and analytics.",
            reply_markup=get_admin_stats_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_STATS

    if text == "📢 Broadcast":
        await update.message.reply_text(
            "📢 **Broadcast Message**\n\nSend a message to all users.\n\nType your message:",
            reply_markup=get_back_menu(),
        )
        return A_BROADCAST_MESSAGE

    if text == "⬅️ Exit Admin":
        await update.message.reply_text(
            "👋 Exited admin panel. Use /start to return to main menu.",
            reply_markup=ReplyKeyboardRemove(),
        )
        context.user_data.clear()
        return ConversationHandler.END

    await update.message.reply_text(
        "❓ Unknown option. Please select from the menu.",
        reply_markup=get_admin_main_menu(),
    )
    return ADMIN_MAIN


@_require_admin
async def admin_users_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    logger.info(f"Admin users menu selection: {text}")

    if text == "⬅️ Back":
        await update.message.reply_text(
            "⚙️ **Admin Panel**",
            reply_markup=get_admin_main_menu(),
            parse_mode="Markdown"
        )
        return ADMIN_MAIN

    elif text == "🔍 Find User":
        await update.message.reply_text(
            "🔍 **Find User**\n\nSend the Telegram ID, username, or name:",
            reply_markup=get_back_menu(),
            parse_mode="Markdown"
        )
        return A_FIND_USER_WAIT

    elif text == "🛠 Make Admin":
        await update.message.reply_text(
            "🛠 **Promote to Admin**\n\nSend the Telegram ID to promote:",
            reply_markup=get_back_menu(),
            parse_mode="Markdown"
        )
        return A_MAKE_ADMIN_WAIT

    elif text == "⚠️ Remove Admin":
        await update.message.reply_text(
            "⚠️ **Remove Admin Rights**\n\nSend the Telegram ID:",
            reply_markup=get_back_menu(),
            parse_mode="Markdown"
        )
        return A_REMOVE_ADMIN_WAIT

    elif text == "🚫 Block User":
        await update.message.reply_text(
            "🚫 **Block User**\n\nSend the Telegram ID to block:",
            reply_markup=get_back_menu(),
            parse_mode="Markdown"
        )
        return A_BLOCK_USER_WAIT

    elif text == "✅ Unblock User":
        await update.message.reply_text(
            "✅ **Unblock User**\n\nSend the Telegram ID to unblock:",
            reply_markup=get_back_menu(),
            parse_mode="Markdown"
        )
        return A_UNBLOCK_USER_WAIT

    elif text == "📋 List Admins":
        with get_db() as db:
            admins = db.query(User).filter(User.is_admin == True).all()
            if not admins:
                await update.message.reply_text("No admins found.")
            else:
                lines = []
                for a in admins:
                    username_text = f"@{a.username}" if a.username else "N/A"
                    username_text = username_text.replace("_", "\\_").replace("*", "\\*")
                    lines.append(
                        f"• {a.first_name or 'Unknown'} ({username_text}) \\- TG: `{a.tg_id}`"
                    )
                await update.message.reply_text(
                    f"👑 **Current Admins ({len(admins)}):**\n\n" + "\n".join(lines),
                    parse_mode="Markdown"
                )
        return ADMIN_USERS

    else:
        await update.message.reply_text(
            "❓ Unknown option. Please select from the menu.",
            reply_markup=get_admin_users_menu()
        )
        return ADMIN_USERS


@_require_admin
async def handle_find_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "⬅️ Back":
        await update.message.reply_text(
            "👥 **User Management**",
            reply_markup=get_admin_users_menu(),
            parse_mode="Markdown"
        )
        return ADMIN_USERS
    with get_db() as db:
        users = []
        tg_id = _parse_int(text)
        if tg_id:
            u = _get_user_by_tg(db, tg_id)
            if u:
                users.append(u)
        if not users:
            search_term = f"%{text}%"
            users = db.query(User).filter(
                (User.first_name.ilike(search_term)) |
                (User.last_name.ilike(search_term)) |
                (User.username.ilike(search_term))
            ).limit(5).all()
        if not users:
            await update.message.reply_text(
                "❌ No users found matching your search.",
                reply_markup=get_back_menu()
            )
            return A_FIND_USER_WAIT
        if len(users) == 1:
            await update.message.reply_text(
                _fmt_user(users[0]),
                reply_markup=get_admin_users_menu(),
                parse_mode="Markdown"
            )
        else:
            results = "\n\n".join([_fmt_user(u) for u in users])
            await update.message.reply_text(
                f"✅ **Found {len(users)} users:**\n\n{results}",
                reply_markup=get_admin_users_menu(),
                parse_mode="Markdown"
            )
        return ADMIN_USERS


@_require_admin
async def handle_make_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "⬅️ Back":
        await update.message.reply_text(
            "👥 **User Management**",
            reply_markup=get_admin_users_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_USERS
    tg_id = _parse_int(text)
    if tg_id is None:
        await update.message.reply_text("❌ Invalid Telegram ID.", reply_markup=get_back_menu())
        return A_MAKE_ADMIN_WAIT
    with get_db() as db:
        u = _get_user_by_tg(db, tg_id)
        if not u:
            await update.message.reply_text("❌ User not found.", reply_markup=get_back_menu())
            return A_MAKE_ADMIN_WAIT
        if u.is_admin:
            await update.message.reply_text(f"ℹ️ {u.full_name} is already an admin.",
                                            reply_markup=get_admin_users_menu())
            return ADMIN_USERS
        admin = _get_user_by_tg(db, update.effective_user.id)
        u.is_admin = True
        db.add(u)
        _log_admin_action(db, admin.id, "make_admin", u.id, f"Promoted {u.full_name}")
        await update.message.reply_text(
            f"✅ **{u.full_name}** is now an admin!",
            reply_markup=get_admin_users_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_USERS


@_require_admin
async def handle_remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "⬅️ Back":
        await update.message.reply_text(
            "👥 **User Management**",
            reply_markup=get_admin_users_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_USERS
    tg_id = _parse_int(text)
    if tg_id is None:
        await update.message.reply_text("❌ Invalid Telegram ID.", reply_markup=get_back_menu())
        return A_REMOVE_ADMIN_WAIT
    with get_db() as db:
        u = _get_user_by_tg(db, tg_id)
        if not u:
            await update.message.reply_text("❌ User not found.", reply_markup=get_back_menu())
            return A_REMOVE_ADMIN_WAIT
        if not u.is_admin:
            await update.message.reply_text(f"ℹ️ {u.full_name} is not an admin.",
                                            reply_markup=get_admin_users_menu())
            return ADMIN_USERS
        if u.tg_id == update.effective_user.id:
            await update.message.reply_text("⚠️ You cannot remove your own admin rights!",
                                            reply_markup=get_admin_users_menu())
            return ADMIN_USERS
        admin = _get_user_by_tg(db, update.effective_user.id)
        u.is_admin = False
        db.add(u)
        _log_admin_action(db, admin.id, "remove_admin", u.id, f"Demoted {u.full_name}")
        await update.message.reply_text(
            f"✅ Admin rights removed from **{u.full_name}**.",
            reply_markup=get_admin_users_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_USERS


@_require_admin
async def handle_block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "⬅️ Back":
        await update.message.reply_text(
            "👥 **User Management**",
            reply_markup=get_admin_users_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_USERS
    tg_id = _parse_int(text)
    if tg_id is None:
        await update.message.reply_text("❌ Invalid Telegram ID.", reply_markup=get_back_menu())
        return A_BLOCK_USER_WAIT
    with get_db() as db:
        u = _get_user_by_tg(db, tg_id)
        if not u:
            await update.message.reply_text("❌ User not found.", reply_markup=get_back_menu())
            return A_BLOCK_USER_WAIT
        if u.is_blocked:
            await update.message.reply_text(f"ℹ️ {u.full_name} is already blocked.",
                                            reply_markup=get_admin_users_menu())
            return ADMIN_USERS
        if u.is_admin:
            await update.message.reply_text("⚠️ Cannot block an admin! Remove admin rights first.",
                                            reply_markup=get_admin_users_menu())
            return ADMIN_USERS
        admin = _get_user_by_tg(db, update.effective_user.id)
        u.is_blocked = True
        db.add(u)
        _log_admin_action(db, admin.id, "block_user", u.id, f"Blocked {u.full_name}")
        await update.message.reply_text(
            f"🚫 **{u.full_name}** has been blocked.",
            reply_markup=get_admin_users_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_USERS


@_require_admin
async def handle_unblock_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "⬅️ Back":
        await update.message.reply_text(
            "👥 **User Management**",
            reply_markup=get_admin_users_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_USERS
    tg_id = _parse_int(text)
    if tg_id is None:
        await update.message.reply_text("❌ Invalid Telegram ID.", reply_markup=get_back_menu())
        return A_UNBLOCK_USER_WAIT
    with get_db() as db:
        u = _get_user_by_tg(db, tg_id)
        if not u:
            await update.message.reply_text("❌ User not found.", reply_markup=get_back_menu())
            return A_UNBLOCK_USER_WAIT
        if not u.is_blocked:
            await update.message.reply_text(f"ℹ️ {u.full_name} is not blocked.",
                                            reply_markup=get_admin_users_menu())
            return ADMIN_USERS
        admin = _get_user_by_tg(db, update.effective_user.id)
        u.is_blocked = False
        db.add(u)
        _log_admin_action(db, admin.id, "unblock_user", u.id, f"Unblocked {u.full_name}")
        await update.message.reply_text(
            f"✅ **{u.full_name}** has been unblocked.",
            reply_markup=get_admin_users_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_USERS


@_require_admin
async def admin_premium_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    logger.info("Admin premium menu selection: %s", text)
    if text == "⬅️ Back":
        await update.message.reply_text(
            "⚙️ **Admin Panel**",
            reply_markup=get_admin_main_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_MAIN
    if text == "➕ Grant Premium":
        await update.message.reply_text(
            "➕ **Grant Premium**\n\nSend the Telegram ID:",
            reply_markup=get_back_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return A_GRANT_PREM_WAIT_ID
    if text == "❌ Revoke Premium":
        await update.message.reply_text(
            "❌ **Revoke Premium**\n\nSend the Telegram ID:",
            reply_markup=get_back_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return A_REVOKE_PREM_WAIT
    elif text == "📋 Active Premiums":
        with get_db() as db:
            now = datetime.now(timezone.utc)
            users = db.query(User).filter(
                User.premium_until != None,
                User.premium_until > now
            ).order_by(User.premium_until.desc()).limit(30).all()
            if not users:
                await update.message.reply_text("ℹ️ No active premium users.")
            else:
                lines = []
                for u in users:
                    name = (u.first_name or "Unknown").replace("_", "\\_").replace("*", "\\*").replace("[",
                                                      "\\[").replace("]", "\\]")
                    username = f"@{u.username}" if u.username else "N/A"
                    username = username.replace("_", "\\_").replace("*", "\\*")
                    exp_date = u.premium_until.strftime("%Y\-%m\-%d %H:%M")
                    lines.append(
                        f"• {name} ({username})\n  TG: `{u.tg_id}` | Until: {exp_date}"
                    )
                await update.message.reply_text(
                    f"💎 **Active Premium Users ({len(users)}):**\n\n" + "\n\n".join(lines),
                    parse_mode="Markdown"
                )
        return ADMIN_PREMIUM
    await update.message.reply_text(
        "❓ Unknown option. Please select from the menu.",
        reply_markup=get_admin_premium_menu(),
    )
    return ADMIN_PREMIUM


@_require_admin
async def handle_grant_premium_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "⬅️ Back":
        await update.message.reply_text(
            "💳 **Premium Management**",
            reply_markup=get_admin_premium_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_PREMIUM
    tg_id = _parse_int(text)
    if tg_id is None:
        await update.message.reply_text("❌ Invalid Telegram ID.", reply_markup=get_back_menu())
        return A_GRANT_PREM_WAIT_ID
    with get_db() as db:
        u = _get_user_by_tg(db, tg_id)
        if not u:
            await update.message.reply_text("❌ User not found.", reply_markup=get_back_menu())
            return A_GRANT_PREM_WAIT_ID
        context.user_data["grant_prem_tg_id"] = tg_id
        context.user_data["grant_prem_user_name"] = u.full_name
        await update.message.reply_text(
            f"✅ User found: **{u.full_name}**\n\n"
            "How many days of premium to grant? (e.g., 7, 30, 90, 365)",
            reply_markup=get_back_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return A_GRANT_PREM_WAIT_DAYS


@_require_admin
async def handle_grant_premium_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "⬅️ Back":
        await update.message.reply_text(
            "💳 **Premium Management**",
            reply_markup=get_admin_premium_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )
        context.user_data.pop("grant_prem_tg_id", None)
        context.user_data.pop("grant_prem_user_name", None)
        return ADMIN_PREMIUM
    days = _parse_int(text)
    if days is None or days <= 0:
        await update.message.reply_text("❌ Please send a positive number of days.", reply_markup=get_back_menu())
        return A_GRANT_PREM_WAIT_DAYS
    tg_id = context.user_data.get("grant_prem_tg_id")
    if not tg_id:
        await update.message.reply_text("⚠️ Session expired. Please start over.",
                                        reply_markup=get_admin_premium_menu())
        return ADMIN_PREMIUM
    with get_db() as db:
        u = _get_user_by_tg(db, tg_id)
        if not u:
            await update.message.reply_text("❌ User not found.", reply_markup=get_admin_premium_menu())
            return ADMIN_PREMIUM
        now = datetime.utcnow()
        base = u.premium_until if (u.premium_until and u.premium_until > now) else now
        expires = base + timedelta(days=days)
        u.plan_code = PlanCode.premium
        u.premium_until = expires
        admin = _get_user_by_tg(db, update.effective_user.id)
        grant = PremiumGrant(
            admin_id=admin.id,
            user_id=u.id,
            days=days,
            expires_at=expires,
            reason=f"Admin grant by {admin.full_name}",
        )
        db.add(u)
        db.add(grant)
        _log_admin_action(db, admin.id, "grant_premium", u.id,
                          f"Granted {days} days premium to {u.full_name}")
        await update.message.reply_text(
            "✅ **Premium Granted!**\n\n"
            f"User: **{u.full_name}**\n"
            f"Duration: **{days} days**\n"
            f"Expires: {expires:%Y-%m-%d %H:%M} UTC",
            reply_markup=get_admin_premium_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )
        context.user_data.pop("grant_prem_tg_id", None)
        context.user_data.pop("grant_prem_user_name", None)
        return ADMIN_PREMIUM


@_require_admin
async def handle_revoke_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "⬅️ Back":
        await update.message.reply_text(
            "💳 **Premium Management**",
            reply_markup=get_admin_premium_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_PREMIUM
    tg_id = _parse_int(text)
    if tg_id is None:
        await update.message.reply_text("❌ Invalid Telegram ID.", reply_markup=get_back_menu())
        return A_REVOKE_PREM_WAIT
    with get_db() as db:
        u = _get_user_by_tg(db, tg_id)
        if not u:
            await update.message.reply_text("❌ User not found.", reply_markup=get_back_menu())
            return A_REVOKE_PREM_WAIT
        if not getattr(u, "is_premium", False) and not (u.premium_until and u.premium_until > datetime.utcnow()):
            await update.message.reply_text(f"ℹ️ {u.full_name} does not have premium.",
                                            reply_markup=get_admin_premium_menu())
            return ADMIN_PREMIUM
        admin = _get_user_by_tg(db, update.effective_user.id)
        u.plan_code = PlanCode.free
        u.premium_until = None
        db.add(u)
        _log_admin_action(db, admin.id, "revoke_premium", u.id, f"Revoked premium from {u.full_name}")
        await update.message.reply_text(
            f"✅ Premium revoked from **{u.full_name}**.",
            reply_markup=get_admin_premium_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_PREMIUM


@_require_admin
async def admin_stats_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    logger.info(f"Admin stats menu selection: {text}")
    if text == "⬅️ Back":
        await update.message.reply_text(
            "⚙️ **Admin Panel**",
            reply_markup=get_admin_main_menu(),
            parse_mode="Markdown"
        )
        return ADMIN_MAIN
    elif text == "📊 Overview":
        with get_db() as db:
            total_users = db.query(User).count()
            active_premium = db.query(User).filter(
                User.premium_until != None,
                User.premium_until > datetime.utcnow()
            ).count()
            total_admins = db.query(User).filter(User.is_admin == True).count()
            blocked_users = db.query(User).filter(User.is_blocked == True).count()
            today = date.today()
            today_quota = db.query(QuotaUsage).filter(
                QuotaUsage.usage_date == today
            ).all()
            today_chats = sum(q.quick_chat + q.code_chat for q in today_quota)
            today_conversions = sum(q.convert for q in today_quota)
            today_pptx = sum(q.pptx for q in today_quota)
            free_users = db.query(User).filter(User.plan_code == PlanCode.free).count()
            premium_users = db.query(User).filter(User.plan_code == PlanCode.premium).count()
            msg = (
                "📊 **Bot Statistics**\n"
                "━━━━━━━━━━━━━━━━\n\n"
                f"👥 **Total Users:** {total_users}\n"
                f"💎 **Active Premium:** {active_premium}\n"
                f"🧑‍💼 **Admins:** {total_admins}\n"
                f"🚫 **Blocked:** {blocked_users}\n\n"
                f"📈 **Plan Distribution:**\n"
                f"  • Free: {free_users}\n"
                f"  • Premium: {premium_users}\n\n"
                f"📅 **Today's Usage:**\n"
                f"  • AI Chats: {today_chats}\n"
                f"  • File Conversions: {today_conversions}\n"
                f"  • PPTX Generated: {today_pptx}"
            )
            await update.message.reply_text(msg, parse_mode="Markdown")
        return ADMIN_STATS
    elif text == "👥 User Stats":
        with get_db() as db:
            today = date.today()
            top_users = db.query(
                QuotaUsage.user_id,
                func.sum(QuotaUsage.quick_chat + QuotaUsage.code_chat +
                         QuotaUsage.convert + QuotaUsage.pptx).label('total')
            ).filter(
                QuotaUsage.usage_date == today
            ).group_by(QuotaUsage.user_id).order_by(func.sum(
                QuotaUsage.quick_chat + QuotaUsage.code_chat +
                QuotaUsage.convert + QuotaUsage.pptx
            ).desc()).limit(10).all()
            if not top_users:
                await update.message.reply_text(
                    "ℹ️ No user activity today.",
                    parse_mode="Markdown"
                )
            else:
                lines = []
                for idx, (user_id, total) in enumerate(top_users, 1):
                    user = db.query(User).filter(User.id == user_id).first()
                    if user:
                        lines.append(
                            f"{idx}. **{user.first_name}** \\- {int(total)} actions"
                        )
                msg = "🏆 **Top 10 Users Today:**\n\n" + "\n".join(lines)
                await update.message.reply_text(msg, parse_mode="Markdown")
        return ADMIN_STATS
    elif text == "💰 Revenue Stats":
        with get_db() as db:
            total_grants = db.query(PremiumGrant).count()
            active_grants = db.query(PremiumGrant).filter(
                PremiumGrant.expires_at > datetime.utcnow()
            ).count()
            total_days = db.query(func.sum(PremiumGrant.days)).scalar() or 0
            msg = (
                "💰 **Premium Statistics**\n"
                "━━━━━━━━━━━━━━━━\n\n"
                f"📋 **Total Grants:** {total_grants}\n"
                f"✅ **Active Grants:** {active_grants}\n"
                f"📆 **Total Days Granted:** {int(total_days)}\n"
            )
            await update.message.reply_text(msg, parse_mode="Markdown")
        return ADMIN_STATS
    else:
        await update.message.reply_text(
            "❓ Unknown option. Please select from the menu.",
            reply_markup=get_admin_stats_menu()
        )
        return ADMIN_STATS


@_require_admin
async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "⬅️ Back":
        await update.message.reply_text(
            "⚙️ **Admin Panel**",
            reply_markup=get_admin_main_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ADMIN_MAIN
    if len(text) < 5:
        await update.message.reply_text(
            "❌ Message too short. Please send a message with at least 5 characters.",
            reply_markup=get_back_menu(),
        )
        return A_BROADCAST_MESSAGE
    context.user_data["broadcast_message"] = text
    await update.message.reply_text(
        f"📢 **Broadcast Preview:**\n\n{text}\n\n"
        "⚠️ This will be sent to ALL users!\n\n"
        "Type **CONFIRM** to proceed or **CANCEL** to abort.",
        reply_markup=get_back_menu(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return A_BROADCAST_CONFIRM


@_require_admin
async def handle_broadcast_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip().upper()
    if text in {"⬅️ BACK", "CANCEL"}:
        context.user_data.pop("broadcast_message", None)
        await update.message.reply_text(
            "❌ Broadcast cancelled.",
            reply_markup=get_admin_main_menu(),
        )
        return ADMIN_MAIN
    if text != "CONFIRM":
        await update.message.reply_text(
            "⚠️ Type **CONFIRM** to send or **CANCEL** to abort.",
            reply_markup=get_back_menu(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return A_BROADCAST_CONFIRM
    broadcast_msg = context.user_data.get("broadcast_message")
    if not broadcast_msg:
        await update.message.reply_text(
            "⚠️ Session expired. Please start over.",
            reply_markup=get_admin_main_menu(),
        )
        return ADMIN_MAIN
    with get_db() as db:
        users = db.query(User).filter(User.is_blocked.is_(False)).all()
        await update.message.reply_text(
            f"📤 Starting broadcast to {len(users)} users...",
            reply_markup=get_admin_main_menu(),
        )
        success, failed = 0, 0
        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user.tg_id,
                    text=f"📢 **Announcement**\n\n{broadcast_msg}",
                    parse_mode=ParseMode.MARKDOWN,
                )
                success += 1
            except Exception as e:
                logger.warning("Failed to send broadcast to %s: %s", user.tg_id, e)
                failed += 1
        admin = _get_user_by_tg(db, update.effective_user.id)
        _log_admin_action(db, admin.id, "broadcast", None,
                          f"Sent to {success} users, {failed} failed")
        await update.message.reply_text(
            "✅ **Broadcast Complete!**\n\n"
            f"✅ Sent: {success}\n"
            f"❌ Failed: {failed}",
            parse_mode=ParseMode.MARKDOWN,
        )
        context.user_data.pop("broadcast_message", None)
        return ADMIN_MAIN


@_require_admin
async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Admin panel closed. Use /admin to return.",
        reply_markup=ReplyKeyboardRemove(),
    )
    context.user_data.clear()
    return ConversationHandler.END


def build_admin_conversation_handler() -> ConversationHandler:
    """Construct and return the admin ConversationHandler."""
    return ConversationHandler(
        entry_points=[CommandHandler("admin", admin_entry)],
        states={
            ADMIN_MAIN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_main_router),
            ],
            ADMIN_USERS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_users_router),
            ],
            ADMIN_PREMIUM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_premium_router),
            ],
            ADMIN_STATS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_stats_router),
            ],
            A_FIND_USER_WAIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_find_user),
            ],
            A_MAKE_ADMIN_WAIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_make_admin),
            ],
            A_REMOVE_ADMIN_WAIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_remove_admin),
            ],
            A_BLOCK_USER_WAIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_block_user),
            ],
            A_UNBLOCK_USER_WAIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unblock_user),
            ],
            A_GRANT_PREM_WAIT_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_grant_premium_user),
            ],
            A_GRANT_PREM_WAIT_DAYS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_grant_premium_days),
            ],
            A_REVOKE_PREM_WAIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_revoke_premium),
            ],
            A_BROADCAST_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_message),
            ],
            A_BROADCAST_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_confirm),
            ],
        },
        fallbacks=[CommandHandler("cancel", admin_cancel)],
        name="admin_conversation",
        persistent=False,
    )


def get_admin_handlers():
    """Return a list containing the admin conversation handler.

    This helper is provided for backwards compatibility with older
    implementations that expect a list of handlers.
    """
    return [build_admin_conversation_handler()]
