# Taxonomy Discovery Engine — Architecture

## Overview
AI-powered system that ingests multi-format documents, automatically discovers taxonomy schemas, extracts structured data, resolves entities across documents, and detects contradictions — with a hybrid chat interface for querying the processed data.

## Stack
- **Backend:** FastAPI (Python) with SQLAlchemy ORM, SQLite
- **Frontend:** Vite + React 19 (TypeScript) + shadcn/ui + Tailwind CSS v3
- **LLM:** Multiple models via litellm (unified interface, defaults to `anthropic/claude-sonnet-4-20250514`)
- **Embeddings:** OpenAI `text-embedding-3-small` for document chunk vectors
- **Package Management:** uv (Python), npm (Node.js)

---

## Application Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + TypeScript)             │
│                                                              │
│  ┌────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │  Document   │  │  Taxonomy        │  │  Chat          │  │
│  │  Panel      │  │  Dashboard       │  │  Panel         │  │
│  │  (upload,   │  │  (grid: docs ×   │  │  (query,       │  │
│  │   list,     │  │   dimensions,    │  │   citations,   │  │
│  │   process)  │  │   contradictions │  │   suggestions) │  │
│  └─────┬──────┘  │   entity review) │  └───────┬────────┘  │
│        │         └────────┬─────────┘          │            │
│  ┌─────┴─────────────────┴────────────────────┴──────────┐  │
│  │              Top Bar — Pipeline Progress               │  │
│  │   [Step 1] → [Step 2] → [Step 3] → [Step 4] → [Step 5] │
│  └────────────────────────┬──────────────────────────────┘  │
└───────────────────────────┼──────────────────────────────────┘
                            │ REST API (polls /status every 2s)
                            ▼
┌───────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                             │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  API Routes (backend/api/routes.py)                    │   │
│  │                                                         │   │
│  │  POST /api/upload ─────────→ Ingestion Service         │   │
│  │  POST /api/process ────────→ Pipeline Orchestrator     │   │
│  │  GET  /api/status ─────────→ Pipeline Status Dict      │   │
│  │  GET  /api/documents ──────→ DB Query                  │   │
│  │  GET  /api/taxonomy ───────→ DB Query                  │   │
│  │  GET  /api/extractions ────→ DB Query (filterable)     │   │
│  │  GET  /api/entities ───────→ DB Query                  │   │
│  │  GET  /api/contradictions ─→ DB Query                  │   │
│  │  PATCH /api/entities/{id} ─→ DB Update                 │   │
│  │  PATCH /api/entity-res/{id}→ DB Update                 │   │
│  │  POST /api/chat ───────────→ Chat Engine               │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                │
│  ┌──────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │  Ingestion   │  │  Pipeline        │  │  Chat Engine   │  │
│  │  Service     │  │  (5 steps)       │  │  (hybrid       │  │
│  │  (PDF/DOCX/  │  │  runs as         │  │   retrieval)   │  │
│  │  DOC/XLSX/   │  │  background task │  │                │  │
│  │  XLS/CSV)    │  │                  │  │                │  │
│  └──────┬───────┘  └────────┬─────────┘  └───────┬────────┘  │
│         │                   │                     │           │
│         ▼                   ▼                     ▼           │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  SQLite Database                                       │   │
│  │  ├── Document            (uploaded files metadata)     │   │
│  │  ├── TaxonomySchema      (discovered dimensions)       │   │
│  │  ├── Extraction          (per-doc extracted values)     │   │
│  │  ├── Entity              (canonical entities)           │   │
│  │  ├── EntityResolution    (mention → entity links)      │   │
│  │  ├── Contradiction       (cross-doc conflicts)         │   │
│  │  └── DocumentChunk       (text chunks + embeddings)    │   │
│  │      └── FTS5 index      (full-text search)            │   │
│  └────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────┘
```

---

## Data Pipeline — Detailed Flow

The pipeline is the core of the system. When users upload documents and click "Process", the 5-step pipeline runs as a background task. Each step builds on the outputs of the previous one.

```
┌──────────────────┐
│  Upload Files     │  User drags PDFs, DOCX, DOC, XLSX, XLS, CSV into Document Panel
│  POST /api/upload │  Files stored to data/originals/, Document records created
└────────┬─────────┘
         ▼
┌──────────────────┐
│  POST /api/process│  Triggers background pipeline thread
│  (with doc IDs)   │  Frontend starts polling /api/status every 2 seconds
└────────┬─────────┘
         ▼
╔══════════════════════════════════════════════════════════════════╗
║  STEP 1: Document Type Detection                                ║
║  (backend/pipeline/step1_doc_type.py)                           ║
║                                                                  ║
║  Input:  Raw document text from each uploaded file               ║
║  Action: Extracts ~600 words from first ~2 pages of each doc    ║
║          Sends combined samples to LLM in one call               ║
║          LLM infers a shared document type                       ║
║  Output: A doc_type string                                       ║
║          e.g. "Quarterly Investor Report for a Public Company"   ║
║                                                                  ║
║  DB:     Updates Document.detected_doc_type for all docs         ║
╚══════════════════╤═══════════════════════════════════════════════╝
                   ▼
╔══════════════════════════════════════════════════════════════════╗
║  TEMPLATE MATCHING (between Step 1 and Step 2)                  ║
║  (backend/pipeline/template_matching.py)                        ║
║                                                                  ║
║  Input:  doc_type, sample text, all TaxonomyTemplates from DB    ║
║  Action: LLM sees all template labels + descriptions and         ║
║          decides which are relevant to these documents.           ║
║          Can match 0, 1, or multiple templates.                  ║
║  Output: List of matched TaxonomyTemplate records                ║
║                                                                  ║
║  Note:   Skipped if no templates are configured.                 ║
╚══════════════════╤═══════════════════════════════════════════════╝
                   ▼
╔══════════════════════════════════════════════════════════════════╗
║  STEP 2: Taxonomy Generation                                    ║
║  (backend/pipeline/step2_taxonomy.py)                           ║
║                                                                  ║
║  Input:  doc_type from Step 1, sample text from first 2 docs,   ║
║          optional company_context string,                        ║
║          matched template dimensions (injected as must-includes) ║
║  Action: LLM analyzes samples and identifies all key dimensions ║
║          (fields/attributes) that should be extracted.           ║
║          Template dimensions are mandatory; LLM adds its own     ║
║          discovered dimensions on top.                           ║
║  Output: JSON array of dimensions, each with:                    ║
║          {name, description, expected_type}                      ║
║                                                                  ║
║  Example dimensions for financial reports:                       ║
║  ┌─────────────────┬──────────────────────────┬──────────┐      ║
║  │ name            │ description              │ type     │      ║
║  ├─────────────────┼──────────────────────────┼──────────┤      ║
║  │ revenue         │ Total revenue reported   │ currency │      ║
║  │ ebitda          │ EBITDA figure             │ currency │      ║
║  │ risk_factors    │ Key risk factors listed   │ text_list│      ║
║  │ ceo_name        │ Name of CEO               │ entity   │      ║
║  │ report_period   │ Reporting period dates    │ date_range│     ║
║  └─────────────────┴──────────────────────────┴──────────┘      ║
║                                                                  ║
║  DB:     Creates TaxonomySchema record with dimensions JSON      ║
╚══════════════════╤═══════════════════════════════════════════════╝
                   ▼
╔══════════════════════════════════════════════════════════════════╗
║  STEP 3: Per-Document Extraction (runs for EACH document)       ║
║  (backend/pipeline/step3_extraction.py + chunking.py)           ║
║                                                                  ║
║  Input:  One document + TaxonomySchema dimensions                ║
║                                                                  ║
║  Action A — Dimension Extraction:                                ║
║    For PDFs: Uses multimodal LLM (Claude vision) on page images  ║
║    For others: Passes document text to LLM                       ║
║    LLM extracts values for each taxonomy dimension:              ║
║    {                                                             ║
║      "revenue":  {"value": "$5.2B", "confidence": 0.95,         ║
║                   "source_pages": [2, 3]},                       ║
║      "ceo_name": {"value": "Jane Smith", "confidence": 0.88,    ║
║                   "source_pages": [1]}                           ║
║    }                                                             ║
║                                                                  ║
║  Action B — Chunking & Embedding:                                ║
║    Splits text into 500-word chunks with 100-word overlap        ║
║    Embeds all chunks via text-embedding-3-small                  ║
║    Populates FTS5 full-text search index                         ║
║                                                                  ║
║  DB:     Creates Extraction records (value per dimension per doc)║
║          Creates DocumentChunk records (text + embedding vector) ║
╚══════════════════╤═══════════════════════════════════════════════╝
                   ▼
╔══════════════════════════════════════════════════════════════════╗
║  STEP 4: Entity Resolution                                      ║
║  (backend/pipeline/step4_entities.py)                           ║
║                                                                  ║
║  Input:  All Extraction records with entity/entity_list types    ║
║                                                                  ║
║  Action: Collects every entity mention across all documents      ║
║          LLM groups mentions that refer to the same real-world   ║
║          entity and assigns a canonical name:                    ║
║                                                                  ║
║          "Tesla", "Tesla Inc", "TSLA" → canonical: "Tesla Inc"  ║
║          "Elon Musk", "E. Musk"       → canonical: "Elon Musk"  ║
║                                                                  ║
║          Each alias gets a confidence score.                     ║
║          Confidence < 0.8 → flagged needs_review for human       ║
║                                                                  ║
║  DB:     Creates Entity records (canonical name + aliases)       ║
║          Creates EntityResolution records (mention → entity)    ║
║          Updates Extraction.resolved_value to canonical name     ║
╚══════════════════╤═══════════════════════════════════════════════╝
                   ▼
╔══════════════════════════════════════════════════════════════════╗
║  STEP 5: Contradiction Detection                                ║
║  (backend/pipeline/step5_contradictions.py)                     ║
║                                                                  ║
║  Input:  All Extraction records for the taxonomy                 ║
║                                                                  ║
║  Action: Groups extractions by (entity, dimension)               ║
║          For groups spanning multiple documents, builds           ║
║          comparison text:                                        ║
║            "Entity: Tesla Inc, Dimension: revenue                ║
║             Doc A (2024-Q1) says: $5.2B                          ║
║             Doc B (2024-Q2) says: $4.8B"                         ║
║          LLM identifies genuine contradictions (not just         ║
║          formatting differences or temporal changes)              ║
║                                                                  ║
║  DB:     Creates Contradiction records with:                     ║
║          doc_a_id, doc_b_id, value_a, value_b,                   ║
║          resolution_status = "unresolved"                        ║
╚══════════════════╤═══════════════════════════════════════════════╝
                   ▼
┌──────────────────────────────────────────────────────────────────┐
│  Pipeline Complete                                                │
│  Frontend detects status="completed", refreshes all data          │
│  Taxonomy Dashboard now shows the extraction grid,                │
│  contradictions highlighted in red, entity reviews in yellow      │
└──────────────────────────────────────────────────────────────────┘
```

### Pipeline Summary Table

| Step | Name | Input | LLM Task | Output (DB Records) |
|------|------|-------|----------|---------------------|
| 1 | Doc Type Detection | Raw text samples | Classify document type | Document.detected_doc_type |
| — | Template Matching | Doc type + samples + templates | Pick relevant templates | (matched list, no DB write) |
| 2 | Taxonomy Generation | Doc type + samples + matched templates | Discover dimensions (must-include template dims) | TaxonomySchema |
| 3 | Per-Doc Extraction | Document + taxonomy | Extract values + chunk/embed text | Extraction, DocumentChunk |
| 4 | Entity Resolution | Entity-type extractions | Group mentions → canonical entities | Entity, EntityResolution |
| 5 | Contradiction Detection | All extractions | Find conflicting values across docs | Contradiction |

---

## Chat / Query System

The chat system uses hybrid retrieval: combining structured database queries with semantic search for comprehensive answers.

```
User types: "What was revenue in Q2?"
              │
              ▼
    ┌─────────────────────┐
    │  Query Classifier    │  LLM classifies into one of:
    │  (classifier.py)     │  FACT_LOOKUP | CROSS_DOC_COMPARISON |
    │                      │  ENTITY_QUERY | TEMPORAL | OPEN_ENDED
    └──────────┬──────────┘
               │ query_type = FACT_LOOKUP
               ▼
    ┌──────────────────────────────────────┐
    │  Parallel Retrieval                   │
    │                                       │
    │  ┌─────────────────────────────────┐ │
    │  │ Structured Search               │ │
    │  │ (structured_retrieval.py)       │ │
    │  │                                  │ │
    │  │ Queries Extraction table by     │ │
    │  │ dimension name / value match.   │ │
    │  │ Also fetches any relevant       │ │
    │  │ Contradiction records.          │ │
    │  │                                  │ │
    │  │ Behavior varies by query_type:  │ │
    │  │ • FACT_LOOKUP → filter match    │ │
    │  │ • ENTITY_QUERY → entity lookup  │ │
    │  │ • TEMPORAL → sort by date       │ │
    │  │ • CROSS_DOC → all extractions   │ │
    │  └─────────────────────────────────┘ │
    │                                       │
    │  ┌─────────────────────────────────┐ │
    │  │ Semantic Search                 │ │
    │  │ (semantic_retrieval.py)         │ │
    │  │                                  │ │
    │  │ Two-path hybrid:               │ │
    │  │ • BM25 via FTS5 full-text index │ │
    │  │ • Cosine similarity on          │ │
    │  │   embedded document chunks      │ │
    │  │                                  │ │
    │  │ Results combined & deduplicated  │ │
    │  │ Returns top-k chunks by score   │ │
    │  └─────────────────────────────────┘ │
    └──────────────────┬───────────────────┘
                       ▼
    ┌──────────────────────────────────────┐
    │  LLM Response Generation             │
    │  (engine.py)                         │
    │                                       │
    │  Assembles context from both          │
    │  retrieval paths + chat history       │
    │  (last 10 exchanges per session)      │
    │                                       │
    │  LLM generates answer with inline     │
    │  citations: [Doc: filename, p.X]      │
    └──────────────────┬───────────────────┘
                       ▼
    ┌──────────────────────────────────────┐
    │  Post-processing                      │
    │  • Extract citations via regex        │
    │  • Add taxonomy-sourced citations     │
    │  • Generate suggested follow-up       │
    │    queries from available dimensions  │
    └──────────────────────────────────────┘
```

---

## Backend Structure

### Core Files
- `main.py` — FastAPI app entrypoint with CORS middleware
- `backend/models.py` — SQLAlchemy ORM models (Document, TaxonomySchema, Extraction, Entity, EntityResolution, Contradiction, DocumentChunk)
- `backend/database.py` — DB initialization + FTS5 virtual table setup
- `backend/config.py` — Centralised Pydantic `BaseSettings` configuration (all app settings: dirs, DB, LLM, embedding, chunking, chat, server). Reads env vars and `.env` file. Access via `get_settings()`.
- `backend/api/routes.py` — All REST endpoints
- `backend/api/schemas.py` — Pydantic request/response models

### Ingestion Layer (`backend/ingestion/`)
- `common.py` — BaseIngester abstract class + registry pattern
- `pdf_ingester.py` — PyMuPDF: renders pages as PIL images at 150 DPI + text extraction
- `word_ingester.py` — python-docx: paragraph text extraction (.docx) + binary text extraction fallback (.doc via LegacyDocIngester)
- `excel_ingester.py` — openpyxl: sheet → tab-separated values (.xlsx) + xlrd for legacy .xls (XlsIngester)
- `csv_ingester.py` — Python csv module: CSV → tab-separated text (CsvIngester)
- `service.py` — Entry point: stores file to disk, creates DB record, calls appropriate ingester. Supports: .pdf, .docx, .doc, .xlsx, .xls, .csv

### Pipeline (`backend/pipeline/`)
- `orchestrator.py` — Runs steps 1–5 sequentially, tracks status in module-level dict
- `step1_doc_type.py` — Document type detection via LLM
- `step2_taxonomy.py` — Taxonomy dimension discovery via LLM
- `step3_extraction.py` — Per-document value extraction (multimodal for PDFs) + chunking/embedding
- `step4_entities.py` — Cross-document entity resolution via LLM
- `step5_contradictions.py` — Contradiction detection via LLM
- `template_matching.py` — LLM-based matching of doc type against configured TaxonomyTemplates
- `chunking.py` — Text splitter (500-word chunks, 100-word overlap) + embedding generation
- `llm.py` — Unified LLM interface via litellm + JSON response parser

### Chat (`backend/chat/`)
- `classifier.py` — Query type classification (FACT_LOOKUP, CROSS_DOC_COMPARISON, ENTITY_QUERY, TEMPORAL, OPEN_ENDED)
- `structured_retrieval.py` — Queries Extraction/Entity/Contradiction tables based on query type
- `semantic_retrieval.py` — Hybrid BM25 (FTS5) + embedding cosine similarity search
- `engine.py` — Orchestrates classification → parallel retrieval → LLM response → citation extraction

## Frontend Structure (`frontend/`)
- Three-panel layout: Documents (left) | Taxonomy/Templates (center, tabbed) | Chat (right)
- Top bar with 5-step pipeline progress indicator
- Center panel has two tabs: **Taxonomy** (extraction grid) and **Templates** (CRUD for taxonomy templates)
- `src/components/document-panel.tsx` — Upload, file list, process trigger
- `src/components/taxonomy-panel.tsx` — Extraction grid with contradiction/entity highlights
- `src/components/templates-panel.tsx` — Create/edit/delete taxonomy templates with dimensions
- `src/components/chat-panel.tsx` — Message history, citations, suggested queries
- `src/components/top-bar.tsx` — Pipeline progress visualization
- `src/lib/api.ts` — Typed API client
- `src/lib/types.ts` — TypeScript interfaces matching backend schemas
- `src/lib/notifications.tsx` — Notification context, provider, and `useNotifications()` hook (auto-dismiss toasts)
- `src/components/notifications.tsx` — Toast display component (fixed top-right, slide-in animation, dismissible)
- Polling `/api/status` every 2s during processing for real-time progress

## API Endpoints
- `POST /api/upload` — Upload document files (multipart FormData)
- `POST /api/process` — Start pipeline processing (spawns background task)
- `GET /api/status` — Pipeline status (polled every 2s by frontend)
- `GET /api/documents` — List documents
- `GET /api/taxonomy` — Get discovered taxonomy schema
- `GET /api/extractions` — Get extracted values (filterable by document_id, dimension_name)
- `GET /api/entities` — Get resolved entities with review counts
- `GET /api/contradictions` — Get detected contradictions
- `PATCH /api/entities/{id}` — Update entity canonical name
- `PATCH /api/entity-resolutions/{id}` — Approve/reject/override entity resolution
- `GET /api/taxonomy-templates` — List all taxonomy templates
- `POST /api/taxonomy-templates` — Create a taxonomy template
- `PUT /api/taxonomy-templates/{id}` — Update a taxonomy template
- `DELETE /api/taxonomy-templates/{id}` — Delete a taxonomy template
- `POST /api/chat` — Send chat message with citation retrieval

## Database Schema

```
Document ──────────┬──→ DocumentChunk (text + embedding + FTS5)
                   ├──→ Extraction ──→ TaxonomySchema
                   └──→ EntityResolution ──→ Entity (canonical + aliases)

TaxonomyTemplate (standalone — matched at pipeline runtime by LLM)

Contradiction ──→ Document A, Document B, Entity (optional)
```

**Key types for TaxonomySchema dimensions:**
`text | number | date | currency | entity | entity_list | text_list | date_range`

## Running

```bash
# Backend
uv sync
uv run uvicorn main:app --reload        # http://localhost:8000

# Frontend
cd frontend && npm install && npm run dev  # http://localhost:5173

# Tests
uv run pytest tests/ -v
```
