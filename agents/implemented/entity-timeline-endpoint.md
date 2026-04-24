# Entity Timeline Endpoint

## Task
Build a `GET /api/entities/{id}/timeline` endpoint that returns chronologically ordered extractions for a given entity across all documents with computed diffs, powering the "Change Feed" feature.

## What Was Done

### Response Models (schemas.py)
Added four new Pydantic models:
- `TimelineDimensionValue` - dimension name, value, confidence, source_pages
- `TimelineDiff` - dimension_name, old_value, new_value, change_type ("new" | "updated" | "contradiction")
- `TimelineNode` - per-document node with dimensions and diffs_from_previous
- `EntityTimelineResponse` - top-level response with entity info + timeline list

### Endpoint Logic (routes.py)
1. Finds entity by ID (404 if not found)
2. Queries all EntityResolution records for the entity to get document IDs
3. Returns empty timeline if no resolutions exist
4. Fetches all related documents and sorts chronologically by `report_date` (falling back to `uploaded_at`)
5. Pre-fetches all extractions and contradictions in bulk queries (not N+1)
6. Builds timeline nodes with diff computation:
   - `"new"` - dimension not present in previous document
   - `"updated"` - dimension value changed
   - `"contradiction"` - unresolved Contradiction record exists for this entity/dimension between the two docs
7. Sets `is_approximate_date = True` when falling back to `uploaded_at`
8. Uses `resolved_value` when available, otherwise `raw_value`

### Tests (test_api.py)
Added 11 tests in `TestEntityTimeline`:
- 404 for missing entity
- Basic response structure
- Chronological ordering
- Node field presence
- Dimension listing per node
- First node has no diffs
- Updated diff detection
- Approximate date fallback
- Contradiction diff type
- New dimension diff type
- Empty timeline for entity with no resolutions
- Resolved value preference over raw value

## Files Modified
- `backend/api/schemas.py` - Added 4 response models
- `backend/api/routes.py` - Added endpoint + schema imports
- `tests/test_api.py` - Added 11 tests, updated route registration test
- `agents/architecture.md` - Added endpoint to API listing
