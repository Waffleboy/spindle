# Fix: Empty Extraction Values + Broken Column Tooltips

## Problem
1. **Empty cells in taxonomy grid:** After pipeline extraction, all grid cells showed no values — only column headers were visible.
2. **Column tooltip shows `?` but no explanation:** Hovering the Info icon on column headers showed a question mark but the tooltip description never appeared.

## Root Cause Analysis

### Bug 1: Empty extraction values
In `backend/pipeline/orchestrator.py`, during Step 3 (extraction), the orchestrator re-ingests documents by calling `ingester.ingest(doc_record.storage_path, ...)`. However, `doc_record.storage_path` is a relative string (e.g. `"data/originals/abc_report.csv"`), while `BaseIngester.ingest()` expects a `Path` object with `.read_bytes()`. The string lacked this method, causing an `AttributeError`.

A broad `except Exception` on line 93 silently swallowed this error and created a fallback `IngestedDocument(text="")`. The LLM then received empty content and returned `null` for every dimension, which step 3 stored as empty strings. All 155 extraction records had `raw_value = ""`.

### Bug 2: Tooltip not showing description
The `TooltipProvider` in `App.tsx` used Radix's default `delayDuration` of 700ms. Users hover briefly over the Info icon and move on before the tooltip renders, making it seem broken.

## Fix

### Bug 1: `backend/pipeline/orchestrator.py`
- Removed the silent `except` fallback that masked ingestion failures
- Convert `storage_path` string to a `Path` object, resolving relative paths against `cwd`
- If ingestion fails now, the error propagates and is properly reported to the user

### Bug 2: `frontend/src/App.tsx`
- Set `delayDuration={200}` on `TooltipProvider` so tooltips appear after 200ms instead of 700ms

## Files Changed
- `backend/pipeline/orchestrator.py` — Fixed file path handling in re-ingestion loop
- `frontend/src/App.tsx` — Reduced tooltip delay
