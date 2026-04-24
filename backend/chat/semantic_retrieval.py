"""Semantic/lexical retrieval path: hybrid BM25 + embedding search."""

import numpy as np
import litellm
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models import Document, DocumentChunk


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _fts5_search(query: str, db: Session, top_k: int) -> list[dict]:
    """Run FTS5 MATCH query on document_chunks_fts.

    Returns list of dicts with chunk_id (rowid), chunk_text, and rank.
    """
    # Escape FTS5 special characters by quoting terms
    # Simple approach: wrap each word in double quotes to avoid syntax errors
    safe_terms = []
    for word in query.split():
        cleaned = word.strip('",;:!?()[]{}')
        if cleaned:
            safe_terms.append(f'"{cleaned}"')
    if not safe_terms:
        return []

    fts_query = " OR ".join(safe_terms)

    try:
        rows = db.execute(
            text(
                "SELECT rowid, chunk_text, rank "
                "FROM document_chunks_fts "
                "WHERE document_chunks_fts MATCH :query "
                "ORDER BY rank "
                "LIMIT :limit"
            ),
            {"query": fts_query, "limit": top_k},
        ).fetchall()
    except Exception:
        # FTS5 query can fail on malformed input; return empty gracefully
        return []

    results = []
    for row in rows:
        results.append({
            "rowid": row[0],
            "chunk_text": row[1],
            "rank": row[2],
        })
    return results


async def _embedding_search(
    query: str, db: Session, top_k: int
) -> list[dict]:
    """Embed the query and compute cosine similarity against stored chunks."""
    cfg = get_settings()
    embed_kwargs = {"model": cfg.embedding_model, "input": [query]}
    if cfg.litellm_api_base:
        embed_kwargs["api_base"] = cfg.litellm_api_base
    if cfg.litellm_api_key:
        embed_kwargs["api_key"] = cfg.litellm_api_key

    response = await litellm.aembedding(**embed_kwargs)
    query_embedding = np.array(response.data[0]["embedding"], dtype=np.float32)

    # Load all chunks with embeddings
    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.embedding.isnot(None))
        .all()
    )

    scored = []
    for chunk in chunks:
        chunk_embedding = np.frombuffer(chunk.embedding, dtype=np.float32)
        score = _cosine_similarity(query_embedding, chunk_embedding)
        scored.append((chunk, score))

    # Sort by score descending and take top_k
    scored.sort(key=lambda x: x[1], reverse=True)
    return [
        {"chunk": c, "score": s}
        for c, s in scored[:top_k]
    ]


def _chunk_to_result(
    chunk: DocumentChunk, doc: Document, score: float, source_detail: str
) -> dict:
    """Convert a chunk into a standardized result dict."""
    return {
        "source": "semantic",
        "text": chunk.chunk_text,
        "document": doc.original_filename,
        "pages": chunk.source_pages,
        "score": score,
        "source_detail": source_detail,
    }


async def semantic_search(
    query: str, db: Session, top_k: int | None = None
) -> list[dict]:
    """Hybrid BM25 + embedding search against document_chunks.

    Returns list of {source: "semantic", text: ..., document: ..., pages: ..., score: ...}
    """
    top_k = top_k if top_k is not None else get_settings().semantic_search_top_k
    results_map: dict[str, dict] = {}  # keyed by chunk.id to deduplicate

    # --- BM25 / FTS5 path ---
    fts_results = _fts5_search(query, db, top_k=top_k * 2)
    for fts_row in fts_results:
        # FTS5 rowid maps to the chunk table's rowid (integer auto-id)
        # We need to find the chunk by matching text since FTS5 content-less tables
        # don't store the original rowid reliably.
        chunk = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.chunk_text == fts_row["chunk_text"])
            .first()
        )
        if chunk and chunk.id not in results_map:
            doc = db.query(Document).filter(Document.id == chunk.document_id).first()
            if doc:
                # Normalize FTS5 rank (negative, lower is better) to a 0-1 score
                fts_score = 1.0 / (1.0 + abs(fts_row["rank"]))
                results_map[chunk.id] = _chunk_to_result(
                    chunk, doc, fts_score, "fts5"
                )

    # --- Embedding path ---
    try:
        emb_results = await _embedding_search(query, db, top_k=top_k * 2)
        for item in emb_results:
            chunk = item["chunk"]
            emb_score = item["score"]
            if chunk.id in results_map:
                # Combine scores: boost items found by both methods
                existing = results_map[chunk.id]
                existing["score"] = existing["score"] + emb_score
                existing["source_detail"] = "fts5+embedding"
            else:
                doc = (
                    db.query(Document)
                    .filter(Document.id == chunk.document_id)
                    .first()
                )
                if doc:
                    results_map[chunk.id] = _chunk_to_result(
                        chunk, doc, emb_score, "embedding"
                    )
    except Exception:
        # If embedding fails (no API key, etc.), proceed with FTS5 results only
        pass

    # Sort by combined score descending
    all_results = sorted(results_map.values(), key=lambda r: r["score"], reverse=True)
    return all_results[:top_k]
