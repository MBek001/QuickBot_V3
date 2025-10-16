"""
Quota and trial management utilities.

Handles daily quota tracking for free features and rolling trial
system for premium features.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from config import TRIAL_PERIOD_DAYS, TRIAL_USES_PER_PERIOD
from models import QuotaUsage, User, TrialUsage

logger = logging.getLogger(__name__)


# ============================================================================
# QUOTA MANAGEMENT (FREE FEATURES)
# ============================================================================

def has_quota(db: Session, user: User, quota_type: str) -> bool:
    """
    Check if user has remaining quota for a feature.

    Args:
        db: Database session
        user: User instance
        quota_type: Type of quota (quick_chat, code_chat, convert, pptx)

    Returns:
        True if user has quota remaining, False otherwise
    """
    # Premium/admin users have unlimited quota
    if user.is_premium or user.is_admin:
        return True

    try:
        quota = QuotaUsage.get_or_create(db, user.id, date.today())
        used = getattr(quota, quota_type, 0)
        limit = user.get_daily_limit(quota_type)

        has_remaining = used < limit

        if not has_remaining:
            logger.info(
                f"⚠️ User {user.tg_id} exceeded {quota_type} quota: {used}/{limit}"
            )

        return has_remaining

    except Exception as e:
        logger.error(f"❌ Error checking quota for user {user.tg_id}: {e}")
        # Fail open - allow usage on error
        return True


def increment_quota(
        db: Session,
        user: User,
        quota_type: str,
        amount: int = 1
) -> None:
    """
    Increment user's quota usage.

    Args:
        db: Database session
        user: User instance
        quota_type: Type of quota to increment
        amount: Amount to increment by (default: 1)
    """
    try:
        quota = QuotaUsage.get_or_create(db, user.id, date.today())
        current = getattr(quota, quota_type, 0)
        setattr(quota, quota_type, current + amount)
        db.add(quota)

        logger.debug(
            f"📊 Incremented {quota_type} for user {user.tg_id}: {current} -> {current + amount}"
        )

    except Exception as e:
        logger.error(f"❌ Error incrementing quota for user {user.tg_id}: {e}")


def get_quota_status(db: Session, user: User) -> dict:
    """
    Get current quota status for all features.

    Args:
        db: Database session
        user: User instance

    Returns:
        Dictionary with quota types as keys and (used, limit) tuples as values
    """
    quota = QuotaUsage.get_or_create(db, user.id, date.today())

    return {
        "quick_chat": (quota.quick_chat, user.get_daily_limit("quick_chat")),
        "code_chat": (quota.code_chat, user.get_daily_limit("code_chat")),
        "convert": (quota.convert, user.get_daily_limit("convert")),
        "pptx": (quota.pptx, user.get_daily_limit("pptx")),
    }


# ============================================================================
# TRIAL MANAGEMENT (PREMIUM FEATURES)
# ============================================================================

def get_or_create_trial(db: Session, user: User) -> TrialUsage:
    """
    Get or create trial record for user.

    Args:
        db: Database session
        user: User instance

    Returns:
        TrialUsage instance
    """
    trial = db.query(TrialUsage).filter(TrialUsage.user_id == user.id).first()

    if not trial:
        trial = TrialUsage(user_id=user.id)
        db.add(trial)
        db.flush()
        logger.info(f"✨ Created trial record for user {user.tg_id}")

    return trial


def maybe_reset_trial(db: Session, user: User) -> bool:
    """
    Check if trial period has expired and reset if needed.

    Args:
        db: Database session
        user: User instance

    Returns:
        True if trial was reset, False otherwise
    """
    trial = get_or_create_trial(db, user)
    now = datetime.utcnow()

    # Check if enough time has passed since last reset
    time_since_reset = now - (trial.last_reset_at or now)

    if time_since_reset >= timedelta(days=TRIAL_PERIOD_DAYS):
        # Reset all counters
        trial.last_reset_at = now
        trial.image_gen_used = 0
        trial.image_edit_used = 0
        trial.pptx_used = 0
        db.add(trial)

        logger.info(
            f"🔄 Reset trial for user {user.tg_id} "
            f"(last reset: {trial.last_reset_at})"
        )

        return True

    return False


def trial_remaining(db: Session, user: User, feature: str) -> int:
    """
    Get remaining trial uses for a feature.

    Args:
        db: Database session
        user: User instance
        feature: Feature name (image_gen, image_edit, pptx)

    Returns:
        Number of remaining uses
    """
    trial = get_or_create_trial(db, user)
    field = f"{feature}_used"
    used = getattr(trial, field, 0)
    remaining = max(0, TRIAL_USES_PER_PERIOD - used)

    return remaining


def consume_trial(db: Session, user: User, feature: str) -> bool:

    trial = get_or_create_trial(db, user)
    field = f"{feature}_used"
    used = getattr(trial, field, 0)

    if used >= TRIAL_USES_PER_PERIOD:
        logger.warning(
            f"⚠️ User {user.tg_id} has no remaining {feature} trials "
            f"({used}/{TRIAL_USES_PER_PERIOD})"
        )
        return False

    setattr(trial, field, used + 1)
    db.add(trial)

    logger.info(
        f"✅ Consumed {feature} trial for user {user.tg_id}: "
        f"{used + 1}/{TRIAL_USES_PER_PERIOD}"
    )

    return True


def get_trial_status(db: Session, user: User) -> dict:
    """
    Get current trial status for all features.

    Args:
        db: Database session
        user: User instance

    Returns:
        Dictionary with feature status information
    """
    trial = get_or_create_trial(db, user)
    now = datetime.utcnow()

    # Calculate when trial will reset
    time_since_reset = now - (trial.last_reset_at or now)
    time_until_reset = timedelta(days=TRIAL_PERIOD_DAYS) - time_since_reset
    days_until_reset = max(0, time_until_reset.days)

    return {
        "image_gen": {
            "used": trial.image_gen_used,
            "remaining": TRIAL_USES_PER_PERIOD - trial.image_gen_used,
            "total": TRIAL_USES_PER_PERIOD,
        },
        "image_edit": {
            "used": trial.image_edit_used,
            "remaining": TRIAL_USES_PER_PERIOD - trial.image_edit_used,
            "total": TRIAL_USES_PER_PERIOD,
        },
        "pptx": {
            "used": trial.pptx_used,
            "remaining": TRIAL_USES_PER_PERIOD - trial.pptx_used,
            "total": TRIAL_USES_PER_PERIOD,
        },
        "last_reset": trial.last_reset_at,
        "days_until_reset": days_until_reset,
        "reset_period_days": TRIAL_PERIOD_DAYS,
    }


# ============================================================================
# COMBINED CHECKS
# ============================================================================

def can_use_feature(
        db: Session,
        user: User,
        feature: str,
        is_premium_feature: bool = False
) -> tuple[bool, str]:

    # Admins can always use everything
    if user.is_admin:
        return True, ""

    # Premium users can use everything
    if user.is_premium:
        return True, ""

    # For premium features, check trial
    if is_premium_feature:
        remaining = trial_remaining(db, user, feature)
        if remaining <= 0:
            return False, "trial_exhausted"
        return True, "trial"

    # For free features, check quota
    if has_quota(db, user, feature):
        return True, "quota"

    return False, "quota_exhausted"
