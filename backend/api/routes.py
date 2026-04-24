"""FastAPI API routes — all endpoints for the Taxonomy Discovery Engine."""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.api.schemas import (
    ChatRequest,
    ChatResponse,
    ContradictionResponse,
    DocumentResponse,
    EntityResponse,
    EntityResolutionResponse,
    EntityUpdateRequest,
    ExtractionResponse,
    ProcessRequest,
    ProcessResponse,
    ResolutionUpdateRequest,
    StatusResponse,
    TaxonomyResponse,
    TaxonomyTemplateCreate,
    TaxonomyTemplateResponse,
    TaxonomyTemplateUpdate,
    UploadedFileInfo,
    UploadResponse,
)
from backend.chat.engine import chat
from backend.database import get_db
from backend.ingestion.service import store_and_ingest
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
    db: Session = Depends(get_db),
):
    """Upload one or more documents (.pdf, .docx, .doc, .xlsx, .xls, .csv)."""
    uploaded: list[UploadedFileInfo] = []
    errors: list[str] = []

    for file in files:
        filename = file.filename or "unknown"
        # Validate extension
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
    result = []
    for ext in extractions:
        doc = db.query(Document).filter(Document.id == ext.document_id).first()
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
