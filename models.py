"""
SQLAlchemy database models for the AI Assistant Bot.

This module defines all database tables and their relationships,
including users, plans, quotas, trials, files, and action logs.
"""

from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, BigInteger,
    ForeignKey, Enum, Text, CheckConstraint, UniqueConstraint,
    Index, JSON
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

from models_enums import (
    PlanCode, Language, FileCategory, FileJobKind,
    JobStatus, ChatMode, UserAction
)

Base = declarative_base()


# ============================================================================
# PLAN MODEL
# ============================================================================

class Plan(Base):
    """Subscription plans with daily limits."""

    __tablename__ = "plans"

    code = Column(Enum(PlanCode), primary_key=True)
    title = Column(String(64), nullable=False, default="")
    description = Column(String(255), nullable=False, default="")

    # Daily limits
    daily_quick_chat = Column(Integer, nullable=False, default=30)
    daily_code_chat = Column(Integer, nullable=False, default=10)
    daily_convert = Column(Integer, nullable=False, default=5)
    daily_pptx = Column(Integer, nullable=False, default=3)

    max_file_mb = Column(Integer, nullable=False, default=30)
    priority = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    users = relationship("User", back_populates="plan")


# ============================================================================
# USER MODEL
# ============================================================================

class User(Base):
    """User accounts and preferences."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint('tg_id > 0', name='check_tg_id_positive'),
    )

    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(64))
    first_name = Column(String(64))
    last_name = Column(String(64))
    phone = Column(String(32))
    lang = Column(Enum(Language), nullable=True)

    # Plan and premium
    plan_code = Column(
        Enum(PlanCode),
        ForeignKey("plans.code", onupdate="CASCADE"),
        nullable=False,
        default=PlanCode.free
    )
    premium_until = Column(DateTime(timezone=True), nullable=True)

    # Custom limits (override plan defaults)
    daily_quick_chat = Column(Integer, nullable=True)
    daily_code_chat = Column(Integer, nullable=True)
    daily_convert = Column(Integer, nullable=True)
    daily_pptx = Column(Integer, nullable=True)

    # Status flags
    is_blocked = Column(Boolean, nullable=False, default=False, index=True)
    is_admin = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    plan = relationship("Plan", back_populates="users")
    quotas = relationship("QuotaUsage", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    storage_files = relationship("StorageFile", back_populates="owner", cascade="all, delete-orphan")
    jobs = relationship("FileJob", back_populates="user", cascade="all, delete-orphan")
    actions = relationship("ActionLog", back_populates="user", cascade="all, delete-orphan")
    premium_grants = relationship(
        "PremiumGrant",
        foreign_keys="PremiumGrant.user_id",
        cascade="all, delete-orphan"
    )
    trial = relationship("TrialUsage", back_populates="user", uselist=False, cascade="all, delete-orphan")

    @property
    def is_premium(self) -> bool:
        """Check if user currently has active premium."""
        return bool(self.premium_until and datetime.utcnow() < self.premium_until)

    @property
    def full_name(self) -> str:
        """Get user's full display name."""
        parts = [self.first_name, self.last_name]
        name = " ".join(p for p in parts if p)
        return name or self.username or f"User{self.tg_id}"

    def get_daily_limit(self, quota_type: str) -> int:
        """Get daily limit for a quota type (respects custom overrides)."""
        override = getattr(self, f"daily_{quota_type}", None)
        if override is not None:
            return override
        return getattr(self.plan, f"daily_{quota_type}", 0)


# ============================================================================
# TRIAL USAGE MODEL
# ============================================================================

class TrialUsage(Base):
    """
    Rolling trial system for premium features.

    Non-premium users get TRIAL_USES_PER_PERIOD uses per feature
    every TRIAL_PERIOD_DAYS days.
    """

    __tablename__ = "trial_usage"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    last_reset_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Usage counters (reset every TRIAL_PERIOD_DAYS)
    image_gen_used = Column(Integer, nullable=False, default=0)
    image_edit_used = Column(Integer, nullable=False, default=0)
    pptx_used = Column(Integer, nullable=False, default=0)

    user = relationship("User", back_populates="trial")


# ============================================================================
# QUOTA USAGE MODEL
# ============================================================================

class QuotaUsage(Base):
    """Daily usage tracking for free features."""

    __tablename__ = "quota_usage"
    __table_args__ = (
        UniqueConstraint("user_id", "usage_date", name="uq_quota_user_day"),
        Index('ix_quota_day', 'usage_date')
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    usage_date = Column(Date, nullable=False, index=True)

    # Daily counters
    quick_chat = Column(Integer, nullable=False, default=0)
    code_chat = Column(Integer, nullable=False, default=0)
    convert = Column(Integer, nullable=False, default=0)
    pptx = Column(Integer, nullable=False, default=0)

    user = relationship("User", back_populates="quotas")

    @classmethod
    def get_or_create(cls, session, user_id: int, usage_date: Optional[date] = None):
        """Get existing quota record or create new one for the date."""
        if usage_date is None:
            usage_date = date.today()

        quota = session.query(cls).filter_by(
            user_id=user_id,
            usage_date=usage_date
        ).first()

        if not quota:
            quota = cls(user_id=user_id, usage_date=usage_date)
            session.add(quota)
            session.flush()

        return quota


# ============================================================================
# STORAGE FILE MODEL
# ============================================================================

class StorageFile(Base):
    __tablename__ = "storage_files"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    telegram_file_id = Column(String, nullable=False)
    storage_channel_id = Column(BigInteger, nullable=False)
    storage_message_id = Column(BigInteger, nullable=False)

    category = Column(String, nullable=False, default=FileCategory.other.value)
    mime = Column(String, nullable=True)
    original_name = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    sha256 = Column(String(64), nullable=True, index=True)
    extra = Column(JSON, nullable=True)

    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())

    # Relationships
    owner = relationship("User", back_populates="storage_files", lazy="joined")

    def __repr__(self):
        return f"<StorageFile id={self.id} category={self.category} owner={self.owner_id}>"


# ============================================================================
# FILE JOB MODEL
# ============================================================================

class FileJob(Base):
    """Asynchronous file processing jobs."""

    __tablename__ = "file_jobs"
    __table_args__ = (
        Index('ix_jobs_user_status', 'user_id', 'status'),
        Index('ix_jobs_status_created', 'status', 'created_at'),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    kind = Column(Enum(FileJobKind), nullable=False, default=FileJobKind.unknown)
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.pending, index=True)
    input_file_id = Column(Integer, ForeignKey("storage_files.id", ondelete="SET NULL"))
    output_file_id = Column(Integer, ForeignKey("storage_files.id", ondelete="SET NULL"))
    params = Column(JSON, nullable=False, default=dict, server_default='{}')
    error = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="jobs")
    input_file = relationship("StorageFile", foreign_keys=[input_file_id])
    output_file = relationship("StorageFile", foreign_keys=[output_file_id])

    @property
    def duration_seconds(self) -> float:
        """Calculate job duration in seconds."""
        if not self.started_at or not self.finished_at:
            return 0
        return (self.finished_at - self.started_at).total_seconds()


# ============================================================================
# CHAT SESSION MODEL
# ============================================================================

class ChatSession(Base):
    """User chat sessions with AI."""

    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index('ix_chat_user_mode', 'user_id', 'mode'),
        Index('ix_chat_last_activity', 'last_activity_at'),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    mode = Column(Enum(ChatMode), nullable=False)
    title = Column(String(128))
    provider_thread_id = Column(String(128))
    token_spent = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_activity_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", back_populates="chat_sessions")


# ============================================================================
# PREMIUM GRANT MODEL
# ============================================================================

class PremiumGrant(Base):
    """Premium access grants by admins."""

    __tablename__ = "premium_grants"
    __table_args__ = (
        Index('ix_grants_user', 'user_id'),
        Index('ix_grants_admin', 'admin_id')
    )

    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    days = Column(Integer, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    reason = Column(String(255))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    admin = relationship("User", foreign_keys=[admin_id])


# ============================================================================
# ACTION LOG MODEL
# ============================================================================

class ActionLog(Base):
    """Audit log of user actions."""

    __tablename__ = "action_logs"
    __table_args__ = (
        Index('ix_actions_user_action', 'user_id', 'action'),
        Index('ix_actions_created', 'created_at'),
        Index('ix_actions_action_created', 'action', 'created_at'),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    action = Column(Enum(UserAction), nullable=False, index=True)
    ref_id = Column(Integer)
    meta = Column(JSON, nullable=False, default=dict, server_default='{}')
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    user = relationship("User", back_populates="actions")
