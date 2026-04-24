# Taxonomy Discovery Engine

AI-powered system that ingests a corpus of documents, autonomously discovers taxonomy dimensions, extracts structured data, resolves entities across documents, and detects contradictions — with a hybrid chat interface for querying the results.

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

### Environment
Set `LLM_MODEL` env var to configure the LLM (default: `anthropic/claude-sonnet-4-20250514`).
Set your API key via `ANTHROPIC_API_KEY` or the appropriate env var for your provider.

## Architecture

**Backend:** FastAPI + SQLAlchemy + SQLite + litellm
**Frontend:** Vite + React 19 + TypeScript + shadcn/ui + Tailwind CSS

### Processing Pipeline
1. **Document Type Detection** — LLM identifies corpus document type
2. **Taxonomy Generation** — LLM discovers extraction dimensions
3. **Per-Document Extraction** — Structured data extraction + chunking/embedding
4. **Entity Resolution** — Cross-document entity matching with human review
5. **Contradiction Detection** — Temporal-aware conflict flagging

### Supported Formats
- PDF (image-based extraction via PyMuPDF)
- Word (.docx via python-docx)
- Excel (.xlsx via openpyxl)

## Tests
```bash
uv run python -m pytest tests/ -v
```
