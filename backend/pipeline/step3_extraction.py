"""Step 3: Per-Document Extraction with chunking and embedding.

For each document, extracts dimension values from the taxonomy schema,
chunks the document text, and generates embeddings for each chunk.
"""

import asyncio
import base64
import io
import uuid
import zlib

import litellm
import numpy as np
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.ingestion.common import IngestedDocument
from backend.models import DocumentChunk, Extraction, TaxonomySchema
from backend.pipeline.chunking import chunk_text
from backend.pipeline.llm import llm_call, parse_json_response


def _get_semaphores() -> tuple[asyncio.Semaphore, asyncio.Semaphore]:
    cfg = get_settings()
    return asyncio.Semaphore(cfg.llm_concurrency), asyncio.Semaphore(cfg.embedding_concurrency)


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


async def fetch_extraction_data(
    document: IngestedDocument,
    taxonomy: TaxonomySchema,
) -> tuple[dict, list[dict] | None, list[float] | None]:
    """Run LLM extraction + embedding calls without touching the DB.

    Returns:
        (extracted_data, chunks_with_embeddings)
        where chunks_with_embeddings is a list of dicts with keys
        text, chunk_index, approx_pages, embedding_bytes — or None if no text.
    """
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

    cfg = get_settings()
    llm_sem, embed_sem = _get_semaphores()

    async def _guarded_llm():
        async with llm_sem:
            return await llm_call(
                prompt=prompt,
                system=system,
                images=images,
                response_format={"type": "json_object"},
            )

    async def _guarded_embed():
        if not cfg.enable_embeddings:
            return None
        async with embed_sem:
            return await _fetch_embeddings(document)

    response_text, chunks_with_embeddings = await asyncio.gather(
        _guarded_llm(), _guarded_embed()
    )

    extracted_data = parse_json_response(response_text)

    # The LLM may wrap dimension data in an outer object (e.g. {"extractions": {...}}).
    # Unwrap: if none of the top-level keys match a dimension name, look one level deeper.
    if isinstance(extracted_data, dict):
        dim_names = {d["name"] for d in taxonomy.dimensions}
        if not (extracted_data.keys() & dim_names):
            for value in extracted_data.values():
                if isinstance(value, dict) and (value.keys() & dim_names):
                    extracted_data = value
                    break

    return extracted_data, chunks_with_embeddings


async def _fetch_embeddings(document: IngestedDocument) -> list[dict] | None:
    """Chunk text and fetch embeddings without DB writes."""
    text = document.text or ""
    if not text.strip():
        return None

    chunks = chunk_text(text)
    if not chunks:
        return None

    chunk_texts = [c["text"] for c in chunks]
    cfg = get_settings()
    embed_kwargs = {"model": cfg.embedding_model, "input": chunk_texts}
    if cfg.litellm_api_base:
        embed_kwargs["api_base"] = cfg.litellm_api_base
    if cfg.litellm_api_key:
        embed_kwargs["api_key"] = cfg.litellm_api_key

    embedding_response = await litellm.aembedding(**embed_kwargs)

    result = []
    for i, chunk_data in enumerate(chunks):
        embedding_vector = embedding_response.data[i]["embedding"]
        embedding_bytes = np.array(embedding_vector, dtype=np.float32).tobytes()
        result.append({
            "text": chunk_data["text"],
            "chunk_index": chunk_data["chunk_index"],
            "approx_pages": chunk_data["approx_pages"],
            "embedding_bytes": embedding_bytes,
        })
    return result


def save_extraction_results(
    document_id: str,
    taxonomy: TaxonomySchema,
    extracted_data: dict,
    chunks_with_embeddings: list[dict] | None,
    db: Session,
) -> list[Extraction]:
    """Write extraction + chunk/embedding results to DB. Called sequentially."""
    import json as json_mod

    extractions = []
    for dim in taxonomy.dimensions:
        dim_name = dim["name"]
        dim_data = extracted_data.get(dim_name, {})

        if isinstance(dim_data, dict):
            raw_value = dim_data.get("value")
            confidence = dim_data.get("confidence", 0.5)
            source_pages = dim_data.get("source_pages")
        else:
            raw_value = dim_data
            confidence = 0.5
            source_pages = None

        if raw_value is None:
            raw_value_str = ""
        elif isinstance(raw_value, (list, dict)):
            raw_value_str = json_mod.dumps(raw_value)
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

    if chunks_with_embeddings:
        db_chunks = []
        for cdata in chunks_with_embeddings:
            chunk_id = str(uuid.uuid4())
            db_chunk = DocumentChunk(
                id=chunk_id,
                document_id=document_id,
                chunk_text=cdata["text"],
                chunk_index=cdata["chunk_index"],
                source_pages=cdata["approx_pages"],
                embedding=cdata["embedding_bytes"],
            )
            db.add(db_chunk)
            db_chunks.append(db_chunk)

        db.commit()

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
    for ext in extractions:
        db.refresh(ext)

    return extractions


async def extract_document(
    document: IngestedDocument,
    document_id: str,
    taxonomy: TaxonomySchema,
    db: Session,
) -> list[Extraction]:
    """Extract taxonomy dimensions from a single document (sequential fallback).

    Prefer fetch_extraction_data + save_extraction_results for parallel pipelines.
    """
    extracted_data, chunks_with_embeddings = await fetch_extraction_data(document, taxonomy)
    return save_extraction_results(document_id, taxonomy, extracted_data, chunks_with_embeddings, db)
