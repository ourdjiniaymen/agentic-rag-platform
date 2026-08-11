import enum


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
