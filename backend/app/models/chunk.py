from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.session import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.document import Document


class Chunk(Base):
    """
    project_id is denormalized here (also reachable via document.project_id)
    to keep the shared HNSW index filterable directly on this table -
    see DECISIONS.md 001.

    Immutable once written at ingestion time - created_at only, no
    updated_at.
    """

    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)

    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dim))
    page_start: Mapped[int] = mapped_column(Integer)
    page_end: Mapped[int] = mapped_column(Integer)
    chunk_index: Mapped[int] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="chunks")
    document: Mapped["Document"] = relationship(back_populates="chunks")
