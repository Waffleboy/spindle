# Architecture Documentation Full Rewrite

## Task
The architecture.md was outdated and incomplete after many features were added. User requested a full codebase scan and documentation update.

## What Was Done
- Deployed 3 parallel agents to scan: (1) all frontend components, (2) all backend code, (3) all tests and agent implementation docs
- Synthesized findings into a complete rewrite of `agents/architecture.md`

## Key Changes to architecture.md
- **Reframed**: From "Taxonomy Discovery Engine" to "Spindle" — investor report intelligence platform
- **Added "How the App Works"**: End-to-end user journey walkthrough (6 steps from landing page to insights)
- **Updated application flow diagram**: Now shows all three center tabs (Insights/Taxonomy/Templates), context-sensitive sidebar, change feed overlay
- **Updated pipeline docs**: Added two-phase extraction detail (parallel fetch → sequential write), nested response unwrapping, race condition fix (pre-seeded status)
- **Added Insights Engine section**: Documents the multi-phase aggregation (contradictions, entity reviews, staleness detection)
- **Updated chat system docs**: Added temporal awareness details, date prefixing, system prompt rules for recency preference
- **Expanded frontend section**: Every component documented with purpose, key features, and interactions. Added UI primitives, library files, theming system.
- **Updated API table**: From 13 to 20 endpoints (added DELETE documents, timeline, templates CRUD, insights)
- **Updated database schema**: Added TaxonomyTemplate table, doc dates on Contradiction, all column types
- **Added configuration table**: All Settings fields with defaults
- **Added testing section**: 148+ tests across 4 files with coverage breakdown
- **Updated running section**: Added start_local.sh convenience script
