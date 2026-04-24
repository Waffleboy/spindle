# GET /api/insights Endpoint

## Task
Build a new `GET /api/insights` endpoint that aggregates contradictions, entity review items, and staleness data into a single response for an investor-report-intelligence dashboard view.

## What was done

### Schema additions (`backend/api/schemas.py`)
Added 4 new Pydantic models:
- `InsightContradiction` — enriched contradiction with entity name, document filenames, values, dates, and `newer_doc` ("a"/"b"/None)
- `InsightEntityReview` — entity with its review count and aliases
- `InsightStaleness` — pairs of documents where values differ for the same (entity, dimension) without a contradiction
- `InsightsResponse` — top-level response with totals and lists of the above

### Endpoint implementation (`backend/api/routes.py`)
Added `GET /api/insights` with three aggregation sections:

1. **Contradictions**: Fetches all contradictions, batch-loads referenced documents and entities, computes `newer_doc` by comparing `report_date` (falling back to `uploaded_at`).

2. **Entities needing review**: Queries all entities, counts `EntityResolution` records with `needs_review=True`, and includes only entities with count > 0.

3. **Staleness detection**: Groups all extractions by `(entity_id, dimension_name)`, skips groups that have contradictions, sorts by document effective date, and emits staleness items for consecutive document pairs with differing values.

### Performance considerations
- Batch-fetches documents and entities to avoid N+1 queries
- Pre-builds lookup dicts (docs_by_id, entities_by_id, resolution_map, contradiction_keys) for O(1) lookups
- Uses `defaultdict` for grouping extractions

### Tests (`tests/test_api.py`)
Added 7 new tests in `TestInsights`:
- Empty database returns zeroed response
- Contradictions returned with correct fields and `newer_doc` computed
- Entities needing review are listed correctly
- Staleness items detected for differing values without contradictions
- No staleness for contradicted dimensions (revenue)
- No staleness for same-value dimensions (ceo)
- Total fields match list lengths

All 55 tests pass.
