# Step 1: Report Date Extraction

## Task
Modify pipeline Step 1 (document type detection) to also extract each document's report date during the same LLM call, as part of the "Investor Report Intelligence" reframe.

## Problem
Everything temporal in the system depends on knowing when each document was authored. The `Document` model has a `report_date` field (nullable DateTime) but nothing was populating it.

## Changes

### `backend/pipeline/step1_doc_type.py`
- Updated the LLM prompt to request JSON output with both `doc_type` and a `document_dates` array mapping each filename to its extracted date (ISO format or null).
- Added `parse_json_response` import from `backend.pipeline.llm` to parse the structured JSON response.
- Added `datetime` import for parsing ISO date strings via `datetime.fromisoformat()`.
- After parsing, stores each extracted date as `Document.report_date` in the database.
- Graceful fallback: if JSON parsing fails (e.g., LLM returns plain text), treats the entire response as doc_type and leaves report_date as None.
- Invalid/unparseable date strings are logged and silently skipped (report_date stays None).
- Function signature and return type unchanged: still returns `str` (the doc_type).

### `tests/test_pipeline.py`
- Updated existing step1 tests to use JSON mock responses matching the new format.
- Added new tests:
  - `test_detect_doc_type_with_dates` - verifies dates are correctly parsed and stored
  - `test_detect_doc_type_null_dates` - verifies null dates leave report_date as None
  - `test_detect_doc_type_fallback_on_invalid_json` - verifies plain-text fallback works
  - `test_detect_doc_type_invalid_date_string` - verifies unparseable dates are handled gracefully

### `agents/architecture.md`
- Updated pipeline summary table and Step 1 description to reflect report date extraction.

## Constraints Followed
- Import `parse_json_response` from `backend.pipeline.llm`
- Import `datetime` from standard library
- Use `datetime.fromisoformat()` for parsing
- Keep function signature: `async def detect_doc_type(documents, document_ids, db) -> str`
- Return value is still the doc_type string (orchestrator not broken)
