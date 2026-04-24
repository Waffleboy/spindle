# Temporally-Aware Chat (Backend)

**Date:** 2026-04-24

## Problem
The chat engine and structured retrieval had no awareness of document temporal ordering. All date references used `uploaded_at` regardless of whether a `report_date` was available, and contradictions lacked temporal context to help the LLM (and users) understand which value is more recent.

## Changes

### `backend/chat/structured_retrieval.py`
1. **`_extraction_to_dict`**: Uses `doc.report_date or doc.uploaded_at` as the effective date instead of just `doc.uploaded_at`. Adds `is_approximate_date: bool` field (True when falling back to uploaded_at, False when report_date is available).
2. **`_contradiction_to_dict`**: Now computes and includes a `temporal_context` field that notes which contradicting value is more recent based on effective document dates.
3. **Query ordering**: FACT_LOOKUP, CROSS_DOC, and TEMPORAL query types now sort by `func.coalesce(Document.report_date, Document.uploaded_at).desc()` (nulls-last via coalesce) so the most recent documents appear first.

### `backend/chat/engine.py`
1. **`_RESPONSE_SYSTEM` prompt**: Added rules 7 (prefer most recent document's value, note date) and 8 (include contradiction notes referencing dates).
2. **`_format_structured_context`**: Includes document date in the formatted output with appropriate prefix -- `(dated: YYYY-MM-DD)` when report_date is available, `(uploaded: YYYY-MM-DD)` when falling back to uploaded_at. Also appends temporal_context to contradiction lines.

### `tests/test_chat.py`
Added 5 new tests:
- `test_is_approximate_date_true_when_no_report_date`
- `test_is_approximate_date_false_when_report_date_set`
- `test_temporal_sorting_prefers_report_date` (verifies coalesce-based ordering)
- `test_contradiction_temporal_context`
- `test_result_structure` updated to assert new fields

All 155 tests pass.
