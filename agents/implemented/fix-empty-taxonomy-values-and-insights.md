# Fix: Empty Taxonomy Values, Stale Insights, and Extraction Concurrency

## Problem

1. **Empty taxonomy grid values**: After processing documents, the taxonomy grid showed document names and dimension headers but all value cells were empty. All 230 extractions in the database had empty `raw_value` with default 0.5 confidence.

2. **Empty insights dashboard**: After processing completed, the Insights tab showed "No insights yet" even though contradictions and entity resolutions were generated.

3. **Extraction step stuck/slow**: Step 3 fires all LLM + embedding calls simultaneously with no concurrency limit, overwhelming rate-limited API gateways and causing long stalls.

## Root Causes and Fixes

### Bug 1: LLM Wraps Extraction Response in Outer Object

The LLM (called with `response_format: json_object`) sometimes wraps the extraction data in an outer object like `{"extractions": {"revenue": {...}, "ceo": {...}}}`. The code in `step3_extraction.py` did `extracted_data.get(dim_name)` directly on the top-level dict, which returned `None` for every dimension since the actual data was nested one level deeper.

Step 2 (taxonomy generation) already handled this pattern for arrays, but step 3 did not.

**Fix**: Added unwrapping logic in `fetch_extraction_data()` that detects when no top-level keys match any dimension name and looks one level deeper for a dict whose keys do match.

### Bug 2: InsightsDashboard Only Fetches Once

`InsightsDashboard` had a `useEffect([], [])` that fetched insights once on component mount. Since the component mounts before processing starts, it fetches empty data and never re-fetches after pipeline completion. `fetchAllData()` in App.tsx refreshed all other data types but insights was independently fetched by the dashboard component.

**Fix**: Added a `refreshKey` prop to `InsightsDashboard` and a `dataVersion` counter in `App.tsx` that increments after fetchAllData completes (on processing complete, clear all, delete document). The dashboard's useEffect now depends on `refreshKey` to trigger re-fetches.

### Bug 3: No Concurrency Control on API Calls

For 5 documents, `asyncio.gather` fired 10 concurrent API calls (5 LLM extractions + 5 embedding batches) simultaneously through the gateway. This overwhelms rate-limited APIs causing retries and long stalls.

**Fix**: Added an `asyncio.Semaphore(3)` in `step3_extraction.py` that gates both LLM and embedding calls, allowing at most 3 concurrent API requests. This prevents rate-limit thrashing while still parallelizing work.

## Files Changed

- `backend/pipeline/step3_extraction.py` - Added LLM response unwrapping, added API concurrency semaphore (limit 3)
- `frontend/src/App.tsx` - Added `dataVersion` state, pass as `refreshKey` to InsightsDashboard
- `frontend/src/components/insights-dashboard.tsx` - Accept `refreshKey` prop, use as useEffect dependency
- `tests/test_pipeline.py` - Added test for wrapped LLM response extraction
