"""Template matching: LLM decides which taxonomy templates apply to the detected documents."""

from sqlalchemy.orm import Session

from backend.models import TaxonomyTemplate
from backend.pipeline.llm import llm_call, parse_json_response


async def match_templates(
    doc_type: str,
    sample_text: str,
    db: Session,
) -> list[TaxonomyTemplate]:
    """Use an LLM call to determine which taxonomy templates apply to the documents.

    Args:
        doc_type: The detected document type from step 1.
        sample_text: Combined sample text from the documents.
        db: SQLAlchemy session.

    Returns:
        List of matching TaxonomyTemplate records (may be empty).
    """
    templates = db.query(TaxonomyTemplate).all()
    if not templates:
        return []

    template_descriptions = "\n".join(
        f'- ID: {t.id} | Label: "{t.label}" | Description: {t.description}'
        for t in templates
    )

    prompt = (
        f'The documents are of type: "{doc_type}"\n\n'
        f"Sample content:\n{sample_text[:2000]}\n\n"
        f"Available taxonomy templates:\n{template_descriptions}\n\n"
        "Which of these templates are relevant to these documents? "
        "A template is relevant if the documents would contain the kind of "
        "information described by that template. Documents can match zero, one, "
        "or multiple templates.\n\n"
        'Return a JSON object: {"matched_ids": ["id1", "id2", ...]}. '
        "Return an empty list if none match."
    )

    system = (
        "You are a document classification expert. Given a document type, "
        "sample content, and a set of taxonomy templates, determine which "
        "templates are relevant. Be inclusive — if there is a reasonable chance "
        "the documents contain information covered by a template, include it."
    )

    response_text = await llm_call(
        prompt=prompt,
        system=system,
        response_format={"type": "json_object"},
    )

    result = parse_json_response(response_text)
    matched_ids = set()
    if isinstance(result, dict):
        matched_ids = set(result.get("matched_ids", []))
    elif isinstance(result, list):
        matched_ids = set(result)

    return [t for t in templates if t.id in matched_ids]
