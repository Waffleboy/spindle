"""Step 4: Entity Resolution.

Collects all entity mentions across documents and groups them by
canonical real-world entity using an LLM call.
"""

import json

from sqlalchemy.orm import Session

from backend.models import Entity, EntityResolution, Extraction, TaxonomySchema
from backend.pipeline.llm import llm_call, parse_json_response


async def resolve_entities(
    taxonomy: TaxonomySchema,
    db: Session,
) -> list[Entity]:
    """Resolve entity mentions across all documents.

    Collects all Extraction records with entity or entity_list dimension types,
    groups entity mentions that refer to the same real-world entity, and creates
    Entity and EntityResolution records.

    Args:
        taxonomy: The TaxonomySchema to filter extractions.
        db: SQLAlchemy session.

    Returns:
        List of Entity records created.
    """
    # Find entity-type dimensions
    entity_dims = {
        d["name"]
        for d in taxonomy.dimensions
        if d["expected_type"] in ("entity", "entity_list")
    }

    if not entity_dims:
        return []

    # Collect all entity mentions from extractions
    extractions = (
        db.query(Extraction)
        .filter(
            Extraction.taxonomy_schema_id == taxonomy.id,
            Extraction.dimension_name.in_(entity_dims),
        )
        .all()
    )

    if not extractions:
        return []

    # Build mentions list: {value, document_id, dimension_name}
    mentions = []
    for ext in extractions:
        if not ext.raw_value:
            continue

        # Try to parse as JSON list for entity_list type
        dim_type = None
        for d in taxonomy.dimensions:
            if d["name"] == ext.dimension_name:
                dim_type = d["expected_type"]
                break

        if dim_type == "entity_list":
            try:
                values = json.loads(ext.raw_value)
                if isinstance(values, list):
                    for v in values:
                        if v:
                            mentions.append({
                                "value": str(v),
                                "document_id": ext.document_id,
                                "dimension_name": ext.dimension_name,
                                "extraction_id": ext.id,
                            })
                    continue
            except (json.JSONDecodeError, TypeError):
                pass

        # Single entity value
        mentions.append({
            "value": ext.raw_value,
            "document_id": ext.document_id,
            "dimension_name": ext.dimension_name,
            "extraction_id": ext.id,
        })

    if not mentions:
        return []

    # Build the prompt with all entity mentions
    mention_list = "\n".join(
        f"- \"{m['value']}\" (from document {m['document_id']}, dimension: {m['dimension_name']})"
        for m in mentions
    )

    prompt = (
        "Below is a list of entity mentions extracted from multiple documents:\n\n"
        f"{mention_list}\n\n"
        "Group these entity mentions that refer to the same real-world entity. "
        "For each group, provide:\n"
        "- canonical_name: the best/most complete name for the entity\n"
        "- entity_type: the type of entity (e.g., person, company, location, product)\n"
        "- aliases: list of objects, each with 'value' (the mention text) and "
        "'confidence' (0.0-1.0 that this alias refers to the canonical entity)\n\n"
        "Return a JSON array of these group objects.\n"
        "Return ONLY the JSON array."
    )

    system = (
        "You are an entity resolution expert. Group entity mentions that refer "
        "to the same real-world entity. Be careful with similar but distinct entities. "
        "Assign high confidence to clear matches and lower confidence to uncertain ones."
    )

    response_text = await llm_call(
        prompt=prompt,
        system=system,
        response_format={"type": "json_object"},
    )

    entity_groups = parse_json_response(response_text)

    # Handle wrapped response
    if isinstance(entity_groups, dict):
        for value in entity_groups.values():
            if isinstance(value, list):
                entity_groups = value
                break

    # Create Entity and EntityResolution records
    entities = []
    # Build a lookup: mention_value -> list of (document_id, extraction_id)
    mention_lookup = {}
    for m in mentions:
        mention_lookup.setdefault(m["value"], []).append(
            (m["document_id"], m["extraction_id"])
        )

    for group in entity_groups:
        if not isinstance(group, dict):
            continue

        canonical_name = group.get("canonical_name", "")
        entity_type = group.get("entity_type", "unknown")
        aliases_data = group.get("aliases", [])

        alias_strings = []
        for alias in aliases_data:
            if isinstance(alias, dict):
                alias_strings.append(alias.get("value", ""))
            elif isinstance(alias, str):
                alias_strings.append(alias)

        entity = Entity(
            canonical_name=canonical_name,
            entity_type=entity_type,
            aliases=[a for a in alias_strings if a],
        )
        db.add(entity)
        db.flush()  # Get the entity ID

        # Create EntityResolution records for each alias
        for alias in aliases_data:
            if isinstance(alias, dict):
                alias_value = alias.get("value", "")
                alias_confidence = alias.get("confidence", 0.5)
            else:
                alias_value = str(alias)
                alias_confidence = 0.5

            if not alias_value:
                continue

            # Find all document occurrences of this alias value
            occurrences = mention_lookup.get(alias_value, [])
            for doc_id, extraction_id in occurrences:
                resolution = EntityResolution(
                    entity_id=entity.id,
                    original_value=alias_value,
                    document_id=doc_id,
                    confidence=float(alias_confidence),
                    needs_review=alias_confidence < 0.8,
                )
                db.add(resolution)

        # Update resolved_value on extractions
        for alias in aliases_data:
            alias_value = alias.get("value", "") if isinstance(alias, dict) else str(alias)
            if not alias_value:
                continue
            occurrences = mention_lookup.get(alias_value, [])
            for _, extraction_id in occurrences:
                ext = db.query(Extraction).filter(Extraction.id == extraction_id).first()
                if ext:
                    ext.resolved_value = canonical_name

        entities.append(entity)

    db.commit()
    for ent in entities:
        db.refresh(ent)

    return entities
