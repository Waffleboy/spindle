# Fix: Chat Entity Retrieval Returns Empty Context

## Problem
When asking the chat "what happened to Starflare Corp?", the response said it had no information, despite the pipeline having detected contradictions and extractions mentioning Starflare Corp.

## Root Causes

### 1. Entity matching had reversed substring checks
The code checked `query_lower in entity.canonical_name.lower()` — i.e., whether `"what happened to starflare corp?"` is a substring of `"starflare corp"`, which is always false.

**Fix:** Changed to bidirectional matching: `canon in query_lower or query_lower in canon`.

### 2. Full query string used for keyword search
FACT_LOOKUP and ENTITY_QUERY fallback paths searched extraction values using `contains("what happened to starflare corp?")`. No extraction value contains that exact sentence.

**Fix:** Added `_extract_keywords()` that strips stop words from the query and searches each keyword individually with OR logic. Now searching for "starflare" and "corp" individually, which match extraction values.

### 3. Contradiction retrieval missed entity names
`_get_contradictions()` only matched on dimension names and values, never on the linked entity. Entity-focused queries missed relevant contradictions.

**Fix:** When a contradiction has an `entity_id`, look up the entity and check if its canonical name or aliases appear in the query.

### 4. `ENABLE_EMBEDDINGS` missing from `.env.example`
The setting was undocumented. Added to `.env.example` under a renamed "Chunking & Embedding" section with description of fallback behavior.

## Files Changed
- `backend/chat/structured_retrieval.py` — Keyword extraction, bidirectional entity matching, entity-aware contradiction search
- `.env.example` — Document `ENABLE_EMBEDDINGS` setting
