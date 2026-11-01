from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)
    app_name: str = "ClaimLens AI"
    database_url: str = "sqlite:///./data/claimlens.db"
    upload_dir: Path = Path("./data/uploads")
    max_upload_bytes: int = 25 * 1024 * 1024
    max_pdf_pages: int = 100
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.2"


@lru_cache
def get_settings() -> Settings:
    return Settings()
