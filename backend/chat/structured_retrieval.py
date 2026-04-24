"""Structured retrieval path: query taxonomy tables directly."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.chat.classifier import QueryType
from backend.models import (
    Contradiction,
    Document,
    Entity,
    EntityResolution,
    Extraction,
)


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
    for c in contradictions:
        # Include contradiction if the dimension name or values loosely match the query
        if (
            c.dimension_name.lower() in query_lower
            or query_lower in c.dimension_name.lower()
            or c.value_a.lower() in query_lower
            or c.value_b.lower() in query_lower
        ):
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
        # Search extractions by dimension_name and resolved_value
        extractions = (
            db.query(Extraction, Document)
            .join(Document, Extraction.document_id == Document.id)
            .filter(
                func.lower(Extraction.dimension_name).contains(query_lower)
                | func.lower(Extraction.raw_value).contains(query_lower)
                | func.lower(Extraction.resolved_value).contains(query_lower)
            )
            .order_by(effective_date.desc())
            .all()
        )
        # If keyword search yields nothing, return all extractions (small corpus)
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
            name_match = query_lower in entity.canonical_name.lower()
            alias_match = any(
                query_lower in alias.lower()
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

        # Fallback: also search extractions by the query text
        if not results:
            extractions = (
                db.query(Extraction, Document)
                .join(Document, Extraction.document_id == Document.id)
                .filter(
                    func.lower(Extraction.raw_value).contains(query_lower)
                    | func.lower(Extraction.resolved_value).contains(query_lower)
                )
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
