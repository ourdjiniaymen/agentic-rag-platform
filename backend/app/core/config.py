from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str

    openai_api_key: str
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536
    chat_model: str = "gpt-4o"
    embedding_batch_size: int = 100

    storage_root: str = "/app/storage"

    # chunk_by_title params — tunable without touching service code.
    # Starting values for prose-heavy PDFs; revisit once real documents
    # are seen.
    chunk_max_characters: int = 1500
    chunk_new_after_n_chars: int = 1200
    chunk_combine_text_under_n_chars: int = 300

    env: str = "development"


settings = Settings()