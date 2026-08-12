"""
v1 has no auth/signup flow (DECISIONS.md 011) and no project-management UI
(v1-requirements.md - single project). Run once, manually, to create the
fixed User/Project rows every other row's foreign keys depend on.

    docker compose exec backend python -m app.db.seed

Idempotent: safe to run more than once, does nothing if the seed rows
already exist.
"""
from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.project import Project
from app.models.user import User


def _sync_sequence(db, table: str) -> None:
    """
    Explicit id= inserts bypass the table's bigserial sequence, so it
    doesn't auto-advance. Without this, a later normal (auto-id) insert
    could collide with a seeded row's id. Safe to call even if the
    sequence is already ahead.
    """
    db.execute(
        text(
            f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
            f"COALESCE((SELECT MAX(id) FROM {table}), 1))"
        )
    )


def seed() -> None:
    db = SessionLocal()
    try:
        user = db.get(User, settings.seed_user_id)
        if user is None:
            user = User(id=settings.seed_user_id)
            db.add(user)
            db.flush()
            print(f"Created User id={user.id}")
        else:
            print(f"User id={user.id} already exists")

        project = db.get(Project, settings.seed_project_id)
        if project is None:
            project = Project(
                id=settings.seed_project_id,
                user_id=user.id,
                name="Default Project",
            )
            db.add(project)
            print(f"Created Project id={project.id}")
        else:
            print(f"Project id={project.id} already exists")

        db.commit()
        _sync_sequence(db, "users")
        _sync_sequence(db, "projects")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
