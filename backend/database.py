from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.config import get_settings

engine = create_engine(
    get_settings().database_url,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db() -> None:
    """Create all tables and FTS5 virtual table for document_chunks."""
    # Import models so they register with Base.metadata
    import backend.models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Migrate: add report_date column if missing (create_all won't alter existing tables)
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(documents)")).fetchall()}
        if "report_date" not in cols:
            conn.execute(text("ALTER TABLE documents ADD COLUMN report_date DATETIME"))
            conn.commit()
        if "source_text" not in cols:
            conn.execute(text("ALTER TABLE documents ADD COLUMN source_text TEXT"))
            conn.commit()
        if "primary_entity_id" not in cols:
            conn.execute(text("ALTER TABLE documents ADD COLUMN primary_entity_id TEXT REFERENCES entities(id)"))
            conn.commit()

        contra_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(contradictions)")).fetchall()}
        if contra_cols and "reason" not in contra_cols:
            conn.execute(text("ALTER TABLE contradictions ADD COLUMN reason TEXT"))
            conn.commit()

    # Create FTS5 virtual table for full-text search on document_chunks
    with engine.connect() as conn:
        conn.execute(
            text(
                "CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts "
                "USING fts5(chunk_text, content='document_chunks', content_rowid='rowid')"
            )
        )
        conn.commit()


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
