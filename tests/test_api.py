"""Tests for the FastAPI API layer.

Uses an in-memory SQLite database and mocks backend services where needed.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.models import (
    Contradiction,
    Document,
    Entity,
    EntityResolution,
    Extraction,
    TaxonomySchema,
    TaxonomyTemplate,
)
from main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_engine():
    """Create an in-memory SQLite engine with check_same_thread=False."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        conn.execute(
            text(
                "CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts "
                "USING fts5(chunk_text)"
            )
        )
        conn.commit()

    return engine


@pytest.fixture
def db_session(db_engine):
    """Create a session bound to the in-memory engine."""
    TestingSession = sessionmaker(bind=db_engine)
    session = TestingSession()
    yield session
    session.close()


@pytest.fixture
def client(db_engine):
    """FastAPI TestClient with the DB dependency overridden."""
    TestingSession = sessionmaker(bind=db_engine)

    def _override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _seed_database(session):
    """Seed the database with sample data."""
    doc1 = Document(
        id="doc-1",
        original_filename="report_q1.pdf",
        storage_path="data/originals/report_q1.pdf",
        file_type="pdf",
        page_count=10,
        uploaded_at=datetime(2024, 3, 31, tzinfo=timezone.utc),
    )
    doc2 = Document(
        id="doc-2",
        original_filename="report_q2.pdf",
        storage_path="data/originals/report_q2.pdf",
        file_type="pdf",
        page_count=12,
        uploaded_at=datetime(2024, 6, 30, tzinfo=timezone.utc),
    )
    session.add_all([doc1, doc2])
    session.commit()

    taxonomy = TaxonomySchema(
        id="tax-1",
        corpus_id="corpus-1",
        dimensions=[
            {"name": "revenue", "description": "Total revenue", "expected_type": "currency"},
            {"name": "ceo", "description": "CEO name", "expected_type": "entity"},
        ],
        doc_type="Quarterly Report",
        company_context="Acme Corp",
        created_at=datetime(2024, 7, 1, tzinfo=timezone.utc),
    )
    session.add(taxonomy)
    session.commit()

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
    session.add_all([ext1, ext2, ext3])
    session.commit()

    entity = Entity(
        id="ent-1",
        canonical_name="John Smith",
        entity_type="person",
        aliases=["John Smith", "J. Smith"],
    )
    session.add(entity)
    session.commit()

    er1 = EntityResolution(
        id="er-1",
        entity_id="ent-1",
        original_value="John Smith",
        document_id="doc-1",
        confidence=0.99,
        needs_review=False,
    )
    er2 = EntityResolution(
        id="er-2",
        entity_id="ent-1",
        original_value="J. Smith",
        document_id="doc-2",
        confidence=0.75,
        needs_review=True,
    )
    session.add_all([er1, er2])
    session.commit()

    contradiction = Contradiction(
        id="contra-1",
        dimension_name="revenue",
        doc_a_id="doc-1",
        doc_b_id="doc-2",
        value_a="$5.2 billion",
        value_b="$5.5 billion",
        doc_a_date=datetime(2024, 3, 31, tzinfo=timezone.utc),
        doc_b_date=datetime(2024, 6, 30, tzinfo=timezone.utc),
        resolution_status="unresolved",
    )
    session.add(contradiction)
    session.commit()


@pytest.fixture
def seeded_client(db_engine, db_session):
    """TestClient that uses the seeded database."""
    _seed_database(db_session)

    TestingSession = sessionmaker(bind=db_engine)

    def _override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: POST /api/upload
# ---------------------------------------------------------------------------


class TestUpload:
    def test_upload_pdf(self, client):
        """Upload a single PDF file with mocked ingestion."""
        mock_doc = MagicMock()
        mock_doc.id = "new-doc-id"
        mock_doc.original_filename = "test.pdf"

        with patch("backend.api.routes.store_and_ingest", return_value=(mock_doc, MagicMock())):
            resp = client.post(
                "/api/upload",
                files=[("files", ("test.pdf", b"fake-pdf-content", "application/pdf"))],
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "document_ids" in data
        assert "new-doc-id" in data["document_ids"]
        assert len(data["uploaded"]) == 1
        assert data["uploaded"][0]["id"] == "new-doc-id"
        assert data["uploaded"][0]["filename"] == "test.pdf"

    def test_upload_multiple_files(self, client):
        """Upload multiple files at once."""
        call_count = 0

        def mock_store(filename, content):
            nonlocal call_count
            call_count += 1
            doc = MagicMock()
            doc.id = f"doc-{call_count}"
            doc.original_filename = filename
            return doc, MagicMock()

        with patch("backend.api.routes.store_and_ingest", side_effect=mock_store):
            resp = client.post(
                "/api/upload",
                files=[
                    ("files", ("a.pdf", b"pdf-content", "application/pdf")),
                    ("files", ("b.docx", b"docx-content", "application/vnd.openxmlformats")),
                    ("files", ("c.xlsx", b"xlsx-content", "application/vnd.openxmlformats")),
                ],
            )

        assert resp.status_code == 200
        assert len(resp.json()["uploaded"]) == 3

    def test_upload_unsupported_extension(self, client):
        """Reject files with unsupported extensions."""
        resp = client.post(
            "/api/upload",
            files=[("files", ("data.pptx", b"dummy", "application/vnd.ms-powerpoint"))],
        )
        assert resp.status_code == 400
        assert "Unsupported" in resp.json()["detail"]

    def test_upload_mixed_valid_invalid(self, client):
        """Valid files are accepted even when some are invalid."""
        mock_doc = MagicMock()
        mock_doc.id = "good-doc"
        mock_doc.original_filename = "good.pdf"

        with patch("backend.api.routes.store_and_ingest", return_value=(mock_doc, MagicMock())):
            resp = client.post(
                "/api/upload",
                files=[
                    ("files", ("good.pdf", b"pdf", "application/pdf")),
                    ("files", ("bad.txt", b"text", "text/plain")),
                ],
            )

        assert resp.status_code == 200
        assert len(resp.json()["uploaded"]) == 1
        assert resp.json()["uploaded"][0]["filename"] == "good.pdf"

    def test_upload_ingestion_failure(self, client):
        """Ingestion errors for individual files are handled gracefully."""
        with patch("backend.api.routes.store_and_ingest", side_effect=RuntimeError("disk full")):
            resp = client.post(
                "/api/upload",
                files=[("files", ("test.pdf", b"pdf", "application/pdf"))],
            )

        assert resp.status_code == 400
        assert "disk full" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Tests: POST /api/process
# ---------------------------------------------------------------------------


class TestProcess:
    def test_process_triggers_background_task(self, client):
        """Process endpoint should return immediately with 'processing' status."""
        resp = client.post(
            "/api/process",
            json={"document_ids": ["doc-1", "doc-2"], "company_context": "Acme"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert "corpus_id" in data
        uuid.UUID(data["corpus_id"])

    def test_process_empty_ids_rejected(self, client):
        """Empty document_ids list should be rejected."""
        resp = client.post("/api/process", json={"document_ids": []})
        assert resp.status_code == 400

    def test_process_no_company_context(self, client):
        """company_context is optional."""
        resp = client.post("/api/process", json={"document_ids": ["doc-1"]})
        assert resp.status_code == 200
        assert "message" in resp.json()


# ---------------------------------------------------------------------------
# Tests: GET /api/status
# ---------------------------------------------------------------------------


class TestStatus:
    def test_status_idle_when_no_pipeline(self, client):
        """Status returns idle when no pipeline has run."""
        with patch("backend.api.routes.pipeline_status", {}):
            resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "idle"
        assert data["current_step"] is None
        assert data["steps_completed"] == []

    def test_status_returns_latest(self, client):
        """Status returns the most recent pipeline status."""
        mock_status = {
            "run-1": {
                "step": 3,
                "description": "Extracting data...",
                "percentage": 55,
                "status": "running",
                "error": None,
            }
        }
        with patch("backend.api.routes.pipeline_status", mock_status):
            resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "running"
        assert data["current_step"] == "extraction"
        assert "type_detection" in data["steps_completed"]
        assert "taxonomy" in data["steps_completed"]
        assert data["error"] is None

    def test_status_with_error(self, client):
        """Status shows error information when pipeline fails."""
        mock_status = {
            "run-1": {
                "step": 2,
                "description": "Pipeline failed at step 2",
                "percentage": 25,
                "status": "error",
                "error": "RuntimeError: LLM API failed",
            }
        }
        with patch("backend.api.routes.pipeline_status", mock_status):
            resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "error"
        assert "RuntimeError" in data["error"]


# ---------------------------------------------------------------------------
# Tests: GET /api/documents
# ---------------------------------------------------------------------------


class TestDocuments:
    def test_list_documents(self, seeded_client):
        resp = seeded_client.get("/api/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        filenames = [d["original_filename"] for d in data]
        assert filenames[0] == "report_q2.pdf"
        assert filenames[1] == "report_q1.pdf"

    def test_list_documents_empty(self, client):
        resp = client.get("/api/documents")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_document_fields(self, seeded_client):
        resp = seeded_client.get("/api/documents")
        doc = resp.json()[0]
        assert "id" in doc
        assert "original_filename" in doc
        assert "file_type" in doc
        assert "page_count" in doc
        assert "uploaded_at" in doc


# ---------------------------------------------------------------------------
# Tests: GET /api/taxonomy
# ---------------------------------------------------------------------------


class TestTaxonomy:
    def test_get_taxonomy(self, seeded_client):
        resp = seeded_client.get("/api/taxonomy")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "tax-1"
        assert data["corpus_id"] == "corpus-1"
        assert len(data["dimensions"]) == 2
        assert data["doc_type"] == "Quarterly Report"
        assert data["company_context"] == "Acme Corp"

    def test_get_taxonomy_returns_null_when_none(self, client):
        resp = client.get("/api/taxonomy")
        assert resp.status_code == 200
        assert resp.json() is None


# ---------------------------------------------------------------------------
# Tests: GET /api/extractions
# ---------------------------------------------------------------------------


class TestExtractions:
    def test_get_all_extractions(self, seeded_client):
        resp = seeded_client.get("/api/extractions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

    def test_filter_by_document_id(self, seeded_client):
        resp = seeded_client.get("/api/extractions", params={"document_id": "doc-1"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert all(e["document_id"] == "doc-1" for e in data)

    def test_filter_by_dimension_name(self, seeded_client):
        resp = seeded_client.get("/api/extractions", params={"dimension_name": "revenue"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert all(e["dimension_name"] == "revenue" for e in data)

    def test_filter_combined(self, seeded_client):
        resp = seeded_client.get(
            "/api/extractions",
            params={"document_id": "doc-1", "dimension_name": "ceo"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["raw_value"] == "John Smith"

    def test_extraction_includes_filename(self, seeded_client):
        resp = seeded_client.get("/api/extractions")
        for ext in resp.json():
            assert ext["document_filename"] is not None

    def test_empty_extractions(self, client):
        resp = client.get("/api/extractions")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# Tests: GET /api/entities
# ---------------------------------------------------------------------------


class TestEntities:
    def test_get_entities(self, seeded_client):
        resp = seeded_client.get("/api/entities")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        entity = data[0]
        assert entity["canonical_name"] == "John Smith"
        assert entity["entity_type"] == "person"
        assert "John Smith" in entity["aliases"]
        assert "J. Smith" in entity["aliases"]

    def test_entity_needs_review_count(self, seeded_client):
        resp = seeded_client.get("/api/entities")
        entity = resp.json()[0]
        # er-2 has needs_review=True
        assert entity["needs_review_count"] == 1

    def test_empty_entities(self, client):
        resp = client.get("/api/entities")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# Tests: GET /api/contradictions
# ---------------------------------------------------------------------------


class TestContradictions:
    def test_get_contradictions(self, seeded_client):
        resp = seeded_client.get("/api/contradictions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        c = data[0]
        assert c["dimension_name"] == "revenue"
        assert c["value_a"] == "$5.2 billion"
        assert c["value_b"] == "$5.5 billion"
        assert c["resolution_status"] == "unresolved"

    def test_contradiction_includes_filenames(self, seeded_client):
        resp = seeded_client.get("/api/contradictions")
        c = resp.json()[0]
        assert c["doc_a_filename"] == "report_q1.pdf"
        assert c["doc_b_filename"] == "report_q2.pdf"

    def test_empty_contradictions(self, client):
        resp = client.get("/api/contradictions")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# Tests: PATCH /api/entities/{id}
# ---------------------------------------------------------------------------


class TestUpdateEntity:
    def test_update_canonical_name(self, seeded_client):
        resp = seeded_client.patch(
            "/api/entities/ent-1",
            json={"canonical_name": "Jonathan Smith"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["canonical_name"] == "Jonathan Smith"
        assert data["id"] == "ent-1"

    def test_update_entity_not_found(self, seeded_client):
        resp = seeded_client.patch(
            "/api/entities/nonexistent",
            json={"canonical_name": "Nobody"},
        )
        assert resp.status_code == 404

    def test_update_entity_persists(self, seeded_client):
        seeded_client.patch(
            "/api/entities/ent-1",
            json={"canonical_name": "Updated Name"},
        )
        resp = seeded_client.get("/api/entities")
        entity = resp.json()[0]
        assert entity["canonical_name"] == "Updated Name"


# ---------------------------------------------------------------------------
# Tests: PATCH /api/entity-resolutions/{id}
# ---------------------------------------------------------------------------


class TestUpdateResolution:
    def test_approve_resolution(self, seeded_client):
        resp = seeded_client.patch(
            "/api/entity-resolutions/er-2",
            json={"approved": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["needs_review"] is False

    def test_approve_with_override_value(self, seeded_client):
        resp = seeded_client.patch(
            "/api/entity-resolutions/er-2",
            json={"approved": True, "override_value": "Jonathan Smith"},
        )
        assert resp.status_code == 200
        assert resp.json()["needs_review"] is False

    def test_reject_resolution(self, seeded_client):
        """When approved=False, needs_review stays unchanged."""
        resp = seeded_client.patch(
            "/api/entity-resolutions/er-2",
            json={"approved": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["needs_review"] is True

    def test_resolution_not_found(self, seeded_client):
        resp = seeded_client.patch(
            "/api/entity-resolutions/nonexistent",
            json={"approved": True},
        )
        assert resp.status_code == 404

    def test_override_value_updates_extraction(self, seeded_client):
        """Override value should propagate to the linked extraction's resolved_value."""
        # er-1 links entity_id=ent-1, document_id=doc-1, original_value="John Smith"
        # ext-3 has document_id=doc-1, dimension_name=ceo, raw_value="John Smith"
        seeded_client.patch(
            "/api/entity-resolutions/er-1",
            json={"approved": True, "override_value": "Dr. John Smith"},
        )
        resp = seeded_client.get("/api/extractions", params={"document_id": "doc-1", "dimension_name": "ceo"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["resolved_value"] == "Dr. John Smith"


# ---------------------------------------------------------------------------
# Tests: POST /api/chat
# ---------------------------------------------------------------------------


class TestChat:
    def test_chat_endpoint(self, seeded_client):
        """Chat endpoint returns properly structured response."""
        mock_result = {
            "response": "Revenue was $5.2B [Doc: report_q1.pdf, p.1]",
            "citations": [{"type": "document", "source": "report_q1.pdf", "page": 1, "detail": "[Doc: report_q1.pdf, p.1]"}],
            "query_type": "fact_lookup",
            "suggested_queries": ["Show me all revenue data."],
        }

        with patch("backend.api.routes.chat", new_callable=AsyncMock, return_value=mock_result):
            resp = seeded_client.post(
                "/api/chat",
                json={"message": "What was the revenue?"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert "citations" in data
        assert "query_type" in data
        assert "suggested_queries" in data
        assert data["query_type"] == "fact_lookup"

    def test_chat_with_session_id(self, seeded_client):
        """Session ID is passed through to the chat engine."""
        mock_result = {
            "response": "Answer",
            "citations": [],
            "query_type": "open_ended",
            "suggested_queries": [],
        }

        with patch("backend.api.routes.chat", new_callable=AsyncMock, return_value=mock_result) as mock_chat:
            resp = seeded_client.post(
                "/api/chat",
                json={"message": "Hello", "session_id": "my-session-123"},
            )

        assert resp.status_code == 200
        mock_chat.assert_called_once()
        call_kwargs = mock_chat.call_args.kwargs
        assert call_kwargs["query"] == "Hello"
        assert call_kwargs["session_id"] == "my-session-123"

    def test_chat_without_session_id_uses_default(self, seeded_client):
        """Omitting session_id defaults to 'default'."""
        mock_result = {
            "response": "Answer",
            "citations": [],
            "query_type": "open_ended",
            "suggested_queries": [],
        }

        with patch("backend.api.routes.chat", new_callable=AsyncMock, return_value=mock_result) as mock_chat:
            resp = seeded_client.post(
                "/api/chat",
                json={"message": "Hi"},
            )

        assert resp.status_code == 200
        mock_chat.assert_called_once()
        call_kwargs = mock_chat.call_args.kwargs
        assert call_kwargs["query"] == "Hi"
        assert call_kwargs["session_id"] == "default"


# ---------------------------------------------------------------------------
# Tests: Router inclusion in app
# ---------------------------------------------------------------------------


class TestAppSetup:
    def test_router_included(self):
        """All expected routes are registered on the app."""
        routes = [r.path for r in app.routes]
        expected = [
            "/api/upload",
            "/api/process",
            "/api/status",
            "/api/documents",
            "/api/taxonomy",
            "/api/extractions",
            "/api/entities",
            "/api/contradictions",
            "/api/entities/{entity_id}",
            "/api/entity-resolutions/{resolution_id}",
            "/api/taxonomy-templates",
            "/api/taxonomy-templates/{template_id}",
            "/api/chat",
        ]
        for path in expected:
            assert path in routes, f"Missing route: {path}"


# ---------------------------------------------------------------------------
# Tests: Taxonomy Templates CRUD
# ---------------------------------------------------------------------------


class TestTaxonomyTemplates:
    def test_list_empty(self, client):
        resp = client.get("/api/taxonomy-templates")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_template(self, client):
        resp = client.post(
            "/api/taxonomy-templates",
            json={
                "label": "Investor Reports",
                "description": "Quarterly/annual investor reports with financial data",
                "dimensions": [
                    {"name": "revenue", "description": "Total revenue", "expected_type": "currency"},
                    {"name": "net_income", "description": "Net income", "expected_type": "currency"},
                ],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["label"] == "Investor Reports"
        assert len(data["dimensions"]) == 2
        assert data["id"] is not None

    def test_create_and_list(self, client):
        client.post(
            "/api/taxonomy-templates",
            json={
                "label": "Template A",
                "description": "Desc A",
                "dimensions": [],
            },
        )
        client.post(
            "/api/taxonomy-templates",
            json={
                "label": "Template B",
                "description": "Desc B",
                "dimensions": [{"name": "field1", "description": "F1", "expected_type": "text"}],
            },
        )
        resp = client.get("/api/taxonomy-templates")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_update_template(self, client):
        create_resp = client.post(
            "/api/taxonomy-templates",
            json={
                "label": "Original",
                "description": "Original desc",
                "dimensions": [],
            },
        )
        template_id = create_resp.json()["id"]

        resp = client.put(
            f"/api/taxonomy-templates/{template_id}",
            json={
                "label": "Updated",
                "description": "Updated desc",
                "dimensions": [{"name": "new_field", "description": "New", "expected_type": "number"}],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["label"] == "Updated"
        assert data["description"] == "Updated desc"
        assert len(data["dimensions"]) == 1

    def test_update_partial(self, client):
        create_resp = client.post(
            "/api/taxonomy-templates",
            json={"label": "Test", "description": "Test desc", "dimensions": []},
        )
        template_id = create_resp.json()["id"]

        resp = client.put(
            f"/api/taxonomy-templates/{template_id}",
            json={"label": "Only Label Updated"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["label"] == "Only Label Updated"
        assert data["description"] == "Test desc"

    def test_update_not_found(self, client):
        resp = client.put(
            "/api/taxonomy-templates/nonexistent",
            json={"label": "Nope"},
        )
        assert resp.status_code == 404

    def test_delete_template(self, client):
        create_resp = client.post(
            "/api/taxonomy-templates",
            json={"label": "To Delete", "description": "Will be removed", "dimensions": []},
        )
        template_id = create_resp.json()["id"]

        resp = client.delete(f"/api/taxonomy-templates/{template_id}")
        assert resp.status_code == 204

        list_resp = client.get("/api/taxonomy-templates")
        assert len(list_resp.json()) == 0

    def test_delete_not_found(self, client):
        resp = client.delete("/api/taxonomy-templates/nonexistent")
        assert resp.status_code == 404
