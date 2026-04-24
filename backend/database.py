from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db() -> None:
    """Create all tables and FTS5 virtual table for document_chunks."""
    # Import models so they register with Base.metadata
    import backend.models  # noqa: F401

    Base.metadata.create_all(bind=engine)

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
