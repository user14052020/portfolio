from enum import Enum

from sqlalchemy import Enum as SqlEnum


class RoleCode(str, Enum):
    ADMIN = "admin"
    EDITOR = "editor"


class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    MODEL3D = "model3d"


class AssetType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"
    MODEL3D = "model3d"


class BlogPostType(str, Enum):
    ARTICLE = "article"
    VIDEO = "video"


class ContactRequestStatus(str, Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class GenerationStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerationProvider(str, Enum):
    COMFYUI = "comfyui"
    MOCK = "mock"


class ChatMessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


def sql_enum(enum_cls: type[Enum], *, name: str) -> SqlEnum:
    return SqlEnum(
        enum_cls,
        name=name,
        values_callable=lambda members: [item.value for item in members],
        validate_strings=True,
    )
