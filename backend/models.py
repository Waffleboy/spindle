import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON, DateTime

from backend.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=_uuid)
    original_filename = Column(Text, nullable=False)
    storage_path = Column(Text, nullable=False)
    file_type = Column(Text, nullable=False)  # pdf, docx, xlsx
    source_text = Column(Text, nullable=True)  # pre-extracted text (e.g. CSV row splits)
    detected_doc_type = Column(Text, nullable=True)
    page_count = Column(Integer, nullable=True)
    report_date = Column(DateTime, nullable=True)
    primary_entity_id = Column(String, ForeignKey("entities.id"), nullable=True)
    uploaded_at = Column(DateTime, default=_utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    extractions = relationship("Extraction", back_populates="document", cascade="all, delete-orphan")
    entity_resolutions = relationship("EntityResolution", back_populates="document", cascade="all, delete-orphan")
    primary_entity = relationship("Entity", foreign_keys=[primary_entity_id])


class TaxonomySchema(Base):
    __tablename__ = "taxonomy_schema"

    id = Column(String, primary_key=True, default=_uuid)
    corpus_id = Column(String, nullable=False)
    dimensions = Column(JSON, nullable=False)  # list of {name, description, expected_type}
    doc_type = Column(Text, nullable=False)
    company_context = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    # Relationships
    extractions = relationship("Extraction", back_populates="taxonomy_schema")


class Extraction(Base):
    __tablename__ = "extractions"

    id = Column(String, primary_key=True, default=_uuid)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    taxonomy_schema_id = Column(String, ForeignKey("taxonomy_schema.id"), nullable=False)
    dimension_name = Column(Text, nullable=False)
    raw_value = Column(Text, nullable=False)
    resolved_value = Column(Text, nullable=True)
    source_pages = Column(JSON, nullable=True)
    confidence = Column(Float, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="extractions")
    taxonomy_schema = relationship("TaxonomySchema", back_populates="extractions")


class Entity(Base):
    __tablename__ = "entities"

    id = Column(String, primary_key=True, default=_uuid)
    canonical_name = Column(Text, nullable=False)
    entity_type = Column(Text, nullable=False)
    aliases = Column(JSON, nullable=False, default=list)  # list of strings

    # Relationships
    resolutions = relationship("EntityResolution", back_populates="entity", cascade="all, delete-orphan")
    contradictions = relationship("Contradiction", back_populates="entity")


class EntityResolution(Base):
    __tablename__ = "entity_resolutions"

    id = Column(String, primary_key=True, default=_uuid)
    entity_id = Column(String, ForeignKey("entities.id"), nullable=False)
    original_value = Column(Text, nullable=False)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    confidence = Column(Float, nullable=False)
    needs_review = Column(Boolean, default=False, nullable=False)

    # Relationships
    entity = relationship("Entity", back_populates="resolutions")
    document = relationship("Document", back_populates="entity_resolutions")


class Contradiction(Base):
    __tablename__ = "contradictions"

    id = Column(String, primary_key=True, default=_uuid)
    dimension_name = Column(Text, nullable=False)
    entity_id = Column(String, ForeignKey("entities.id"), nullable=True)
    doc_a_id = Column(String, ForeignKey("documents.id"), nullable=False)
    doc_b_id = Column(String, ForeignKey("documents.id"), nullable=False)
    value_a = Column(Text, nullable=False)
    value_b = Column(Text, nullable=False)
    doc_a_date = Column(DateTime, nullable=True)
    doc_b_date = Column(DateTime, nullable=True)
    reason = Column(Text, nullable=True)
    resolution_status = Column(Text, default="unresolved", nullable=False)

    # Relationships
    entity = relationship("Entity", back_populates="contradictions")
    doc_a = relationship("Document", foreign_keys=[doc_a_id])
    doc_b = relationship("Document", foreign_keys=[doc_b_id])


class TaxonomyTemplate(Base):
    __tablename__ = "taxonomy_templates"

    id = Column(String, primary_key=True, default=_uuid)
    label = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    dimensions = Column(JSON, nullable=False, default=list)  # list of {name, description, expected_type}
    created_at = Column(DateTime, default=_utcnow, nullable=False)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String, primary_key=True, default=_uuid)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    source_pages = Column(JSON, nullable=True)
    embedding = Column(LargeBinary, nullable=True)  # numpy array stored as bytes

    # Relationships
    document = relationship("Document", back_populates="chunks")
