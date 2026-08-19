from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str

    cors_origins: list[str] = []

    openai_api_key: str
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536
    chat_model: str = "gpt-4o"
    embedding_batch_size: int = 100

    # Retrieval (services/retrieval.py). v1-global; per-project override
    # is a later-version feature once Project settings actually exist.
    retrieval_top_k: int = 5
    # Cosine SIMILARITY floor (not distance) - a chunk must be at least
    # this similar to be kept, even if it's within the top_k nearest.
    retrieval_similarity_threshold: float = 0.4

    storage_root: str = "/app/storage"

    # v1 has no auth/login (DECISIONS.md 011) - every row still needs a
    # user_id, so we pin it to a seeded row created via Alembic/fixture
    # rather than hardcoding the literal id inline at each call site.
    seed_user_id: int = 1
    seed_project_id: int = 1

    # chunk_by_title params — tunable without touching service code.
    # Starting values for prose-heavy PDFs; revisit once real documents
    # are seen.
    chunk_max_characters: int = 1500
    chunk_new_after_n_chars: int = 1200
    chunk_combine_text_under_n_chars: int = 300

    env: str = "development"


settings = Settings()
