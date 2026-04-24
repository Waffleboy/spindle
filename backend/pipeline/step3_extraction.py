"""Step 3: Per-Document Extraction with chunking and embedding.

For each document, extracts dimension values from the taxonomy schema,
chunks the document text, and generates embeddings for each chunk.
"""

import base64
import io
import uuid
import zlib

import litellm
import numpy as np
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from backend.ingestion.common import IngestedDocument
from backend.models import DocumentChunk, Extraction, TaxonomySchema
from backend.pipeline.chunking import chunk_text
from backend.pipeline.llm import llm_call, parse_json_response


def _images_to_base64(pages: list) -> list[str]:
    """Convert a list of PIL images to base64-encoded PNG strings."""
    result = []
    for img in pages:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        result.append(b64)
    return result


def _uuid_to_fts_rowid(chunk_uuid: str) -> int:
    """Convert a UUID string to a positive integer for FTS5 rowid.

    Uses CRC32 to get a 32-bit positive integer from the UUID.
    Collisions are unlikely at small scale and FTS is supplementary.
    """
    return zlib.crc32(chunk_uuid.encode()) & 0x7FFFFFFF


async def extract_document(
    document: IngestedDocument,
    document_id: str,
    taxonomy: TaxonomySchema,
    db: Session,
) -> list[Extraction]:
    """Extract taxonomy dimensions from a single document.

    Also handles chunking the document text and generating embeddings
    for each chunk.

    Args:
        document: The ingested document.
        document_id: The Document DB record ID.
        taxonomy: The TaxonomySchema with dimensions to extract.
        db: SQLAlchemy session.

    Returns:
        List of Extraction records created.
    """
    # Build the extraction prompt
    dimensions_desc = "\n".join(
        f"- {d['name']} ({d['expected_type']}): {d['description']}"
        for d in taxonomy.dimensions
    )

    prompt = (
        f"Extract the following dimensions from this document:\n{dimensions_desc}\n\n"
        "For each dimension, provide the extracted value. "
        "If a value is not found, use null. "
        "For entity_list and text_list types, return arrays. "
        "For currency type, include the currency symbol/code. "
        "For date_range, return an object with 'start' and 'end' keys.\n\n"
        "Return a JSON object where each key is the dimension name and the value "
        "is an object with 'value' (the extracted data), 'confidence' (0.0-1.0), "
        "and 'source_pages' (list of page numbers where found, or null).\n"
        "Return ONLY the JSON object."
    )

    # Determine if we use multimodal (PDF with pages) or text-only
    images = None
    if document.file_type == "pdf" and document.pages:
        images = _images_to_base64(document.pages)
        prompt = f"Document: {document.original_filename}\n\n{prompt}"
    else:
        text_content = document.text or ""
        prompt = (
            f"Document: {document.original_filename}\n\n"
            f"Document content:\n{text_content}\n\n{prompt}"
        )

    system = (
        "You are a precise document data extraction assistant. "
        "Extract structured information from documents according to the specified dimensions. "
        "Be accurate and include confidence scores."
    )

    response_text = await llm_call(
        prompt=prompt,
        system=system,
        images=images,
        response_format={"type": "json_object"},
    )

    extracted_data = parse_json_response(response_text)

    # Create Extraction records
    extractions = []
    for dim in taxonomy.dimensions:
        dim_name = dim["name"]
        dim_data = extracted_data.get(dim_name, {})

        if isinstance(dim_data, dict):
            raw_value = dim_data.get("value")
            confidence = dim_data.get("confidence", 0.5)
            source_pages = dim_data.get("source_pages")
        else:
            # LLM returned just the value directly
            raw_value = dim_data
            confidence = 0.5
            source_pages = None

        # Convert raw_value to string for storage
        if raw_value is None:
            raw_value_str = ""
        elif isinstance(raw_value, (list, dict)):
            import json
            raw_value_str = json.dumps(raw_value)
        else:
            raw_value_str = str(raw_value)

        extraction = Extraction(
            document_id=document_id,
            taxonomy_schema_id=taxonomy.id,
            dimension_name=dim_name,
            raw_value=raw_value_str,
            confidence=float(confidence),
            source_pages=source_pages,
        )
        db.add(extraction)
        extractions.append(extraction)

    db.commit()
    for ext in extractions:
        db.refresh(ext)

    # --- Chunking and Embedding ---
    await _chunk_and_embed(document, document_id, db)

    return extractions


async def _chunk_and_embed(
    document: IngestedDocument,
    document_id: str,
    db: Session,
) -> list[DocumentChunk]:
    """Chunk the document text and generate embeddings for each chunk.

    Args:
        document: The ingested document.
        document_id: The Document DB record ID.
        db: SQLAlchemy session.

    Returns:
        List of DocumentChunk records created.
    """
    text = document.text or ""
    if not text.strip():
        return []

    chunks = chunk_text(text)
    if not chunks:
        return []

    # Batch embed all chunks at once for efficiency
    chunk_texts = [c["text"] for c in chunks]
    from backend.config import get_settings

    cfg = get_settings()
    embed_kwargs = {"model": cfg.embedding_model, "input": chunk_texts}
    if cfg.litellm_api_base:
        embed_kwargs["api_base"] = cfg.litellm_api_base
    if cfg.litellm_api_key:
        embed_kwargs["api_key"] = cfg.litellm_api_key

    embedding_response = await litellm.aembedding(**embed_kwargs)

    db_chunks = []
    for i, chunk_data in enumerate(chunks):
        embedding_vector = embedding_response.data[i]["embedding"]
        embedding_bytes = np.array(embedding_vector, dtype=np.float32).tobytes()

        chunk_id = str(uuid.uuid4())
        db_chunk = DocumentChunk(
            id=chunk_id,
            document_id=document_id,
            chunk_text=chunk_data["text"],
            chunk_index=chunk_data["chunk_index"],
            source_pages=chunk_data["approx_pages"],
            embedding=embedding_bytes,
        )
        db.add(db_chunk)
        db_chunks.append(db_chunk)

    db.commit()

    # Populate FTS5 index
    for db_chunk in db_chunks:
        fts_rowid = _uuid_to_fts_rowid(db_chunk.id)
        db.execute(
            sql_text(
                "INSERT INTO document_chunks_fts(rowid, chunk_text) "
                "VALUES (:rowid, :text)"
            ),
            {"rowid": fts_rowid, "text": db_chunk.chunk_text},
        )
    db.commit()

    return db_chunks
