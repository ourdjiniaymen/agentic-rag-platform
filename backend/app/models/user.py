from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.project import Project


class User(Base):
    """
    Stripped to id + created_at for v1 - no email/username/password.
    v1 has no login flow (single seeded user). See DECISIONS.md 011:
    real identity columns get added once auth (Clerk) is wired in, not
    guessed at now.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    projects: Mapped[list["Project"]] = relationship(back_populates="user")
