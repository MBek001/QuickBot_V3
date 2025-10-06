"""
Enumeration types used by the bot's SQLAlchemy models.

These enums mirror business logic concepts such as plan codes, language
choices, file categories and job statuses.  Defining them centrally
ensures that columns using Enum(...) remain consistent across the
application.
"""

from enum import Enum


class PlanCode(str, Enum):
    """Subscription plans for end users."""
    free = "free"
    premium = "premium"


class Language(str, Enum):
    """Supported user interface languages."""
    uz = "uz"
    ru = "ru"
    en = "en"


class FileCategory(str, Enum):
    """High level classification of files stored by the bot."""
    other = "other"
    image = "image"
    pptx = "pptx"
    pdf = "pdf"
    docx = "docx"


class FileJobKind(str, Enum):
    """Kinds of processing jobs that can be queued for files."""
    convert = "convert"
    pptx = "pptx"
    analysis = "analysis"


class JobStatus(str, Enum):
    """Lifecycle states for file processing jobs."""
    pending = "pending"
    running = "running"
    finished = "finished"
    failed = "failed"


class ChatMode(str, Enum):
    """Different chat contexts for user conversations."""
    quick = "quick"
    code = "code"
    image = "image"


class UserAction(str, Enum):
    """Enumeration of actions taken by users and admins.

    Logged into the `action_logs` table to provide an audit trail.
    """
    profile_view = "profile_view"
    grant_premium = "grant_premium"
    revoke_premium = "revoke_premium"
    make_admin = "make_admin"
    remove_admin = "remove_admin"
    block_user = "block_user"
    unblock_user = "unblock_user"
    broadcast = "broadcast"
    chat = "chat"
    image_generation = "image_generation"
    image_analysis = "image_analysis"
    pptx_creation = "pptx_creation"
    convert = "convert"
