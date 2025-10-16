"""
Enumeration types used throughout the application.

These enums provide type safety and consistency for database models
and application logic.
"""

from enum import Enum


class PlanCode(str, Enum):
    """User subscription plan types."""
    free = "free"
    premium = "premium"


class Language(str, Enum):
    """Supported interface languages."""
    en = "en"  # English
    ru = "ru"  # Russian
    uz = "uz"  # Uzbek


from enum import Enum

class FileCategory(str, Enum):
    image_gen = "image_gen"
    image_edit = "image_edit"
    pptx = "pptx"
    document = "document"
    audio = "audio"
    video = "video"
    other = "other"


class FileJobKind(str, Enum):
    """Types of file processing jobs."""
    unknown = "unknown"
    image_generation = "image_generation"
    image_editing = "image_editing"
    pptx_creation = "pptx_creation"


class JobStatus(str, Enum):
    """Status of file processing jobs."""
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class ChatMode(str, Enum):
    """Chat interaction modes."""
    normal = "normal"
    image_edit = "image_edit"
    image_gen = "image_gen"
    pptx = "pptx"


class UserAction(str, Enum):
    """Types of user actions logged in the system."""
    chat = "chat"
    file_upload = "file_upload"
    file_download = "file_download"
    conversion = "conversion"
    image_generation = "image_generation"
    image_edit = "image_edit"
    pptx_creation = "pptx_creation"
    trial_reset = "trial_reset"
    profile_view = "profile_view"
    language_change = "language_change"
    phone_added = "phone_added"
