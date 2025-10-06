"""
Quota management utilities.

Each user belongs to a plan that specifies daily limits for certain
activities.  The `QuotaUsage` table tracks how many times the user has
performed each activity on the current day.  These functions check
limits and increment counters as necessary.
"""

from sqlalchemy.orm import Session

from models import User, QuotaUsage


def has_quota(db: Session, user: User, quota_type: str) -> bool:
    """Determine whether the user still has quota left for the given type.

    Parameters
    ----------
    db : Session
        An active database session.
    user : User
        The user performing the action.
    quota_type : str
        One of 'quick_chat', 'code_chat', 'convert', 'pptx'.

    Returns
    -------
    bool
        True if the user has remaining quota or if no limit is set.
    """
    limit = user.get_daily_limit(quota_type)
    # Zero or negative limit implies unlimited usage
    if limit <= 0:
        return True
    quota = QuotaUsage.get_or_create(db, user.id)
    used = getattr(quota, quota_type, 0)
    return used < limit


def increment_quota(db: Session, user: User, quota_type: str, amount: int = 1) -> None:
    """Increment the usage counter for the given quota type.

    If the quota record does not exist it will be created automatically.

    Parameters
    ----------
    db : Session
        An active database session.
    user : User
        The user performing the action.
    quota_type : str
        The name of the quota column to increment.
    amount : int
        How much to increment the counter by.  Defaults to 1.
    """
    quota = QuotaUsage.get_or_create(db, user.id)
    current = getattr(quota, quota_type, 0)
    setattr(quota, quota_type, current + amount)
    db.add(quota)
    # Committing is the responsibility of the caller via get_db context manager
