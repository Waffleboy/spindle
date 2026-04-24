# Contradiction Reasoning Context & False Positive Fix

## Problem
1. Contradiction cards in the Insights dashboard showed conflicting values but no explanation of WHY the system flagged them, making it impossible for users to verify if the contradiction is genuine.
2. INVESTMENT_AMOUNT, CONTACT_DATE, COMPANY_FOUNDED_YEAR etc. were flagged as contradictory across different entities (e.g., Sarah Wong $2M vs William Liew $1.4M) — these are different people/companies with their own values, not contradictions.

## Root Cause
The grouping logic in `step5_contradictions.py` mapped each document to ALL entities it was associated with (via `doc_entity_map[doc_id] -> set of entity_ids`). When CSV rows were split into separate documents, each row-document could get loosely linked to multiple entities. This caused values from completely different entities to end up in the same comparison group, generating false contradictions.

Additionally, documents without any entity resolution fell into a `(None, dim_name)` bucket that compared all unresolved documents against each other.

## Changes

### Backend — Grouping Fix (root cause)
- **`backend/pipeline/step5_contradictions.py`**: 
  - Each document now maps to at most ONE entity (highest-confidence EntityResolution) instead of all associated entities.
  - Groups without an entity (`entity_id=None`) are skipped entirely — without entity context we cannot determine whether values from different docs are truly contradictory.
  - Scoped the EntityResolution query to only docs relevant to the current taxonomy.

### Backend — Reason field
- **`backend/models.py`**: Added `reason` column (Text, nullable) to the `Contradiction` model.
- **`backend/database.py`**: Added migration to add `reason` column to existing `contradictions` table.
- **`backend/pipeline/step5_contradictions.py`**: 
  - Updated LLM prompt to require a `reason` field explaining why each flagged item is a genuine contradiction.
  - Added explicit exclusion rule for per-entity scalar values.
  - Stores the LLM-provided reason in the Contradiction record.
- **`backend/api/schemas.py`**: Added `reason` field to both `ContradictionResponse` and `InsightContradiction` schemas.
- **`backend/api/routes.py`**: Passes `reason` through in the insights endpoint response.

### Frontend
- **`frontend/src/lib/types.ts`**: Added `reason` field to `ContradictionType` and `InsightContradiction` interfaces.
- **`frontend/src/components/contradiction-popover.tsx`**: Displays the reason in a muted box between the temporal indicator and status badge.
- **`frontend/src/components/insights-dashboard.tsx`**: 
  - ContradictionCard now shows the reason text below the value comparison.
  - CSV export includes the Reason column.

### Tests
- **`tests/test_pipeline.py`**: Updated `test_detect_contradictions` and `test_no_contradictions_found` to create Entity + EntityResolution records, matching the new requirement that contradiction detection only works within entity-grouped documents.
