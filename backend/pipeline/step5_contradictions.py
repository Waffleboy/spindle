"""Step 5: Contradiction Detection.

Compares extracted values for the same dimension across documents
for the same entity to find contradictions.
"""

from collections import defaultdict

from sqlalchemy.orm import Session

from backend.models import Contradiction, Document, Entity, EntityResolution, Extraction, TaxonomySchema
from backend.pipeline.llm import llm_call, parse_json_response


def _build_primary_entity_map(
    doc_ids: set[str],
    db: Session,
) -> dict[str, str]:
    """Map each document to its primary (company) entity.

    Picks the company-type entity with highest confidence for each document.
    Falls back to the highest-confidence entity of any type.
    Returns dict of doc_id -> entity_id.
    """
    resolutions = (
        db.query(EntityResolution)
        .filter(EntityResolution.document_id.in_(doc_ids))
        .all()
    )
    if not resolutions:
        return {}

    entity_ids = {er.entity_id for er in resolutions}
    entities = db.query(Entity).filter(Entity.id.in_(entity_ids)).all()
    entity_type_map = {e.id: e.entity_type for e in entities}

    # For each doc, find the best entity (prefer company type)
    doc_candidates: dict[str, list[tuple[str, float, bool]]] = defaultdict(list)
    for er in resolutions:
        is_company = entity_type_map.get(er.entity_id, "").lower() in (
            "company", "organisation", "organization",
        )
        doc_candidates[er.document_id].append(
            (er.entity_id, er.confidence, is_company)
        )

    result: dict[str, str] = {}
    for doc_id, candidates in doc_candidates.items():
        # Sort: company entities first, then by confidence descending
        candidates.sort(key=lambda c: (c[2], c[1]), reverse=True)
        result[doc_id] = candidates[0][0]

    return result


async def detect_contradictions(
    taxonomy: TaxonomySchema,
    db: Session,
) -> list[Contradiction]:
    """Detect contradictions in extracted values across documents.

    Groups extractions by primary entity (company) and dimension, then uses
    an LLM to identify contradictions between values from different documents.

    Args:
        taxonomy: The TaxonomySchema to filter extractions.
        db: SQLAlchemy session.

    Returns:
        List of Contradiction records created.
    """
    extractions = (
        db.query(Extraction)
        .filter(Extraction.taxonomy_schema_id == taxonomy.id)
        .all()
    )

    if not extractions:
        return []

    # Map each document to its primary entity (company)
    taxonomy_doc_ids = {ext.document_id for ext in extractions}
    doc_primary_entity = _build_primary_entity_map(taxonomy_doc_ids, db)

    # Group extractions by (primary_entity_id, dimension_name)
    # Each extraction is counted exactly once under its document's primary entity
    grouped: dict[tuple[str | None, str], list[Extraction]] = defaultdict(list)
    for ext in extractions:
        entity_id = doc_primary_entity.get(ext.document_id)
        grouped[(entity_id, ext.dimension_name)].append(ext)

    # Filter to groups spanning multiple documents for the SAME entity.
    # Skip groups without an entity — without entity context we cannot
    # determine whether values from different docs are truly contradictory.
    multi_doc_groups: dict[tuple[str, str], list[Extraction]] = {}
    for (entity_id, dim_name), exts in grouped.items():
        if entity_id is None:
            continue
        doc_ids = {e.document_id for e in exts}
        if len(doc_ids) > 1:
            multi_doc_groups[(entity_id, dim_name)] = exts

    if not multi_doc_groups:
        return []

    # Pre-fetch entity names and document metadata
    all_entity_ids = {eid for eid, _ in multi_doc_groups}
    entity_name_map: dict[str, str] = {}
    for entity in db.query(Entity).filter(Entity.id.in_(all_entity_ids)).all():
        entity_name_map[entity.id] = entity.canonical_name

    all_doc_ids = set()
    for exts in multi_doc_groups.values():
        for ext in exts:
            all_doc_ids.add(ext.document_id)
    doc_meta: dict[str, tuple[str, str | None]] = {}
    for doc in db.query(Document).filter(Document.id.in_(all_doc_ids)).all():
        date_str = None
        effective_date = doc.report_date or doc.uploaded_at
        if effective_date:
            date_str = effective_date.strftime("%Y-%m-%d")
        doc_meta[doc.id] = (doc.original_filename, date_str)

    # Build dimension type lookup from taxonomy
    dim_type_map: dict[str, str] = {}
    for dim in taxonomy.dimensions:
        dim_type_map[dim["name"]] = dim.get("expected_type", "text")

    # Build comparison text for the LLM
    comparisons = []
    group_keys = []
    for (entity_id, dim_name), exts in multi_doc_groups.items():
        entity_name = entity_name_map.get(entity_id, "Unknown")
        dim_type = dim_type_map.get(dim_name, "text")

        values_desc = []
        for ext in exts:
            value = ext.resolved_value or ext.raw_value
            filename, date_str = doc_meta.get(ext.document_id, (ext.document_id, None))
            date_part = f", dated {date_str}" if date_str else ""
            values_desc.append(
                f"  Document {ext.document_id} (\"{filename}\"{date_part}): \"{value}\""
            )

        comparisons.append(
            f"Entity: {entity_name}, Dimension: {dim_name} (type: {dim_type})\n"
            + "\n".join(values_desc)
        )
        group_keys.append((entity_id, dim_name, exts))

    comparisons_text = "\n\n".join(comparisons)

    prompt = (
        "Below are extracted values for the same dimensions across different documents, "
        "grouped by entity and dimension. Each group contains values from documents about "
        "the SAME company/entity. Each dimension has a type annotation.\n\n"
        f"{comparisons_text}\n\n"
        "Identify any contradictions — cases where different documents report "
        "conflicting or inconsistent values for the same entity and dimension.\n\n"
        "IMPORTANT rules for what is NOT a contradiction:\n"
        "- Minor formatting differences (e.g. '$5.2B' vs '$5.2 billion')\n"
        "- For list-type dimensions (entity_list, text_list): different members across "
        "documents are NOT contradictions. These dimensions naturally have different "
        "entries per document. For example, if Document A lists 'Rachel Goh' and "
        "Document B lists 'James Chia' for an entity_list dimension like "
        "'ESG_REPRESENTATIVES', that is NOT a contradiction — they are simply "
        "different people listed in different reports. Only flag a contradiction "
        "for list-type dimensions if the same specific item has conflicting attributes.\n"
        "- Temporal changes that reflect genuine updates over time (use document dates "
        "to judge this — values naturally evolve across reports)\n"
        "- Per-entity scalar values that differ across entities: only flag "
        "a contradiction when the SAME entity has conflicting values for the same "
        "dimension across different documents.\n"
        "- Metrics that are inherently time-specific (e.g. revenue, headcount, "
        "capacity) reported for different periods — these are expected to change.\n\n"
        "Only flag genuine factual disagreements where the same entity reports "
        "conflicting values for what should be the same fact.\n\n"
        "For each contradiction, provide:\n"
        "- entity_name: the entity involved\n"
        "- dimension_name: the dimension with conflicting values\n"
        "- doc_a_value: value from the first document\n"
        "- doc_b_value: value from the second document\n"
        "- doc_a_id: the document ID for the first value\n"
        "- doc_b_id: the document ID for the second value\n"
        "- reason: a brief explanation (1-2 sentences) of WHY this is a genuine "
        "contradiction that a human reviewer should verify\n\n"
        "Return a JSON array of contradiction objects. "
        "If there are no contradictions, return an empty array [].\n"
        "Return ONLY the JSON."
    )

    system = (
        "You are a data quality expert analyzing multi-document corporate reports. "
        "Identify genuine contradictions in extracted data. "
        "Do not flag formatting differences or rounding differences as contradictions. "
        "For list-type dimensions (entity_list, text_list), different members across "
        "documents are expected and are NOT contradictions. "
        "Use document dates to distinguish temporal evolution from true contradictions. "
        "Focus on factual disagreements about the same specific item or scalar value "
        "within the same company."
    )

    response_text = await llm_call(
        prompt=prompt,
        system=system,
        response_format={"type": "json_object"},
    )

    contradiction_data = parse_json_response(response_text)

    # Handle wrapped response
    if isinstance(contradiction_data, dict):
        for value in contradiction_data.values():
            if isinstance(value, list):
                contradiction_data = value
                break
        else:
            contradiction_data = []

    # Create Contradiction records
    contradictions = []
    for item in contradiction_data:
        if not isinstance(item, dict):
            continue

        dim_name = item.get("dimension_name", "")
        doc_a_id = item.get("doc_a_id", "")
        doc_b_id = item.get("doc_b_id", "")
        value_a = item.get("doc_a_value", "")
        value_b = item.get("doc_b_value", "")

        if not (dim_name and doc_a_id and doc_b_id):
            continue

        # Find the entity_id for this contradiction
        entity_id = None
        entity_name = item.get("entity_name", "")
        if entity_name:
            entity = (
                db.query(Entity)
                .filter(Entity.canonical_name == entity_name)
                .first()
            )
            if entity:
                entity_id = entity.id

        doc_a = db.query(Document).filter(Document.id == doc_a_id).first()
        doc_b = db.query(Document).filter(Document.id == doc_b_id).first()
        doc_a_date = (doc_a.report_date or doc_a.uploaded_at) if doc_a else None
        doc_b_date = (doc_b.report_date or doc_b.uploaded_at) if doc_b else None

        reason = item.get("reason", None)

        contradiction = Contradiction(
            dimension_name=dim_name,
            entity_id=entity_id,
            doc_a_id=doc_a_id,
            doc_b_id=doc_b_id,
            value_a=str(value_a),
            value_b=str(value_b),
            doc_a_date=doc_a_date,
            doc_b_date=doc_b_date,
            reason=str(reason) if reason else None,
            resolution_status="unresolved",
        )
        db.add(contradiction)
        contradictions.append(contradiction)

    db.commit()
    for c in contradictions:
        db.refresh(c)

    return contradictions
