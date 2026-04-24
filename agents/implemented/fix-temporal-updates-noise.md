# Fix: Temporal Updates Showing Noise Instead of Fact Differences

## Problem
The Temporal Updates section in the Insights dashboard was showing trivial, meaningless changes like `REPORT_ID` going from "Report 1" to "Report 2" across consecutive documents. These are per-document identifiers, not evolving facts. The user expected to see actual fact differences (e.g., "investment amount changed from $3M to $10M").

## Root Cause
The staleness detection in `GET /api/insights` (`backend/api/routes.py`) compared ALL dimension values between consecutive documents grouped by `(entity_id, dimension_name)`. Two issues:

1. **Entity/entity_list dimensions** (like company names) were included in staleness detection, but these are references/identifiers, not facts that evolve.
2. **Per-document identifier dimensions** (like `REPORT_ID`, `REPORT_TITLE`) have unique values per document by design. When grouped with `entity_id=None`, every consecutive pair showed as "changed."
3. **Non-entity dimensions** with `entity_id=None` lumped ALL documents together, comparing unrelated documents' values.

## Fix (backend/api/routes.py)
Three-layer filtering in the staleness detection:

1. **Skip entity-reference dimensions**: Dimensions with `expected_type` of `entity` or `entity_list` are excluded from staleness — they are identifiers/references, not evolving facts.

2. **Detect per-document identifier dimensions**: Text-type dimensions where every document has a unique value (>= 3 docs, all unique values) are identified as document-level identifiers and excluded. Numeric, currency, and date types are exempt from this check since they naturally evolve over time.

3. **Entity-aware re-grouping for non-entity dimensions**: When `entity_id=None`, non-entity dimensions are re-grouped by the entities each document is associated with (via EntityResolution). This ensures we only compare facts about the same subject entity across time, rather than comparing unrelated documents.

## Test Changes (tests/test_api.py)
- Added entity resolution for doc-3 in the insights test seed data to support entity-aware grouping.
- Added `test_insights_no_staleness_for_identifier_dimensions` to verify that per-document identifier fields (like `report_id` with unique values per doc) do NOT produce temporal updates.
