from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import MessageRole

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class Message(Base):
    """
    `references` is a point-in-time JSON snapshot of citation metadata
    (chunk_id, filename, file_type, file_path, start_page, end_page)
    captured at generation time - intentionally not a normalized FK/join
    to live chunks, so a deleted or re-chunked document can't silently
    corrupt historical citations. See DECISIONS.md 010.

    Immutable once created - no edit-message feature in v1 - so
    created_at only, no updated_at (same reasoning as Chunk).
    """

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id"), index=True
    )
    role: Mapped[MessageRole] = mapped_column()
    content: Mapped[str] = mapped_column(Text)
    references: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
