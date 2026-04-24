# Spindle — Architecture

## Overview

**Spindle** is an AI-powered investor report intelligence platform. It ingests multi-format documents, automatically discovers taxonomy schemas, extracts structured data, resolves entities across documents, detects contradictions, tracks temporal changes — and surfaces answers and alerts through a hybrid chat interface.

The core philosophy: **the output is answers and alerts, not a table.** The extraction grid is a reference layer; the primary value is the Insights dashboard (contradictions, staleness, entity reviews) and the temporally-aware chat.

## Stack
- **Backend:** FastAPI (Python 3.11+) with SQLAlchemy ORM, SQLite, background task threading
- **Frontend:** Vite + React 19 (TypeScript) + Radix UI primitives + Tailwind CSS v3 (dual light/dark theme via CSS variables + `ThemeProvider`)
- **UI Components:** Custom component library built on Radix UI (Popover, Tooltip, ScrollArea) + Lucide icons
- **LLM:** Multiple models via litellm (unified interface, defaults to `anthropic/claude-sonnet-4-20250514`)
- **Embeddings:** OpenAI `text-embedding-3-small` for document chunk vectors
- **Search:** Hybrid BM25 (SQLite FTS5) + cosine similarity on embeddings
- **Package Management:** uv (Python), npm (Node.js)

---

## How the App Works — User Journey

```
1. User visits "/"
   └── Landing page (SaaS marketing page with pipeline walkthrough)
       └── "Open Spindle" button → navigates to #app

2. User enters the app (#app)
   └── Three-panel layout appears:
       ├── LEFT:   Document Panel (upload, manage)
       ├── CENTER: Tabbed content (Insights | Taxonomy | Templates)
       └── RIGHT:  Context-sensitive sidebar (Schema + Chat | Chat)

3. User uploads documents
   └── Drag-and-drop or file picker (PDF, DOCX, DOC, XLSX, XLS, CSV)
       └── Optional: add company context for better extraction
       └── Optional: "Each CSV row is a separate document" checkbox (splits CSV rows into individual documents)
       └── Click "Process" → triggers 5-step background pipeline

4. Pipeline runs (progress shown in top bar)
   ├── Step 1: Detect document type + extract report dates
   ├── Step 1.5: Match against taxonomy templates (if configured)
   ├── Step 2: Discover taxonomy dimensions (schema generation)
   ├── Step 3: Extract values per document + chunk/embed text
   ├── Step 4: Resolve entities across documents
   └── Step 5: Detect contradictions between documents

5. Pipeline completes → data loads automatically
   ├── Insights tab: Contradictions, entities needing review, staleness alerts
   ├── Taxonomy tab: Extraction grid (docs × dimensions) with interactive cells
   ├── Schema sidebar: Dimension list with coverage bars
   └── Chat: Ask questions with citation-backed answers

6. User interacts with results
   ├── Click contradiction → see temporal comparison (which doc is newer)
   ├── Click entity for review → approve/reject/override alias resolution
   ├── Click entity in insights → change feed timeline (how values evolved)
   ├── Ask chat questions → get cited answers with suggested follow-ups
   └── Export insights → CSV download
```

---

## Application Flow Diagram

```
┌───────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + TypeScript)                │
│                                                                 │
│  ┌─────────────┐  ┌──────────────────────┐  ┌───────────────┐ │
│  │  Document    │  │  Center Panel (tabs)  │  │  Sidebar      │ │
│  │  Panel       │  │                       │  │  (context-    │ │
│  │  (288px)     │  │  ┌─ Insights ──────┐ │  │   sensitive)  │ │
│  │              │  │  │  Contradictions  │ │  │               │ │
│  │  • Source    │  │  │  Entity Reviews  │ │  │  When Taxonomy│ │
│  │    selector  │  │  │  Staleness       │ │  │  tab active:  │ │
│  │  • Drag-drop │  │  │  CSV Export      │ │  │  • Schema tab │ │
│  │    upload    │  │  └─────────────────┘ │  │  • Chat tab   │ │
│  │  • File list │  │  ┌─ Taxonomy ──────┐ │  │               │ │
│  │    (sorted   │  │  │  Extraction grid │ │  │  Otherwise:   │ │
│  │    by date)  │  │  │  (docs × dims)  │ │  │  • Chat only  │ │
│  │  • Company   │  │  │  Cell popovers  │ │  │               │ │
│  │    context   │  │  │  Entity review   │ │  │  Chat has:    │ │
│  │  • Process   │  │  │  Contradiction   │ │  │  • Citations  │ │
│  │    button    │  │  │  highlights      │ │  │  • Suggestions│ │
│  └──────┬──────┘  │  └─────────────────┘ │  │  • Callouts   │ │
│         │         │  ┌─ Templates ──────┐ │  │  • History     │ │
│         │         │  │  CRUD for reusable│ │  └───────┬───────┘ │
│         │         │  │  taxonomy schemas │ │          │         │
│         │         │  └─────────────────┘ │          │         │
│  ┌──────┴──────────────┴──────────────────┴──────────┴───────┐ │
│  │                 Top Bar — Pipeline Progress                 │ │
│  │   [Step 1] → [Step 2] → [Step 3] → [Step 4] → [Step 5]   │ │
│  │   Type Detection → Taxonomy → Extraction → Entities → Contradictions │
│  └─────────────────────────┬──────────────────────────────────┘ │
│  ┌─────────────────────────┴──────────────────────────────────┐ │
│  │  Change Feed (overlay) — Entity timeline with diffs         │ │
│  │  Shows value evolution across documents (new/updated/       │ │
│  │  contradiction) with vertical timeline visualization        │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST API (polls /status every 2s)
                             ▼
┌────────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND                             │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  API Routes (backend/api/routes.py)                       │  │
│  │                                                            │  │
│  │  POST /api/upload ──────────→ Ingestion Service           │  │
│  │  POST /api/process ─────────→ Pipeline Orchestrator       │  │
│  │  GET  /api/status ──────────→ Pipeline Status Dict        │  │
│  │  GET  /api/documents ───────→ DB Query                    │  │
│  │  DELETE /api/documents ─────→ Cascade Delete All          │  │
│  │  DELETE /api/documents/{id} → Delete Single               │  │
│  │  GET  /api/taxonomy ────────→ DB Query                    │  │
│  │  GET  /api/extractions ─────→ DB Query (filterable)       │  │
│  │  GET  /api/entities ────────→ DB Query + review counts    │  │
│  │  PATCH /api/entities/{id} ──→ DB Update                   │  │
│  │  GET  /api/entities/{id}/timeline → Timeline Builder      │  │
│  │  PATCH /api/entity-resolutions/{id} → DB Update           │  │
│  │  GET  /api/contradictions ──→ DB Query                    │  │
│  │  GET  /api/taxonomy-templates ─→ CRUD                     │  │
│  │  POST /api/taxonomy-templates ─→ CRUD                     │  │
│  │  PUT  /api/taxonomy-templates/{id} → CRUD                 │  │
│  │  DELETE /api/taxonomy-templates/{id} → CRUD               │  │
│  │  GET  /api/insights ────────→ Aggregation Engine          │  │
│  │  POST /api/chat ────────────→ Chat Engine                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  Ingestion   │  │  Pipeline        │  │  Chat Engine     │  │
│  │  Service     │  │  (5 steps)       │  │  (hybrid         │  │
│  │  (PDF/DOCX/  │  │  runs as         │  │   retrieval)     │  │
│  │  DOC/XLSX/   │  │  background task │  │                  │  │
│  │  XLS/CSV)    │  │                  │  │  Structured +    │  │
│  │              │  │  Template match   │  │  Semantic search │  │
│  │  6 formats   │  │  between S1 & S2 │  │  Temporal-aware  │  │
│  └──────┬───────┘  └────────┬─────────┘  └───────┬──────────┘  │
│         │                   │                     │             │
│         ▼                   ▼                     ▼             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  SQLite Database                                          │  │
│  │  ├── Document            (uploaded files + report dates)  │  │
│  │  ├── TaxonomySchema      (discovered dimensions JSON)     │  │
│  │  ├── Extraction          (per-doc extracted values)       │  │
│  │  ├── Entity              (canonical entities + aliases)   │  │
│  │  ├── EntityResolution    (mention → entity links)         │  │
│  │  ├── Contradiction       (cross-doc conflicts + dates)    │  │
│  │  ├── TaxonomyTemplate    (reusable schema templates)      │  │
│  │  └── DocumentChunk       (text chunks + embeddings)       │  │
│  │      └── FTS5 index      (full-text search, BM25)        │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

---

## Data Pipeline — Detailed Flow

The pipeline is the core of the system. When users upload documents and click "Process", the 5-step pipeline runs as a background thread. Each step builds on the outputs of the previous one.

```
┌──────────────────┐
│  Upload Files     │  User drags PDFs, DOCX, DOC, XLSX, XLS, CSV into Document Panel
│  POST /api/upload │  Files stored to data/originals/, Document records created
└────────┬─────────┘
         ▼
┌──────────────────┐
│  POST /api/process│  Pre-seeds pipeline_status as "running" (avoids race condition)
│  (with doc IDs)   │  Spawns background thread via _run_pipeline_in_thread()
│                   │  Frontend starts polling /api/status every 2 seconds
└────────┬─────────┘
         ▼
╔══════════════════════════════════════════════════════════════════╗
║  STEP 1: Document Type Detection + Date Extraction              ║
║  (backend/pipeline/step1_doc_type.py)                           ║
║                                                                  ║
║  Input:  Raw document text from each uploaded file               ║
║  Action: Extracts ~600 words from first ~2 pages of each doc    ║
║          Single LLM call returns JSON:                           ║
║          { "doc_type": "...", "document_dates": ["2024-03-15"]}  ║
║  Output: doc_type string + per-document report_date              ║
║  Fallback: If JSON parsing fails, treats response as doc_type    ║
║                                                                  ║
║  DB:     Updates Document.detected_doc_type for all docs         ║
║          Updates Document.report_date per doc (nullable)         ║
╚══════════════════╤═══════════════════════════════════════════════╝
                   ▼
╔══════════════════════════════════════════════════════════════════╗
║  TEMPLATE MATCHING (between Step 1 and Step 2)                  ║
║  (backend/pipeline/template_matching.py)                        ║
║                                                                  ║
║  Input:  doc_type, sample text, all TaxonomyTemplates from DB    ║
║  Action: LLM decides which templates are relevant to these docs  ║
║  Output: List of matched TaxonomyTemplate records                ║
║  Note:   Skipped if no templates are configured.                 ║
╚══════════════════╤═══════════════════════════════════════════════╝
                   ▼
╔══════════════════════════════════════════════════════════════════╗
║  STEP 2: Taxonomy Generation                                    ║
║  (backend/pipeline/step2_taxonomy.py)                           ║
║                                                                  ║
║  Input:  doc_type, sample text (~800 words from first 2 docs),  ║
║          optional company_context,                               ║
║          matched template dimensions (injected as must-includes) ║
║  Action: LLM discovers all dimensions to extract                 ║
║          Template dimensions are mandatory; LLM adds its own     ║
║  Output: JSON array of {name, description, expected_type}        ║
║  Types:  text | number | date | currency | entity |              ║
║          entity_list | text_list | date_range                    ║
║                                                                  ║
║  DB:     Creates TaxonomySchema record with dimensions JSON      ║
╚══════════════════╤═══════════════════════════════════════════════╝
                   ▼
╔══════════════════════════════════════════════════════════════════╗
║  STEP 3: Per-Document Extraction (two-phase)                    ║
║  (backend/pipeline/step3_extraction.py + chunking.py)           ║
║                                                                  ║
║  PHASE A — Parallel fetch (no DB writes):                       ║
║    asyncio.gather() across all documents:                        ║
║    • LLM extraction: value + confidence + source_pages per dim   ║
║      - PDFs: multimodal (base64 page images sent to Claude)      ║
║      - Others: text-based extraction                             ║
║      - Unwraps nested LLM responses ({"extractions": {...}})    ║
║    • Chunking: 500-word chunks with 100-word overlap             ║
║    • Embedding: text-embedding-3-small on all chunks             ║
║                                                                  ║
║  PHASE B — Sequential DB writes:                                 ║
║    For each document:                                            ║
║    • Creates Extraction records (value per dimension)            ║
║    • Creates DocumentChunk records (text + embedding bytes)      ║
║    • Inserts chunk text into FTS5 virtual table                  ║
║    • Marks Document.processed_at = now                           ║
╚══════════════════╤═══════════════════════════════════════════════╝
                   ▼
╔══════════════════════════════════════════════════════════════════╗
║  STEP 4: Entity Resolution                                      ║
║  (backend/pipeline/step4_entities.py)                           ║
║                                                                  ║
║  Input:  All extractions with entity/entity_list types           ║
║  Action: Collects every entity mention across all documents      ║
║          LLM groups mentions → canonical entity + aliases        ║
║          Each alias gets a confidence score                      ║
║          Confidence < 0.8 → flagged needs_review                ║
║                                                                  ║
║  DB:     Creates Entity records (canonical_name + aliases)       ║
║          Creates EntityResolution records (mention → entity)     ║
║          Updates Extraction.resolved_value to canonical name     ║
╚══════════════════╤═══════════════════════════════════════════════╝
                   ▼
╔══════════════════════════════════════════════════════════════════╗
║  STEP 5: Contradiction Detection                                ║
║  (backend/pipeline/step5_contradictions.py)                     ║
║                                                                  ║
║  Input:  All extractions grouped by (entity_id, dimension_name)  ║
║  Action: Keeps only groups spanning multiple documents            ║
║          LLM identifies genuine contradictions                   ║
║          (not formatting differences or temporal changes)         ║
║          Stores doc dates for temporal context                    ║
║                                                                  ║
║  DB:     Creates Contradiction records with:                     ║
║          doc_a/b IDs, values, dates, resolution_status           ║
╚══════════════════╤═══════════════════════════════════════════════╝
                   ▼
┌──────────────────────────────────────────────────────────────────┐
│  Pipeline Complete                                                │
│  Frontend detects status="completed", auto-refreshes all data     │
│  Shows success notification (or error with retry button)          │
└──────────────────────────────────────────────────────────────────┘
```

### Pipeline Summary Table

| Step | Name | Input | LLM Task | Output (DB Records) |
|------|------|-------|----------|---------------------|
| 1 | Doc Type Detection + Date Extraction | Raw text samples | Classify document type + extract report dates | Document.detected_doc_type, Document.report_date |
| — | Template Matching | Doc type + samples + templates | Pick relevant templates | (matched list, no DB write) |
| 2 | Taxonomy Generation | Doc type + samples + matched templates | Discover dimensions (must-include template dims) | TaxonomySchema |
| 3 | Per-Doc Extraction | Document + taxonomy | Extract values + chunk/embed text | Extraction, DocumentChunk, FTS5 index |
| 4 | Entity Resolution | Entity-type extractions | Group mentions → canonical entities | Entity, EntityResolution |
| 5 | Contradiction Detection | All extractions (multi-doc groups) | Find conflicting values across docs | Contradiction |

---

## Chat / Query System

The chat system uses hybrid retrieval: structured database queries combined with semantic search for comprehensive, citation-backed answers. It is temporally aware — it prefers recent data and includes dates in contradiction context.

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
    │  │ Query-type-specific DB queries: │ │
    │  │ • FACT_LOOKUP → dimension/value  │ │
    │  │   match on Extraction table      │ │
    │  │ • ENTITY_QUERY → entity lookup   │ │
    │  │   via aliases → linked docs      │ │
    │  │ • TEMPORAL → sort by date desc   │ │
    │  │ • CROSS_DOC → all extractions    │ │
    │  │                                  │ │
    │  │ All paths: join with Document    │ │
    │  │ for effective_date (coalesce     │ │
    │  │ report_date, uploaded_at)        │ │
    │  │                                  │ │
    │  │ Appends matching contradictions  │ │
    │  │ with temporal_context            │ │
    │  └─────────────────────────────────┘ │
    │                                       │
    │  ┌─────────────────────────────────┐ │
    │  │ Semantic Search                 │ │
    │  │ (semantic_retrieval.py)         │ │
    │  │                                  │ │
    │  │ Hybrid two-path:               │ │
    │  │ • BM25 via FTS5 full-text index │ │
    │  │ • Cosine similarity on          │ │
    │  │   embedded document chunks      │ │
    │  │                                  │ │
    │  │ Results combined, deduplicated   │ │
    │  │ (both paths → score added)      │ │
    │  │ Returns top-k chunks by score   │ │
    │  └─────────────────────────────────┘ │
    └──────────────────┬───────────────────┘
                       ▼
    ┌──────────────────────────────────────┐
    │  LLM Response Generation             │
    │  (engine.py)                         │
    │                                       │
    │  Context includes:                    │
    │  • Structured results (with date      │
    │    prefix: "(dated: ...)" or          │
    │    "(uploaded: ...)")                  │
    │  • Semantic chunks                    │
    │  • Chat history (last 10 exchanges)   │
    │                                       │
    │  System prompt rules:                 │
    │  • Use context only, cite everything  │
    │  • Prefer most recent values          │
    │  • Note contradictions with dates     │
    │  • Format: [Doc: filename, p.X]       │
    └──────────────────┬───────────────────┘
                       ▼
    ┌──────────────────────────────────────┐
    │  Post-processing                      │
    │  • Regex extracts [Doc: X, p.Y]       │
    │  • Add taxonomy-sourced citations     │
    │  • Generate 3 suggested follow-ups    │
    │  • Store in session history            │
    └──────────────────────────────────────┘
```

---

## Insights Engine

The `/api/insights` endpoint performs multi-phase aggregation to surface actionable intelligence:

1. **Contradictions** — All unresolved contradictions with temporal context (which document is newer). Pre-fetches documents and entities in batch to avoid N+1 queries.

2. **Entity Reviews** — Entities with low-confidence alias resolutions (`needs_review=true`). Grouped by entity with review count.

3. **Staleness Detection** — Groups extractions by (entity_id, dimension_name). For groups spanning 2+ documents without an existing contradiction, compares consecutive values to find changes. Returns older vs newer value pairs with document dates.

---

## Backend Structure

### Core Files
- `main.py` — FastAPI app entrypoint with CORS middleware, startup DB init
- `backend/models.py` — SQLAlchemy ORM models (8 tables: Document, TaxonomySchema, Extraction, Entity, EntityResolution, Contradiction, TaxonomyTemplate, DocumentChunk)
- `backend/database.py` — DB initialization, schema migration (report_date column), FTS5 virtual table setup
- `backend/config.py` — Centralised Pydantic `BaseSettings` configuration (all app settings: dirs, DB, LLM, embedding, chunking, chat, server). Reads env vars and `.env` file. Access via `get_settings()`.
- `backend/api/routes.py` — All REST endpoints (20 routes)
- `backend/api/schemas.py` — Pydantic request/response models (25+ schemas)

### Ingestion Layer (`backend/ingestion/`)
- `common.py` — BaseIngester ABC, IngestedDocument dataclass, registry pattern
- `pdf_ingester.py` — PyMuPDF: renders pages as PIL images at 150 DPI + text extraction
- `word_ingester.py` — python-docx (.docx) + binary text extraction fallback (.doc via LegacyDocIngester)
- `excel_ingester.py` — openpyxl (.xlsx) + xlrd for legacy .xls (XlsIngester, renders integers without trailing .0)
- `csv_ingester.py` — Python csv module: CSV → tab-separated text (UTF-8-sig → Latin-1 fallback). Supports `ingest_rows()` to split a CSV into one IngestedDocument per data row (key-value format using headers), triggered by the `split_rows` upload option.
- `service.py` — Entry point: `store_and_ingest()` stores file to disk, creates DB record, calls appropriate ingester. `store_and_ingest_csv_rows()` splits a CSV file into one Document per row.

### Pipeline (`backend/pipeline/`)
- `orchestrator.py` — Runs steps 1–5 sequentially in background thread, tracks status in module-level dict, handles errors with full traceback logging
- `step1_doc_type.py` — Document type detection + report date extraction via LLM
- `step2_taxonomy.py` — Taxonomy dimension discovery via LLM (with template injection)
- `step3_extraction.py` — Two-phase: parallel LLM+embedding fetch, then sequential DB writes. Handles nested LLM response unwrapping.
- `step4_entities.py` — Cross-document entity resolution via LLM (confidence < 0.8 → needs_review)
- `step5_contradictions.py` — Contradiction detection via LLM, stores document dates for temporal context
- `template_matching.py` — LLM-based matching of doc type against configured TaxonomyTemplates
- `chunking.py` — Text splitter (500-word chunks, 100-word overlap) + page estimation
- `llm.py` — Unified LLM interface via litellm + JSON response parser (handles markdown fences)

### Chat (`backend/chat/`)
- `classifier.py` — Query type classification (FACT_LOOKUP, CROSS_DOC_COMPARISON, ENTITY_QUERY, TEMPORAL, OPEN_ENDED). LLM-based with string-match fallback.
- `structured_retrieval.py` — Query-type-specific DB queries on Extraction/Entity/Contradiction tables. Temporally aware: uses `coalesce(report_date, uploaded_at)` for sorting. Returns `is_approximate_date` flag and `temporal_context` on contradictions.
- `semantic_retrieval.py` — Hybrid BM25 (FTS5) + embedding cosine similarity search. Deduplicates and combines scores from both paths.
- `engine.py` — Orchestrates classification → parallel retrieval → context formatting → LLM response → citation extraction → suggested queries. Maintains per-session chat history (module-level dict, configurable limit).

---

## Frontend Structure (`frontend/`)

### Layout & Routing
- Hash-based routing: `/` shows landing page, `#app` shows main application
- Three-panel layout: Document Panel (left, 288px) | Center Panel (tabbed) | Sidebar (right, 320px)
- Top bar with 5-step pipeline progress indicator (animated pulse for current step)
- Theme toggle (dark/light) persisted to localStorage

### Application Shell
- `src/App.tsx` — Root component. Manages all global state (documents, taxonomy, extractions, entities, contradictions, templates). Handles polling loop (2s interval during processing), batch data fetching via Promise.all, auto-refetch on pipeline completion. Retry mechanism for failed pipelines.

### Main Components
- `src/components/landing-page.tsx` — Marketing landing page (2000+ lines of embedded CSS). Calistoga + Inter + JetBrains Mono typography. Electric Blue (#0052FF) gradient accent. IntersectionObserver scroll-triggered reveals, floating hero graphic, animated counters, feature grid, 5-step pipeline timeline, product preview, CTA. Supports `prefers-reduced-motion`.
- `src/components/top-bar.tsx` — Pipeline progress: 5 sequential step indicators with animated progress bars, completion markers, document counter
- `src/components/document-panel.tsx` — Source selector (Sharepoint/Database/Manual Upload), drag-and-drop upload zone with staged file preview, sortable file list (by report_date or uploaded_at), file type icons, company context textarea, process/clear-all buttons, per-document delete
- `src/components/insights-dashboard.tsx` — Summary banner (3 stat cards), contradiction cards (doc A vs B with newer-doc highlighting), entity review list, staleness grid (old→new value transitions), CSV export button. Refreshes on `dataVersion` change.
- `src/components/taxonomy-panel.tsx` — Extraction grid (documents × dimensions). Sticky left column. Cell rendering: resolved/raw values, confidence bars, source pages, contradiction highlighting (red bg), entity review highlighting (amber bg), confirmed indicators (green border). Cell detail popover on click. Column header tooltips with dimension info. Staggered slide-in animations.
- `src/components/taxonomy-schema-panel.tsx` — Sidebar: dimensions list with type-specific icons, expected_type badges, descriptions (2-line clamp), per-dimension extraction coverage progress bars
- `src/components/templates-panel.tsx` — Full CRUD for taxonomy templates: list/create/edit/delete with dimension editor (name, description, expected_type dropdown)
- `src/components/chat-panel.tsx` — Chat with session ID (crypto.randomUUID). Message rendering with inline citation badges (blue=taxonomy, green=document). Contradiction/note callout detection (renders as warning blocks). Typing indicator (3-dot animation). Suggested queries as pill buttons. Supports `embedded` prop for sidebar mode.
- `src/components/change-feed.tsx` — Entity timeline: entity selector dropdown, vertical timeline with connecting line, TimelineNodeCard per document showing dimension values + diffs (New=green, Updated=amber, Contradiction=red badges). Fetches from `/api/entities/{id}/timeline`.
- `src/components/entity-review-card.tsx` — Inline overlay card for entity alias confirmation: canonical name, aliases as badges, color-coded confidence bar, approve/reject buttons
- `src/components/contradiction-popover.tsx` — Radix Popover: dimension header, two value cards with temporal comparison, newer-doc highlighting, arrow showing temporal direction, resolution status badge
- `src/components/notifications.tsx` — Fixed top-right toast stack: color-coded (success/error/info/warning), icons, auto-dismiss (5s or 8s), slide-in animation, optional action buttons (used for retry)

### UI Primitives (`src/components/ui/`)
All built on Radix UI with CVA (class-variance-authority):
- `button.tsx` — Variants: default, destructive, outline, secondary, ghost, link. Sizes: default, sm, lg, icon.
- `badge.tsx` — Variants: default, secondary, destructive, warning, success, outline
- `card.tsx` — Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter
- `popover.tsx` — Radix Popover wrapper
- `tooltip.tsx` — Radix Tooltip wrapper
- `scroll-area.tsx` — Radix ScrollArea for scrollable regions
- `input.tsx` — Standard input with focus ring

### Library / Utilities (`src/lib/`)
- `api.ts` — Typed API client wrapping all 20 endpoints. Generic `request<T>()` with JSON headers and error handling.
- `types.ts` — TypeScript interfaces matching backend schemas: Document, Extraction, Entity, Contradiction, Taxonomy, TaxonomyTemplate, ChatMessage, ChatResponse, Citation, Insights (contradictions + entity reviews + staleness), EntityTimeline (nodes + diffs), PipelineStatus
- `theme.tsx` — ThemeProvider context: dark/light toggle, persists to localStorage (`spindle-theme`), modifies document `.dark` class. Default: dark.
- `notifications.tsx` — NotificationProvider context + `useNotifications()` hook: add/remove notifications, auto-dismiss timers, supports action buttons
- `utils.ts` — `cn()` function merging clsx + tailwind-merge

### Styling & Theming
- `src/index.css` — CSS variables (HSL-based) for light and dark themes. Colors: background, foreground, card, border, primary, secondary, accent, destructive, success, warning. Custom scrollbar. Typing dot animation.
- `tailwind.config.js` — Class-based dark mode. All CSS variables mapped to theme colors. Custom animations: slide-in (translateY), slide-in-right/slide-out-right (translateX), pulse-border. Plugin: tailwindcss-animate.
- `index.html` — Google Fonts preload: Calistoga (display), Instrument Serif (headers), Inter (body), JetBrains Mono (code). Theme flash prevention script (reads localStorage before React hydrates).

---

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/upload` | Upload document files (multipart, accepts PDF/DOCX/DOC/XLSX/XLS/CSV) |
| POST | `/api/process` | Start pipeline (spawns background thread, pre-seeds status) |
| GET | `/api/status` | Pipeline status with step names, document counts, error info |
| GET | `/api/documents` | List documents (sorted by uploaded_at desc) |
| DELETE | `/api/documents` | Cascade delete all documents and related data |
| DELETE | `/api/documents/{id}` | Delete single document |
| GET | `/api/taxonomy` | Get most recent taxonomy schema |
| GET | `/api/extractions` | Get extractions (filterable by document_id, dimension_name) |
| GET | `/api/entities` | Get entities with needs_review_count |
| PATCH | `/api/entities/{id}` | Update entity canonical name |
| GET | `/api/entities/{id}/timeline` | Chronological entity change feed with computed diffs |
| PATCH | `/api/entity-resolutions/{id}` | Approve/reject/override entity resolution |
| GET | `/api/contradictions` | Get contradictions with document filenames |
| GET | `/api/taxonomy-templates` | List taxonomy templates |
| POST | `/api/taxonomy-templates` | Create taxonomy template |
| PUT | `/api/taxonomy-templates/{id}` | Update taxonomy template |
| DELETE | `/api/taxonomy-templates/{id}` | Delete taxonomy template |
| GET | `/api/insights` | Aggregated dashboard: contradictions, entity reviews, staleness |
| POST | `/api/chat` | Chat with hybrid retrieval, citations, suggested queries |

---

## Database Schema

```
Document ──────────┬──→ DocumentChunk (text + embedding + FTS5)
                   ├──→ Extraction ──→ TaxonomySchema
                   └──→ EntityResolution ──→ Entity (canonical + aliases)

TaxonomyTemplate (standalone — matched at pipeline runtime by LLM)

Contradiction ──→ Document A, Document B, Entity (optional)
```

### Tables

| Table | Key Columns | Notes |
|-------|-------------|-------|
| Document | id, original_filename, storage_path, file_type, detected_doc_type, page_count, report_date, uploaded_at, processed_at | report_date populated by pipeline Step 1 |
| TaxonomySchema | id, corpus_id, dimensions (JSON), doc_type, company_context, created_at | dimensions: [{name, description, expected_type}] |
| Extraction | id, document_id (FK), taxonomy_schema_id (FK), dimension_name, raw_value, resolved_value, source_pages (JSON), confidence | resolved_value set by Step 4 |
| Entity | id, canonical_name, entity_type, aliases (JSON) | aliases: string array |
| EntityResolution | id, entity_id (FK), original_value, document_id (FK), confidence, needs_review | needs_review=true when confidence < 0.8 |
| Contradiction | id, dimension_name, entity_id (FK, nullable), doc_a_id (FK), doc_b_id (FK), value_a, value_b, doc_a_date, doc_b_date, resolution_status | resolution_status default "unresolved" |
| TaxonomyTemplate | id, label, description, dimensions (JSON), created_at | User-created reusable schemas |
| DocumentChunk | id, document_id (FK), chunk_text, chunk_index, source_pages (JSON), embedding (LargeBinary) | embedding: numpy float32 bytes |

**Dimension expected_type values:** `text | number | date | currency | entity | entity_list | text_list | date_range`

All models use UUID string PKs and UTC timestamps.

---

## Configuration (`backend/config.py`)

All settings via Pydantic `BaseSettings` (reads env vars + `.env` file):

| Setting | Default | Purpose |
|---------|---------|---------|
| `llm_model` | `anthropic/claude-sonnet-4-20250514` | LLM model via litellm |
| `embedding_model` | `text-embedding-3-small` | Embedding model |
| `litellm_api_base` | None | Optional custom API base |
| `litellm_api_key` | None | Optional API key override |
| `database_url` | `sqlite:///data/taxonomy.db` | SQLite database path |
| `pdf_render_dpi` | 150 | DPI for PDF page rendering |
| `chunk_size` | 500 | Words per chunk |
| `chunk_overlap` | 100 | Overlapping words between chunks |
| `chat_history_limit` | 10 | Recent exchanges in chat context |
| `semantic_search_top_k` | 5 | Results per search path |
| `host` / `port` | `0.0.0.0` / `8000` | Server binding |

---

## Testing

148+ tests across 4 files, all using in-memory SQLite with FTS5:

| File | Tests | Coverage |
|------|-------|----------|
| `tests/test_api.py` | ~55 | All 20 API endpoints, entity timeline diffs, insights aggregation, template CRUD |
| `tests/test_pipeline.py` | ~38 | All 5 pipeline steps, chunking, JSON parsing, orchestrator error handling |
| `tests/test_chat.py` | ~43 | Query classification, structured/semantic retrieval, citations, session management |
| `tests/test_ingestion.py` | ~34 | All 6 file formats, encoding fallbacks, service layer, error cases |

Test patterns: pytest fixtures, extensive AsyncMock/MagicMock, seeded databases with realistic data, parametrized tests.

---

## Running

```bash
# Backend
uv sync
uv run uvicorn main:app --reload        # http://localhost:8000

# Frontend
cd frontend && npm install && npm run dev  # http://localhost:5173

# Both (convenience script)
./start_local.sh

# Tests
uv run pytest tests/ -v
```
