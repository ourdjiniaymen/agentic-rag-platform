from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.document import Document
    from app.models.conversation import Conversation
    from app.models.chunk import Chunk


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String)

    user: Mapped["User"] = relationship(back_populates="projects")
    documents: Mapped[list["Document"]] = relationship(back_populates="project")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="project")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="project")
