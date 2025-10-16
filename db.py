"""
Database connection and utility functions.

Provides session management, initialization, and common database operations.

FIXED FOR:
- Windows emoji encoding issues
- SQLAlchemy 2.0 text() requirements
"""

import logging
from contextlib import contextmanager
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from config import DATABASE_URL
from models import Base, ActionLog
from models_enums import UserAction, PlanCode

logger = logging.getLogger(__name__)

# ============================================================================
# ENGINE CONFIGURATION (OPTIMIZED)
# ============================================================================

# Create engine with appropriate settings
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 20  # Increase timeout to 20 seconds
    } if DATABASE_URL.startswith("sqlite") else {},
    future=True,
    echo=False,  # Set to True for SQL debugging
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Create session factory
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    future=True
)


# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def init_db() -> None:
    """
    Initialize database schema and create default data.

    Creates all tables and inserts default plans if they don't exist.
    """
    from models import Plan

    logger.info("Initializing database...")

    # Create all tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")

    # Create default plans
    with get_db() as db:
        # Free plan
        free_plan = db.query(Plan).filter(Plan.code == PlanCode.free).first()
        if not free_plan:
            free_plan = Plan(
                code=PlanCode.free,
                title="Free Plan",
                description="Basic features with daily limits",
                daily_quick_chat=30,
                daily_code_chat=10,
                daily_convert=5,
                daily_pptx=3,
                max_file_mb=10,
                priority=False,
            )
            db.add(free_plan)
            logger.info("Created Free plan")

        # Premium plan
        premium_plan = db.query(Plan).filter(Plan.code == PlanCode.premium).first()
        if not premium_plan:
            premium_plan = Plan(
                code=PlanCode.premium,
                title="Premium Plan",
                description="Unlimited access to all features",
                daily_quick_chat=999999,
                daily_code_chat=999999,
                daily_convert=999999,
                daily_pptx=999999,
                max_file_mb=50,
                priority=True,
            )
            db.add(premium_plan)
            logger.info("Created Premium plan")

    logger.info("Database initialization complete")


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

@contextmanager
def get_db():
    """
    Context manager for database sessions.

    Usage:
        with get_db() as db:
            user = db.query(User).first()
            # ... do work ...

    Automatically commits on success and rolls back on error.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}", exc_info=True)
        raise
    finally:
        db.close()


def get_session() -> Session:
    """
    Get a new database session.

    Note: Caller is responsible for closing the session.
    Use get_db() context manager when possible.
    """
    return SessionLocal()


# ============================================================================
# LOGGING HELPERS
# ============================================================================

def log_action(
        db: Session,
        user_id: int,
        action: UserAction,
        ref_id: Optional[int] = None,
        meta: Optional[dict] = None
) -> ActionLog:
    """
    Log a user action to the database.

    Args:
        db: Database session
        user_id: ID of the user performing the action
        action: Type of action being logged
        ref_id: Optional reference ID (e.g., file ID, job ID)
        meta: Optional metadata dictionary

    Returns:
        Created ActionLog instance
    """
    try:
        log = ActionLog(
            user_id=user_id,
            action=action,
            ref_id=ref_id,
            meta=meta or {}
        )
        db.add(log)
        db.flush()
        return log
    except Exception as e:
        logger.error(f"Failed to log action {action} for user {user_id}: {e}")
        # Don't raise - logging failure shouldn't break the app
        return None


# ============================================================================
# CLEANUP UTILITIES
# ============================================================================

def cleanup_old_sessions(days: int = 30) -> int:
    """
    Remove chat sessions older than specified days.

    Args:
        days: Number of days of inactivity before cleanup

    Returns:
        Number of sessions deleted
    """
    from datetime import datetime, timedelta
    from models import ChatSession

    cutoff = datetime.utcnow() - timedelta(days=days)

    with get_db() as db:
        deleted = db.query(ChatSession).filter(
            ChatSession.last_activity_at < cutoff
        ).delete()
        logger.info(f"Cleaned up {deleted} old chat sessions")
        return deleted


def cleanup_old_quotas(days: int = 90) -> int:
    """
    Remove quota records older than specified days.

    Args:
        days: Number of days to keep quota records

    Returns:
        Number of quota records deleted
    """
    from datetime import date, timedelta
    from models import QuotaUsage

    cutoff = date.today() - timedelta(days=days)

    with get_db() as db:
        deleted = db.query(QuotaUsage).filter(
            QuotaUsage.usage_date < cutoff
        ).delete()
        logger.info(f"Cleaned up {deleted} old quota records")
        return deleted


# ============================================================================
# DATABASE HEALTH CHECK (FIXED FOR SQLALCHEMY 2.0)
# ============================================================================

def check_db_health() -> bool:
    """
    Check if database connection is healthy.

    Returns:
        True if database is accessible, False otherwise
    """
    try:
        with get_db() as db:
            # FIXED: Use text() for raw SQL in SQLAlchemy 2.0
            db.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
