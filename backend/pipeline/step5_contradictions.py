"""Step 5: Contradiction Detection.

Compares extracted values for the same dimension across documents
for the same entity to find contradictions.
"""

from collections import defaultdict

from sqlalchemy.orm import Session

from backend.models import Contradiction, Entity, EntityResolution, Extraction, TaxonomySchema
from backend.pipeline.llm import llm_call, parse_json_response


async def detect_contradictions(
    taxonomy: TaxonomySchema,
    db: Session,
) -> list[Contradiction]:
    """Detect contradictions in extracted values across documents.

    Groups extractions by entity and dimension, then uses an LLM to identify
    contradictions between values from different documents.

    Args:
        taxonomy: The TaxonomySchema to filter extractions.
        db: SQLAlchemy session.

    Returns:
        List of Contradiction records created.
    """
    # Get all extractions for this taxonomy
    extractions = (
        db.query(Extraction)
        .filter(Extraction.taxonomy_schema_id == taxonomy.id)
        .all()
    )

    if not extractions:
        return []

    # Build entity -> document -> dimension -> value mapping
    # First, get entity resolutions to know which entity each document maps to
    entity_resolutions = db.query(EntityResolution).all()

    # Build doc_id -> entity_id mapping
    doc_entity_map = defaultdict(set)
    for er in entity_resolutions:
        doc_entity_map[er.document_id].add(er.entity_id)

    # Group extractions by (entity_id, dimension_name)
    # For extractions without entity resolution, group by dimension only
    grouped = defaultdict(list)
    for ext in extractions:
        entity_ids = doc_entity_map.get(ext.document_id, set())
        if entity_ids:
            for entity_id in entity_ids:
                grouped[(entity_id, ext.dimension_name)].append(ext)
        else:
            grouped[(None, ext.dimension_name)].append(ext)

    # Filter to groups with multiple documents (potential contradictions)
    multi_doc_groups = {}
    for key, exts in grouped.items():
        doc_ids = {e.document_id for e in exts}
        if len(doc_ids) > 1:
            multi_doc_groups[key] = exts

    if not multi_doc_groups:
        return []

    # Build comparison text for the LLM
    comparisons = []
    group_keys = []
    for (entity_id, dim_name), exts in multi_doc_groups.items():
        entity_name = "Unknown"
        if entity_id:
            entity = db.query(Entity).filter(Entity.id == entity_id).first()
            if entity:
                entity_name = entity.canonical_name

        values_desc = []
        for ext in exts:
            value = ext.resolved_value or ext.raw_value
            values_desc.append(
                f"  Document {ext.document_id}: \"{value}\""
            )

        comparisons.append(
            f"Entity: {entity_name}, Dimension: {dim_name}\n"
            + "\n".join(values_desc)
        )
        group_keys.append((entity_id, dim_name, exts))

    comparisons_text = "\n\n".join(comparisons)

    prompt = (
        "Below are extracted values for the same dimensions across different documents, "
        "grouped by entity and dimension:\n\n"
        f"{comparisons_text}\n\n"
        "Identify any contradictions — cases where different documents report "
        "conflicting or inconsistent values for the same entity and dimension. "
        "Minor formatting differences are NOT contradictions. "
        "Only flag genuine factual disagreements.\n\n"
        "For each contradiction, provide:\n"
        "- entity_name: the entity involved\n"
        "- dimension_name: the dimension with conflicting values\n"
        "- doc_a_value: value from the first document\n"
        "- doc_b_value: value from the second document\n"
        "- doc_a_id: the document ID for the first value\n"
        "- doc_b_id: the document ID for the second value\n\n"
        "Return a JSON array of contradiction objects. "
        "If there are no contradictions, return an empty array [].\n"
        "Return ONLY the JSON."
    )

    system = (
        "You are a data quality expert. Identify genuine contradictions in extracted data. "
        "Do not flag formatting differences or rounding differences as contradictions. "
        "Focus on factual disagreements."
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

        contradiction = Contradiction(
            dimension_name=dim_name,
            entity_id=entity_id,
            doc_a_id=doc_a_id,
            doc_b_id=doc_b_id,
            value_a=str(value_a),
            value_b=str(value_b),
            resolution_status="unresolved",
        )
        db.add(contradiction)
        contradictions.append(contradiction)

    db.commit()
    for c in contradictions:
        db.refresh(c)

    return contradictions
