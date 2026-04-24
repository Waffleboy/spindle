# Investor Report Intelligence Reframe — Implementation Summary

## Date: 2026-04-24

## Problem
Reframe the app from a taxonomy infrastructure tool to a workflow-first "Investor Report Intelligence" product — drop in analyst reports, extract facts, resolve entities, build timelines, flag contradictions, and answer questions from the most recent, consistent data.

## What Was Implemented

### Phase 4: Document Date Extraction (P0)
- Added `report_date` (nullable DateTime) to `Document` model
- Modified `step1_doc_type.py` to extract report dates via LLM JSON response alongside doc type detection
- Fallback to `uploaded_at` when LLM can't extract a date
- `step5_contradictions.py` now populates `doc_a_date`/`doc_b_date` from `report_date`
- Frontend document panel shows dates with "uploaded" prefix for approximate dates, sorted by report_date

### Phase 1: Insights Dashboard (P0)
- `GET /api/insights` endpoint aggregating contradictions, entity reviews, and staleness data
- `insights-dashboard.tsx` with summary banner, contradiction cards (with "more recent" badges), entity review items, staleness indicators
- CSV export of all insights data
- Tab structure updated to Insights | Taxonomy | Templates, with auto-switch to Insights after processing

### Phase 3: Temporally-Aware Chat (P1)
- `structured_retrieval.py` uses `coalesce(report_date, uploaded_at)` for temporal ordering
- Contradiction results include `temporal_context` identifying which value is more recent
- `engine.py` system prompt updated with rules 7+8 for temporal preference and contradiction notes
- Chat panel renders contradiction callout blocks with visual distinction

### Phase 2: Change Feed (P1)
- `GET /api/entities/{id}/timeline` endpoint with server-side diffs between consecutive documents
- `change-feed.tsx` with entity selector, vertical timeline, color-coded diffs (green=new, amber=updated, red=contradiction)
- Accessible from insights dashboard via entity click

### Phase 5: Product Reframe (P2)
- Header subtitle: "Intelligence from your reports"
- Updated empty states with workflow-oriented messaging
- CSV export button on insights dashboard

## Post-Review Fixes
- Fixed CSV export escaping (commas, quotes, newlines)
- Fixed N+1 query in insights entity reviews (single grouped COUNT query)
- Fixed N+1 query in GET /api/extractions (batch document lookup)

## Files Modified
### Backend
- `backend/models.py`, `backend/api/schemas.py`, `backend/api/routes.py`
- `backend/pipeline/step1_doc_type.py`, `backend/pipeline/step5_contradictions.py`
- `backend/chat/engine.py`, `backend/chat/structured_retrieval.py`

### Frontend
- `frontend/src/App.tsx`, `frontend/src/lib/types.ts`, `frontend/src/lib/api.ts`
- `frontend/src/components/insights-dashboard.tsx` (new)
- `frontend/src/components/change-feed.tsx` (new)
- `frontend/src/components/document-panel.tsx`, `frontend/src/components/taxonomy-panel.tsx`
- `frontend/src/components/chat-panel.tsx`
