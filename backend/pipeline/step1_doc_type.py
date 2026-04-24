"""Step 1: Document Type Detection & Report Date Extraction.

Analyzes sample text from ingested documents to determine what type
of documents they are (e.g., "Quarterly Investor Report for a Public Company")
and extracts the report date/period for each document.
"""

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from backend.ingestion.common import IngestedDocument
from backend.models import Document
from backend.pipeline.llm import llm_call, parse_json_response

logger = logging.getLogger(__name__)


async def detect_doc_type(
    documents: list[IngestedDocument],
    document_ids: list[str],
    db: Session,
) -> str:
    """Detect the document type and extract report dates from ingested documents.

    Sends a single LLM call with sample text from the first ~2 pages
    of each document to determine the overall document type and extract
    each document's report date/period.

    Args:
        documents: List of IngestedDocument objects.
        document_ids: List of Document DB record IDs (parallel to documents).
        db: SQLAlchemy session.

    Returns:
        A doc_type string describing the document collection.
    """
    # Build a mapping from filename to document_id for DB updates
    filename_to_id: dict[str, str] = {}
    for doc, doc_id in zip(documents, document_ids):
        filename_to_id[doc.original_filename] = doc_id

    # Build sample text from first ~2 pages of each document
    samples = []
    for doc in documents:
        text = doc.text or ""
        # Take roughly the first 2 pages worth of text (~600 words)
        words = text.split()
        sample = " ".join(words[:600])
        samples.append(f"--- Document: {doc.original_filename} ---\n{sample}")

    combined_sample = "\n\n".join(samples)

    prompt = (
        "Below are excerpts from a set of uploaded documents.\n\n"
        "1. What type of documents are these? Be specific.\n"
        "2. For EACH document, extract the report date or reporting period "
        "(the date the document covers or was authored). Use ISO 8601 format "
        "(YYYY-MM-DD). If the document covers a period/quarter, use the end date "
        "of that period. If you cannot determine the date, use null.\n\n"
        "Return your answer as JSON with this exact structure:\n"
        "{\n"
        '  "doc_type": "short phrase describing document type",\n'
        '  "document_dates": [\n'
        '    {"filename": "example.pdf", "date": "2024-03-31"},\n'
        '    {"filename": "other.pdf", "date": null}\n'
        "  ]\n"
        "}\n\n"
        f"{combined_sample}"
    )

    system = (
        "You are a document classification expert. Given sample text from documents, "
        "identify the specific document type and extract report dates. "
        "Be precise and descriptive. Always respond with valid JSON only."
    )

    raw_response = await llm_call(prompt=prompt, system=system)

    # Parse the structured JSON response
    try:
        parsed = parse_json_response(raw_response)
    except Exception:
        # Fallback: treat entire response as doc_type, no dates extracted
        logger.warning("Failed to parse JSON from step1 LLM response, falling back to plain text")
        doc_type = raw_response.strip().strip('"').strip("'")
        for doc_id in document_ids:
            db_doc = db.query(Document).filter(Document.id == doc_id).first()
            if db_doc:
                db_doc.detected_doc_type = doc_type
        db.commit()
        return doc_type

    doc_type = str(parsed.get("doc_type", "")).strip().strip('"').strip("'")
    document_dates = parsed.get("document_dates", [])

    # Build a lookup from filename to extracted date string
    date_by_filename: dict[str, str | None] = {}
    for entry in document_dates:
        fname = entry.get("filename")
        date_str = entry.get("date")
        if fname:
            date_by_filename[fname] = date_str

    # Update each Document record with detected type and report date
    for doc, doc_id in zip(documents, document_ids):
        db_doc = db.query(Document).filter(Document.id == doc_id).first()
        if not db_doc:
            continue
        db_doc.detected_doc_type = doc_type

        date_str = date_by_filename.get(doc.original_filename)
        if date_str:
            try:
                db_doc.report_date = datetime.fromisoformat(date_str)
            except (ValueError, TypeError):
                logger.warning(
                    "Could not parse date %r for document %s",
                    date_str,
                    doc.original_filename,
                )
    db.commit()

    return doc_type
