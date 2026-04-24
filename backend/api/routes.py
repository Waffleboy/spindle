"""FastAPI API routes — all endpoints for the Taxonomy Discovery Engine."""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from collections import defaultdict

from backend.api.schemas import (
    ChatRequest,
    ChatResponse,
    ContradictionResponse,
    DocumentResponse,
    EntityResponse,
    EntityResolutionResponse,
    EntityTimelineResponse,
    EntityUpdateRequest,
    ExtractionResponse,
    InsightContradiction,
    InsightEntityReview,
    InsightStaleness,
    InsightsResponse,
    ProcessRequest,
    ProcessResponse,
    ResolutionUpdateRequest,
    StatusResponse,
    TaxonomyResponse,
    TaxonomyTemplateCreate,
    TaxonomyTemplateResponse,
    TaxonomyTemplateUpdate,
    TimelineDiff,
    TimelineDimensionValue,
    TimelineNode,
    UploadedFileInfo,
    UploadResponse,
)
from backend.chat.engine import chat
from backend.database import get_db
from backend.ingestion.service import store_and_ingest, store_and_ingest_csv_rows
from backend.models import (
    Contradiction,
    Document,
    Entity,
    EntityResolution,
    Extraction,
    TaxonomySchema,
    TaxonomyTemplate,
)
from backend.pipeline.orchestrator import pipeline_status

router = APIRouter(prefix="/api")

_SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv"}


# ---------------------------------------------------------------------------
# POST /api/upload
# ---------------------------------------------------------------------------


@router.post("/upload", response_model=UploadResponse)
async def upload_documents(
    files: list[UploadFile] = File(...),
    company_context: Optional[str] = Form(None),
    split_rows: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Upload one or more documents (.pdf, .docx, .doc, .xlsx, .xls, .csv).

    When split_rows is "true" and a CSV is uploaded, each row becomes a
    separate document.
    """
    uploaded: list[UploadedFileInfo] = []
    errors: list[str] = []
    should_split = split_rows and split_rows.lower() == "true"

    for file in files:
        filename = file.filename or "unknown"
        ext = ""
        dot_idx = filename.rfind(".")
        if dot_idx >= 0:
            ext = filename[dot_idx:].lower()

        if ext not in _SUPPORTED_EXTENSIONS:
            errors.append(
                f"Unsupported file type for '{filename}'. "
                f"Supported: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}"
            )
            continue

        content = await file.read()
        try:
            if should_split and ext == ".csv":
                pairs = store_and_ingest_csv_rows(filename, content)
                for doc, _ingested in pairs:
                    uploaded.append(UploadedFileInfo(id=doc.id, filename=doc.original_filename))
            else:
                doc, _ingested = store_and_ingest(filename, content)
                uploaded.append(UploadedFileInfo(id=doc.id, filename=doc.original_filename))
        except Exception as exc:
            errors.append(f"Failed to ingest '{filename}': {exc}")

    if not uploaded and errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    return UploadResponse(
        document_ids=[u.id for u in uploaded],
        message=f"Uploaded {len(uploaded)} document(s)",
        uploaded=uploaded,
    )


# ---------------------------------------------------------------------------
# POST /api/process
# ---------------------------------------------------------------------------


def _run_pipeline_in_thread(document_ids: list[str], company_context: str | None, corpus_id: str):
    """Run the async pipeline from a synchronous background task thread."""
    from backend.database import SessionLocal
    from backend.pipeline.orchestrator import run_pipeline

    db = SessionLocal()
    try:
        asyncio.run(run_pipeline(document_ids=document_ids, company_context=company_context, db=db))
    finally:
        db.close()


@router.post("/process", response_model=ProcessResponse)
async def trigger_pipeline(
    body: ProcessRequest,
    background_tasks: BackgroundTasks,
):
    """Trigger the processing pipeline as a background task."""
    if not body.document_ids:
        raise HTTPException(status_code=400, detail="document_ids must not be empty")

    corpus_id = str(uuid.uuid4())

    # Pre-seed pipeline_status so the first /status poll sees "running"
    # instead of "idle" (race between poll and background task startup).
    pipeline_status.clear()
    seed_id = f"pre-{corpus_id}"
    pipeline_status[seed_id] = {
        "run_id": seed_id,
        "step": 1,
        "total_steps": 5,
        "description": "Starting pipeline...",
        "percentage": 0,
        "status": "running",
        "error": None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "document_ids": body.document_ids,
    }

    background_tasks.add_task(
        _run_pipeline_in_thread,
        document_ids=body.document_ids,
        company_context=body.company_context,
        corpus_id=corpus_id,
    )
    return ProcessResponse(message="Processing started", corpus_id=corpus_id)


# ---------------------------------------------------------------------------
# GET /api/status
# ---------------------------------------------------------------------------


STEP_NAMES = [
    "type_detection",
    "taxonomy",
    "extraction",
    "entities",
    "contradictions",
]


def _get_pipeline_document_ids() -> list[str]:
    """Extract document IDs from any pipeline status entry that carries them."""
    for entry in reversed(list(pipeline_status.values())):
        ids = entry.get("document_ids")
        if ids:
            return ids
    return []


@router.get("/status", response_model=StatusResponse)
async def get_status(db: Session = Depends(get_db)):
    """Return the current pipeline processing status."""
    if not pipeline_status:
        return StatusResponse()

    latest = list(pipeline_status.values())[-1]
    step_num = latest.get("step", 0)
    status_str = latest.get("status", "idle")

    if status_str == "complete":
        status_str = "completed"

    steps_completed = STEP_NAMES[: max(0, step_num - 1)] if status_str == "running" else (
        STEP_NAMES[:step_num] if status_str == "completed" else []
    )
    current_step = STEP_NAMES[step_num - 1] if 0 < step_num <= 5 and status_str == "running" else None

    doc_ids = _get_pipeline_document_ids()
    total_documents = len(doc_ids)
    processed_documents = 0
    if doc_ids:
        processed_documents = (
            db.query(Document)
            .filter(Document.id.in_(doc_ids), Document.processed_at.isnot(None))
            .count()
        )

    return StatusResponse(
        status=status_str,
        current_step=current_step,
        steps_completed=steps_completed,
        total_documents=total_documents,
        processed_documents=processed_documents,
        error=latest.get("error"),
    )


# ---------------------------------------------------------------------------
# GET /api/documents
# ---------------------------------------------------------------------------


@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(db: Session = Depends(get_db)):
    """List all uploaded documents with metadata."""
    docs = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    return [DocumentResponse.model_validate(d) for d in docs]


@router.delete("/documents", status_code=204)
async def clear_all_documents(db: Session = Depends(get_db)):
    """Delete all documents and their associated data (extractions, entities, etc.)."""
    db.query(Contradiction).delete()
    db.query(EntityResolution).delete()
    db.query(Entity).delete()
    db.query(Extraction).delete()
    db.query(TaxonomySchema).delete()
    from backend.models import DocumentChunk
    db.query(DocumentChunk).delete()
    db.query(Document).delete()
    db.commit()


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(document_id: str, db: Session = Depends(get_db)):
    """Delete a single document and its associated extractions and chunks."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(doc)
    db.commit()


# ---------------------------------------------------------------------------
# GET /api/taxonomy
# ---------------------------------------------------------------------------


@router.get("/taxonomy")
async def get_taxonomy(db: Session = Depends(get_db)):
    """Return the most recent taxonomy schema, or null if none exists."""
    taxonomy = (
        db.query(TaxonomySchema)
        .order_by(TaxonomySchema.created_at.desc())
        .first()
    )
    if taxonomy is None:
        return None
    return TaxonomyResponse.model_validate(taxonomy)


# ---------------------------------------------------------------------------
# GET /api/extractions
# ---------------------------------------------------------------------------


@router.get("/extractions", response_model=list[ExtractionResponse])
async def get_extractions(
    document_id: Optional[str] = None,
    dimension_name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Return extraction records, optionally filtered by document_id or dimension_name."""
    query = db.query(Extraction)
    if document_id:
        query = query.filter(Extraction.document_id == document_id)
    if dimension_name:
        query = query.filter(Extraction.dimension_name == dimension_name)

    extractions = query.all()
    doc_ids = {ext.document_id for ext in extractions}
    docs_map = {d.id: d for d in db.query(Document).filter(Document.id.in_(doc_ids)).all()} if doc_ids else {}
    result = []
    for ext in extractions:
        doc = docs_map.get(ext.document_id)
        resp = ExtractionResponse.model_validate(ext)
        resp.document_filename = doc.original_filename if doc else None
        result.append(resp)
    return result


# ---------------------------------------------------------------------------
# GET /api/entities
# ---------------------------------------------------------------------------


@router.get("/entities", response_model=list[EntityResponse])
async def get_entities(db: Session = Depends(get_db)):
    """Return all entities with their review counts."""
    entities = db.query(Entity).all()
    result = []
    for ent in entities:
        needs_review_count = (
            db.query(EntityResolution)
            .filter(
                EntityResolution.entity_id == ent.id,
                EntityResolution.needs_review.is_(True),
            )
            .count()
        )
        resp = EntityResponse.model_validate(ent)
        resp.needs_review_count = needs_review_count
        result.append(resp)
    return result


# ---------------------------------------------------------------------------
# GET /api/contradictions
# ---------------------------------------------------------------------------


@router.get("/contradictions", response_model=list[ContradictionResponse])
async def get_contradictions(db: Session = Depends(get_db)):
    """Return all contradictions with document filenames."""
    contradictions = db.query(Contradiction).all()
    result = []
    for c in contradictions:
        doc_a = db.query(Document).filter(Document.id == c.doc_a_id).first()
        doc_b = db.query(Document).filter(Document.id == c.doc_b_id).first()
        resp = ContradictionResponse.model_validate(c)
        resp.doc_a_filename = doc_a.original_filename if doc_a else None
        resp.doc_b_filename = doc_b.original_filename if doc_b else None
        result.append(resp)
    return result


# ---------------------------------------------------------------------------
# PATCH /api/entities/{id}
# ---------------------------------------------------------------------------


@router.patch("/entities/{entity_id}", response_model=EntityResponse)
async def update_entity(
    entity_id: str,
    body: EntityUpdateRequest,
    db: Session = Depends(get_db),
):
    """Update an entity's canonical_name."""
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    entity.canonical_name = body.canonical_name
    db.commit()
    db.refresh(entity)

    needs_review_count = (
        db.query(EntityResolution)
        .filter(
            EntityResolution.entity_id == entity.id,
            EntityResolution.needs_review.is_(True),
        )
        .count()
    )
    resp = EntityResponse.model_validate(entity)
    resp.needs_review_count = needs_review_count
    return resp


# ---------------------------------------------------------------------------
# GET /api/entities/{id}/timeline
# ---------------------------------------------------------------------------


@router.get("/entities/{entity_id}/timeline", response_model=EntityTimelineResponse)
async def get_entity_timeline(
    entity_id: str,
    db: Session = Depends(get_db),
):
    """Return chronologically ordered extractions for an entity across all documents with computed diffs."""
    # 1. Find entity
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    # 2. Find all EntityResolution records for this entity -> get document IDs
    resolutions = (
        db.query(EntityResolution)
        .filter(EntityResolution.entity_id == entity_id)
        .all()
    )
    doc_ids = list({r.document_id for r in resolutions})

    if not doc_ids:
        return EntityTimelineResponse(
            entity_id=entity.id,
            entity_name=entity.canonical_name,
            entity_type=entity.entity_type,
            timeline=[],
        )

    # 3. Fetch documents and sort chronologically (oldest first)
    documents = (
        db.query(Document)
        .filter(Document.id.in_(doc_ids))
        .all()
    )
    documents.sort(key=lambda d: d.report_date or d.uploaded_at)

    # 4. Pre-fetch all extractions for these documents in one query
    all_extractions = (
        db.query(Extraction)
        .filter(Extraction.document_id.in_(doc_ids))
        .all()
    )
    # Group extractions by document_id
    extractions_by_doc: dict[str, list[Extraction]] = {}
    for ext in all_extractions:
        extractions_by_doc.setdefault(ext.document_id, []).append(ext)

    # 5. Pre-fetch unresolved contradictions involving these documents and this entity
    unresolved_contradictions = (
        db.query(Contradiction)
        .filter(
            Contradiction.resolution_status == "unresolved",
            Contradiction.entity_id == entity_id,
        )
        .all()
    )
    # Index contradictions by (doc_a_id, doc_b_id, dimension_name) for fast lookup
    contradiction_set: set[tuple[str, str, str]] = set()
    for c in unresolved_contradictions:
        contradiction_set.add((c.doc_a_id, c.doc_b_id, c.dimension_name))
        contradiction_set.add((c.doc_b_id, c.doc_a_id, c.dimension_name))

    # 6. Build timeline nodes with diffs
    timeline: list[TimelineNode] = []
    prev_dims: dict[str, str] = {}  # dimension_name -> value from previous doc

    for doc in documents:
        doc_extractions = extractions_by_doc.get(doc.id, [])
        is_approximate = doc.report_date is None
        doc_date = doc.report_date or doc.uploaded_at

        dimensions = [
            TimelineDimensionValue(
                dimension_name=ext.dimension_name,
                value=ext.resolved_value or ext.raw_value,
                confidence=ext.confidence,
                source_pages=ext.source_pages,
            )
            for ext in doc_extractions
        ]

        # Compute diffs from previous document
        current_dims: dict[str, str] = {
            ext.dimension_name: (ext.resolved_value or ext.raw_value)
            for ext in doc_extractions
        }

        diffs: list[TimelineDiff] = []
        prev_doc_id = timeline[-1].document_id if timeline else None

        for dim_name, new_value in current_dims.items():
            if dim_name not in prev_dims:
                # New dimension - only flag if there was a previous document
                if prev_doc_id is not None:
                    diffs.append(TimelineDiff(
                        dimension_name=dim_name,
                        old_value="",
                        new_value=new_value,
                        change_type="new",
                    ))
            elif prev_dims[dim_name] != new_value:
                # Value changed - check for contradiction
                has_contradiction = (
                    prev_doc_id is not None
                    and (prev_doc_id, doc.id, dim_name) in contradiction_set
                )
                diffs.append(TimelineDiff(
                    dimension_name=dim_name,
                    old_value=prev_dims[dim_name],
                    new_value=new_value,
                    change_type="contradiction" if has_contradiction else "updated",
                ))

        timeline.append(TimelineNode(
            document_id=doc.id,
            document_filename=doc.original_filename,
            document_date=doc_date,
            is_approximate_date=is_approximate,
            dimensions=dimensions,
            diffs_from_previous=diffs,
        ))

        prev_dims = current_dims

    return EntityTimelineResponse(
        entity_id=entity.id,
        entity_name=entity.canonical_name,
        entity_type=entity.entity_type,
        timeline=timeline,
    )


# ---------------------------------------------------------------------------
# PATCH /api/entity-resolutions/{id}
# ---------------------------------------------------------------------------


@router.patch("/entity-resolutions/{resolution_id}", response_model=EntityResolutionResponse)
async def update_resolution(
    resolution_id: str,
    body: ResolutionUpdateRequest,
    db: Session = Depends(get_db),
):
    """Approve or reject an entity resolution; optionally override the resolved value."""
    resolution = db.query(EntityResolution).filter(EntityResolution.id == resolution_id).first()
    if resolution is None:
        raise HTTPException(status_code=404, detail="Entity resolution not found")

    if body.approved:
        resolution.needs_review = False

    if body.override_value is not None:
        # Find the extraction linked to this document + entity's dimension and update resolved_value
        entity = db.query(Entity).filter(Entity.id == resolution.entity_id).first()
        if entity:
            extractions = (
                db.query(Extraction)
                .filter(
                    Extraction.document_id == resolution.document_id,
                    Extraction.raw_value == resolution.original_value,
                )
                .all()
            )
            for ext in extractions:
                ext.resolved_value = body.override_value

    db.commit()
    db.refresh(resolution)
    return EntityResolutionResponse.model_validate(resolution)


# ---------------------------------------------------------------------------
# Taxonomy Templates CRUD
# ---------------------------------------------------------------------------


@router.get("/taxonomy-templates", response_model=list[TaxonomyTemplateResponse])
async def list_taxonomy_templates(db: Session = Depends(get_db)):
    """List all taxonomy templates."""
    templates = db.query(TaxonomyTemplate).order_by(TaxonomyTemplate.created_at.desc()).all()
    return [TaxonomyTemplateResponse.model_validate(t) for t in templates]


@router.post("/taxonomy-templates", response_model=TaxonomyTemplateResponse, status_code=201)
async def create_taxonomy_template(
    body: TaxonomyTemplateCreate,
    db: Session = Depends(get_db),
):
    """Create a new taxonomy template."""
    template = TaxonomyTemplate(
        label=body.label,
        description=body.description,
        dimensions=[d.model_dump() for d in body.dimensions],
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return TaxonomyTemplateResponse.model_validate(template)


@router.put("/taxonomy-templates/{template_id}", response_model=TaxonomyTemplateResponse)
async def update_taxonomy_template(
    template_id: str,
    body: TaxonomyTemplateUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing taxonomy template."""
    template = db.query(TaxonomyTemplate).filter(TaxonomyTemplate.id == template_id).first()
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")

    if body.label is not None:
        template.label = body.label
    if body.description is not None:
        template.description = body.description
    if body.dimensions is not None:
        template.dimensions = [d.model_dump() for d in body.dimensions]

    db.commit()
    db.refresh(template)
    return TaxonomyTemplateResponse.model_validate(template)


@router.delete("/taxonomy-templates/{template_id}", status_code=204)
async def delete_taxonomy_template(
    template_id: str,
    db: Session = Depends(get_db),
):
    """Delete a taxonomy template."""
    template = db.query(TaxonomyTemplate).filter(TaxonomyTemplate.id == template_id).first()
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")

    db.delete(template)
    db.commit()


# ---------------------------------------------------------------------------
# GET /api/insights
# ---------------------------------------------------------------------------


def _doc_effective_date(doc: Document) -> datetime | None:
    """Return report_date if set, otherwise uploaded_at."""
    return doc.report_date or doc.uploaded_at


@router.get("/insights", response_model=InsightsResponse)
async def get_insights(db: Session = Depends(get_db)):
    """Aggregate contradictions, entity reviews, and staleness into a single dashboard response."""

    # ------------------------------------------------------------------
    # 1. Contradictions
    # ------------------------------------------------------------------
    contradictions_db = db.query(Contradiction).all()

    # Pre-fetch all referenced documents in one query to avoid N+1
    contra_doc_ids: set[str] = set()
    contra_entity_ids: set[str] = set()
    for c in contradictions_db:
        contra_doc_ids.update((c.doc_a_id, c.doc_b_id))
        if c.entity_id:
            contra_entity_ids.add(c.entity_id)

    docs_by_id: dict[str, Document] = {}
    if contra_doc_ids:
        for doc in db.query(Document).filter(Document.id.in_(contra_doc_ids)).all():
            docs_by_id[doc.id] = doc

    entities_by_id: dict[str, Entity] = {}
    if contra_entity_ids:
        for ent in db.query(Entity).filter(Entity.id.in_(contra_entity_ids)).all():
            entities_by_id[ent.id] = ent

    insight_contradictions: list[InsightContradiction] = []
    for c in contradictions_db:
        doc_a = docs_by_id.get(c.doc_a_id)
        doc_b = docs_by_id.get(c.doc_b_id)
        date_a = _doc_effective_date(doc_a) if doc_a else (c.doc_a_date or None)
        date_b = _doc_effective_date(doc_b) if doc_b else (c.doc_b_date or None)

        newer_doc: str | None = None
        if date_a is not None and date_b is not None:
            newer_doc = "a" if date_a > date_b else "b" if date_b > date_a else None

        entity = entities_by_id.get(c.entity_id) if c.entity_id else None

        insight_contradictions.append(InsightContradiction(
            id=c.id,
            dimension_name=c.dimension_name,
            entity_name=entity.canonical_name if entity else None,
            doc_a_id=c.doc_a_id,
            doc_a_filename=doc_a.original_filename if doc_a else "Unknown",
            doc_a_value=c.value_a,
            doc_a_date=date_a,
            doc_b_id=c.doc_b_id,
            doc_b_filename=doc_b.original_filename if doc_b else "Unknown",
            doc_b_value=c.value_b,
            doc_b_date=date_b,
            newer_doc=newer_doc,
            reason=c.reason,
            resolution_status=c.resolution_status,
        ))

    # ------------------------------------------------------------------
    # 2. Entities needing review
    # ------------------------------------------------------------------
    from sqlalchemy import func as sa_func
    review_counts = dict(
        db.query(EntityResolution.entity_id, sa_func.count())
        .filter(EntityResolution.needs_review.is_(True))
        .group_by(EntityResolution.entity_id)
        .all()
    )
    insight_entity_reviews: list[InsightEntityReview] = []
    if review_counts:
        review_entity_objs = db.query(Entity).filter(Entity.id.in_(review_counts.keys())).all()
        for ent in review_entity_objs:
            insight_entity_reviews.append(InsightEntityReview(
                entity_id=ent.id,
                canonical_name=ent.canonical_name,
                entity_type=ent.entity_type,
                review_count=review_counts[ent.id],
                aliases=ent.aliases or [],
            ))

    # ------------------------------------------------------------------
    # 3. Staleness detection
    # ------------------------------------------------------------------
    # Build a set of (entity_id or None, dimension_name) pairs that have contradictions
    contradiction_keys: set[tuple[str | None, str]] = set()
    for c in contradictions_db:
        contradiction_keys.add((c.entity_id, c.dimension_name))

    # Fetch all extractions with their documents
    all_extractions = db.query(Extraction).all()

    # Pre-fetch all documents needed for extractions
    extraction_doc_ids = {ext.document_id for ext in all_extractions}
    if extraction_doc_ids - set(docs_by_id.keys()):
        for doc in db.query(Document).filter(
            Document.id.in_(extraction_doc_ids - set(docs_by_id.keys()))
        ).all():
            docs_by_id[doc.id] = doc

    # Group extractions by (entity_id, dimension_name).
    # For entity-type extractions, resolve entity_id via EntityResolution.
    # For non-entity extractions, group by (None, dimension_name).

    # Pre-fetch entity resolutions for entity lookup
    all_resolutions = db.query(EntityResolution).all()
    # Map (document_id, original_value) -> entity_id
    resolution_map: dict[tuple[str, str], str] = {}
    for r in all_resolutions:
        resolution_map[(r.document_id, r.original_value)] = r.entity_id

    # Fetch all entities for name lookups
    all_entities = db.query(Entity).all()
    all_entities_by_id: dict[str, Entity] = {e.id: e for e in all_entities}

    # Group extractions: key = (entity_id or None, dimension_name) -> list of (extraction, document)
    ExtractionGroup = list[tuple[Extraction, Document]]
    grouped: dict[tuple[str | None, str], ExtractionGroup] = defaultdict(list)

    for ext in all_extractions:
        doc = docs_by_id.get(ext.document_id)
        if doc is None:
            continue

        # Try to resolve an entity_id for this extraction
        entity_id = resolution_map.get((ext.document_id, ext.raw_value))
        grouped[(entity_id, ext.dimension_name)].append((ext, doc))

    # Build doc_id -> set of entity_ids for entity-aware staleness grouping
    doc_entity_map: dict[str, set[str]] = defaultdict(set)
    for r in all_resolutions:
        doc_entity_map[r.document_id].add(r.entity_id)
    has_any_entities = bool(doc_entity_map)

    # Build dimension type lookup from all taxonomy schemas
    all_taxonomies = db.query(TaxonomySchema).all()
    dim_type_map: dict[str, str] = {}
    for tax in all_taxonomies:
        for dim in tax.dimensions:
            dim_type_map[dim["name"]] = dim.get("expected_type", "text")

    # Detect per-document identifier dimensions: text-type dimensions where
    # every document has a unique value (e.g. REPORT_ID, REPORT_TITLE) are
    # document-level identifiers, not evolving facts worth tracking.
    # Numeric, currency, and date types are excluded since those naturally
    # evolve over time (e.g. employee_count, revenue).
    _fact_types = {"number", "currency", "date", "date_range"}
    dim_doc_values: dict[str, dict[str, str]] = defaultdict(dict)
    for ext in all_extractions:
        val = ext.resolved_value or ext.raw_value
        if val:
            dim_doc_values[ext.dimension_name][ext.document_id] = val
    identifier_dims: set[str] = set()
    for dname, doc_vals in dim_doc_values.items():
        if dim_type_map.get(dname) in _fact_types:
            continue
        if len(doc_vals) >= 3 and len(set(doc_vals.values())) == len(doc_vals):
            identifier_dims.add(dname)

    def _collect_staleness(
        sub_items: ExtractionGroup,
        eid: str | None,
        dim: str,
        out: list[InsightStaleness],
        seen: set[tuple[str, str, str]],
    ) -> None:
        """Compare consecutive doc pairs and append staleness items."""
        sub_items.sort(key=lambda pair: _doc_effective_date(pair[1]) or datetime.min)
        for i in range(len(sub_items) - 1):
            older_ext, older_doc = sub_items[i]
            newer_ext, newer_doc = sub_items[i + 1]
            dedup_key = (older_doc.id, newer_doc.id, dim)
            if dedup_key in seen:
                continue
            older_value = older_ext.resolved_value or older_ext.raw_value
            newer_value = newer_ext.resolved_value or newer_ext.raw_value
            if older_value != newer_value:
                seen.add(dedup_key)
                entity_name = (
                    all_entities_by_id[eid].canonical_name
                    if eid and eid in all_entities_by_id
                    else None
                )
                out.append(InsightStaleness(
                    dimension_name=dim,
                    entity_name=entity_name,
                    newest_value=newer_value,
                    newest_doc_filename=newer_doc.original_filename,
                    newest_doc_date=_doc_effective_date(newer_doc),
                    older_value=older_value,
                    older_doc_filename=older_doc.original_filename,
                    older_doc_date=_doc_effective_date(older_doc),
                ))

    insight_staleness: list[InsightStaleness] = []
    staleness_seen: set[tuple[str, str, str]] = set()

    for (entity_id, dim_name), items in grouped.items():
        if len(items) < 2:
            continue
        if (entity_id, dim_name) in contradiction_keys:
            continue
        # Skip entity-reference dimensions — they are identifiers, not facts
        if dim_type_map.get(dim_name) in ("entity", "entity_list"):
            continue
        # Skip per-document identifier dimensions (every doc has a unique value)
        if dim_name in identifier_dims:
            continue

        if entity_id is not None:
            _collect_staleness(items, entity_id, dim_name, insight_staleness, staleness_seen)
        elif has_any_entities:
            # Non-entity dimension: re-group by the entities each document
            # is associated with so we only compare facts about the same subject.
            sub_groups: dict[str, ExtractionGroup] = defaultdict(list)
            for ext, doc in items:
                for eid in doc_entity_map.get(doc.id, set()):
                    sub_groups[eid].append((ext, doc))

            for eid, sub_items in sub_groups.items():
                if (eid, dim_name) in contradiction_keys:
                    continue
                seen_docs: set[str] = set()
                unique: ExtractionGroup = []
                for ext, doc in sub_items:
                    if doc.id not in seen_docs:
                        seen_docs.add(doc.id)
                        unique.append((ext, doc))
                if len(unique) >= 2:
                    _collect_staleness(unique, eid, dim_name, insight_staleness, staleness_seen)
        else:
            # No entities in system at all — fall back to ungrouped comparison
            _collect_staleness(items, None, dim_name, insight_staleness, staleness_seen)

    return InsightsResponse(
        total_contradictions=len(insight_contradictions),
        total_entities_needing_review=len(insight_entity_reviews),
        total_staleness_items=len(insight_staleness),
        contradictions=insight_contradictions,
        entities_needing_review=insight_entity_reviews,
        staleness_items=insight_staleness,
    )


# ---------------------------------------------------------------------------
# POST /api/chat
# ---------------------------------------------------------------------------


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    body: ChatRequest,
    db: Session = Depends(get_db),
):
    """Send a chat message and receive a response with citations."""
    result = await chat(
        query=body.message,
        session_id=body.session_id or "default",
        db=db,
    )
    return ChatResponse(**result)
