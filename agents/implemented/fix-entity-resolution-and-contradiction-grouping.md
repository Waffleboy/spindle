# Fix Entity Resolution and Contradiction Grouping

## Problem

Two structural bugs in the pipeline caused:
1. **Frivolous contradictions across companies** — e.g., GreenWave Solar's report date being compared to Apex Precision Engineering's report date
2. **Poor entity resolution for name variants** — e.g., "Tan Kim Bock" vs "Bock Kim Tan" not being resolved because the LLM lacked document context

## Root Causes

### Step 5 (Contradiction Detection) — `backend/pipeline/step5_contradictions.py`

The grouping logic had two flaws:

1. **Non-entity dimensions grouped under `(None, dimension_name)`**: Scalar dimensions like REVENUE, STAFF_COUNT, report dates were grouped across ALL companies since they had no entity association. This meant Company A's revenue was being compared to Company B's revenue.

2. **Entity dimensions mapped to ALL entities per document**: If a document had entity resolutions for GreenWave Solar (company), Tan Kim Bock (person), and Rachel Ong (person), then every extraction in that document was duplicated into groups for all three entities, creating noisy cross-entity comparisons.

### Step 4 (Entity Resolution) — `backend/pipeline/step4_entities.py`

Entity mentions were shown to the LLM with only opaque UUIDs as document identifiers. The LLM couldn't see that "Tan Kim Bock" and "Bock Kim Tan" both appeared in GreenWave Solar documents, making it much harder to resolve Asian name variants where surname/given-name order differs.

## Fix

### Step 5 — Primary Entity Grouping

- Introduced `_build_primary_entity_map()` that assigns each document to ONE primary entity, preferring company-type entities over person-type
- Each extraction is grouped exactly once under its document's primary company entity
- Documents without entity resolution are excluded from contradiction detection entirely — without knowing which company a document belongs to, cross-doc comparison is meaningless
- Added document filenames and dates to the LLM prompt for better temporal judgment

### Step 4 — Richer Context for Entity Resolution

- Added document filenames to the LLM prompt instead of opaque UUIDs
- Added co-occurring entities per document so the LLM can see "Tan Kim Bock appears alongside GreenWave Solar, Rachel Ong"
- Enhanced the system prompt with specific guidance for Asian name variants (surname/given-name swaps, Chinese romanization variants, Malay name abbreviations)

## New Tests

- `test_skips_docs_without_entity_resolution` — verifies documents without entity resolution are not compared
- `test_cross_company_values_not_compared` — verifies Company A's values are never compared to Company B's
- `test_primary_entity_prefers_company_type` — verifies company entities take priority over person entities for grouping
