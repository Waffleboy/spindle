"""Centralised application settings powered by Pydantic BaseSettings.

All configuration across the app lives here.  Values are read from
environment variables (case-insensitive) and can be overridden via a
`.env` file in the project root.
"""

from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings


_BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # --- Directories ---
    data_dir: Path = _BASE_DIR / "data"
    originals_dir: Path = _BASE_DIR / "data" / "originals"

    # --- Database ---
    database_url: str = f"sqlite:///{_BASE_DIR / 'data' / 'taxonomy.db'}"

    # --- LLM ---
    llm_model: str = "anthropic/claude-sonnet-4-20250514"
    embedding_model: str = "text-embedding-3-small"
    litellm_api_base: str | None = None
    litellm_api_key: str | None = None

    # --- Ingestion ---
    pdf_render_dpi: int = 150
    word_chars_per_page: int = 3000

    # --- Chunking & Embedding ---
    chunk_size: int = 500
    chunk_overlap: int = 100
    words_per_page: int = 300
    enable_embeddings: bool = False

    # --- Concurrency ---
    llm_concurrency: int = 10
    embedding_concurrency: int = 10

    # --- Chat ---
    chat_history_limit: int = 10
    semantic_search_top_k: int = 5

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.originals_dir.mkdir(parents=True, exist_ok=True)
    return settings
