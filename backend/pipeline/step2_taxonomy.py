"""Step 2: Taxonomy Generation.

Given the detected document type and sample content, discovers the taxonomy
dimensions that should be extracted from each document.
"""

import uuid

from sqlalchemy.orm import Session

from backend.ingestion.common import IngestedDocument
from backend.models import TaxonomySchema, TaxonomyTemplate
from backend.pipeline.llm import llm_call, parse_json_response


async def generate_taxonomy(
    doc_type: str,
    documents: list[IngestedDocument],
    corpus_id: str = None,
    company_context: str = None,
    matched_templates: list[TaxonomyTemplate] | None = None,
    db: Session = None,
) -> TaxonomySchema:
    """Generate a taxonomy schema based on document type and sample content.

    Sends a single LLM call to discover the dimensions that should be
    extracted from documents of the detected type. If matched templates
    are provided, their dimensions are injected as mandatory includes.

    Args:
        doc_type: The detected document type from step 1.
        documents: List of IngestedDocument objects (uses first ~2 for samples).
        corpus_id: An identifier for this corpus/batch of documents.
        company_context: Optional company context to guide taxonomy generation.
        matched_templates: Templates whose dimensions must be included.
        db: SQLAlchemy session.

    Returns:
        A TaxonomySchema DB record with the discovered dimensions.
    """
    corpus_id = corpus_id or str(uuid.uuid4())

    # Build sample from first ~2 documents
    samples = []
    for doc in documents[:2]:
        text = doc.text or ""
        words = text.split()
        sample = " ".join(words[:800])
        samples.append(f"--- {doc.original_filename} ---\n{sample}")

    combined_sample = "\n\n".join(samples)

    context_clause = ""
    if company_context:
        context_clause = f"\nAdditional context about the company/domain: {company_context}\n"

    template_clause = ""
    if matched_templates:
        required_dims = []
        for tmpl in matched_templates:
            for dim in tmpl.dimensions:
                required_dims.append(
                    f"  - {dim['name']} ({dim.get('expected_type', 'text')}): "
                    f"{dim.get('description', '')}"
                )
        template_clause = (
            "\nThe following dimensions MUST be included in your output "
            "(they come from matched taxonomy templates). Include them exactly "
            "as specified, plus any additional dimensions you discover:\n"
            + "\n".join(required_dims) + "\n"
        )

    prompt = (
        f"These documents are of type: \"{doc_type}\"\n"
        f"{context_clause}\n"
        f"Sample content from the documents:\n{combined_sample}\n\n"
        f"{template_clause}"
        "Based on the document type and sample content, identify all the key "
        "dimensions (fields/attributes) that should be extracted from each document. "
        "For each dimension, provide:\n"
        "- name: a short, snake_case field name\n"
        "- description: what this dimension represents\n"
        "- expected_type: one of [text, number, date, currency, entity, "
        "entity_list, text_list, date_range]\n\n"
        "Return a JSON array of objects with keys: name, description, expected_type.\n"
        "Return ONLY the JSON array, no other text."
    )

    system = (
        "You are a data schema expert. Given a document type and sample content, "
        "you discover the taxonomy of information dimensions that should be extracted "
        "from each document. Be thorough but practical — include dimensions that are "
        "likely present across most documents of this type."
    )

    response_text = await llm_call(
        prompt=prompt,
        system=system,
        response_format={"type": "json_object"},
    )

    dimensions = parse_json_response(response_text)

    # If the LLM wrapped it in an object, extract the array
    if isinstance(dimensions, dict):
        # Look for the first list value in the dict
        for value in dimensions.values():
            if isinstance(value, list):
                dimensions = value
                break

    # Validate dimension structure
    valid_types = {
        "text", "number", "date", "currency",
        "entity", "entity_list", "text_list", "date_range",
    }
    validated = []
    for dim in dimensions:
        if isinstance(dim, dict) and "name" in dim:
            dim.setdefault("description", "")
            dim.setdefault("expected_type", "text")
            if dim["expected_type"] not in valid_types:
                dim["expected_type"] = "text"
            validated.append({
                "name": dim["name"],
                "description": dim["description"],
                "expected_type": dim["expected_type"],
            })
    dimensions = validated

    # Create TaxonomySchema record
    schema = TaxonomySchema(
        corpus_id=corpus_id,
        dimensions=dimensions,
        doc_type=doc_type,
        company_context=company_context,
    )
    db.add(schema)
    db.commit()
    db.refresh(schema)

    return schema
