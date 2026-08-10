from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str

    openai_api_key: str
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536
    chat_model: str = "gpt-4o"

    storage_root: str = "/app/storage"

    env: str = "development"


settings = Settings()
