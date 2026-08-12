from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Integer, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin
from app.models.enums import DocumentStatus

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.chunk import Chunk


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)

    path: Mapped[str] = mapped_column(String)
    filename: Mapped[str] = mapped_column(String)
    file_type: Mapped[str] = mapped_column(String)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger)
    page_count: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String)
    status: Mapped[DocumentStatus] = mapped_column(
        default=DocumentStatus.PENDING
    )
    checksum: Mapped[str] = mapped_column(String(64))

    project: Mapped["Project"] = relationship(back_populates="documents")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document")
