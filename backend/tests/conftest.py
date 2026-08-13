import os
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

# Import models before Base.metadata is used, same reason as alembic/env.py
from app import models  # noqa
from app.db.session import Base, get_db
from app.main import app

TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(TEST_DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """
    App code (ingestion, retrieval) calls db.commit()/db.rollback()
    multiple times per request (e.g. a failed upload: seed -> insert ->
    PROCESSING commit -> rollback -> FAILED commit - five transaction
    boundaries). A savepoint-based external-transaction fixture assumes
    a much simpler commit pattern and drifts out of sync under this many
    nested cycles, producing hard-to-diagnose "row not present" errors
    that don't reflect any real application bug.

    Simpler and robust instead: a real session against the real test DB,
    committing/rolling back exactly as the app does, with cleanup by
    truncating all tables after each test rather than relying on
    transaction rollback for isolation. Slower per test, but correct
    regardless of how many internal transaction boundaries a request
    crosses.
    """
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()

    yield session

    session.close()
    with db_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def client(db_session):
    def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def seed_project(db_session):
    """Matches app.db.seed but scoped to the test transaction."""
    from app.models.project import Project
    from app.models.user import User

    user = User(id=1)
    db_session.add(user)
    db_session.flush()
    project = Project(id=1, user_id=1, name="Test Project")
    db_session.add(project)
    db_session.commit()
    return project


@pytest.fixture
def mock_openai(monkeypatch):
    """
    Patches the OpenAI client used by both services/embeddings.py and
    services/retrieval.py. Fixed fake embedding vector (dimension must
    match settings.embedding_dim) and a fixed chat completion response -
    override response content in individual tests via the returned mock.
    """
    from app.core.config import settings

    fake_vector = [0.01] * settings.embedding_dim

    mock_client = MagicMock()
    mock_client.embeddings.create.side_effect = lambda model, input: SimpleNamespace(
        data=[
            SimpleNamespace(embedding=fake_vector, index=i) for i in range(len(input))
        ]
    )
    mock_client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Default mocked answer."))]
    )

    monkeypatch.setattr("app.services.embeddings.client", mock_client)
    monkeypatch.setattr("app.services.retrieval.client", mock_client)
    return mock_client


@pytest.fixture
def mock_ingestion_pipeline(monkeypatch):
    """
    Replaces partition/chunk with fixed fake elements so tests don't run
    real hi_res partitioning (slow, needs model weights, non-deterministic
    OCR) or need a real PDF fixture beyond a minimal valid one for the
    pypdf page-count read in the router.
    """

    def fake_partition(path):
        return ["fake-element"]

    def fake_chunk(elements):
        page = SimpleNamespace(metadata=SimpleNamespace(page_number=1))
        chunk = SimpleNamespace(
            text="This is a fake chunk of document content for testing.",
            metadata=SimpleNamespace(orig_elements=[page]),
        )
        return [chunk]

    monkeypatch.setattr("app.services.ingestion._partition", fake_partition)
    monkeypatch.setattr("app.services.ingestion._chunk", fake_chunk)