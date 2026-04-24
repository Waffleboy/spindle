"""Structured retrieval path: query taxonomy tables directly."""

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend.chat.classifier import QueryType
from backend.models import (
    Contradiction,
    Document,
    Entity,
    EntityResolution,
    Extraction,
)

_STOP_WORDS = frozenset(
    "a an the is was were be been being have has had do does did will would "
    "shall should may might can could about above after again all also am and "
    "any are at before between but by for from get got had has have he her "
    "here him his how i if in into is it its just let me my no nor not of "
    "off on or our out own say she so some such than that the their them then "
    "there these they this to too up us very want was we what when where which "
    "while who whom why with you your happened show tell".split()
)


def _extract_keywords(query: str) -> list[str]:
    """Extract meaningful keywords from a query, filtering out stop words."""
    words = []
    for w in query.lower().split():
        cleaned = w.strip("?,.:;!\"'()[]{}").strip()
        if cleaned and cleaned not in _STOP_WORDS and len(cleaned) > 1:
            words.append(cleaned)
    return words


def _extraction_to_dict(ext: Extraction, doc: Document) -> dict:
    """Convert an Extraction + its Document into a result dict."""
    effective_date = doc.report_date or doc.uploaded_at
    is_approximate = doc.report_date is None
    return {
        "source": "taxonomy",
        "data": {
            "dimension_name": ext.dimension_name,
            "raw_value": ext.raw_value,
            "resolved_value": ext.resolved_value,
            "confidence": ext.confidence,
        },
        "document": doc.original_filename,
        "document_date": effective_date.isoformat() if effective_date else None,
        "is_approximate_date": is_approximate,
        "pages": ext.source_pages,
    }


def _contradiction_to_dict(c: Contradiction, doc_a: Document, doc_b: Document) -> dict:
    """Convert a Contradiction into a result dict."""
    date_a = doc_a.report_date or doc_a.uploaded_at
    date_b = doc_b.report_date or doc_b.uploaded_at

    # Determine which value is more recent for temporal context
    temporal_context = None
    if date_a and date_b:
        if date_a >= date_b:
            temporal_context = (
                f"Most recent value: '{c.value_a}' from {doc_a.original_filename} "
                f"({date_a.strftime('%Y-%m-%d')}), "
                f"older value: '{c.value_b}' from {doc_b.original_filename} "
                f"({date_b.strftime('%Y-%m-%d')})"
            )
        else:
            temporal_context = (
                f"Most recent value: '{c.value_b}' from {doc_b.original_filename} "
                f"({date_b.strftime('%Y-%m-%d')}), "
                f"older value: '{c.value_a}' from {doc_a.original_filename} "
                f"({date_a.strftime('%Y-%m-%d')})"
            )

    return {
        "source": "taxonomy",
        "type": "contradiction",
        "data": {
            "dimension_name": c.dimension_name,
            "value_a": c.value_a,
            "value_b": c.value_b,
            "resolution_status": c.resolution_status,
        },
        "document_a": doc_a.original_filename,
        "document_b": doc_b.original_filename,
        "temporal_context": temporal_context,
    }


def _get_contradictions(query: str, db: Session) -> list[dict]:
    """Fetch contradictions that may be relevant to the query."""
    contradictions = db.query(Contradiction).all()
    results = []
    query_lower = query.lower()

    entity_cache: dict[str, Entity | None] = {}
    for c in contradictions:
        dim_lower = c.dimension_name.lower()
        dim_match = dim_lower in query_lower or query_lower in dim_lower
        val_match = c.value_a.lower() in query_lower or c.value_b.lower() in query_lower

        entity_match = False
        if c.entity_id:
            if c.entity_id not in entity_cache:
                entity_cache[c.entity_id] = db.query(Entity).filter(Entity.id == c.entity_id).first()
            entity = entity_cache[c.entity_id]
            if entity:
                canon = entity.canonical_name.lower()
                entity_match = canon in query_lower or any(
                    alias.lower() in query_lower for alias in (entity.aliases or [])
                )

        if dim_match or val_match or entity_match:
            doc_a = db.query(Document).filter(Document.id == c.doc_a_id).first()
            doc_b = db.query(Document).filter(Document.id == c.doc_b_id).first()
            if doc_a and doc_b:
                results.append(_contradiction_to_dict(c, doc_a, doc_b))
    return results


async def structured_search(
    query: str, query_type: QueryType, db: Session
) -> list[dict]:
    """Query taxonomy tables directly based on query type.

    Returns list of {source: "taxonomy", data: ..., document: ..., pages: ...}
    """
    results: list[dict] = []
    query_lower = query.lower()

    # Effective date expression: prefer report_date, fall back to uploaded_at
    effective_date = func.coalesce(Document.report_date, Document.uploaded_at)

    if query_type == QueryType.FACT_LOOKUP:
        keywords = _extract_keywords(query)
        keyword_filters = []
        for kw in keywords:
            keyword_filters.append(func.lower(Extraction.dimension_name).contains(kw))
            keyword_filters.append(func.lower(Extraction.raw_value).contains(kw))
            keyword_filters.append(func.lower(Extraction.resolved_value).contains(kw))

        extractions = (
            db.query(Extraction, Document)
            .join(Document, Extraction.document_id == Document.id)
            .filter(or_(*keyword_filters) if keyword_filters else func.lower(Extraction.dimension_name).contains(query_lower))
            .order_by(effective_date.desc())
            .all()
        )
        if not extractions:
            extractions = (
                db.query(Extraction, Document)
                .join(Document, Extraction.document_id == Document.id)
                .order_by(effective_date.desc())
                .all()
            )
        for ext, doc in extractions:
            results.append(_extraction_to_dict(ext, doc))

    elif query_type == QueryType.CROSS_DOC:
        # Search extractions across multiple documents for same dimension, group by doc date
        extractions = (
            db.query(Extraction, Document)
            .join(Document, Extraction.document_id == Document.id)
            .order_by(effective_date.desc())
            .all()
        )
        for ext, doc in extractions:
            results.append(_extraction_to_dict(ext, doc))

    elif query_type == QueryType.ENTITY_QUERY:
        # Search entities table for matching canonical_name or aliases
        entities = db.query(Entity).all()
        matched_entity_ids = set()
        for entity in entities:
            canon = entity.canonical_name.lower()
            name_match = canon in query_lower or query_lower in canon
            alias_match = any(
                alias.lower() in query_lower or query_lower in alias.lower()
                for alias in (entity.aliases or [])
            )
            if name_match or alias_match:
                matched_entity_ids.add(entity.id)

        if matched_entity_ids:
            # Find linked documents via EntityResolution
            resolutions = (
                db.query(EntityResolution, Document)
                .join(Document, EntityResolution.document_id == Document.id)
                .filter(EntityResolution.entity_id.in_(matched_entity_ids))
                .all()
            )
            seen_doc_ids = set()
            for resolution, doc in resolutions:
                if doc.id not in seen_doc_ids:
                    seen_doc_ids.add(doc.id)
                    # Get all extractions for this document
                    doc_extractions = (
                        db.query(Extraction)
                        .filter(Extraction.document_id == doc.id)
                        .all()
                    )
                    for ext in doc_extractions:
                        results.append(_extraction_to_dict(ext, doc))

        # Fallback: search extractions by individual keywords
        if not results:
            keywords = _extract_keywords(query)
            keyword_filters = []
            for kw in keywords:
                keyword_filters.append(func.lower(Extraction.raw_value).contains(kw))
                keyword_filters.append(func.lower(Extraction.resolved_value).contains(kw))
            if keyword_filters:
                extractions = (
                    db.query(Extraction, Document)
                    .join(Document, Extraction.document_id == Document.id)
                    .filter(or_(*keyword_filters))
                    .all()
                )
                for ext, doc in extractions:
                    results.append(_extraction_to_dict(ext, doc))

    elif query_type == QueryType.TEMPORAL:
        # Search extractions sorted by document date (newest first)
        extractions = (
            db.query(Extraction, Document)
            .join(Document, Extraction.document_id == Document.id)
            .order_by(effective_date.desc())
            .all()
        )
        for ext, doc in extractions:
            results.append(_extraction_to_dict(ext, doc))

    elif query_type == QueryType.OPEN_ENDED:
        # Return all extractions (limited to fit context window)
        extractions = (
            db.query(Extraction, Document)
            .join(Document, Extraction.document_id == Document.id)
            .limit(100)
            .all()
        )
        for ext, doc in extractions:
            results.append(_extraction_to_dict(ext, doc))

    # Append relevant contradictions for all query types
    contradictions = _get_contradictions(query, db)
    results.extend(contradictions)

    return results
