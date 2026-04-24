"""Chat engine: orchestrates classification, retrieval, and response generation."""

import asyncio
import re

from sqlalchemy.orm import Session

from backend.chat.classifier import QueryType, classify_query
from backend.chat.semantic_retrieval import semantic_search
from backend.chat.structured_retrieval import structured_search
from backend.config import get_settings
from backend.models import Extraction, Document
from backend.pipeline.llm import llm_call

# Module-level session storage (simple dict for hackathon)
_chat_sessions: dict[str, list[dict]] = {}

_RESPONSE_SYSTEM = (
    "You are a helpful document analysis assistant. Answer the user's question "
    "using ONLY the provided context. Follow these rules:\n"
    "1. Prefer structured taxonomy data for factual answers.\n"
    "2. Supplement with raw document content when taxonomy data is insufficient.\n"
    "3. Include citations in format [Doc: filename, p.X] for every claim.\n"
    "4. If a contradiction exists between documents, mention it explicitly.\n"
    "5. If the context does not contain enough information to answer, say so.\n"
    "6. Be concise and direct.\n"
    "7. When multiple documents contain values for the same dimension, prefer the "
    "most recent document's value. Note the document date in your answer.\n"
    "8. When your answer references a fact that has a known contradiction across "
    "documents, include a note like: 'Note: this value (X from the [date] report) "
    "differs from Y in the [date] report.'\n"
)


def _format_structured_context(results: list[dict]) -> str:
    """Format structured retrieval results into a text block for the LLM."""
    if not results:
        return ""
    lines = ["=== Structured Taxonomy Data ==="]
    for r in results:
        if r.get("type") == "contradiction":
            data = r["data"]
            contradiction_line = (
                f"CONTRADICTION on '{data['dimension_name']}': "
                f"'{data['value_a']}' (in {r['document_a']}) vs "
                f"'{data['value_b']}' (in {r['document_b']}). "
                f"Status: {data['resolution_status']}"
            )
            if r.get("temporal_context"):
                contradiction_line += f" | {r['temporal_context']}"
            lines.append(contradiction_line)
        else:
            data = r["data"]
            value = data.get("resolved_value") or data.get("raw_value", "N/A")
            pages = r.get("pages") or []
            page_str = ", ".join(f"p.{p}" for p in pages) if pages else "N/A"
            # Format date with appropriate prefix based on whether it's extracted or approximate
            date_str = ""
            if r.get("document_date"):
                prefix = "uploaded" if r.get("is_approximate_date") else "dated"
                date_str = f" ({prefix}: {r['document_date'][:10]})"
            lines.append(
                f"- {data['dimension_name']}: {value} "
                f"[Doc: {r['document']}{date_str}, {page_str}] "
                f"(confidence: {data.get('confidence', 'N/A')})"
            )
    return "\n".join(lines)


def _format_semantic_context(results: list[dict]) -> str:
    """Format semantic retrieval results into a text block for the LLM."""
    if not results:
        return ""
    lines = ["=== Document Content (Semantic Search) ==="]
    for r in results:
        pages = r.get("pages") or []
        page_str = ", ".join(f"p.{p}" for p in pages) if pages else "N/A"
        lines.append(
            f"--- From {r['document']} ({page_str}) ---\n"
            f"{r['text']}\n"
        )
    return "\n".join(lines)


def _format_chat_history(session_id: str) -> str:
    """Format recent chat history for context."""
    history = _chat_sessions.get(session_id, [])
    if not history:
        return ""
    recent = history[-get_settings().chat_history_limit:]
    lines = ["=== Recent Chat History ==="]
    for msg in recent:
        role = msg["role"].capitalize()
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)


def _parse_citations(response_text: str) -> list[dict]:
    """Extract citations in [Doc: filename, p.X] format from the response."""
    # Match patterns like [Doc: filename.pdf, p.3] or [Doc: filename.pdf]
    pattern = r'\[Doc:\s*([^,\]]+?)(?:,\s*p\.(\d+))?\]'
    citations = []
    seen = set()
    for match in re.finditer(pattern, response_text):
        source = match.group(1).strip()
        page = int(match.group(2)) if match.group(2) else None
        key = (source, page)
        if key not in seen:
            seen.add(key)
            citations.append({
                "type": "document",
                "source": source,
                "page": page,
                "detail": match.group(0),
            })
    return citations


def _generate_suggested_queries(
    query_type: QueryType, structured_results: list[dict]
) -> list[str]:
    """Generate suggested follow-up queries based on available taxonomy data."""
    suggestions = []
    dimensions = set()
    documents = set()

    for r in structured_results:
        if r.get("type") == "contradiction":
            continue
        data = r.get("data", {})
        dim = data.get("dimension_name")
        doc = r.get("document")
        if dim:
            dimensions.add(dim)
        if doc:
            documents.add(doc)

    dim_list = sorted(dimensions)
    doc_list = sorted(documents)

    if len(doc_list) >= 2:
        suggestions.append(
            f"How do the values compare between {doc_list[0]} and {doc_list[1]}?"
        )
    if dim_list:
        suggestions.append(f"What is the latest value for {dim_list[0]}?")
    if len(dim_list) >= 2:
        suggestions.append(
            f"Show me all data for {dim_list[0]} and {dim_list[1]}."
        )
    if doc_list:
        suggestions.append(f"Summarize the key findings from {doc_list[0]}.")

    # Limit to 3 suggestions
    return suggestions[:3]


async def chat(
    query: str,
    session_id: str = "default",
    db: Session = None,
) -> dict:
    """Process a chat query and return response with citations.

    Returns {
        response: str,
        citations: [{type, source, page, detail}],
        query_type: str,
        suggested_queries: [str]
    }
    """
    # Step 1: Classify the query
    query_type = await classify_query(query)

    # Step 2: Run structured and semantic search in parallel
    structured_task = structured_search(query, query_type, db)
    semantic_task = semantic_search(query, db)
    structured_results, semantic_results = await asyncio.gather(
        structured_task, semantic_task
    )

    # Step 3: Build context for LLM
    structured_ctx = _format_structured_context(structured_results)
    semantic_ctx = _format_semantic_context(semantic_results)
    history_ctx = _format_chat_history(session_id)

    context_parts = [p for p in [history_ctx, structured_ctx, semantic_ctx] if p]
    full_context = "\n\n".join(context_parts)

    prompt = (
        f"Context:\n{full_context}\n\n"
        f"User question: {query}\n\n"
        "Answer the question using the context above. "
        "Include [Doc: filename, p.X] citations for every factual claim."
    )

    # Step 4: Generate response via LLM
    response_text = await llm_call(prompt=prompt, system=_RESPONSE_SYSTEM)

    # Step 5: Parse citations from response
    citations = _parse_citations(response_text)

    # Also add taxonomy-sourced citations for structured results
    for r in structured_results:
        if r.get("type") == "contradiction":
            continue
        doc_name = r.get("document", "")
        pages = r.get("pages") or []
        for page in pages:
            citation = {
                "type": "taxonomy",
                "source": doc_name,
                "page": page,
                "detail": f"{r['data']['dimension_name']}: {r['data'].get('resolved_value') or r['data'].get('raw_value', '')}",
            }
            if citation not in citations:
                citations.append(citation)

    # Step 6: Store in session history
    if session_id not in _chat_sessions:
        _chat_sessions[session_id] = []
    _chat_sessions[session_id].append({"role": "user", "content": query})
    _chat_sessions[session_id].append({"role": "assistant", "content": response_text})

    # Step 7: Generate suggested follow-up queries
    suggested = _generate_suggested_queries(query_type, structured_results)

    return {
        "response": response_text,
        "citations": citations,
        "query_type": query_type.value,
        "suggested_queries": suggested,
    }
