# Task: Update Architecture Documentation with Diagrams and Pipeline Explanation

## What was asked
Update `agents/architecture.md` with a visual diagram of the app flow and a detailed explanation of the data pipeline (doc type detection → taxonomy → extraction → entities → contradictions).

## What was done
Rewrote `agents/architecture.md` with:
1. **Full application flow diagram** — ASCII art showing Frontend (3-panel layout + top bar) → REST API → Backend (routes, ingestion, pipeline, chat) → SQLite database
2. **Detailed pipeline flow diagram** — Step-by-step ASCII art showing each of the 5 pipeline stages with inputs, actions, LLM tasks, and DB outputs
3. **Pipeline summary table** — Quick reference of what each step does
4. **Chat/query system diagram** — Shows the hybrid retrieval flow: classification → parallel structured + semantic search → LLM response → citations
5. **Database schema relationship diagram** — Shows how tables connect
6. Retained and expanded all existing sections (backend structure, frontend structure, API endpoints, running instructions)
