"""Query classification for the hybrid chat engine."""

from enum import Enum

from backend.pipeline.llm import llm_call, parse_json_response


class QueryType(Enum):
    FACT_LOOKUP = "fact_lookup"  # "What was Company X's revenue in Q2?"
    CROSS_DOC = "cross_doc_comparison"  # "How did revenue change between March and August?"
    ENTITY_QUERY = "entity_query"  # "What reports mention Tan Kim Bock?"
    TEMPORAL = "temporal_query"  # "What's the latest info on risk factors?"
    OPEN_ENDED = "open_ended"  # "Summarize the company's trajectory"


_CLASSIFICATION_SYSTEM = (
    "You are a query classifier for a document analysis system. "
    "Classify the user's query into exactly one of the following types. "
    "Respond with ONLY a JSON object: {\"query_type\": \"<type>\"}\n\n"
    "Types:\n"
    "- fact_lookup: Looking up a specific fact or value from a document. "
    "Example: \"What was Company X's revenue in Q2?\"\n"
    "- cross_doc_comparison: Comparing data across multiple documents or time periods. "
    "Example: \"How did revenue change between March and August?\"\n"
    "- entity_query: Asking about a specific person, company, or entity and their appearances. "
    "Example: \"What reports mention Tan Kim Bock?\"\n"
    "- temporal_query: Asking for the most recent or time-ordered information. "
    "Example: \"What's the latest info on risk factors?\"\n"
    "- open_ended: Broad summaries, analysis, or opinion-like questions. "
    "Example: \"Summarize the company's trajectory\"\n"
)

# Map string values back to enum members for fast lookup
_TYPE_MAP = {t.value: t for t in QueryType}


async def classify_query(query: str) -> QueryType:
    """Use LLM to classify the query type. Returns QueryType."""
    response = await llm_call(
        prompt=query,
        system=_CLASSIFICATION_SYSTEM,
    )
    try:
        parsed = parse_json_response(response)
        query_type_str = parsed.get("query_type", "open_ended")
    except Exception:
        # Fallback: try to find a known type string in the raw response
        query_type_str = "open_ended"
        lower = response.lower()
        for qt in QueryType:
            if qt.value in lower:
                query_type_str = qt.value
                break

    return _TYPE_MAP.get(query_type_str, QueryType.OPEN_ENDED)
