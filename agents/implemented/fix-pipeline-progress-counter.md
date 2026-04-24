# Fix: Pipeline Progress "0/0 docs" Counter

## Problem
The pipeline progress bar in the UI always showed "0/0 docs" even after documents were uploaded and processed. The header counter ("5/5 processed") worked correctly, but the pipeline progress counter did not.

## Root Cause
In `backend/api/routes.py`, the `GET /api/status` endpoint had `total_documents` and `processed_documents` hardcoded to `0` (lines 185-186) instead of querying actual document counts.

## Fix
1. Added `document_ids` to the pipeline status seed entry created in `POST /api/process`, so the status endpoint knows which documents belong to the current pipeline run.
2. Added a `_get_pipeline_document_ids()` helper that extracts document IDs from the pipeline status dict.
3. Updated `GET /api/status` to accept a `db` session dependency and query the `Document` table for actual counts:
   - `total_documents`: count of document IDs passed to the pipeline
   - `processed_documents`: count of those documents where `processed_at IS NOT NULL`

## Files Changed
- `backend/api/routes.py`
