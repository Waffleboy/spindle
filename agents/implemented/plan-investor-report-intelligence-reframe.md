# Plan: Reframe to "Investor Report Intelligence"

## Problem Statement

The image specifies a workflow-first product: **"Investor Report Intelligence"** — drop in 5-10 analyst reports about the same company over time, and the system extracts key facts, resolves entities, builds a timeline, flags contradictions, and lets you ask questions answered from the most recent, consistent data.

**The most compelling framing: the output is answers and alerts, not a table.**

### What's currently built (and working)
- Document upload + 5-step pipeline (type detection, taxonomy generation, extraction, entity resolution, contradiction detection)
- Extraction grid (documents × dimensions) with contradiction/entity highlighting
- Chat with hybrid RAG (structured + semantic retrieval)
- Taxonomy templates
- Real-time pipeline progress

### What the image actually wants (the gap)

| Feature | Image says | Current state | Gap |
|---------|-----------|---------------|-----|
| **Contradiction/staleness dashboard** | Primary view: "these 3 facts conflict across your documents" | Contradictions are highlighted cells buried in extraction grid | Need a dedicated, prominent contradiction dashboard |
| **Temporal knowledge base** | "This knows that August supersedes March" — answers grounded in most recent data | Chat RAG treats all chunks equally, no temporal preference | Chat needs temporal awareness: prefer recent docs, note when answer contradicts older data |
| **Change feed** | "Here's what changed about Entity X across your last 5 documents" — a living diff | Does not exist | New feature: entity-centric change timeline |
| **Answer-first UX** | User sees: "You asked about Company X's revenue. Here's the answer, sourced from August report. Note: this contradicts what was stated in the June report." | Chat doesn't proactively surface contradictions in answers | Chat response format needs contradiction annotations |
| **Product framing** | "Investor Report Intelligence" — a workflow a fund analyst would actually use | "Taxonomy Discovery Engine" / "Spindle" — infrastructure pitch | Rebrand header, empty states, onboarding copy |
| **Timeline** | "Builds a timeline" | No temporal visualization | Timeline view showing fact evolution over time per entity |

---

## Implementation Plan

### Phase 1: Contradiction & Insights Dashboard (PRIMARY VIEW)

**Goal:** Make contradictions and alerts the first thing the user sees after processing — not buried in a grid.

#### 1.1 New component: `insights-dashboard.tsx`
- Replace "Taxonomy" as the default center tab after processing completes
- Three sections:
  1. **Alerts banner** — count of contradictions, entities needing review, with severity badges
  2. **Contradiction cards** — each card shows:
     - Dimension name + entity name
     - Doc A value (with doc name + date) vs Doc B value (with doc name + date)
     - "Which is more recent?" indicator
     - Resolution action buttons (accept A / accept B / flag for review)
  3. **Staleness indicators** — dimensions where the most recent document overrides an older one (not a contradiction, just a temporal update)

#### 1.2 Backend: `GET /api/insights` endpoint
- Aggregates contradictions, entity review items, and staleness data into a single response
- Includes temporal context: which doc is newer for each contradiction
- Requires document dates — may need to extract `report_date` as a standard dimension in Step 2

#### 1.3 Update Tab structure
- Tab order: **Insights** (first) | **Taxonomy** | **Templates**
- Insights is the leftmost tab and auto-selected after processing completes
- User can freely switch between all three tabs

---

### Phase 2: Change Feed (Entity Timeline)

**Goal:** "Here's what changed about Entity X across your last 5 documents"

#### 2.1 New component: `change-feed.tsx`
- Entity selector dropdown (from resolved entities)
- For the selected entity, shows a vertical timeline:
  - Each node = a document (ordered by date)
  - Each node shows: what dimensions were extracted for this entity in this doc
  - Diff highlighting: what changed vs. the previous document
  - Color coding: green = new info, yellow = updated value, red = contradiction

#### 2.2 Backend: `GET /api/entities/{id}/timeline` endpoint
- Returns chronologically ordered extractions for a given entity across all documents
- Computes diffs between consecutive documents
- Includes contradiction references where applicable

#### 2.3 Add to Tab structure or as a slide-over panel
- Could be a sub-view within Insights dashboard (click an entity → see its timeline)
- Or a dedicated tab if there are many entities

---

### Phase 3: Temporally-Aware Chat

**Goal:** Chat answers should prefer the most recent data and proactively note contradictions.

#### 3.1 Backend: Enhance chat engine (`backend/chat/engine.py`)
- **Temporal ranking:** When multiple extractions exist for the same dimension, prefer the one from the most recent document
- **Contradiction annotations:** When the answer references a fact that has a known contradiction, append a note: "Note: this value ($4.2M from the August report) contradicts $3.9M stated in the July report"
- **Source dating:** Include document dates in citations, not just filenames

#### 3.2 Backend: Enhance structured retrieval (`backend/chat/structured_retrieval.py`)
- For FACT_LOOKUP and TEMPORAL queries, sort by document date descending
- Include contradiction context when returning extraction results
- Add a `temporal_context` field to retrieval results

#### 3.3 Frontend: Enhanced chat message rendering
- Citation badges show document date alongside filename
- Contradiction warnings rendered as a distinct callout block within the chat message (not just text)
- "Most recent" badge on the source citation when there are multiple docs

---

### Phase 4: Document Date Extraction

**Goal:** The entire temporal intelligence depends on knowing when each document was authored/published.

#### 4.1 Backend: Add `report_date` to Step 1 or Step 3
- During doc type detection or extraction, also extract the document's date/period
- Store as `Document.report_date` (new column)
- Fall back to file modification date or upload date if not extractable

#### 4.2 Database migration
- Add `report_date` column to Document table (nullable DATE)
- Backfill from existing extractions if a date-type dimension was already discovered

#### 4.3 Frontend: Show dates in document list
- Document panel shows report date next to filename
- Documents ordered by date (most recent first)

---

### Phase 5: Product Reframe & UX Polish

**Goal:** Rebrand from infrastructure tool to workflow tool.

#### 5.1 Branding
- Header: "Spindle" subtitle changes from "Structure from chaos" → something like "Intelligence from your reports"
- Empty state messaging: guides user through the workflow ("Drop your analyst reports here → we'll find the facts, flag the conflicts, and answer your questions")

#### 5.2 Onboarding flow
- First-time empty state in center panel should explain the value prop, not just "No Taxonomy Discovered Yet"
- After processing, auto-switch to Insights dashboard instead of extraction grid

#### 5.3 Export
- Add "Export" button to insights dashboard
- CSV export of: contradictions list, entity timeline, clean extraction table

---

## Execution Order & Priority

| Priority | Phase | Effort | Why this order |
|----------|-------|--------|----------------|
| **P0** | Phase 4: Document Date Extraction | Small | Everything temporal depends on this — do it first |
| **P0** | Phase 1: Insights Dashboard | Medium | The core ask: "the output is answers and alerts, not a table" |
| **P1** | Phase 3: Temporally-Aware Chat | Medium | Second most important: chat that knows August supersedes March |
| **P1** | Phase 2: Change Feed | Medium | The "so what" — living diff per entity |
| **P2** | Phase 5: Product Reframe | Small | Polish pass after features are built |

**Total estimated effort:** ~2-3 focused sessions

---

## Key Technical Decisions

1. **Document dates:** Extract via LLM as part of Step 1 (doc type detection) — cheapest place to add it since we already send text samples. Store as ISO date string on Document model. **Fallback:** If LLM can't extract a date, store `NULL` and fall back to `created_at` (upload timestamp) for temporal ordering. Label fallback dates as "uploaded Apr 24" in the UI so the user knows the ordering is approximate.

2. **Insights endpoint:** Single aggregate endpoint rather than client-side assembly — keeps frontend simple and allows backend to compute temporal ordering/staleness efficiently.

3. **Chat temporal awareness:** Modify the system prompt in `engine.py` to instruct the LLM to prefer recent sources and flag contradictions. Also pre-sort structured retrieval results by date.

4. **Change feed diffs:** Computed server-side to avoid shipping all historical extractions to the frontend. Backend diffs consecutive docs and returns a pre-computed timeline.

5. **Tab addition:** Insights is added as a new tab alongside Taxonomy and Templates. Auto-selected after processing, but all three tabs remain fully accessible. No existing tabs are removed or renamed.
