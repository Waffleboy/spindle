# Centralise Configuration with Pydantic BaseSettings

## Task
Migrate all scattered configuration (env vars, hardcoded constants) into a single `backend/config.py` using Pydantic `BaseSettings`, and add litellm endpoint/API key override support.

## Changes

### `backend/config.py` — Complete rewrite
- Replaced bare module-level constants with a `Settings(BaseSettings)` class
- Added `pydantic-settings` dependency
- All settings read from env vars (case-insensitive) and optional `.env` file
- Singleton access via `get_settings()` (lru_cache)
- New settings: `litellm_api_base`, `litellm_api_key`, `embedding_model`, `pdf_render_dpi`, `word_chars_per_page`, `chunk_size`, `chunk_overlap`, `words_per_page`, `chat_history_limit`, `semantic_search_top_k`, `host`, `port`

### `backend/pipeline/llm.py`
- Applies `litellm.api_base` and `litellm.api_key` from settings on module load
- Uses `get_settings().llm_model` instead of `LLM_MODEL` constant

### `backend/database.py`
- Uses `get_settings().database_url`

### `backend/ingestion/service.py`
- Uses `get_settings().originals_dir`

### `backend/ingestion/pdf_ingester.py`
- Uses `get_settings().pdf_render_dpi` instead of `_RENDER_DPI` constant

### `backend/ingestion/word_ingester.py`
- Uses `get_settings().word_chars_per_page` instead of `_CHARS_PER_PAGE` constant

### `backend/pipeline/chunking.py`
- Uses settings defaults for `chunk_size`, `chunk_overlap`, `words_per_page`

### `backend/pipeline/step3_extraction.py`, `backend/chat/semantic_retrieval.py`
- Uses `get_settings().embedding_model` instead of hardcoded `"text-embedding-3-small"`

### `backend/chat/engine.py`
- Uses `get_settings().chat_history_limit` instead of hardcoded `10`

### `backend/chat/semantic_retrieval.py`
- Uses `get_settings().semantic_search_top_k` as default for `top_k`

### `main.py`
- Uses `get_settings().host` and `get_settings().port`

### `tests/test_ingestion.py`
- Updated monkeypatch to use `_patch_settings()` helper that creates a real `Settings` instance

### `pyproject.toml`
- Added `pydantic-settings` to dependencies

All 132 tests pass.
