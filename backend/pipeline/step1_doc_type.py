"""Step 1: Document Type Detection.

Analyzes sample text from ingested documents to determine what type
of documents they are (e.g., "Quarterly Investor Report for a Public Company").
"""

from sqlalchemy.orm import Session

from backend.ingestion.common import IngestedDocument
from backend.models import Document
from backend.pipeline.llm import llm_call


async def detect_doc_type(
    documents: list[IngestedDocument],
    document_ids: list[str],
    db: Session,
) -> str:
    """Detect the document type from sample text of ingested documents.

    Sends a single LLM call with sample text from the first ~2 pages
    of each document to determine the overall document type.

    Args:
        documents: List of IngestedDocument objects.
        document_ids: List of Document DB record IDs (parallel to documents).
        db: SQLAlchemy session.

    Returns:
        A doc_type string describing the document collection.
    """
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
        "Below are excerpts from a set of uploaded documents. "
        "What type of documents are these? Be specific about the document type. "
        "Return ONLY the document type as a short phrase, nothing else.\n\n"
        f"{combined_sample}"
    )

    system = (
        "You are a document classification expert. Given sample text from documents, "
        "identify the specific document type. Be precise and descriptive."
    )

    doc_type = await llm_call(prompt=prompt, system=system)
    doc_type = doc_type.strip().strip('"').strip("'")

    # Update each Document record with the detected type
    for doc_id in document_ids:
        db_doc = db.query(Document).filter(Document.id == doc_id).first()
        if db_doc:
            db_doc.detected_doc_type = doc_type
    db.commit()

    return doc_type
