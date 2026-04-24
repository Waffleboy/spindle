"""Tests for the 5-step LLM processing pipeline.

All LLM calls are mocked — no real API calls are made.
Uses an in-memory SQLite database for isolation.
"""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch



import numpy as np
import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.ingestion.common import IngestedDocument
from backend.models import (
    Contradiction,
    Document,
    DocumentChunk,
    Entity,
    EntityResolution,
    Extraction,
    TaxonomySchema,
)
from backend.pipeline.chunking import chunk_text
from backend.pipeline.llm import parse_json_response


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    """Create an in-memory SQLite database session for testing."""
    engine = create_engine("sqlite:///:memory:")

    # Enable WAL and foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)

    # Create FTS5 virtual table
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
def sample_documents():
    """Create sample IngestedDocument objects for testing."""
    doc1 = IngestedDocument(
        original_filename="report_q1_2024.pdf",
        storage_path="data/originals/report_q1_2024.pdf",
        file_type="pdf",
        pages=[],
        text="Acme Corporation Q1 2024 Quarterly Report. "
             "Revenue was $5.2 billion, up 12% year-over-year. "
             "Net income reached $800 million. CEO John Smith announced "
             "expansion into European markets. The company operates in "
             "the technology sector and is headquartered in San Francisco. "
             + " ".join(["Additional context for testing."] * 50),
        metadata={},
        page_count=10,
    )
    doc2 = IngestedDocument(
        original_filename="report_q2_2024.pdf",
        storage_path="data/originals/report_q2_2024.pdf",
        file_type="pdf",
        pages=[],
        text="Acme Corp Q2 2024 Quarterly Report. "
             "Revenue was $5.5 billion, up 15% year-over-year. "
             "Net income reached $850 million. CEO John Smith announced "
             "acquisition of Beta Technologies. The company continues "
             "to grow its cloud services division. "
             + " ".join(["More context for testing."] * 50),
        metadata={},
        page_count=12,
    )
    return [doc1, doc2]


@pytest.fixture
def db_documents(db_session):
    """Create Document DB records for testing."""
    doc1 = Document(
        id=str(uuid.uuid4()),
        original_filename="report_q1_2024.pdf",
        storage_path="data/originals/report_q1_2024.pdf",
        file_type="pdf",
        page_count=10,
    )
    doc2 = Document(
        id=str(uuid.uuid4()),
        original_filename="report_q2_2024.pdf",
        storage_path="data/originals/report_q2_2024.pdf",
        file_type="pdf",
        page_count=12,
    )
    db_session.add_all([doc1, doc2])
    db_session.commit()
    return [doc1, doc2]


def _make_llm_response(content: str):
    """Create a mock litellm response object."""
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


def _make_embedding_response(texts: list[str], dim: int = 16):
    """Create a mock litellm embedding response."""
    response = MagicMock()
    data = []
    for i, _ in enumerate(texts):
        embedding_obj = {"embedding": np.random.randn(dim).tolist()}
        data.append(embedding_obj)
    response.data = data
    return response


# ---------------------------------------------------------------------------
# Tests: chunking.py
# ---------------------------------------------------------------------------

class TestChunkText:
    def test_basic_chunking(self):
        text_input = " ".join([f"word{i}" for i in range(1000)])
        chunks = chunk_text(text_input, chunk_size=500, overlap=100)
        assert len(chunks) >= 2
        assert chunks[0]["chunk_index"] == 0
        assert chunks[1]["chunk_index"] == 1

    def test_chunk_structure(self):
        text_input = " ".join(["hello"] * 600)
        chunks = chunk_text(text_input, chunk_size=500, overlap=100)
        for chunk in chunks:
            assert "text" in chunk
            assert "chunk_index" in chunk
            assert "approx_pages" in chunk
            assert isinstance(chunk["approx_pages"], list)

    def test_small_text_single_chunk(self):
        text_input = "This is a short text with only a few words."
        chunks = chunk_text(text_input, chunk_size=500, overlap=100)
        assert len(chunks) == 1
        assert chunks[0]["text"] == text_input
        assert chunks[0]["chunk_index"] == 0

    def test_empty_text(self):
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_overlap_works(self):
        words = [f"w{i}" for i in range(20)]
        text_input = " ".join(words)
        chunks = chunk_text(text_input, chunk_size=10, overlap=3)
        # The second chunk should start 7 words in (10 - 3)
        if len(chunks) > 1:
            second_words = chunks[1]["text"].split()
            first_words = chunks[0]["text"].split()
            # Check overlap: last 3 words of first chunk appear at start of second
            assert first_words[-3:] == second_words[:3]

    def test_exact_chunk_size(self):
        words = [f"w{i}" for i in range(500)]
        text_input = " ".join(words)
        chunks = chunk_text(text_input, chunk_size=500, overlap=100)
        assert len(chunks) == 1

    def test_chunk_indices_sequential(self):
        text_input = " ".join(["word"] * 2000)
        chunks = chunk_text(text_input, chunk_size=300, overlap=50)
        for i, chunk in enumerate(chunks):
            assert chunk["chunk_index"] == i

    def test_all_words_covered(self):
        words = [f"w{i}" for i in range(150)]
        text_input = " ".join(words)
        chunks = chunk_text(text_input, chunk_size=50, overlap=10)
        # Every word should appear in at least one chunk
        all_chunk_words = set()
        for chunk in chunks:
            all_chunk_words.update(chunk["text"].split())
        for w in words:
            assert w in all_chunk_words


# ---------------------------------------------------------------------------
# Tests: llm.py (parse_json_response)
# ---------------------------------------------------------------------------

class TestParseJsonResponse:
    def test_clean_json_object(self):
        result = parse_json_response('{"key": "value", "num": 42}')
        assert result == {"key": "value", "num": 42}

    def test_clean_json_array(self):
        result = parse_json_response('[{"name": "test"}, {"name": "test2"}]')
        assert len(result) == 2

    def test_markdown_wrapped_json(self):
        text = '```json\n{"key": "value"}\n```'
        result = parse_json_response(text)
        assert result == {"key": "value"}

    def test_markdown_wrapped_no_language(self):
        text = '```\n{"key": "value"}\n```'
        result = parse_json_response(text)
        assert result == {"key": "value"}

    def test_whitespace_padded(self):
        text = '  \n  {"key": "value"}  \n  '
        result = parse_json_response(text)
        assert result == {"key": "value"}

    def test_nested_json(self):
        text = '{"dimensions": [{"name": "revenue", "type": "currency"}]}'
        result = parse_json_response(text)
        assert "dimensions" in result
        assert len(result["dimensions"]) == 1

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_json_response("not json at all")

    def test_markdown_with_array(self):
        text = '```json\n[{"a": 1}, {"b": 2}]\n```'
        result = parse_json_response(text)
        assert isinstance(result, list)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Tests: step1_doc_type.py
# ---------------------------------------------------------------------------

class TestStep1DocType:
    @pytest.mark.asyncio
    async def test_detect_doc_type(self, db_session, sample_documents, db_documents):
        mock_response = _make_llm_response("Quarterly Investor Report for a Public Company")

        with patch("backend.pipeline.step1_doc_type.llm_call", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Quarterly Investor Report for a Public Company"

            from backend.pipeline.step1_doc_type import detect_doc_type

            doc_ids = [d.id for d in db_documents]
            result = await detect_doc_type(
                documents=sample_documents,
                document_ids=doc_ids,
                db=db_session,
            )

            assert result == "Quarterly Investor Report for a Public Company"
            mock_llm.assert_called_once()

            # Verify DB records were updated
            for doc_id in doc_ids:
                doc = db_session.query(Document).filter(Document.id == doc_id).first()
                assert doc.detected_doc_type == "Quarterly Investor Report for a Public Company"

    @pytest.mark.asyncio
    async def test_detect_doc_type_strips_quotes(self, db_session, sample_documents, db_documents):
        with patch("backend.pipeline.step1_doc_type.llm_call", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = '"Quarterly Report"'

            from backend.pipeline.step1_doc_type import detect_doc_type

            doc_ids = [d.id for d in db_documents]
            result = await detect_doc_type(
                documents=sample_documents,
                document_ids=doc_ids,
                db=db_session,
            )

            assert result == "Quarterly Report"


# ---------------------------------------------------------------------------
# Tests: step2_taxonomy.py
# ---------------------------------------------------------------------------

class TestStep2Taxonomy:
    @pytest.mark.asyncio
    async def test_generate_taxonomy(self, db_session, sample_documents):
        dimensions = [
            {"name": "revenue", "description": "Total revenue", "expected_type": "currency"},
            {"name": "net_income", "description": "Net income", "expected_type": "currency"},
            {"name": "ceo", "description": "Chief Executive Officer", "expected_type": "entity"},
            {"name": "reporting_period", "description": "Report period", "expected_type": "date_range"},
        ]
        llm_response = json.dumps({"dimensions": dimensions})

        with patch("backend.pipeline.step2_taxonomy.llm_call", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_response

            from backend.pipeline.step2_taxonomy import generate_taxonomy

            taxonomy = await generate_taxonomy(
                doc_type="Quarterly Report",
                documents=sample_documents,
                company_context="Acme Corporation, a tech company",
                db=db_session,
            )

            assert taxonomy.id is not None
            assert taxonomy.doc_type == "Quarterly Report"
            assert taxonomy.company_context == "Acme Corporation, a tech company"
            assert len(taxonomy.dimensions) == 4
            assert taxonomy.dimensions[0]["name"] == "revenue"
            mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_taxonomy_validates_types(self, db_session, sample_documents):
        dimensions = [
            {"name": "field1", "description": "Test", "expected_type": "invalid_type"},
            {"name": "field2", "description": "Test2"},  # missing expected_type
        ]
        llm_response = json.dumps(dimensions)

        with patch("backend.pipeline.step2_taxonomy.llm_call", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_response

            from backend.pipeline.step2_taxonomy import generate_taxonomy

            taxonomy = await generate_taxonomy(
                doc_type="Report",
                documents=sample_documents,
                db=db_session,
            )

            # Invalid type should be replaced with "text"
            assert taxonomy.dimensions[0]["expected_type"] == "text"
            # Missing type should default to "text"
            assert taxonomy.dimensions[1]["expected_type"] == "text"


# ---------------------------------------------------------------------------
# Tests: step3_extraction.py
# ---------------------------------------------------------------------------

class TestStep3Extraction:
    @pytest.mark.asyncio
    async def test_extract_document(self, db_session, sample_documents, db_documents):
        # Create a taxonomy first
        taxonomy = TaxonomySchema(
            corpus_id=str(uuid.uuid4()),
            dimensions=[
                {"name": "revenue", "description": "Revenue", "expected_type": "currency"},
                {"name": "ceo", "description": "CEO name", "expected_type": "entity"},
            ],
            doc_type="Quarterly Report",
        )
        db_session.add(taxonomy)
        db_session.commit()
        db_session.refresh(taxonomy)

        extraction_response = json.dumps({
            "revenue": {"value": "$5.2 billion", "confidence": 0.95, "source_pages": [1, 2]},
            "ceo": {"value": "John Smith", "confidence": 0.99, "source_pages": [1]},
        })

        fake_embedding = np.random.randn(16).tolist()
        embedding_response = _make_embedding_response(["dummy"] * 5, dim=16)

        with patch("backend.pipeline.step3_extraction.llm_call", new_callable=AsyncMock) as mock_llm, \
             patch("backend.pipeline.step3_extraction.litellm") as mock_litellm:
            mock_llm.return_value = extraction_response
            mock_litellm.aembedding = AsyncMock(return_value=embedding_response)

            from backend.pipeline.step3_extraction import extract_document

            extractions = await extract_document(
                document=sample_documents[0],
                document_id=db_documents[0].id,
                taxonomy=taxonomy,
                db=db_session,
            )

            assert len(extractions) == 2
            revenue_ext = next(e for e in extractions if e.dimension_name == "revenue")
            assert revenue_ext.raw_value == "$5.2 billion"
            assert revenue_ext.confidence == 0.95

            ceo_ext = next(e for e in extractions if e.dimension_name == "ceo")
            assert ceo_ext.raw_value == "John Smith"

            # Verify chunks were created
            chunks = db_session.query(DocumentChunk).filter(
                DocumentChunk.document_id == db_documents[0].id
            ).all()
            assert len(chunks) > 0
            assert all(c.embedding is not None for c in chunks)

    @pytest.mark.asyncio
    async def test_extract_document_with_images(self, db_session, db_documents):
        """Test that PDFs with page images use multimodal LLM call."""
        from PIL import Image

        # Create a small test image
        img = Image.new("RGB", (100, 100), color="white")

        doc = IngestedDocument(
            original_filename="visual_report.pdf",
            storage_path="data/originals/visual_report.pdf",
            file_type="pdf",
            pages=[img],
            text="Some text content",
            metadata={},
            page_count=1,
        )

        taxonomy = TaxonomySchema(
            corpus_id=str(uuid.uuid4()),
            dimensions=[
                {"name": "title", "description": "Title", "expected_type": "text"},
            ],
            doc_type="Report",
        )
        db_session.add(taxonomy)
        db_session.commit()
        db_session.refresh(taxonomy)

        extraction_response = json.dumps({
            "title": {"value": "Visual Report", "confidence": 0.9, "source_pages": [1]},
        })
        embedding_response = _make_embedding_response(["dummy"], dim=16)

        with patch("backend.pipeline.step3_extraction.llm_call", new_callable=AsyncMock) as mock_llm, \
             patch("backend.pipeline.step3_extraction.litellm") as mock_litellm:
            mock_llm.return_value = extraction_response
            mock_litellm.aembedding = AsyncMock(return_value=embedding_response)

            from backend.pipeline.step3_extraction import extract_document

            extractions = await extract_document(
                document=doc,
                document_id=db_documents[0].id,
                taxonomy=taxonomy,
                db=db_session,
            )

            # Check that images were passed to llm_call
            call_kwargs = mock_llm.call_args
            assert call_kwargs.kwargs.get("images") is not None
            assert len(call_kwargs.kwargs["images"]) == 1

    @pytest.mark.asyncio
    async def test_extract_handles_missing_values(self, db_session, db_documents):
        """Test extraction when LLM returns null/missing values."""
        taxonomy = TaxonomySchema(
            corpus_id=str(uuid.uuid4()),
            dimensions=[
                {"name": "revenue", "description": "Revenue", "expected_type": "currency"},
                {"name": "missing_field", "description": "Not in doc", "expected_type": "text"},
            ],
            doc_type="Report",
        )
        db_session.add(taxonomy)
        db_session.commit()
        db_session.refresh(taxonomy)

        doc = IngestedDocument(
            original_filename="test.docx",
            storage_path="data/originals/test.docx",
            file_type="docx",
            pages=[],
            text="Revenue was $1M. " + " ".join(["filler"] * 50),
            metadata={},
            page_count=1,
        )

        extraction_response = json.dumps({
            "revenue": {"value": "$1M", "confidence": 0.8, "source_pages": [1]},
            "missing_field": {"value": None, "confidence": 0.0, "source_pages": None},
        })
        embedding_response = _make_embedding_response(["dummy"], dim=16)

        with patch("backend.pipeline.step3_extraction.llm_call", new_callable=AsyncMock) as mock_llm, \
             patch("backend.pipeline.step3_extraction.litellm") as mock_litellm:
            mock_llm.return_value = extraction_response
            mock_litellm.aembedding = AsyncMock(return_value=embedding_response)

            from backend.pipeline.step3_extraction import extract_document

            extractions = await extract_document(
                document=doc,
                document_id=db_documents[0].id,
                taxonomy=taxonomy,
                db=db_session,
            )

            missing = next(e for e in extractions if e.dimension_name == "missing_field")
            assert missing.raw_value == ""
            assert missing.confidence == 0.0


# ---------------------------------------------------------------------------
# Tests: step4_entities.py
# ---------------------------------------------------------------------------

class TestStep4Entities:
    @pytest.mark.asyncio
    async def test_resolve_entities(self, db_session, db_documents):
        # Create taxonomy with entity dimensions
        taxonomy = TaxonomySchema(
            corpus_id=str(uuid.uuid4()),
            dimensions=[
                {"name": "ceo", "description": "CEO", "expected_type": "entity"},
                {"name": "revenue", "description": "Revenue", "expected_type": "currency"},
            ],
            doc_type="Report",
        )
        db_session.add(taxonomy)
        db_session.commit()
        db_session.refresh(taxonomy)

        # Create extraction records
        ext1 = Extraction(
            document_id=db_documents[0].id,
            taxonomy_schema_id=taxonomy.id,
            dimension_name="ceo",
            raw_value="John Smith",
            confidence=0.95,
        )
        ext2 = Extraction(
            document_id=db_documents[1].id,
            taxonomy_schema_id=taxonomy.id,
            dimension_name="ceo",
            raw_value="J. Smith",
            confidence=0.90,
        )
        ext3 = Extraction(
            document_id=db_documents[0].id,
            taxonomy_schema_id=taxonomy.id,
            dimension_name="revenue",
            raw_value="$5.2B",
            confidence=0.95,
        )
        db_session.add_all([ext1, ext2, ext3])
        db_session.commit()

        entity_groups = [
            {
                "canonical_name": "John Smith",
                "entity_type": "person",
                "aliases": [
                    {"value": "John Smith", "confidence": 0.99},
                    {"value": "J. Smith", "confidence": 0.85},
                ],
            }
        ]
        llm_response = json.dumps({"entities": entity_groups})

        with patch("backend.pipeline.step4_entities.llm_call", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_response

            from backend.pipeline.step4_entities import resolve_entities

            entities = await resolve_entities(taxonomy=taxonomy, db=db_session)

            assert len(entities) == 1
            assert entities[0].canonical_name == "John Smith"
            assert entities[0].entity_type == "person"
            assert "John Smith" in entities[0].aliases
            assert "J. Smith" in entities[0].aliases

            # Check EntityResolution records
            resolutions = db_session.query(EntityResolution).all()
            assert len(resolutions) == 2

            # Check resolved_value on extractions
            db_session.refresh(ext1)
            db_session.refresh(ext2)
            assert ext1.resolved_value == "John Smith"
            assert ext2.resolved_value == "John Smith"

    @pytest.mark.asyncio
    async def test_resolve_entities_no_entity_dims(self, db_session):
        taxonomy = TaxonomySchema(
            corpus_id=str(uuid.uuid4()),
            dimensions=[
                {"name": "revenue", "description": "Revenue", "expected_type": "currency"},
            ],
            doc_type="Report",
        )
        db_session.add(taxonomy)
        db_session.commit()
        db_session.refresh(taxonomy)

        from backend.pipeline.step4_entities import resolve_entities

        entities = await resolve_entities(taxonomy=taxonomy, db=db_session)
        assert entities == []

    @pytest.mark.asyncio
    async def test_resolve_entities_flags_low_confidence(self, db_session, db_documents):
        taxonomy = TaxonomySchema(
            corpus_id=str(uuid.uuid4()),
            dimensions=[
                {"name": "company", "description": "Company", "expected_type": "entity"},
            ],
            doc_type="Report",
        )
        db_session.add(taxonomy)
        db_session.commit()
        db_session.refresh(taxonomy)

        ext = Extraction(
            document_id=db_documents[0].id,
            taxonomy_schema_id=taxonomy.id,
            dimension_name="company",
            raw_value="Acme Corp",
            confidence=0.9,
        )
        db_session.add(ext)
        db_session.commit()

        entity_groups = [
            {
                "canonical_name": "Acme Corporation",
                "entity_type": "company",
                "aliases": [
                    {"value": "Acme Corp", "confidence": 0.7},
                ],
            }
        ]
        llm_response = json.dumps({"entities": entity_groups})

        with patch("backend.pipeline.step4_entities.llm_call", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_response

            from backend.pipeline.step4_entities import resolve_entities

            entities = await resolve_entities(taxonomy=taxonomy, db=db_session)

            resolutions = db_session.query(EntityResolution).all()
            assert len(resolutions) == 1
            assert resolutions[0].needs_review is True


# ---------------------------------------------------------------------------
# Tests: step5_contradictions.py
# ---------------------------------------------------------------------------

class TestStep5Contradictions:
    @pytest.mark.asyncio
    async def test_detect_contradictions(self, db_session, db_documents):
        taxonomy = TaxonomySchema(
            corpus_id=str(uuid.uuid4()),
            dimensions=[
                {"name": "revenue", "description": "Revenue", "expected_type": "currency"},
            ],
            doc_type="Report",
        )
        db_session.add(taxonomy)
        db_session.commit()
        db_session.refresh(taxonomy)

        ext1 = Extraction(
            document_id=db_documents[0].id,
            taxonomy_schema_id=taxonomy.id,
            dimension_name="revenue",
            raw_value="$5.2 billion",
            confidence=0.95,
        )
        ext2 = Extraction(
            document_id=db_documents[1].id,
            taxonomy_schema_id=taxonomy.id,
            dimension_name="revenue",
            raw_value="$4.8 billion",
            confidence=0.90,
        )
        db_session.add_all([ext1, ext2])
        db_session.commit()

        contradictions_data = [
            {
                "entity_name": "Unknown",
                "dimension_name": "revenue",
                "doc_a_value": "$5.2 billion",
                "doc_b_value": "$4.8 billion",
                "doc_a_id": db_documents[0].id,
                "doc_b_id": db_documents[1].id,
            }
        ]
        llm_response = json.dumps({"contradictions": contradictions_data})

        with patch("backend.pipeline.step5_contradictions.llm_call", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_response

            from backend.pipeline.step5_contradictions import detect_contradictions

            contradictions = await detect_contradictions(taxonomy=taxonomy, db=db_session)

            assert len(contradictions) == 1
            assert contradictions[0].dimension_name == "revenue"
            assert contradictions[0].value_a == "$5.2 billion"
            assert contradictions[0].value_b == "$4.8 billion"
            assert contradictions[0].resolution_status == "unresolved"

    @pytest.mark.asyncio
    async def test_no_contradictions_found(self, db_session, db_documents):
        taxonomy = TaxonomySchema(
            corpus_id=str(uuid.uuid4()),
            dimensions=[
                {"name": "title", "description": "Title", "expected_type": "text"},
            ],
            doc_type="Report",
        )
        db_session.add(taxonomy)
        db_session.commit()
        db_session.refresh(taxonomy)

        ext1 = Extraction(
            document_id=db_documents[0].id,
            taxonomy_schema_id=taxonomy.id,
            dimension_name="title",
            raw_value="Q1 Report",
            confidence=0.95,
        )
        ext2 = Extraction(
            document_id=db_documents[1].id,
            taxonomy_schema_id=taxonomy.id,
            dimension_name="title",
            raw_value="Q2 Report",
            confidence=0.90,
        )
        db_session.add_all([ext1, ext2])
        db_session.commit()

        llm_response = json.dumps({"contradictions": []})

        with patch("backend.pipeline.step5_contradictions.llm_call", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_response

            from backend.pipeline.step5_contradictions import detect_contradictions

            contradictions = await detect_contradictions(taxonomy=taxonomy, db=db_session)
            assert contradictions == []

    @pytest.mark.asyncio
    async def test_no_extractions_returns_empty(self, db_session):
        taxonomy = TaxonomySchema(
            corpus_id=str(uuid.uuid4()),
            dimensions=[
                {"name": "revenue", "description": "Revenue", "expected_type": "currency"},
            ],
            doc_type="Report",
        )
        db_session.add(taxonomy)
        db_session.commit()
        db_session.refresh(taxonomy)

        from backend.pipeline.step5_contradictions import detect_contradictions

        contradictions = await detect_contradictions(taxonomy=taxonomy, db=db_session)
        assert contradictions == []


# ---------------------------------------------------------------------------
# Tests: orchestrator.py
# ---------------------------------------------------------------------------

class TestOrchestrator:
    @pytest.mark.asyncio
    async def test_run_pipeline_all_steps(self, db_session, sample_documents, db_documents):
        """Test that the orchestrator runs all 5 steps in order."""
        doc_ids = [d.id for d in db_documents]
        call_order = []

        async def mock_detect_doc_type(documents, document_ids, db):
            call_order.append("step1")
            return "Quarterly Report"

        taxonomy = TaxonomySchema(
            id=str(uuid.uuid4()),
            corpus_id=str(uuid.uuid4()),
            dimensions=[
                {"name": "revenue", "description": "Revenue", "expected_type": "currency"},
            ],
            doc_type="Quarterly Report",
        )

        async def mock_generate_taxonomy(doc_type, documents, corpus_id, company_context, matched_templates, db):
            call_order.append("step2")
            db.add(taxonomy)
            db.commit()
            db.refresh(taxonomy)
            return taxonomy

        async def mock_extract_document(document, document_id, taxonomy, db):
            call_order.append("step3")
            ext = Extraction(
                document_id=document_id,
                taxonomy_schema_id=taxonomy.id,
                dimension_name="revenue",
                raw_value="$5B",
                confidence=0.9,
            )
            db.add(ext)
            db.commit()
            return [ext]

        async def mock_resolve_entities(taxonomy, db):
            call_order.append("step4")
            return []

        async def mock_detect_contradictions(taxonomy, db):
            call_order.append("step5")
            return []

        async def mock_match_templates(doc_type, sample_text, db):
            return []

        with patch("backend.pipeline.orchestrator.detect_doc_type", side_effect=mock_detect_doc_type), \
             patch("backend.pipeline.orchestrator.match_templates", side_effect=mock_match_templates), \
             patch("backend.pipeline.orchestrator.generate_taxonomy", side_effect=mock_generate_taxonomy), \
             patch("backend.pipeline.orchestrator.extract_document", side_effect=mock_extract_document), \
             patch("backend.pipeline.orchestrator.resolve_entities", side_effect=mock_resolve_entities), \
             patch("backend.pipeline.orchestrator.detect_contradictions", side_effect=mock_detect_contradictions), \
             patch("backend.pipeline.orchestrator.get_ingester") as mock_ingester:

            # Mock the re-ingestion
            ingester_instance = MagicMock()
            ingester_instance.ingest.return_value = sample_documents[0]
            mock_ingester.return_value = ingester_instance

            from backend.pipeline.orchestrator import run_pipeline

            result = await run_pipeline(
                document_ids=doc_ids,
                company_context="Acme Corp",
                db=db_session,
            )

            assert result["status"] == "complete"
            assert result["percentage"] == 100
            # Steps 1,2,4,5 called once each; step 3 called once per document
            assert call_order == ["step1", "step2", "step3", "step3", "step4", "step5"]

    @pytest.mark.asyncio
    async def test_run_pipeline_no_documents(self, db_session):
        from backend.pipeline.orchestrator import run_pipeline

        result = await run_pipeline(
            document_ids=["nonexistent-id"],
            db=db_session,
        )
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_run_pipeline_handles_step_error(self, db_session, db_documents):
        doc_ids = [d.id for d in db_documents]

        async def mock_detect_doc_type(documents, document_ids, db):
            raise RuntimeError("LLM API error")

        with patch("backend.pipeline.orchestrator.detect_doc_type", side_effect=mock_detect_doc_type), \
             patch("backend.pipeline.orchestrator.match_templates", new_callable=AsyncMock, return_value=[]), \
             patch("backend.pipeline.orchestrator.get_ingester") as mock_ingester:

            ingester_instance = MagicMock()
            ingester_instance.ingest.return_value = IngestedDocument(
                original_filename="test.pdf",
                storage_path="test.pdf",
                file_type="pdf",
                pages=[],
                text="text",
                metadata={},
                page_count=1,
            )
            mock_ingester.return_value = ingester_instance

            from backend.pipeline.orchestrator import run_pipeline

            result = await run_pipeline(
                document_ids=doc_ids,
                db=db_session,
            )

            assert result["status"] == "error"
            assert "RuntimeError" in result["error"]

    @pytest.mark.asyncio
    async def test_pipeline_status_tracking(self, db_session, db_documents):
        """Test that pipeline_status is updated as steps progress."""
        doc_ids = [d.id for d in db_documents]

        from backend.pipeline.orchestrator import pipeline_status

        recorded_statuses = []

        original_update = None

        async def mock_detect_doc_type(documents, document_ids, db):
            # At this point, status should show step 1
            for status in pipeline_status.values():
                if status["step"] == 1:
                    recorded_statuses.append(status.copy())
            return "Report"

        taxonomy = TaxonomySchema(
            id=str(uuid.uuid4()),
            corpus_id=str(uuid.uuid4()),
            dimensions=[],
            doc_type="Report",
        )

        async def mock_generate_taxonomy(*args, **kwargs):
            db = kwargs["db"]
            db.add(taxonomy)
            db.commit()
            db.refresh(taxonomy)
            return taxonomy

        async def mock_extract(document, document_id, taxonomy, db):
            return []

        async def mock_resolve(taxonomy, db):
            return []

        async def mock_contradict(taxonomy, db):
            return []

        with patch("backend.pipeline.orchestrator.detect_doc_type", side_effect=mock_detect_doc_type), \
             patch("backend.pipeline.orchestrator.match_templates", new_callable=AsyncMock, return_value=[]), \
             patch("backend.pipeline.orchestrator.generate_taxonomy", side_effect=mock_generate_taxonomy), \
             patch("backend.pipeline.orchestrator.extract_document", side_effect=mock_extract), \
             patch("backend.pipeline.orchestrator.resolve_entities", side_effect=mock_resolve), \
             patch("backend.pipeline.orchestrator.detect_contradictions", side_effect=mock_contradict), \
             patch("backend.pipeline.orchestrator.get_ingester") as mock_ingester:

            ingester_instance = MagicMock()
            ingester_instance.ingest.return_value = IngestedDocument(
                original_filename="test.pdf", storage_path="test.pdf",
                file_type="pdf", pages=[], text="text", metadata={}, page_count=1,
            )
            mock_ingester.return_value = ingester_instance

            from backend.pipeline.orchestrator import run_pipeline

            result = await run_pipeline(document_ids=doc_ids, db=db_session)

            assert result["status"] == "complete"
            # We should have captured at least one status at step 1
            assert len(recorded_statuses) >= 1
            assert recorded_statuses[0]["step"] == 1


# ---------------------------------------------------------------------------
# Tests: __init__.py re-exports
# ---------------------------------------------------------------------------

class TestPipelineInit:
    def test_reexports(self):
        from backend.pipeline import pipeline_status, run_pipeline

        assert callable(run_pipeline)
        assert isinstance(pipeline_status, dict)
