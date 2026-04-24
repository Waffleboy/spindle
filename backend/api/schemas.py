"""Pydantic models for API request/response validation."""

from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


class DocumentResponse(BaseModel):
    id: str
    original_filename: str
    file_type: str
    detected_doc_type: str | None = None
    page_count: int | None = None
    report_date: datetime | None = None
    uploaded_at: datetime
    processed_at: datetime | None = None

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


class UploadedFileInfo(BaseModel):
    id: str
    filename: str


class UploadResponse(BaseModel):
    document_ids: list[str]
    message: str
    uploaded: list[UploadedFileInfo] = []


# ---------------------------------------------------------------------------
# Process / Status
# ---------------------------------------------------------------------------


class ProcessRequest(BaseModel):
    document_ids: list[str]
    company_context: str | None = None


class ProcessResponse(BaseModel):
    message: str
    corpus_id: str


class StatusResponse(BaseModel):
    status: str = "idle"
    current_step: str | None = None
    steps_completed: list[str] = []
    total_documents: int = 0
    processed_documents: int = 0
    error: str | None = None


# ---------------------------------------------------------------------------
# Taxonomy
# ---------------------------------------------------------------------------


class TaxonomyResponse(BaseModel):
    id: str
    corpus_id: str
    dimensions: list[dict]
    doc_type: str
    company_context: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Extractions
# ---------------------------------------------------------------------------


class ExtractionResponse(BaseModel):
    id: str
    document_id: str
    document_filename: str | None = None
    taxonomy_schema_id: str
    dimension_name: str
    raw_value: str
    resolved_value: str | None = None
    source_pages: list | None = None
    confidence: float

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------


class EntityResponse(BaseModel):
    id: str
    canonical_name: str
    entity_type: str
    aliases: list[str]
    needs_review_count: int = 0

    model_config = {"from_attributes": True}


class EntityUpdateRequest(BaseModel):
    canonical_name: str


# ---------------------------------------------------------------------------
# Entity Resolutions
# ---------------------------------------------------------------------------


class ResolutionUpdateRequest(BaseModel):
    approved: bool
    override_value: str | None = None


class EntityResolutionResponse(BaseModel):
    id: str
    entity_id: str
    original_value: str
    document_id: str
    confidence: float
    needs_review: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Contradictions
# ---------------------------------------------------------------------------


class ContradictionResponse(BaseModel):
    id: str
    dimension_name: str
    entity_id: str | None = None
    doc_a_id: str
    doc_a_filename: str | None = None
    doc_b_id: str
    doc_b_filename: str | None = None
    value_a: str
    value_b: str
    doc_a_date: datetime | None = None
    doc_b_date: datetime | None = None
    reason: str | None = None
    resolution_status: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Taxonomy Templates
# ---------------------------------------------------------------------------


class TaxonomyTemplateDimension(BaseModel):
    name: str
    description: str = ""
    expected_type: str = "text"


class TaxonomyTemplateCreate(BaseModel):
    label: str
    description: str
    dimensions: list[TaxonomyTemplateDimension]


class TaxonomyTemplateUpdate(BaseModel):
    label: str | None = None
    description: str | None = None
    dimensions: list[TaxonomyTemplateDimension] | None = None


class TaxonomyTemplateResponse(BaseModel):
    id: str
    label: str
    description: str
    dimensions: list[dict]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Entity Timeline
# ---------------------------------------------------------------------------


class TimelineDimensionValue(BaseModel):
    dimension_name: str
    value: str
    confidence: float
    source_pages: list | None = None


class TimelineDiff(BaseModel):
    dimension_name: str
    old_value: str
    new_value: str
    change_type: str  # "new" | "updated" | "contradiction"


class TimelineNode(BaseModel):
    document_id: str
    document_filename: str
    document_date: datetime | None = None
    is_approximate_date: bool = False
    dimensions: list[TimelineDimensionValue]
    diffs_from_previous: list[TimelineDiff]


class EntityTimelineResponse(BaseModel):
    entity_id: str
    entity_name: str
    entity_type: str
    timeline: list[TimelineNode]


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    citations: list[dict]
    query_type: str
    suggested_queries: list[str]


# ---------------------------------------------------------------------------
# Insights (aggregated dashboard view)
# ---------------------------------------------------------------------------


class InsightContradiction(BaseModel):
    id: str
    dimension_name: str
    entity_name: str | None = None
    doc_a_id: str
    doc_a_filename: str
    doc_a_value: str
    doc_a_date: datetime | None = None
    doc_b_id: str
    doc_b_filename: str
    doc_b_value: str
    doc_b_date: datetime | None = None
    newer_doc: str | None = None  # "a" or "b" or None if dates unknown
    reason: str | None = None
    resolution_status: str


class InsightEntityReview(BaseModel):
    entity_id: str
    canonical_name: str
    entity_type: str
    review_count: int
    aliases: list[str]


class InsightStaleness(BaseModel):
    dimension_name: str
    entity_name: str | None = None
    newest_value: str
    newest_doc_filename: str
    newest_doc_date: datetime | None = None
    older_value: str
    older_doc_filename: str
    older_doc_date: datetime | None = None


class InsightsResponse(BaseModel):
    total_contradictions: int
    total_entities_needing_review: int
    total_staleness_items: int
    contradictions: list[InsightContradiction]
    entities_needing_review: list[InsightEntityReview]
    staleness_items: list[InsightStaleness]
