# Spindle

Autonomous intelligence from your documents.

Upload a corpus of reports and Spindle discovers what to extract, pulls structured data, resolves entities across documents, detects contradictions with temporal awareness, and lets you query everything through a citation-backed chat interface. No predefined schema. No configuration.

The ingestion layer is designed to be pluggable - SharePoint, Slack, Outlook, databases. The pipeline stays the same regardless of source. For this version, documents are uploaded manually through the UI.

## Quick Start

### Backend
```bash
uv sync
uv run uvicorn main:app --reload
```
Backend runs on http://localhost:8000

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend runs on http://localhost:5173 (proxies API calls to backend)

### Convenience Scripts
```bash
./start_backend.sh   # installs deps + starts backend
./start_frontend.sh  # installs deps + starts frontend
```

### Environment
Set `LLM_MODEL` env var to configure the LLM (default: `anthropic/claude-sonnet-4-20250514`).
Set your API key via `ANTHROPIC_API_KEY` or the appropriate env var for your provider.

All settings can be overridden via environment variables or a `.env` file — see [Configuration](#configuration) below.

## Architecture

**Backend:** FastAPI + SQLAlchemy + SQLite + litellm (Python 3.12+)
**Frontend:** Vite 8 + React 19 + TypeScript 6 + Radix UI + Tailwind CSS

### Processing Pipeline
1. **Document Type Detection** - LLM identifies corpus document type and extracts report dates
2. **Template Matching** - LLM matches detected doc type against configured taxonomy templates (skipped if no templates exist)
3. **Taxonomy Generation** - LLM discovers extraction dimensions from the content itself (template dimensions injected as must-includes)
4. **Per-Document Extraction** - Structured data extraction + chunking/embedding (parallel LLM + embedding fetch, then sequential DB writes)
5. **Entity Resolution** - Cross-document entity matching with human-in-the-loop review; assigns a primary entity to each document based on entity type and confidence
6. **Contradiction Detection** - Temporal-aware conflict flagging across reports, grouped by primary entity

### Chat System
Hybrid retrieval combining structured database queries with semantic search (BM25 via FTS5 + embedding cosine similarity). Temporally aware — prefers recent data and includes dates in contradiction context. Query types: `FACT_LOOKUP`, `CROSS_DOC_COMPARISON`, `ENTITY_QUERY`, `TEMPORAL`, `OPEN_ENDED`.

### Supported Formats
- PDF (image-based extraction via PyMuPDF)
- Word (.docx via python-docx, .doc via binary text fallback)
- Excel (.xlsx via openpyxl, .xls via xlrd)
- CSV (with optional row splitting — each row becomes a separate document)

## Configuration

All settings live in `backend/config.py` via Pydantic `BaseSettings`. Override with env vars or `.env`:

| Setting | Default | Purpose |
|---------|---------|---------|
| `llm_model` | `anthropic/claude-sonnet-4-20250514` | LLM model via litellm |
| `embedding_model` | `text-embedding-3-small` | Embedding model |
| `enable_embeddings` | `false` | Toggle embedding generation |
| `litellm_api_base` | — | Optional custom API base |
| `litellm_api_key` | — | Optional API key override |
| `database_url` | `sqlite:///data/taxonomy.db` | SQLite database path |
| `pdf_render_dpi` | `150` | DPI for PDF page rendering |
| `word_chars_per_page` | `3000` | Characters per estimated page (Word docs) |
| `chunk_size` | `500` | Words per chunk |
| `chunk_overlap` | `100` | Overlapping words between chunks |
| `words_per_page` | `300` | Words per estimated page (chunking) |
| `llm_concurrency` | `10` | Max parallel LLM calls |
| `embedding_concurrency` | `10` | Max parallel embedding calls |
| `chat_history_limit` | `10` | Recent exchanges kept in chat context |
| `semantic_search_top_k` | `5` | Results per search path |
| `host` / `port` | `0.0.0.0` / `8000` | Server binding |

## Database Schema

8 tables, all using UUID string PKs and UTC timestamps:

| Table | Key Columns | Notes |
|-------|-------------|-------|
| Document | original_filename, file_type, detected_doc_type, report_date, primary_entity_id (FK), source_text | primary_entity_id links to the subject entity; source_text stores pre-extracted text for CSV row splits |
| TaxonomySchema | corpus_id, dimensions (JSON), doc_type, company_context | dimensions: [{name, description, expected_type}] |
| Extraction | document_id, taxonomy_schema_id, dimension_name, raw_value, resolved_value, confidence, source_pages | resolved_value set by entity resolution step |
| Entity | canonical_name, entity_type, aliases (JSON) | aliases: string array |
| EntityResolution | entity_id, original_value, document_id, confidence, needs_review | needs_review=true when confidence < 0.8 |
| Contradiction | dimension_name, entity_id (nullable), doc_a_id, doc_b_id, value_a, value_b, doc_a/b_date, reason, resolution_status | reason stores LLM explanation of the conflict |
| TaxonomyTemplate | label, description, dimensions (JSON) | User-created reusable schemas |
| DocumentChunk | document_id, chunk_text, chunk_index, source_pages, embedding | embedding: numpy float32 bytes; FTS5 virtual table for BM25 search |

Dimension expected types: `text | number | date | currency | entity | entity_list | text_list | date_range`

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/upload` | Upload files (multipart; PDF, DOCX, DOC, XLSX, XLS, CSV) |
| POST | `/api/process` | Start pipeline (background thread) |
| GET | `/api/status` | Pipeline progress with step names and error info |
| GET | `/api/documents` | List documents (sorted by uploaded_at desc) |
| DELETE | `/api/documents` | Cascade delete all documents and related data |
| DELETE | `/api/documents/{id}` | Delete single document |
| GET | `/api/taxonomy` | Most recent taxonomy schema |
| GET | `/api/extractions` | Extractions (filterable by document_id, dimension_name) |
| GET | `/api/entities` | Entities with needs_review_count |
| PATCH | `/api/entities/{id}` | Update entity canonical name |
| GET | `/api/entities/{id}/timeline` | Chronological entity change feed with diffs |
| PATCH | `/api/entity-resolutions/{id}` | Approve/reject/override entity resolution |
| GET | `/api/contradictions` | Contradictions with document filenames |
| GET | `/api/taxonomy-templates` | List taxonomy templates |
| POST | `/api/taxonomy-templates` | Create taxonomy template |
| PUT | `/api/taxonomy-templates/{id}` | Update taxonomy template |
| DELETE | `/api/taxonomy-templates/{id}` | Delete taxonomy template |
| GET | `/api/insights` | Aggregated dashboard: contradictions, entity reviews, staleness |
| POST | `/api/chat` | Chat with hybrid retrieval, citations, suggested queries |

## Tests

185 tests across 4 files, all using in-memory SQLite with FTS5:

| File | Tests | Coverage |
|------|-------|----------|
| `tests/test_api.py` | 71 | All API endpoints, entity timeline diffs, insights aggregation, template CRUD |
| `tests/test_ingestion.py` | 42 | All 6 file formats, encoding fallbacks, service layer, CSV row splitting |
| `tests/test_pipeline.py` | 41 | All pipeline steps, chunking, JSON parsing, orchestrator error handling |
| `tests/test_chat.py` | 31 | Query classification, structured/semantic retrieval, citations, session management |

```bash
uv run pytest tests/ -v
```
