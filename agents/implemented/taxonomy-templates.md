# Task: Taxonomy Templates — Configurable Fixed Dimensions per Document Type

## What was asked
Add a way to configure fixed taxonomy dimensions for certain document types. When the pipeline runs, an LLM call determines which configured templates match the detected documents, and those template dimensions are injected as must-includes into the taxonomy generation prompt (on top of whatever the LLM infers).

## What was done

### Backend
- **New model** `TaxonomyTemplate` in `backend/models.py` — stores label, description, and dimensions JSON
- **New schemas** in `backend/api/schemas.py` — `TaxonomyTemplateCreate`, `TaxonomyTemplateUpdate`, `TaxonomyTemplateResponse`
- **CRUD routes** in `backend/api/routes.py` — `GET/POST /api/taxonomy-templates`, `PUT/DELETE /api/taxonomy-templates/{id}`
- **Template matching** `backend/pipeline/template_matching.py` — LLM call that takes doc_type + sample text + all templates, returns which ones are relevant
- **Modified Step 2** `backend/pipeline/step2_taxonomy.py` — accepts `matched_templates` param, injects their dimensions as must-includes in the prompt
- **Modified orchestrator** `backend/pipeline/orchestrator.py` — calls `match_templates()` between Step 1 and Step 2

### Frontend
- **New type** `TaxonomyTemplateType` in `frontend/src/lib/types.ts`
- **API client** functions in `frontend/src/lib/api.ts` — `getTaxonomyTemplates`, `createTaxonomyTemplate`, `updateTaxonomyTemplate`, `deleteTaxonomyTemplate`
- **Templates panel** `frontend/src/components/templates-panel.tsx` — full CRUD UI with dimension editor (name, description, type selector)
- **Tab switcher** in `frontend/src/App.tsx` — center panel now has Taxonomy / Templates tabs

### Tests
- Added 8 template CRUD tests to `tests/test_api.py`
- Updated orchestrator tests in `tests/test_pipeline.py` to mock the new `match_templates` call
- Updated route inclusion test with new template routes
- All 132 tests pass
