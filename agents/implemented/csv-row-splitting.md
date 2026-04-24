# CSV Row Splitting

## Problem
When uploading a CSV like `investor_report1.csv` where each row represents a distinct meeting/document, the system treated the entire file as a single document. This meant all rows were merged into one extraction, losing the per-row granularity needed for meaningful entity resolution, contradiction detection, and temporal tracking.

## Solution
Added a user-toggled "Each CSV row is a separate document" option that splits a CSV file into one Document per data row at ingestion time. The rest of the pipeline (extraction, entities, contradictions) works unchanged since it already operates per-document.

## Changes

### Backend
- **`backend/models.py`** — Added nullable `source_text` column to `Document`. Stores pre-extracted text for row-split CSV documents so the pipeline doesn't need to re-ingest from the shared CSV file.
- **`backend/database.py`** — Migration: adds `source_text` column if missing.
- **`backend/ingestion/csv_ingester.py`** — Added `ingest_rows()` method to `CsvIngester`. Returns one `IngestedDocument` per CSV data row, with text formatted as key-value pairs using the header row (e.g., `Meeting: Board Q1\nDate: 2024-03-15`). Falls back to single-doc mode if the CSV has no data rows. Extracted shared `_read_csv_content()` helper.
- **`backend/ingestion/service.py`** — Added `store_and_ingest_csv_rows()` function. Stores the CSV file once to disk, calls `ingest_rows()`, creates one Document DB record per row with filename like `investor_report1.csv [Row 1]` and `source_text` set to the row's key-value text. Extracted shared `_store_file()` helper. Added `db.expunge(doc)` to both service functions so returned Document objects remain usable after session close.
- **`backend/pipeline/orchestrator.py`** — Re-ingestion now checks `doc_record.source_text` first; if present, constructs an `IngestedDocument` directly from it instead of re-ingesting from the file. This is what makes row-split CSVs actually work through the pipeline.
- **`backend/api/routes.py`** — Upload endpoint now accepts optional `split_rows` form parameter. When `"true"` and file is `.csv`, routes to `store_and_ingest_csv_rows()` instead of `store_and_ingest()`.

### Frontend
- **`frontend/src/lib/api.ts`** — `uploadDocuments()` accepts optional `splitRows: boolean` parameter, sends as `split_rows` form field.
- **`frontend/src/components/document-panel.tsx`** — Added `splitRows` state and checkbox that appears only when CSV files are staged. Wired through `handleProcess` → `onUploadAndProcess`.
- **`frontend/src/App.tsx`** — `handleUploadAndProcess` signature updated to accept and pass `splitRows`.

### Tests
- **`tests/test_ingestion.py`** — Added `TestCsvIngesterRows` (6 tests: basic split, preserves file type, header-only fallback, single row, empty cells, extra columns) and `TestStoreAndIngestCsvRows` (1 integration test).
- **`tests/test_api.py`** — Added 3 upload tests: CSV with split_rows, CSV without split_rows, split_rows ignored for non-CSV.

### Docs
- **`agents/architecture.md`** — Updated ingestion layer and user journey sections.
