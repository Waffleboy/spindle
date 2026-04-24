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

### Environment
Set `LLM_MODEL` env var to configure the LLM (default: `anthropic/claude-sonnet-4-20250514`).
Set your API key via `ANTHROPIC_API_KEY` or the appropriate env var for your provider.

## Architecture

**Backend:** FastAPI + SQLAlchemy + SQLite + litellm
**Frontend:** Vite + React 19 + TypeScript + Radix UI + Tailwind CSS

### Processing Pipeline
1. **Document Type Detection** - LLM identifies corpus document type and extracts report dates
2. **Taxonomy Generation** - LLM discovers extraction dimensions from the content itself
3. **Per-Document Extraction** - Structured data extraction + chunking/embedding
4. **Entity Resolution** - Cross-document entity matching with human-in-the-loop review
5. **Contradiction Detection** - Temporal-aware conflict flagging across reports

### Supported Formats
- PDF (image-based extraction via PyMuPDF)
- Word (.docx via python-docx)
- Excel (.xlsx via openpyxl)
- CSV (with optional row splitting)

## Tests
```bash
uv run python -m pytest tests/ -v
```
