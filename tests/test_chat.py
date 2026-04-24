"""Tests for the hybrid chat engine.

All LLM calls are mocked -- no real API calls are made.
Uses an in-memory SQLite database for isolation.
"""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from backend.chat.classifier import QueryType, classify_query
from backend.chat.engine import _chat_sessions, _parse_citations, chat
from backend.chat.semantic_retrieval import semantic_search
from backend.chat.structured_retrieval import structured_search
from backend.database import Base
from backend.models import (
    Contradiction,
    Document,
    DocumentChunk,
    Entity,
    EntityResolution,
    Extraction,
    TaxonomySchema,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database session for testing."""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)

    # Create FTS5 virtual table (content-less for testing)
    with engine.connect() as conn:
        conn.execute(
            text(
                "CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts "
                "USING fts5(chunk_text)"
            )
        )
        conn.commit()

    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def seeded_db(db_session):
    """Seed the database with documents, taxonomy, extractions, entities, and contradictions."""
    # Documents
    doc1 = Document(
        id="doc-1",
        original_filename="report_q1_2024.pdf",
        storage_path="data/originals/report_q1_2024.pdf",
        file_type="pdf",
        page_count=10,
        uploaded_at=datetime(2024, 3, 31, tzinfo=timezone.utc),
    )
    doc2 = Document(
        id="doc-2",
        original_filename="report_q2_2024.pdf",
        storage_path="data/originals/report_q2_2024.pdf",
        file_type="pdf",
        page_count=12,
        uploaded_at=datetime(2024, 6, 30, tzinfo=timezone.utc),
    )
    db_session.add_all([doc1, doc2])
    db_session.commit()

    # Taxonomy
    taxonomy = TaxonomySchema(
        id="tax-1",
        corpus_id="corpus-1",
        dimensions=[
            {"name": "revenue", "description": "Total revenue", "expected_type": "currency"},
            {"name": "ceo", "description": "CEO name", "expected_type": "entity"},
        ],
        doc_type="Quarterly Report",
    )
    db_session.add(taxonomy)
    db_session.commit()

    # Extractions
    ext1 = Extraction(
        id="ext-1",
        document_id="doc-1",
        taxonomy_schema_id="tax-1",
        dimension_name="revenue",
        raw_value="$5.2 billion",
        resolved_value="$5.2 billion",
        source_pages=[1, 2],
        confidence=0.95,
    )
    ext2 = Extraction(
        id="ext-2",
        document_id="doc-2",
        taxonomy_schema_id="tax-1",
        dimension_name="revenue",
        raw_value="$5.5 billion",
        resolved_value="$5.5 billion",
        source_pages=[1],
        confidence=0.92,
    )
    ext3 = Extraction(
        id="ext-3",
        document_id="doc-1",
        taxonomy_schema_id="tax-1",
        dimension_name="ceo",
        raw_value="John Smith",
        resolved_value="John Smith",
        source_pages=[1],
        confidence=0.99,
    )
    ext4 = Extraction(
        id="ext-4",
        document_id="doc-2",
        taxonomy_schema_id="tax-1",
        dimension_name="ceo",
        raw_value="J. Smith",
        resolved_value="John Smith",
        source_pages=[1],
        confidence=0.90,
    )
    db_session.add_all([ext1, ext2, ext3, ext4])
    db_session.commit()

    # Entity
    entity = Entity(
        id="ent-1",
        canonical_name="John Smith",
        entity_type="person",
        aliases=["John Smith", "J. Smith"],
    )
    db_session.add(entity)
    db_session.commit()

    # Entity resolutions
    er1 = EntityResolution(
        id="er-1",
        entity_id="ent-1",
        original_value="John Smith",
        document_id="doc-1",
        confidence=0.99,
    )
    er2 = EntityResolution(
        id="er-2",
        entity_id="ent-1",
        original_value="J. Smith",
        document_id="doc-2",
        confidence=0.85,
    )
    db_session.add_all([er1, er2])
    db_session.commit()

    # Contradiction
    contradiction = Contradiction(
        id="contra-1",
        dimension_name="revenue",
        entity_id=None,
        doc_a_id="doc-1",
        doc_b_id="doc-2",
        value_a="$5.2 billion",
        value_b="$5.5 billion",
        doc_a_date=datetime(2024, 3, 31, tzinfo=timezone.utc),
        doc_b_date=datetime(2024, 6, 30, tzinfo=timezone.utc),
        resolution_status="unresolved",
    )
    db_session.add(contradiction)
    db_session.commit()

    # Document chunks with embeddings
    emb1 = np.random.randn(16).astype(np.float32)
    emb2 = np.random.randn(16).astype(np.float32)
    chunk1 = DocumentChunk(
        id="chunk-1",
        document_id="doc-1",
        chunk_text="Acme Corp Q1 2024 revenue was $5.2 billion up 12% year over year",
        chunk_index=0,
        source_pages=[1, 2],
        embedding=emb1.tobytes(),
    )
    chunk2 = DocumentChunk(
        id="chunk-2",
        document_id="doc-2",
        chunk_text="Acme Corp Q2 2024 revenue reached $5.5 billion with strong growth",
        chunk_index=0,
        source_pages=[1],
        embedding=emb2.tobytes(),
    )
    db_session.add_all([chunk1, chunk2])
    db_session.commit()

    # Insert into FTS5 table
    db_session.execute(
        text("INSERT INTO document_chunks_fts(chunk_text) VALUES (:t)"),
        {"t": chunk1.chunk_text},
    )
    db_session.execute(
        text("INSERT INTO document_chunks_fts(chunk_text) VALUES (:t)"),
        {"t": chunk2.chunk_text},
    )
    db_session.commit()

    return db_session


@pytest.fixture(autouse=True)
def clear_chat_sessions():
    """Clear chat sessions between tests."""
    _chat_sessions.clear()
    yield
    _chat_sessions.clear()


def _make_embedding_response(dim: int = 16):
    """Create a mock litellm embedding response."""
    response = MagicMock()
    embedding_obj = {"embedding": np.random.randn(dim).tolist()}
    response.data = [embedding_obj]
    return response


# ---------------------------------------------------------------------------
# Tests: Query Classification
# ---------------------------------------------------------------------------


class TestClassifyQuery:
    @pytest.mark.asyncio
    async def test_fact_lookup(self):
        with patch("backend.chat.classifier.llm_call", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = '{"query_type": "fact_lookup"}'
            result = await classify_query("What was the revenue in Q2?")
            assert result == QueryType.FACT_LOOKUP

    @pytest.mark.asyncio
    async def test_cross_doc(self):
        with patch("backend.chat.classifier.llm_call", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = '{"query_type": "cross_doc_comparison"}'
            result = await classify_query("How did revenue change between Q1 and Q2?")
            assert result == QueryType.CROSS_DOC

    @pytest.mark.asyncio
    async def test_entity_query(self):
        with patch("backend.chat.classifier.llm_call", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = '{"query_type": "entity_query"}'
            result = await classify_query("What reports mention John Smith?")
            assert result == QueryType.ENTITY_QUERY

    @pytest.mark.asyncio
    async def test_temporal_query(self):
        with patch("backend.chat.classifier.llm_call", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = '{"query_type": "temporal_query"}'
            result = await classify_query("What's the latest info on risk factors?")
            assert result == QueryType.TEMPORAL

    @pytest.mark.asyncio
    async def test_open_ended(self):
        with patch("backend.chat.classifier.llm_call", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = '{"query_type": "open_ended"}'
            result = await classify_query("Summarize the company's trajectory")
            assert result == QueryType.OPEN_ENDED

    @pytest.mark.asyncio
    async def test_fallback_on_invalid_json(self):
        with patch("backend.chat.classifier.llm_call", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "I'm not sure, maybe fact_lookup?"
            result = await classify_query("What was revenue?")
            assert result == QueryType.FACT_LOOKUP

    @pytest.mark.asyncio
    async def test_fallback_on_completely_unknown(self):
        with patch("backend.chat.classifier.llm_call", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Something completely irrelevant"
            result = await classify_query("test query")
            assert result == QueryType.OPEN_ENDED

    @pytest.mark.asyncio
    async def test_markdown_wrapped_json(self):
        with patch("backend.chat.classifier.llm_call", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = '```json\n{"query_type": "temporal_query"}\n```'
            result = await classify_query("What's the latest report?")
            assert result == QueryType.TEMPORAL


# ---------------------------------------------------------------------------
# Tests: Structured Retrieval
# ---------------------------------------------------------------------------


class TestStructuredRetrieval:
    @pytest.mark.asyncio
    async def test_fact_lookup_finds_matching_extractions(self, seeded_db):
        results = await structured_search("revenue", QueryType.FACT_LOOKUP, seeded_db)
        taxonomy_results = [r for r in results if r.get("type") != "contradiction"]
        assert len(taxonomy_results) >= 2
        # Should find revenue extractions
        revenues = [r for r in taxonomy_results if r["data"]["dimension_name"] == "revenue"]
        assert len(revenues) == 2

    @pytest.mark.asyncio
    async def test_fact_lookup_includes_contradictions(self, seeded_db):
        results = await structured_search("revenue", QueryType.FACT_LOOKUP, seeded_db)
        contradictions = [r for r in results if r.get("type") == "contradiction"]
        assert len(contradictions) == 1
        assert contradictions[0]["data"]["dimension_name"] == "revenue"

    @pytest.mark.asyncio
    async def test_cross_doc_returns_all_extractions(self, seeded_db):
        results = await structured_search("revenue comparison", QueryType.CROSS_DOC, seeded_db)
        taxonomy_results = [r for r in results if r.get("type") != "contradiction"]
        assert len(taxonomy_results) == 4  # all extractions across both docs

    @pytest.mark.asyncio
    async def test_entity_query_finds_john_smith(self, seeded_db):
        results = await structured_search("john smith", QueryType.ENTITY_QUERY, seeded_db)
        taxonomy_results = [r for r in results if r.get("type") != "contradiction"]
        assert len(taxonomy_results) >= 2  # extractions from both documents

    @pytest.mark.asyncio
    async def test_temporal_returns_newest_first(self, seeded_db):
        results = await structured_search("latest revenue", QueryType.TEMPORAL, seeded_db)
        taxonomy_results = [r for r in results if r.get("type") != "contradiction"]
        assert len(taxonomy_results) >= 2
        # First result should be from the newer document (doc-2, June 2024)
        assert taxonomy_results[0]["document"] == "report_q2_2024.pdf"

    @pytest.mark.asyncio
    async def test_open_ended_returns_all(self, seeded_db):
        results = await structured_search("summarize everything", QueryType.OPEN_ENDED, seeded_db)
        taxonomy_results = [r for r in results if r.get("type") != "contradiction"]
        assert len(taxonomy_results) == 4  # all 4 extractions

    @pytest.mark.asyncio
    async def test_result_structure(self, seeded_db):
        results = await structured_search("revenue", QueryType.FACT_LOOKUP, seeded_db)
        taxonomy_results = [r for r in results if r.get("type") != "contradiction"]
        for r in taxonomy_results:
            assert r["source"] == "taxonomy"
            assert "data" in r
            assert "document" in r
            assert "pages" in r
            assert "dimension_name" in r["data"]
            assert "raw_value" in r["data"]
            assert "document_date" in r


# ---------------------------------------------------------------------------
# Tests: Semantic Retrieval
# ---------------------------------------------------------------------------


class TestSemanticRetrieval:
    @pytest.mark.asyncio
    async def test_fts5_search_returns_results(self, seeded_db):
        mock_emb = _make_embedding_response(dim=16)
        with patch("backend.chat.semantic_retrieval.litellm") as mock_litellm:
            mock_litellm.aembedding = AsyncMock(return_value=mock_emb)
            results = await semantic_search("revenue", seeded_db, top_k=5)
            assert len(results) >= 1
            for r in results:
                assert r["source"] == "semantic"
                assert "text" in r
                assert "document" in r
                assert "score" in r

    @pytest.mark.asyncio
    async def test_semantic_search_with_embedding(self, seeded_db):
        mock_emb = _make_embedding_response(dim=16)
        with patch("backend.chat.semantic_retrieval.litellm") as mock_litellm:
            mock_litellm.aembedding = AsyncMock(return_value=mock_emb)
            results = await semantic_search("Acme Corp revenue", seeded_db, top_k=5)
            assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_semantic_search_deduplicates(self, seeded_db):
        """Results found by both FTS5 and embedding should be deduplicated."""
        mock_emb = _make_embedding_response(dim=16)
        with patch("backend.chat.semantic_retrieval.litellm") as mock_litellm:
            mock_litellm.aembedding = AsyncMock(return_value=mock_emb)
            results = await semantic_search("revenue", seeded_db, top_k=10)
            # Should have at most 2 results (one per chunk), not duplicates
            assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_semantic_search_empty_query(self, seeded_db):
        """Empty query should return empty results gracefully."""
        mock_emb = _make_embedding_response(dim=16)
        with patch("backend.chat.semantic_retrieval.litellm") as mock_litellm:
            mock_litellm.aembedding = AsyncMock(return_value=mock_emb)
            results = await semantic_search("", seeded_db, top_k=5)
            # FTS5 won't match empty, but embedding may still return results
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_semantic_search_graceful_embedding_failure(self, seeded_db):
        """If embedding call fails, should still return FTS5 results."""
        with patch("backend.chat.semantic_retrieval.litellm") as mock_litellm:
            mock_litellm.aembedding = AsyncMock(side_effect=Exception("API error"))
            results = await semantic_search("revenue", seeded_db, top_k=5)
            # Should still have FTS5 results
            assert isinstance(results, list)


# ---------------------------------------------------------------------------
# Tests: Citation Parsing
# ---------------------------------------------------------------------------


class TestCitationParsing:
    def test_parse_simple_citation(self):
        text = "Revenue was $5.2B [Doc: report_q1.pdf, p.2]."
        citations = _parse_citations(text)
        assert len(citations) == 1
        assert citations[0]["source"] == "report_q1.pdf"
        assert citations[0]["page"] == 2

    def test_parse_citation_without_page(self):
        text = "See [Doc: report.pdf] for details."
        citations = _parse_citations(text)
        assert len(citations) == 1
        assert citations[0]["source"] == "report.pdf"
        assert citations[0]["page"] is None

    def test_parse_multiple_citations(self):
        text = (
            "Revenue was $5.2B [Doc: q1.pdf, p.1] "
            "and grew to $5.5B [Doc: q2.pdf, p.3]."
        )
        citations = _parse_citations(text)
        assert len(citations) == 2

    def test_parse_deduplicates(self):
        text = (
            "Revenue [Doc: q1.pdf, p.1] was mentioned again [Doc: q1.pdf, p.1]."
        )
        citations = _parse_citations(text)
        assert len(citations) == 1

    def test_parse_no_citations(self):
        text = "There are no citations in this text."
        citations = _parse_citations(text)
        assert len(citations) == 0


# ---------------------------------------------------------------------------
# Tests: Chat Engine End-to-End
# ---------------------------------------------------------------------------


class TestChatEngine:
    @pytest.mark.asyncio
    async def test_chat_returns_response_with_citations(self, seeded_db):
        llm_responses = [
            '{"query_type": "fact_lookup"}',  # classifier
            "Revenue was $5.2 billion in Q1 [Doc: report_q1_2024.pdf, p.1] "
            "and $5.5 billion in Q2 [Doc: report_q2_2024.pdf, p.1].",  # response
        ]
        call_count = 0

        async def mock_llm_side_effect(**kwargs):
            nonlocal call_count
            result = llm_responses[call_count]
            call_count += 1
            return result

        mock_emb = _make_embedding_response(dim=16)

        with patch("backend.chat.classifier.llm_call", new_callable=AsyncMock) as mock_classify, \
             patch("backend.chat.engine.llm_call", new_callable=AsyncMock) as mock_response, \
             patch("backend.chat.semantic_retrieval.litellm") as mock_litellm:
            mock_classify.return_value = '{"query_type": "fact_lookup"}'
            mock_response.return_value = (
                "Revenue was $5.2 billion in Q1 [Doc: report_q1_2024.pdf, p.1] "
                "and $5.5 billion in Q2 [Doc: report_q2_2024.pdf, p.1]."
            )
            mock_litellm.aembedding = AsyncMock(return_value=mock_emb)

            result = await chat("What was the revenue?", session_id="test-1", db=seeded_db)

            assert "response" in result
            assert "citations" in result
            assert "query_type" in result
            assert "suggested_queries" in result
            assert result["query_type"] == "fact_lookup"
            assert len(result["citations"]) >= 2
            assert "report_q1_2024.pdf" in result["response"]

    @pytest.mark.asyncio
    async def test_chat_session_history_maintained(self, seeded_db):
        mock_emb = _make_embedding_response(dim=16)

        with patch("backend.chat.classifier.llm_call", new_callable=AsyncMock) as mock_classify, \
             patch("backend.chat.engine.llm_call", new_callable=AsyncMock) as mock_response, \
             patch("backend.chat.semantic_retrieval.litellm") as mock_litellm:
            mock_classify.return_value = '{"query_type": "fact_lookup"}'
            mock_response.return_value = "Answer 1 [Doc: report_q1_2024.pdf, p.1]"
            mock_litellm.aembedding = AsyncMock(return_value=mock_emb)

            await chat("First question", session_id="test-session", db=seeded_db)

            assert "test-session" in _chat_sessions
            assert len(_chat_sessions["test-session"]) == 2  # user + assistant
            assert _chat_sessions["test-session"][0]["role"] == "user"
            assert _chat_sessions["test-session"][0]["content"] == "First question"
            assert _chat_sessions["test-session"][1]["role"] == "assistant"

            mock_response.return_value = "Answer 2 [Doc: report_q2_2024.pdf, p.1]"

            await chat("Second question", session_id="test-session", db=seeded_db)

            assert len(_chat_sessions["test-session"]) == 4  # 2 exchanges

    @pytest.mark.asyncio
    async def test_chat_suggested_queries(self, seeded_db):
        mock_emb = _make_embedding_response(dim=16)

        with patch("backend.chat.classifier.llm_call", new_callable=AsyncMock) as mock_classify, \
             patch("backend.chat.engine.llm_call", new_callable=AsyncMock) as mock_response, \
             patch("backend.chat.semantic_retrieval.litellm") as mock_litellm:
            mock_classify.return_value = '{"query_type": "open_ended"}'
            mock_response.return_value = "Here is a summary."
            mock_litellm.aembedding = AsyncMock(return_value=mock_emb)

            result = await chat("Summarize everything", session_id="test-2", db=seeded_db)

            assert isinstance(result["suggested_queries"], list)
            assert len(result["suggested_queries"]) <= 3

    @pytest.mark.asyncio
    async def test_chat_different_sessions_isolated(self, seeded_db):
        mock_emb = _make_embedding_response(dim=16)

        with patch("backend.chat.classifier.llm_call", new_callable=AsyncMock) as mock_classify, \
             patch("backend.chat.engine.llm_call", new_callable=AsyncMock) as mock_response, \
             patch("backend.chat.semantic_retrieval.litellm") as mock_litellm:
            mock_classify.return_value = '{"query_type": "fact_lookup"}'
            mock_response.return_value = "Answer [Doc: report_q1_2024.pdf, p.1]"
            mock_litellm.aembedding = AsyncMock(return_value=mock_emb)

            await chat("Q1", session_id="session-a", db=seeded_db)
            await chat("Q2", session_id="session-b", db=seeded_db)

            assert len(_chat_sessions["session-a"]) == 2
            assert len(_chat_sessions["session-b"]) == 2
            assert _chat_sessions["session-a"][0]["content"] == "Q1"
            assert _chat_sessions["session-b"][0]["content"] == "Q2"

    @pytest.mark.asyncio
    async def test_chat_entity_query_type(self, seeded_db):
        mock_emb = _make_embedding_response(dim=16)

        with patch("backend.chat.classifier.llm_call", new_callable=AsyncMock) as mock_classify, \
             patch("backend.chat.engine.llm_call", new_callable=AsyncMock) as mock_response, \
             patch("backend.chat.semantic_retrieval.litellm") as mock_litellm:
            mock_classify.return_value = '{"query_type": "entity_query"}'
            mock_response.return_value = "John Smith appears in both reports [Doc: report_q1_2024.pdf, p.1]."
            mock_litellm.aembedding = AsyncMock(return_value=mock_emb)

            result = await chat("What reports mention John Smith?", session_id="test-ent", db=seeded_db)
            assert result["query_type"] == "entity_query"
            assert "John Smith" in result["response"]


# ---------------------------------------------------------------------------
# Tests: Re-exports
# ---------------------------------------------------------------------------


class TestChatInit:
    def test_reexport(self):
        from backend.chat import chat as imported_chat

        assert callable(imported_chat)
        assert imported_chat is chat
