# Full Implementation — Taxonomy Discovery Engine

## What was built

Complete full-stack implementation of the Taxonomy Discovery & Entity Resolution Engine:

### Backend (Python/FastAPI)
- **Database layer**: SQLAlchemy models for 7 tables (documents, taxonomy_schema, extractions, entities, entity_resolutions, contradictions, document_chunks) + FTS5 virtual table
- **Ingestion layer**: PDF (PyMuPDF image rendering), Word (python-docx), Excel (openpyxl) handlers behind a common interface
- **Processing pipeline**: 5-step LLM pipeline via litellm — doc type detection, taxonomy generation, per-document extraction with chunking/embedding, entity resolution, contradiction detection
- **Chat engine**: Hybrid retrieval (structured taxonomy queries + BM25/FTS5 + embedding cosine similarity), query classification, dual citations, session history
- **API layer**: 11 FastAPI endpoints with Pydantic validation, background pipeline processing

### Frontend (Vite + React + TypeScript)
- Three-panel layout: Documents (left), Taxonomy Dashboard (center), Chat (right)
- Dark zinc theme with shadcn/ui components
- Color-coded cells: rose for contradictions, amber for entity review, emerald for confirmed
- Drag-and-drop upload, pipeline progress bar, entity review cards, contradiction popovers
- Chat with citation badges and suggested queries

### Test Coverage
- 124 tests across ingestion (19), pipeline (34), chat (31), and API (40) layers
- All tests use mocked LLM calls and in-memory SQLite

## How to run
- Backend: `uv run uvicorn main:app --reload` (port 8000)
- Frontend: `cd frontend && npm run dev` (port 5173, proxies /api to backend)
